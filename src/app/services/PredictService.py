import torch
from src.app.services.LearningService import cypher_df

def predict_next_purchase_for_test_users():
    """
    link prediction 방식으로 사용자의 과거 구매 내역을 입력으로 받아,
    저장된 GraphSAGE 모델로 다음 구매 내역(상위 5개 상품)을 예측합니다.
    """
    # 1. 저장된 모델 및 임베딩 불러오기
    ckpt = torch.load("src/resources/models/trained_graphsage_lp.pt")
    user_emb = ckpt['emb_user']    # [num_users, emb_dim]
    prod_emb = ckpt['emb_product'] # [num_products, emb_dim]
    u_inv = ckpt['u_inv']          # {member_id: user_idx}
    p_inv = ckpt['p_inv']          # {product_id: prod_idx}

    # 2. eval_set='TEST'인 Order의 Member 리스트 추출
    df_test = cypher_df("""
        MATCH (m:Member)-[:ORDERED]->(o:Order {eval_set:'TEST'})
        RETURN DISTINCT m.member_id AS mid
    """)
    print("테스트 대상 사용자 수:", len(df_test))

    # 3. 각 테스트 Member별로 추천
    results = {}
    for _, row in df_test.iterrows():
        member_id = int(row.mid)
        if member_id not in u_inv:
            print(f"[SKIP] u_inv에 없는 member_id: {member_id}")
            continue
        user_idx = u_inv[member_id]

        # 4. 이미 구매한 상품(과거 prior/train/test) 제외
        bought_df = cypher_df(f"""
            MATCH (m:Member {{member_id: {member_id}}})-[:ORDERED]->(o:Order)
            WHERE o.eval_set IN ['PRIOR', 'TRAIN', 'TEST']
            MATCH (o)-[:CONTAINS]->(p:Product)
            RETURN DISTINCT p.product_id AS pid
        """)
        bought_pids = set(int(pid) for pid in bought_df['pid'].tolist() if pid in p_inv)

        # 5. 추천 점수 계산 (내적)
        scores = (user_emb[user_idx] @ prod_emb.T).cpu()
        # 이미 구매한 상품은 -inf로 마스킹
        mask = torch.ones(prod_emb.size(0), dtype=torch.bool)
        for pid in bought_pids:
            mask[p_inv[pid]] = False
        scores_masked = scores.clone()
        scores_masked[~mask] = float('-inf')

        # 6. 상위 5개 상품 추천
        top5_idx = torch.topk(scores_masked, 5).indices.tolist()
        # product_id로 변환
        inv_p_inv = {v: k for k, v in p_inv.items()}
        top5_pids = [inv_p_inv[idx] for idx in top5_idx]
        print(f"member_id={member_id} 추천 상품 5개: {top5_pids}")
        results[member_id] = top5_pids
    return results

def evaluate_top5_precision():
    """
    eval_set='TEST_PRIOR'만 입력으로 사용,
    eval_set='TEST_TRAIN'을 정답으로 하여 top-5 추천 정확도(precision@5) 평가
    결과를 dict로 반환
    """
    ckpt = torch.load("src/resources/models/trained_graphsage_lp.pt")
    user_emb = ckpt['emb_user']
    prod_emb = ckpt['emb_product']
    u_inv = ckpt['u_inv']
    p_inv = ckpt['p_inv']

    df_test = cypher_df("""
        MATCH (m:Member)-[:ORDERED]->(o:Order {eval_set:'TEST_PRIOR'})
        RETURN DISTINCT m.member_id AS mid
    """)
    print("테스트 대상 사용자 수:", len(df_test))

    total = 0
    hit = 0
    per_user = []
    for _, row in df_test.iterrows():
        member_id = int(row.mid)
        if member_id not in u_inv:
            print(f"[SKIP] u_inv에 없는 member_id: {member_id}")
            continue
        user_idx = u_inv[member_id]

        bought_df = cypher_df(f"""
            MATCH (m:Member {{member_id: {member_id}}})-[:ORDERED]->(o:Order)
            WHERE o.eval_set IN ['PRIOR', 'TRAIN', 'TEST_PRIOR']
            MATCH (o)-[:CONTAINS]->(p:Product)
            RETURN DISTINCT p.product_id AS pid
        """)
        bought_pids = set(int(pid) for pid in bought_df['pid'].tolist() if pid in p_inv)

        scores = (user_emb[user_idx] @ prod_emb.T).cpu()
        mask = torch.ones(prod_emb.size(0), dtype=torch.bool)
        for pid in bought_pids:
            mask[p_inv[pid]] = False
        scores_masked = scores.clone()
        scores_masked[~mask] = float('-inf')

        top5_idx = torch.topk(scores_masked, 5).indices.tolist()
        inv_p_inv = {v: k for k, v in p_inv.items()}
        top5_pids = [inv_p_inv[idx] for idx in top5_idx]

        gt_df = cypher_df(f"""
            MATCH (m:Member {{member_id: {member_id}}})-[:ORDERED]->(o:Order {{eval_set:'TEST_TRAIN'}})
            MATCH (o)-[:CONTAINS]->(p:Product)
            RETURN DISTINCT p.product_id AS pid
        """)
        gt_pids = set(int(pid) for pid in gt_df['pid'].tolist() if pid in p_inv)
        if not gt_pids:
            continue

        hit_count = len(set(top5_pids) & gt_pids)
        precision = hit_count / 5
        per_user.append({
            "member_id": member_id,
            "precision@5": precision,
            "hit": hit_count,
            "gt_count": len(gt_pids),
            "top5": top5_pids,
            "gt": list(gt_pids)
        })
        total += 1
        hit += precision

    result = {
        "total_users": total,
        "mean_precision@5": (hit/total if total > 0 else 0),
        "per_user": per_user
    }
    return result

