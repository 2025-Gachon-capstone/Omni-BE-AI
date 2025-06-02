<<<<<<< HEAD
from typing import List

import numpy as np
from ...models import Member as Neo4jMember
from ...utils.neo4j import safe_connect
=======
from collections import namedtuple
import heapq

import numpy as np
from ...models import Member as Neo4jMember
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
from neomodel import db

class Neo4jMemberRepository:

    @staticmethod
<<<<<<< HEAD
    def create_member_if_not_exist(member_id: int) -> Neo4jMember:
=======
    def create_member_if_not_exist(member_id: str) -> Neo4jMember:
        member_id = str(member_id)  # Ensure member_id is a string
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
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

<<<<<<< HEAD
    @staticmethod
    def find_members_by_predict_order(predict_vectors: list[list[float]], top_k: int = 5) -> list:
        """
        Neo4j 내장 벡터 인덱스를 활용하여 predict_order_list 유사도가 높은 회원 조회
        """
        try:
            # 여러 개의 벡터 중 첫 번째만 사용 (대표값으로)
            # 또는 평균을 내서 사용하는 방식도 가능
            query_vector = np.mean(predict_vectors, axis=0).tolist()

            query = f"""
            CALL db.index.vector.queryNodes('memberPredictOrderListIndex', $topK, $vector)
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
=======
    
    @staticmethod
    def find_members_by_predict_order(product_ids: list[str], top_k: int = 5, batch_size: int = 100) -> dict:
        """
        match_count 상/중/하 그룹을 실시간 유지하며 유사 회원 탐색
        """
        ScoredMember = namedtuple("ScoredMember", ["score", "member_id", "metadata"])
        MATCH_THRESHOLD = 2  # 유의미하다고 간주할 최소 유사도

        offset = 0
        high_heap = []  # min-heap → 낮은 점수 제거
        low_heap = []   # max-heap → 높은 점수 제거 (음수 사용)

        while True:
            query = """
            MATCH (m:Member)
            WHERE m.predict_order_list IS NOT NULL
            WITH m,
                size([p IN $product_ids WHERE p IN m.predict_order_list]) AS match_count
            WHERE match_count > 0
            RETURN m.member_id AS member_id,
                m.metadata AS metadata,
                m.predict_order_list AS predict_order_list,
                match_count
            ORDER BY match_count DESC
            SKIP $skip LIMIT $limit
            """
            results, _ = db.cypher_query(query, {
                "skip": offset,
                "limit": batch_size,
                "product_ids": product_ids
            })

            if not results:
                print(f"조회된 결과가 없습니다. 총 조회된 오프셋: {offset}")
                break

            for member_id, metadata, predict_order_list, match_count in results:
                print(f"🔍 {member_id} - 유사도: {match_count}, 주문예측: {predict_order_list}")
                scored = ScoredMember(match_count, member_id, metadata)

                if match_count > MATCH_THRESHOLD:
                    # High group
                    heapq.heappush(high_heap, (match_count, scored))
                    if len(high_heap) > top_k:
                        heapq.heappop(high_heap)
                else:
                    # Low group
                    heapq.heappush(low_heap, (-match_count, scored))
                    if len(low_heap) > top_k:
                        heapq.heappop(low_heap)                         

            offset += batch_size

        # 정렬 후 결과 구성
        high_group = [{"member_id": s.member_id, "metadata": s.metadata, "score": s.score}
                    for _, s in sorted(high_heap, key=lambda x: -x[0])]
        low_group = [{"member_id": s.member_id, "metadata": s.metadata, "score": s.score}
                    for _, s in sorted(low_heap, key=lambda x: x[0])]

        print(f"🔝 상위 {top_k}: {[m['member_id'] for m in high_group]}")
        print(f"🔻 하위 {top_k}: {[m['member_id'] for m in low_group]}")

        return high_group, low_group
        
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
        
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
<<<<<<< HEAD
=======
    
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
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
