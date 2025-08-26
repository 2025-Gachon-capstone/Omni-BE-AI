from collections import namedtuple
import heapq
import random
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import numpy as np
from ...models import Member as Neo4jMember
from neomodel import db

class Neo4jMemberRepository:

    @staticmethod
    def create_member_if_not_exist(member_id: str) -> Neo4jMember:
        member_id = str(member_id)  # Ensure member_id is a string
        member = Neo4jMember.nodes.get_or_none(member_id=member_id)
        if not member:
            member = Neo4jMember(member_id=member_id).save()
        return member
    
    @staticmethod
    def update_member_fields(member, field_dict: dict):
        """
        Member 노드의 일부 필드를 동적으로 업데이트하는 함수.
        
        Args:
            member (StructuredNode): 대상 Member 노드
            field_dict (dict): {필드명: 값} 형태의 딕셔너리

        Example:
            update_member_fields(member, {
                "metadata": "이 고객은 ...",
                "metadata_vector": [...],
            })
        """
        for field, value in field_dict.items():
            if hasattr(member, field):
                setattr(member, field, value)
        member.save()

    @staticmethod
    def find_buyers_by_product_ids(
        product_ids: list[str],
        top_k: int = 10,
        min_total_orders: int = 10,
    ) -> dict:
        try:
            # 1) 전체 최소 주문건수 확인 (최근 since_days 내)
            count_query = """
            MATCH (o:Order)-[:CONTAINS]->(p:Product)
            WHERE p.product_id IN $product_ids
            RETURN count(o) AS total_orders
            """
            params = {"product_ids": product_ids}
            results, _ = db.cypher_query(count_query, params)
            total_orders = results[0][0] if results else 0
            if total_orders < min_total_orders:
                return {
                    "total_orders": total_orders,
                    "by_product": []
                }

            # 2) 상품별 최근 구매자 Top-K (주문 수 기준)
            #    - o.paid_at 필드는 프로젝트 스키마에 맞게 조정하세요 (예: ordered_at 등)
            topk_query = """
            MATCH (m:Member)-[:ORDERED]->(o:Order)-[:CONTAINS]->(p:Product)
            WHERE p.product_id IN $product_ids
            WITH p.product_id AS pid, m, count(o) AS order_count
            ORDER BY pid, order_count DESC
            WITH pid, collect({m: m, order_count: order_count})[0..$top_k] AS top_members
            RETURN pid, top_members
            """
            params.update({"top_k": top_k})
            results, _ = db.cypher_query(topk_query, params)

            by_product = []
            for row in results:
                pid = row[0]
                top_members = row[1] or []
                members_pack = []
                for pack in top_members:
                    # pack = {"m": <node>, "order_count": int}
                    member_node = pack.get("m")
                    oc = pack.get("order_count", 0)
                    if member_node is None:
                        continue
                    members_pack.append({
                        "member": Neo4jMember.inflate(member_node),
                        "order_count": int(oc),
                    })
                by_product.append({
                    "product_id": pid,
                    "members": members_pack
                })

            return {
                "total_orders": int(total_orders),
                "by_product": by_product
            }

        except Exception as e:
            print(f"[Neo4jMemberRepository] 최근 구매자 조회 실패: {e}")
            return {"total_orders": 0, "by_product": []}

        
    
    @staticmethod
    def find_members_by_metadata_vector(metadata_vectors: list[list[float]], top_k: int = 5) -> list:
        """
        Neo4j 내장 벡터 인덱스를 활용하여 predict_order_list 유사도가 높은 회원 조회
        """
        try:
            # 여러 개의 벡터 중 첫 번째만 사용 (대표값으로)
            # 또는 평균을 내서 사용하는 방식도 가능
            query_vector = np.mean(metadata_vectors, axis=0).tolist()

            query = f"""
            CALL db.index.vector.queryNodes('metadataVectorIndex', $topK, $vector)
            YIELD node, score
            RETURN node
            """
            params = {
                "topK": top_k,
                "vector": query_vector
            }

            results, _ = db.cypher_query(query, params)
            return [Neo4jMember.inflate(row[0]) for row in results]

        except Exception as e:
            print(f"[Neo4jMemberRepository] 벡터 검색 실패: {e}")
            return []
        
    @staticmethod
    def find_members_by_target_member(target_member_vector: list[float], top_k: int = 5) -> list:
        """
        Neo4j 내장 벡터 인덱스를 활용하여 predict_order_list 유사도가 높은 회원 조회
        """
        try:

            query = f"""
            CALL db.index.vector.queryNodes('metadataVectorIndex', $topK, $vector)
            YIELD node, score
            RETURN node
            """
            params = {
                "topK": top_k,
                "vector": target_member_vector
            }

            results, _ = db.cypher_query(query, params)
            return [Neo4jMember.inflate(row[0]) for row in results]

        except Exception as e:
            print(f"[Neo4jMemberRepository] 벡터 검색 실패: {e}")
            return []

    @staticmethod
    def get_all_members():
        """
        Neo4j에 저장된 모든 멤버 노드를 반환합니다.
        """
        return Neo4jMember.nodes.all()
    
    @staticmethod
    def get_members_without_metadata(limit: int = 10, skip: int = 0):
        """
        metadata가 없거나 빈 문자열인 멤버를 페이징 방식으로 조회
        """
        try:
            query =f"""
            MATCH (m:Member)
            WHERE m.metadata IS NULL OR m.metadata = ''
            RETURN m
            SKIP $skip
            LIMIT $limit
            """
            results, _ = db.cypher_query(query, {
                "skip": skip,
                "limit": limit
            })
            print(f"no_metadata_member_count: {len(results)}")
            if results:
                return [Neo4jMember.inflate(row[0]) for row in results]
            return None
        except Exception as e:
            print(f"Error in get_members_without_metadata: {e}")
            return None
    
    @staticmethod
    def get_member_ids_missing_embedding(page_size: int = 5000) -> Iterable[List[str]]:
        """
        Member 중 node_embedding이 없거나 NULL인 member_id를 페이지 단위로 반환
        member_id는 StringProperty이므로 str로 다룹니다.
        """
        skip = 0
        q = """
        MATCH (m:Member)
        WHERE m.node_embedding IS NULL OR coalesce(m.node_embedding, []) = []
        WITH m.member_id AS member_id
        ORDER BY member_id
        SKIP $skip LIMIT $limit
        RETURN member_id
        """
        while True:
            rows, _ = db.cypher_query(q, {"skip": skip, "limit": page_size})
            ids = [r[0] for r in rows]  # member_id (str)
            if not ids:
                break
            yield ids
            skip += page_size

    @staticmethod
    def upsert_member_embeddings(rows: List[Dict[str, Any]]):
        """
        rows: [{member_id: str, vector: List[float]}]
        """
        if not rows:
            return
        q = """
        UNWIND $rows AS row
        MERGE (m:Member {member_id: row.member_id})
        SET m.node_embedding = row.vector,
            m.updatedAt = datetime()
        """
        db.cypher_query(q, {"rows": rows})
    
    @staticmethod
    def _knn_nodes(
        index_name: str,
        vec: List[float],
        k: int,
        exclude: Set[str],
        extra_where: Optional[str] = None,
        order_desc: bool = True,
    ) -> List[Tuple[str, float]]:
        where_clause = f"WHERE {extra_where}" if extra_where else ""
        order_dir = "DESC" if order_desc else "ASC"
        rows, _ = db.cypher_query(f"""
            CALL db.index.vector.queryNodes($index, $k, $vec)
            YIELD node, score
            {where_clause}
            WITH node, score
            WHERE node.node_embedding IS NOT NULL
              AND (NOT node.member_id IN $exclude)
            RETURN node.member_id AS id, score
            ORDER BY score {order_dir}
            LIMIT $k
        """, {"index": index_name, "k": k, "vec": vec, "exclude": list(exclude)})
        return [(r[0], float(r[1])) for r in rows]

    @staticmethod
    def _random_ids_by_count(
        n: int,
        exclude: Set[str],
        *,
        extra_where: Optional[str] = None,      # "m.status='ACTIVE'" 등
        require_embedding: bool = False,        # True면 임베딩 보유자만
        order_prop: str = "member_id",          # 인덱스 권장
    ) -> List[str]:
        if n <= 0:
            return []

        conds = []
        if require_embedding:
            conds.append("m.node_embedding IS NOT NULL")
        if extra_where:
            conds.append(extra_where)
        conds.append("NOT m.member_id IN $exclude")
        where_clause = f"WHERE {' AND '.join(conds)}"

        params = {"exclude": list(exclude)}

        # 1) 후보 수 카운트
        rows, _ = db.cypher_query(f"""
            MATCH (m:Member)
            {where_clause}
            RETURN count(m) AS cnt
        """, params)
        cnt = int(rows[0][0]) if rows else 0
        if cnt == 0:
            return []

        pick = min(n, cnt)
        offsets = sorted(random.sample(range(cnt), k=pick))

        # 2) 각 오프셋 → 실제 member_id 매핑
        # offsets: 0-based 유지
        rows, _ = db.cypher_query(f"""
            MATCH (m:Member)
            {where_clause}
            WITH m
            ORDER BY m.{order_prop}
            WITH collect(m.member_id) AS ids
            // 유효 범위를 벗어나는 오프셋은 걸러내고 해당 위치의 id를 뽑는다
            WITH [o IN $offs WHERE o < size(ids) | ids[o]] AS picked
            UNWIND picked AS id
            RETURN id
        """, {**params, "offs": offsets})

        return [r[0] for r in rows if r and r[0]]

    @staticmethod
    def allocate_coupons_mixed(
        *,
        centroid: np.ndarray,
        total: int,
        index_name: str = "member_node_embedding_vec",  # ← 너가 만든 인덱스명
        ratios: Tuple[float, float, float] = (0.2, 0.3, 0.5),  # det / prob / rand
        deterministic_top_oversample: int = 50,
        prob_oversample_factor: float = 5.0,
        temperature: float = 0.07,
        exclude_member_ids: Optional[Set[str]] = None,
        extra_where_knn: Optional[str] = None,      # 예: "node.status='ACTIVE'"
        extra_where_rand: Optional[str] = None,     # 예: "m.status='ACTIVE'"
        require_embedding_for_random: bool = False, # 랜덤 풀에 임베딩 필수?
    ) -> List[str]:
        if total <= 0:
            return []

        det_ratio, prob_ratio, rand_ratio = ratios
        # 정수 배분(잔여는 랜덤에 몰아주기)
        n_det = int(total * det_ratio)
        n_prob = int(total * prob_ratio)
        n_rand = total - n_det - n_prob

        exclude = set(exclude_member_ids or set())
        vec = np.asarray(centroid, dtype=np.float32).tolist()
        selected: List[str] = []

        # 1) 20% 확정: Top-K 바로
        k_det_fetch = max(n_det + deterministic_top_oversample, n_det)
        det_rows = Neo4jMemberRepository._knn_nodes(
            index_name=index_name,
            vec=vec,
            k=k_det_fetch,
            exclude=exclude,
            extra_where=extra_where_knn,
            order_desc=True,
        )
        det_ids = [mid for mid, _ in det_rows][:n_det]
        selected.extend(det_ids)
        exclude.update(det_ids)

        # --- DEBUG: Deterministic (Top-K) ---
        try:
            print(f"[benefit:deterministic] total={total} ratios={ratios} picked={len(det_ids)} ids(sample)={det_ids[:20]}")
        except Exception:
            pass

        # 2) 30% 확률: 상위 후보(과샘플) 받아서 softmax(score/T)로 샘플
        n_prob_rem = n_prob
        if n_prob_rem > 0:
            k_prob_fetch = max(int(n_prob_rem * prob_oversample_factor), n_prob_rem)
            prob_rows = Neo4jMemberRepository._knn_nodes(
                index_name=index_name,
                vec=vec,
                k=k_prob_fetch,
                exclude=exclude,
                extra_where=extra_where_knn,
                order_desc=True,
            )
            if prob_rows:
                cand_ids = np.array([mid for mid, _ in prob_rows], dtype=object)
                scores = np.array([s for _, s in prob_rows], dtype=np.float32)
                logits = scores / max(1e-6, temperature)
                logits -= float(np.max(logits))
                probs = np.exp(logits)
                probs_sum = probs.sum()
                probs = probs / probs_sum if probs_sum > 0 else np.ones_like(probs) / len(probs)

                pick = min(n_prob_rem, cand_ids.size)
                if pick > 0:
                    idx = np.random.choice(np.arange(cand_ids.size), size=pick, replace=False, p=probs)
                    prob_ids = cand_ids[idx].tolist()
                    selected.extend(prob_ids)
                    exclude.update(prob_ids)

                    # --- DEBUG: Probabilistic (Softmax sampling) ---
                    try:
                        id2p = {str(cid): float(p) for cid, p in zip(cand_ids.tolist(), probs.tolist())}
                        sel_dbg = [{"id": mid, "p": id2p.get(str(mid))} for mid in prob_ids]
                        print(f"[benefit:probabilistic] pool={cand_ids.size} picked={len(prob_ids)} sample={sel_dbg[:20]}")
                    except Exception:
                        pass
            # 후보가 모자라면 남는 수량은 랜덤으로 넘어가도록 두기

        # 3) 50% 랜덤(잔여 포함)
        n_selected = len(selected)
        n_rand_final = max(0, total - n_selected)
        if n_rand_final > 0:
            rand_ids = Neo4jMemberRepository._random_ids_by_count(
                n=n_rand_final,
                exclude=exclude,
                extra_where=extra_where_rand,
                require_embedding=require_embedding_for_random,
            )
            selected.extend(rand_ids)
            exclude.update(rand_ids)

            # --- DEBUG: Random (Count/Offset sampling) ---
            try:
                print(f"[benefit:random] picked={len(rand_ids)} ids(sample)={rand_ids[:20]}")
            except Exception:
                pass

        # 유니크 보장(혹시 모를 중복)
        selected = list(dict.fromkeys(selected))
        # 혹시 여전히 모자라면 마지막으로 k-NN 추가 호출로 보충
        if len(selected) < total:
            need = total - len(selected)
            more_rows = Neo4jMemberRepository._knn_nodes(
                index_name=index_name, vec=vec, k=need * 2, exclude=exclude,
                extra_where=extra_where_knn, order_desc=True
            )
            more_ids = [mid for mid, _ in more_rows][:need]
            selected.extend(more_ids)

        # --- DEBUG: Summary ---
        try:
            print(f"[benefit:summary] requested={total} selected_total={len(selected[:total])}")
        except Exception:
            pass

        return selected[:total]
