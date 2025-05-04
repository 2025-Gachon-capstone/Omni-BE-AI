# train_link_pred_neomodel.py
import os, json, torch, torch.nn.functional as F
from torch import nn
from torch_geometric.data import HeteroData
from torch_geometric.loader import LinkNeighborLoader
from torch_geometric.nn import SAGEConv, HeteroConv
from neomodel import config as nconfig, db                         # ← 핵심
from src.app.config import config as app_cfg                       # ← 환경 변수 객체
from tqdm import tqdm

###############################################################################
# 0. Neo4j 연결 ----------------------------------------------------------------
host = app_cfg.NEO4J_HOST.split(':')[0] if ':' in str(app_cfg.NEO4J_HOST) else app_cfg.NEO4J_HOST
port = app_cfg.NEO4J_PORT if hasattr(app_cfg, 'NEO4J_PORT') else 7687
nconfig.DATABASE_URL = f"bolt://{app_cfg.NEO4J_USER}:{app_cfg.DB_PASSWORD}@{host}:{port}"

###############################################################################
# 1. 그래프 추출 ---------------------------------------------------------------
def cypher_df(query:str, params:dict=None):
    records, columns = db.cypher_query(query, params or {})
    import pandas as pd
    return pd.DataFrame(records, columns=columns)

def main():
    print("①  Member / Product 노드 로드...")
    df_user  = cypher_df("MATCH (m:Member)  RETURN id(m) AS nid, m.member_id  AS mid")
    df_prod  = cypher_df("MATCH (p:Product) RETURN id(p) AS nid, p.product_id AS pid")

    u_map = {nid:i for i,nid in enumerate(df_user.nid)}
    p_map = {nid:i for i,nid in enumerate(df_prod.nid, start=len(u_map))}
    u_inv = {row.mid:i for i,row in df_user.iterrows()}
    p_inv = {row.pid:i+len(u_map) for i,row in df_prod.iterrows()}

    print("②  eval_set='prior' 구매 관계 로드...")
    q_prior = """
    MATCH (m:Member)-[:ORDERED]->(:Order {eval_set:'prior'})
          -[:CONTAINS]->(p:Product)
    RETURN id(m) AS src, id(p) AS dst
    """
    rec, _ = db.cypher_query(q_prior)
    e_src, e_dst = [], []
    for r in rec:
        if r[0] in u_map and r[1] in p_map:
            e_src.append(u_map[r[0]])
            e_dst.append(p_map[r[1]])
    edge_index = torch.tensor([e_src, e_dst], dtype=torch.long)

    print("③  eval_set='train'  (라벨)  로드...")
    q_train = """
    MATCH (m:Member)-[:ORDERED]->(:Order {eval_set:'train'})
          -[:CONTAINS]->(p:Product)
    RETURN m.member_id AS mid, p.product_id AS pid
    """
    lbl_pos, _ = db.cypher_query(q_train)
    lbl_pairs = [(int(r[0]), int(r[1])) for r in lbl_pos]

    N_user   = len(u_map)
    N_prod   = len(p_map)
    EMB_DIM  = 32
    data = HeteroData()
    data['user'].num_nodes    = N_user
    data['product'].num_nodes = N_prod
    data['user','buys','product'].edge_index       = edge_index
    data['product','bought_by','user'].edge_index  = edge_index.flip(0)

    type_user    = torch.tensor([[1,0]]).repeat(N_user ,1)
    type_product = torch.tensor([[0,1]]).repeat(N_prod ,1)
    emb_user     = nn.Embedding(N_user , EMB_DIM, sparse=True)
    emb_product  = nn.Embedding(N_prod , EMB_DIM, sparse=True)
    data['user'].x    = torch.cat([type_user   , emb_user .weight], 1)
    data['product'].x = torch.cat([type_product, emb_product.weight],1)

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
    model = HetSAGE(in_dim=2+EMB_DIM, hid=64, out=64).to(device)

    loader = LinkNeighborLoader(
        data,
        num_neighbors=[25,10],
        batch_size=4096,
        edge_label_index=(('user','buys','product'), data['user','buys','product'].edge_index),
        edge_label=torch.ones(data['user','buys','product'].edge_index.size(1)),
        shuffle=True, neg_sampling_ratio=1.0)

    opt = torch.optim.Adam(model.parameters(), lr=0.002)
    model.train()
    for epoch in range(5):
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

if __name__ == "__main__":
    main()
