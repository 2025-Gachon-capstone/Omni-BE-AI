from collections import namedtuple
import heapq
from typing import Any, Dict, Iterable, List, Set

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

