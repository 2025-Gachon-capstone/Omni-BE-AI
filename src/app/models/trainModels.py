import torch
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv
from torch_geometric.data import Data
import numpy as np
from neomodel import db
import os

class GraphSAGE(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super().__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        return x

def extract_graph_and_labels():
    # 1. 모든 노드 추출 및 인덱스 부여
    query_nodes = """
    MATCH (n) RETURN id(n) as node_id, labels(n)[0] as node_type, n.member_id, n.order_id, n.product_id
    """
    nodes, _ = db.cypher_query(query_nodes)
    node_id_map = {node[0]: idx for idx, node in enumerate(nodes)}
    num_nodes = len(nodes)
    node_types = [node[1] for node in nodes]
    member_ids = [node[2] for node in nodes]
    order_ids = [node[3] for node in nodes]
    product_ids = [node[4] for node in nodes]

    # 2. Product 노드만 추출하여 product_id <-> index 매핑
    product_id_list = [pid for t, pid in zip(node_types, product_ids) if t == 'Product']
    product_id_list = [int(pid) for pid in product_id_list if pid is not None]
    product_id_to_idx = {pid: idx for idx, pid in enumerate(sorted(set(product_id_list)))}
    num_products = len(product_id_to_idx)

    # 3. One-hot feature 생성 (노드 타입별)
    node_features = np.eye(num_nodes, dtype=np.float32)  # [num_nodes, num_nodes] one-hot
    node_features = torch.tensor(node_features, dtype=torch.float)

    # 4. 엣지 추출
    query_edges = """
    MATCH (n)-[r]->(m) RETURN id(n) as src, id(m) as dst
    """
    edges, _ = db.cypher_query(query_edges)
    edge_index = []
    for src, dst in edges:
        if src in node_id_map and dst in node_id_map:
            edge_index.append([node_id_map[src], node_id_map[dst]])
    edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous() if edge_index else torch.empty((2,0), dtype=torch.long)

    # 5. Order 노드별 라벨 생성 (multi-hot: 구매한 상품)
    # Order 노드 인덱스 찾기
    order_node_indices = [i for i, t in enumerate(node_types) if t == 'Order']
    labels = torch.zeros((len(order_node_indices), num_products), dtype=torch.float)
    for label_idx, node_idx in enumerate(order_node_indices):
        order_id = order_ids[node_idx]
        # 해당 주문이 구매한 상품 찾기
        query = """
        MATCH (o:Order)-[:CONTAINS]->(p:Product) WHERE o.order_id = $oid RETURN p.product_id
        """
        result, _ = db.cypher_query(query, {'oid': order_id})
        for row in result:
            pid = int(row[0])
            if pid in product_id_to_idx:
                labels[label_idx, product_id_to_idx[pid]] = 1.0

    return node_features, edge_index, labels, order_node_indices

def train_graphsage_model(node_features, edge_index, labels, order_node_indices, epochs=100, lr=0.01):
    in_channels = node_features.size(1)
    hidden_channels = 32
    out_channels = labels.size(1)  # 상품 개수
    model = GraphSAGE(in_channels, hidden_channels, out_channels)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = torch.nn.BCEWithLogitsLoss()  # multi-label

    data = Data(x=node_features, edge_index=edge_index)
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        out = model(data.x, data.edge_index)  # [num_nodes, num_products]
        # Order 노드에 대해서만 loss 계산
        out_orders = out[order_node_indices]
        loss = loss_fn(out_orders, labels)
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0:
            print(f'Epoch {epoch}, Loss: {loss.item()}')
    return model

if __name__ == "__main__":
    node_features, edge_index, labels, order_node_indices = extract_graph_and_labels()
    model = train_graphsage_model(node_features, edge_index, labels, order_node_indices)
    os.makedirs("./models", exist_ok=True)
    torch.save(model, "./models/trained_graphsage_model.pt")
