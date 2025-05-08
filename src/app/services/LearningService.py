# neo4j의 모든 Member, order 노드를 읽어와 벡터화된 값만 학습에 적용
# 학습 대상에서 metadata_vector는 제외 

import os, json, torch, torch.nn.functional as F
from torch import nn
from torch_geometric.data import HeteroData
from torch_geometric.loader import LinkNeighborLoader
from torch_geometric.nn import SAGEConv, HeteroConv
from neomodel import config as neomodel, db
from src.app.config import config as app_cfg
from tqdm import tqdm
import pandas as pd
import random

###############################################################################
# 0. Neo4j 연결 ----------------------------------------------------------------
host = app_cfg.NEO4J_HOST
port = app_cfg.NEO4J_PORT
neomodel.DATABASE_URL = f'bolt://{app_cfg.NEO4J_USER}:{app_cfg.DB_PASSWORD}@{host}:{port}'
###############################################################################
# 1. 그래프 추출 ---------------------------------------------------------------
def cypher_df(query:str, params:dict=None):
    records, columns = db.cypher_query(query, params or {})
    return pd.DataFrame(records, columns=columns)

def main():
    print("① 노드 개수 로드...")
    df_user = cypher_df("MATCH (m:Member) RETURN id(m) AS nid, m.member_id AS mid")
    df_prod = cypher_df("MATCH (p:Product) RETURN id(p) AS nid, p.product_id AS pid")

    N_user = len(df_user)
    N_prod = len(df_prod)
    EMB_DIM = 32

    print(f"N_user: {N_user}, N_prod: {N_prod}")

    # 임의의 learnable embedding 할당 (featureless GNN)
    emb_user = nn.Embedding(N_user, EMB_DIM, sparse=True)
    emb_product = nn.Embedding(N_prod, EMB_DIM, sparse=True)

    # HeteroData 객체 생성
    data = HeteroData()
    data['user'].num_nodes = N_user
    data['product'].num_nodes = N_prod
    data['user'].x = emb_user.weight
    data['product'].x = emb_product.weight

    # 엣지 생성
    u_inv = {row.mid: i for i, row in df_user.iterrows()}
    p_inv = {row.pid: i for i, row in df_prod.iterrows()}

    print("② prior+test_prior 구매 이력(훈련 데이터) 로드...")
    q_prior = """
    MATCH (m:Member)-[:ORDERED]->(o:Order)-[:CONTAINS]->(p:Product)
    WHERE o.eval_set IN ['PRIOR', 'TEST_PRIOR']
    RETURN m.member_id AS mid, p.product_id AS pid
    """
    prior_pairs_raw, _ = db.cypher_query(q_prior)
    e_src, e_dst = [], []
    for r in prior_pairs_raw:
        if int(r[0]) in u_inv and int(r[1]) in p_inv:
            e_src.append(u_inv[int(r[0])])
            e_dst.append(p_inv[int(r[1])])
    edge_index = torch.tensor([e_src, e_dst], dtype=torch.long)
    data['user', 'buys', 'product'].edge_index = edge_index
    data['product', 'bought_by', 'user'].edge_index = edge_index.flip(0)

    print("③ train 구매 이력(라벨) 로드...")
    q_train = """
    MATCH (m:Member)-[:ORDERED]->(:Order {eval_set:'TRAIN'})-[:CONTAINS]->(p:Product)
    RETURN m.member_id AS mid, p.product_id AS pid
    """
    train_pairs_raw, _ = db.cypher_query(q_train)
    lbl_pairs = [(u_inv[int(r[0])], p_inv[int(r[1])]) for r in train_pairs_raw if int(r[0]) in u_inv and int(r[1]) in p_inv]

    print(f"edge_index shape: {edge_index.shape}")
    print(f"train label pairs: {len(lbl_pairs)}")

    # GNN 모델 정의
    class HetSAGE(nn.Module):
        def __init__(self, in_dim, hid, out):
            super().__init__()
            self.conv1 = HeteroConv({
                ('user','buys','product'):   SAGEConv((-1,-1), hid),
                ('product','bought_by','user'): SAGEConv((-1,-1), hid)},
                aggr='mean')
            self.conv2 = HeteroConv({
                ('user','buys','product'):   SAGEConv((hid,hid), out),
                ('product','bought_by','user'): SAGEConv((hid,hid), out)},
                aggr='mean')
        def forward(self, x_dict, edge_dict):
            h = {k:F.relu(v) for k,v in self.conv1(x_dict, edge_dict).items()}
            return self.conv2(h, edge_dict)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = HetSAGE(in_dim=EMB_DIM, hid=64, out=64).to(device)

    # LinkNeighborLoader로 학습 데이터 생성
    loader = LinkNeighborLoader(
        data,
        num_neighbors=[25,10],
        batch_size=4096,
        edge_label_index=(('user','buys','product'), data['user','buys','product'].edge_index),
        edge_label=torch.ones(data['user','buys','product'].edge_index.size(1)),
        shuffle=True, neg_sampling_ratio=1.0)

    print(f"LinkNeighborLoader batch 수: {len(loader)}")

    opt = torch.optim.Adam(model.parameters(), lr=0.002)
    model.train()
    for epoch in range(100):
        tot=0
        for batch in loader:
            batch = batch.to(device)
            z = model(batch.x_dict, batch.edge_index_dict)
            src = z['user'   ][batch['user','buys','product'].edge_label_index[0]]
            dst = z['product'][batch['user','buys','product'].edge_label_index[1]]
            logit = (src*dst).sum(-1)
            loss  = F.binary_cross_entropy_with_logits(logit,
                    batch['user','buys','product'].edge_label.float())
            opt.zero_grad(); loss.backward(); opt.step()
            tot += loss.item()
        print(f"epoch {epoch+1}  loss {tot/len(loader):.4f}")

    model.eval()
    with torch.no_grad():
        z = model(
            {'user':data['user'].x.to(device),
             'product':data['product'].x.to(device)},
            {k:v.to(device) for k,v in data.edge_index_dict.items()}
        )
    torch.save({
        'model_state': model.state_dict(),
        'emb_user':    z['user'].cpu(),
        'emb_product': z['product'].cpu(),
        'u_inv':       u_inv,
        'p_inv':       p_inv
    }, "src/resources/models/trained_graphsage_lp.pt")
    print("✔  모델과 노드 임베딩이 src/resources/models/trained_graphsage_lp.pt 에 저장되었습니다.")

    # 전체 정확도 출력
    try:
        from src.app.services.PredictService import evaluate_top5_precision
        result = evaluate_top5_precision()
        print(f"전체 top-5 정확도(mean_precision@5): {result['mean_precision@5']}")
    except Exception as e:
        print(f"정확도 평가 중 오류 발생: {e}")