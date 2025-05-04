from typing import List

import numpy as np
from ...models import Member as Neo4jMember
from ...utils.neo4j import safe_connect
from neomodel import db

class Neo4jMemberRepository:

    @staticmethod
    def create_member_if_not_exist(member_id: int) -> Neo4jMember:
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
