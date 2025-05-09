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
import numpy as np

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
    df_order = cypher_df("MATCH (o:Order) RETURN id(o) AS oid, o.eval_set AS eval_set")

    N_user = len(df_user)
    N_prod = len(df_prod)
    N_order = len(df_order)

    EMB_DIM = 32

    print(f"N_user: {N_user}, N_prod: {N_prod}, N_order: {N_order}")

    # 임의의 learnable embedding 할당 (featureless GNN)
    emb_user = nn.Embedding(N_user, EMB_DIM, sparse=True)
    emb_product = nn.Embedding(N_prod, EMB_DIM, sparse=True)
    emb_order = nn.Embedding(N_order, EMB_DIM, sparse=True)

    # HeteroData 객체 생성
    data = HeteroData()
    data['user'].num_nodes = N_user
    data['product'].num_nodes = N_prod
    data['order'].num_nodes = N_order

    data['user'].x = emb_user.weight
    data['product'].x = emb_product.weight
    data['order'].x = emb_order.weight

    # 노드 id 매핑
    u_inv = {row.mid: i for i, row in df_user.iterrows()}
    p_inv = {row.pid: i for i, row in df_prod.iterrows()}
    o_inv = {row.oid: i for i, row in df_order.iterrows()}

    print("② prior+test_prior 구매 이력(훈련 데이터) 로드...")
    # user-order edge
    q_user_order = """
    MATCH (m:Member)-[:ORDERED]->(o:Order)
    WHERE o.eval_set IN ['PRIOR', 'TRAIN', 'TEST_PRIOR', 'TEST_TRAIN']
    RETURN m.member_id AS mid, id(o) AS oid
    """
    user_order_raw, _ = db.cypher_query(q_user_order)
    e_user_order_src, e_user_order_dst = [], []
    for r in user_order_raw:
        if int(r[0]) in u_inv and int(r[1]) in o_inv:
            e_user_order_src.append(u_inv[int(r[0])])
            e_user_order_dst.append(o_inv[int(r[1])])
    data['user', 'ordered', 'order'].edge_index = torch.tensor([e_user_order_src, e_user_order_dst], dtype=torch.long)
    data['order', 'ordered_by', 'user'].edge_index = torch.tensor([e_user_order_dst, e_user_order_src], dtype=torch.long)

    # order-product edge
    q_order_product = """
    MATCH (o:Order)-[:CONTAINS]->(p:Product)
    WHERE o.eval_set IN ['PRIOR', 'TRAIN', 'TEST_PRIOR', 'TEST_TRAIN']
    RETURN id(o) AS oid, p.product_id AS pid
    """
    order_product_raw, _ = db.cypher_query(q_order_product)
    e_order_product_src, e_order_product_dst = [], []
    for r in order_product_raw:
        if int(r[0]) in o_inv and int(r[1]) in p_inv:
            e_order_product_src.append(o_inv[int(r[0])])
            e_order_product_dst.append(p_inv[int(r[1])])
    data['order', 'contains', 'product'].edge_index = torch.tensor([e_order_product_src, e_order_product_dst], dtype=torch.long)
    data['product', 'contained_in', 'order'].edge_index = torch.tensor([e_order_product_dst, e_order_product_src], dtype=torch.long)

    print("③ train+test 정답(라벨) 로드...")
    # user-product edge (label용)
    q_user_product = """
    MATCH (m:Member)-[:ORDERED]->(o:Order)-[:CONTAINS]->(p:Product)
    WHERE o.eval_set IN ['TRAIN', 'TEST_TRAIN']
    RETURN m.member_id AS mid, p.product_id AS pid
    """
    user_product_raw, _ = db.cypher_query(q_user_product)
    e_user_product_src, e_user_product_dst = [], []
    for r in user_product_raw:
        if int(r[0]) in u_inv and int(r[1]) in p_inv:
            e_user_product_src.append(u_inv[int(r[0])])
            e_user_product_dst.append(p_inv[int(r[1])])
        else:
            print('잘못된 user/product id:', r[0], r[1])
    data['user', 'buys', 'product'].edge_index = torch.tensor([e_user_product_src, e_user_product_dst], dtype=torch.long)
    data['product', 'bought_by', 'user'].edge_index = torch.tensor([e_user_product_dst, e_user_product_src], dtype=torch.long)

    print(f"user-order edge: {len(e_user_order_src)}")
    print(f"order-product edge: {len(e_order_product_src)}")
    print(f"user-product label edge: {len(e_user_product_src)}")

    # 기존 positive (user, product) 쌍
    pos_u = np.array(e_user_product_src)
    pos_p = np.array(e_user_product_dst)
    pos_label = np.ones(len(pos_u))

    # negative 샘플 생성
    neg_u, neg_p = [], []
    neg_per_user = 5  # user당 negative 샘플 개수 (조절 가능)
    for u in set(pos_u):
        bought = set(pos_p[pos_u == u])
        candidates = list(set(range(N_prod)) - bought)
        if len(candidates) >= neg_per_user:
            neg_p_sample = np.random.choice(candidates, size=neg_per_user, replace=False)
        elif len(candidates) > 0:
            neg_p_sample = np.random.choice(candidates, size=len(candidates), replace=False)
        else:
            continue
        neg_u.extend([u]*len(neg_p_sample))
        neg_p.extend(neg_p_sample)
    neg_label = np.zeros(len(neg_u))

    # positive + negative 합치기
    edge_label_index = np.concatenate([
        np.stack([pos_u, pos_p]),
        np.stack([neg_u, neg_p])
    ], axis=1)
    edge_label = np.concatenate([pos_label, neg_label])

    # torch로 변환
    edge_label_index = torch.tensor(edge_label_index, dtype=torch.long)
    edge_label = torch.tensor(edge_label, dtype=torch.float)

    # GNN 모델 정의
    class HetSAGE(nn.Module):
        def __init__(self, in_dim, hid, out):
            super().__init__()
            self.conv1 = HeteroConv({
                ('user','ordered','order'):   SAGEConv((-1,-1), hid),
                ('order','ordered_by','user'): SAGEConv((-1,-1), hid),
                ('order','contains','product'): SAGEConv((-1,-1), hid),
                ('product','contained_in','order'): SAGEConv((-1,-1), hid),
                ('user','buys','product'): SAGEConv((-1,-1), hid),
                ('product','bought_by','user'): SAGEConv((-1,-1), hid)},
                aggr='mean')
            self.conv2 = HeteroConv({
                ('user','ordered','order'):   SAGEConv((hid,hid), out),
                ('order','ordered_by','user'): SAGEConv((hid,hid), out),
                ('order','contains','product'): SAGEConv((hid,hid), out),
                ('product','contained_in','order'): SAGEConv((hid,hid), out),
                ('user','buys','product'): SAGEConv((hid,hid), out),
                ('product','bought_by','user'): SAGEConv((hid,hid), out)},
                aggr='mean')
        def forward(self, x_dict, edge_dict):
            h = {k:F.relu(v) for k,v in self.conv1(x_dict, edge_dict).items()}
            return self.conv2(h, edge_dict)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = HetSAGE(in_dim=EMB_DIM, hid=64, out=64).to(device)

    # LinkNeighborLoader로 학습 데이터 생성 (user-product edge 기준)
    loader = LinkNeighborLoader(
        data,
        num_neighbors=[25,10],
        batch_size=4096,
        edge_label_index=(('user','buys','product'), edge_label_index),
        edge_label=edge_label,
        shuffle=True
    )

    opt = torch.optim.Adam(model.parameters(), lr=0.001)
    model.train()
    best_precision = -1
    best_state = None
    best_emb_user = None
    best_emb_product = None
    best_emb_order = None
    best_u_inv = None
    best_p_inv = None
    best_o_inv = None
    for epoch in range(1000):
        tot=0
        for batch in loader:
            batch = batch.to(device)
            z = model(batch.x_dict, batch.edge_index_dict)
            src = z['user'][batch['user','buys','product'].edge_label_index[0]]
            dst = z['product'][batch['user','buys','product'].edge_label_index[1]]
            logit = (src*dst).sum(-1)
            loss  = F.binary_cross_entropy_with_logits(logit, batch['user','buys','product'].edge_label.float())
            opt.zero_grad(); loss.backward(); opt.step()
            tot += loss.item()
        # epoch별 loss 및 정확도 출력
        try:
            from src.app.services.PredictService import evaluate_top5_precision
            result = evaluate_top5_precision()
            mean_precision = result['mean_precision@5']
            print(f"[EPOCH {epoch+1}] loss: {tot/len(loader):.4f}  mean_precision@5: {mean_precision}")
            if mean_precision > best_precision:
                best_precision = mean_precision
                # best 모델 파라미터와 임베딩 저장
                model.eval()
                with torch.no_grad():
                    z = model(
                        {'user':data['user'].x.to(device),
                         'product':data['product'].x.to(device),
                         'order':data['order'].x.to(device)},
                        {k:v.to(device) for k,v in data.edge_index_dict.items()}
                    )
                    best_state = {k: v.cpu() for k, v in model.state_dict().items()}
                    best_emb_user = z['user'].cpu()
                    best_emb_product = z['product'].cpu()
                    best_emb_order = z['order'].cpu()
                    best_u_inv = u_inv.copy()
                    best_p_inv = p_inv.copy()
                    best_o_inv = o_inv.copy()
                model.train()
        except Exception as e:
            print(f"[EPOCH {epoch+1}] loss: {tot/len(loader):.4f}  (정확도 평가 오류: {e})")

    # 학습 종료 후 best 결과 저장
    if best_state is not None:
        torch.save({
            'model_state': best_state,
            'emb_user':    best_emb_user,
            'emb_product': best_emb_product,
            'emb_order':   best_emb_order,
            'u_inv':       best_u_inv,
            'p_inv':       best_p_inv,
            'o_inv':       best_o_inv
        }, "src/resources/models/trained_graphsage_lp.pt")
        print(f"✔  best 모델과 노드 임베딩이 src/resources/models/trained_graphsage_lp.pt 에 저장되었습니다. (mean_precision@5={best_precision})")
    else:
        print("❌ best 모델이 저장되지 않았습니다. (정확도 평가 오류)")

    model.eval()
    with torch.no_grad():
        print("==== [임베딩/노드/엣지 일관성 점검] ====")
        print("user embedding shape:", data['user'].x.shape)
        print("product embedding shape:", data['product'].x.shape)
        print("order embedding shape:", data['order'].x.shape)
        print("user num_nodes:", data['user'].num_nodes)
        print("product num_nodes:", data['product'].num_nodes)
        print("order num_nodes:", data['order'].num_nodes)
        print("user edge_index max:", data['user','ordered','order'].edge_index[0].max().item())
        print("order edge_index max (user->order):", data['user','ordered','order'].edge_index[1].max().item())
        print("order edge_index max (order->product):", data['order','contains','product'].edge_index[0].max().item())
        print("product edge_index max:", data['order','contains','product'].edge_index[1].max().item())
        order_max_idx = max(
            data['user','ordered','order'].edge_index[1].max().item(),
            data['order','contains','product'].edge_index[0].max().item()
        )
        print("order embedding shape[0]:", data['order'].x.shape[0], "order 관련 edge_index max:", order_max_idx)
        if data['order'].x.shape[0] <= order_max_idx:
            print("❌ order 임베딩 shape가 edge_index의 최대 인덱스보다 작음! (에러 발생 가능)")
        x_dict = {'user': data['user'].x, 'product': data['product'].x, 'order': data['order'].x}
        print("x_dict keys:", list(x_dict.keys()))
        z = model(
            {'user':data['user'].x.to(device),
             'product':data['product'].x.to(device),
             'order':data['order'].x.to(device)},
            {k:v.to(device) for k,v in data.edge_index_dict.items()}
        )

    # 전체 정확도 출력
    try:
        from src.app.services.PredictService import evaluate_top5_precision
        result = evaluate_top5_precision()
        print(f"전체 top-5 정확도(mean_precision@5): {result['mean_precision@5']}")
    except Exception as e:
        print(f"정확도 평가 중 오류 발생: {e}")

    print('u_inv 길이:', len(u_inv))
    print('p_inv 길이:', len(p_inv))
    print('user num_nodes:', data['user'].num_nodes)
    print('product num_nodes:', data['product'].num_nodes)
    print('user edge_index max:', data['user','buys','product'].edge_index[0].max().item())
    print('product edge_index max:', data['user','buys','product'].edge_index[1].max().item())
    print('user 인덱스 범위:', min(pos_u), max(pos_u))
    print('product 인덱스 범위:', min(pos_p), max(pos_p))
    print('negative user 인덱스 범위:', min(neg_u) if neg_u else None, max(neg_u) if neg_u else None)
    print('negative product 인덱스 범위:', min(neg_p) if neg_p else None, max(neg_p) if neg_p else None)
    print('N_user:', N_user, 'N_prod:', N_prod)

# [설명]
# HetSAGE(HeteroConv+SAGEConv)는 user/product처럼 노드 타입이 여러 개인 이종 그래프(heterogeneous graph)에 적합합니다.
# GraphSAGE는 노드 타입이 하나인 동종 그래프(homogeneous graph)에만 바로 쓸 수 있습니다.
# 만약 user/product를 하나의 노드 타입으로 취급(즉, 모든 노드가 같은 feature space를 공유)한다면 GraphSAGE를 쓸 수 있지만,
# 실제 추천 문제에서는 user와 product의 의미/feature가 다르기 때문에 HetSAGE 구조가 더 일반적입니다.