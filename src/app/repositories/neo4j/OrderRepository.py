from typing import List
from ...models import Order as Neo4jOrder, Product as Neo4jProduct, Member as Neo4jMember, ContainsRel
from ...utils.neo4j import safe_connect
from neomodel import db

class Neo4jOrderRepository:

    @staticmethod
    def create_member_if_not_exist(member_id: int) -> Neo4jMember:
        member = Neo4jMember.nodes.get_or_none(member_id=member_id)
        if not member:
            member = Neo4jMember(member_id=member_id).save()
        return member

    @staticmethod
    def create_order_if_not_exist(order_info: dict, order_info_normalized: dict) -> Neo4jOrder:
        print(f'order_info: {order_info}')
        print(f'order_info_normalized: {order_info_normalized}')

        order = Neo4jOrder.nodes.get_or_none(order_id=order_info['orderId'])
        print(f'order: {order}')
        if not order:
            order = Neo4jOrder(
                order_id=order_info.get("orderId"),
                eval_set=order_info.get("status"),

                days_since_prior_order=order_info.get("daysSincePrior"),
                order_dow=order_info.get("orderDow"),
                order_hour_of_day=order_info.get("orderHour"),
                order_count=order_info.get("orderCount"),
                
                days_since_prior_order_vector=order_info_normalized.get("daysSincePrior"),
                order_dow_vector=order_info_normalized.get("orderDow"),
                order_hour_of_day_vector=order_info_normalized.get("orderHour"),
                order_count_vector=order_info_normalized.get("orderCount"),
            ).save()
        return order

    @staticmethod
    def create_product_if_not_exist(product_mysql: dict, product_name_vecotor: List[float], product_category_vecotor: List[float]) -> Neo4jProduct:
        product_id = product_mysql.get("productId")
        product = Neo4jProduct.nodes.get_or_none(product_id=product_id)

        if not product:
            product = Neo4jProduct(
                product_id=product_id,
                name=product_mysql.get("productName"),
                category=product_mysql.get("category"),

                name_vector=product_name_vecotor, 
                category_vector=product_category_vecotor)
            product.save()

        return product

    @staticmethod
    def get_previous_order(member: Neo4jMember, new_order_id: int) -> Neo4jOrder:
        try:
            query = """
            MATCH (m:Member {member_id: $member_id})-[:ORDERED]->(o:Order)
            WHERE o.order_id < $new_order_id
            RETURN o ORDER BY o.order_id DESC LIMIT 1
            """
            print(f'주문한 유저 id: {member.member_id}')
            results, _ = db.cypher_query(query, {
                "member_id": member.member_id,
                "new_order_id": new_order_id
            })

            if results:
                return Neo4jOrder.inflate(results[0][0])
            return None
        except Exception as e:
            print(f"Error in get_previous_order: {e}")
            return None

    @staticmethod
    def update_previous_order(previous_order: Neo4jOrder, new_order: Neo4jOrder, next_order_list=None):
        print(f'//------------test-----------------//')
        print(f'previous_order_next_order_list: {next_order_list}')
        print(f'previous_order: {previous_order.eval_set}')
        previous_order.next_order_list = next_order_list
        previous_order.eval_set = 'PRIOR'
        print(f'previous_order_next_order_list: {next_order_list}')
        print(f'previous_order: {previous_order.eval_set}')

        safe_connect(previous_order.next_to, new_order)
        
        previous_order.save()

    @staticmethod
    def get_last_n_orders(current_order, n: int = 5):
        """
        현재 Order 노드를 기준으로 역방향(NEXT) 관계를 따라가며,
        최신 순서대로 최대 n개의 주문을 리스트로 반환함.
        
        Args:
            current_order (Order): 기준이 되는 최신 주문 노드
            n (int): 가져올 주문 개수 (기본값: 5)

        Returns:
            List[Order]: 최신 주문부터 과거 순서로 정렬된 주문 리스트
        """
        orders = []
        cursor = current_order
        for _ in range(n):
            if cursor is None:
                break
            orders.append(cursor)
            # 역방향으로 이전 주문 찾기 (NEXT 역참조)
            prev = cursor.previous_from.all()
            cursor = prev[0] if prev else None

        return orders
    
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