from typing import List, Optional
from ...models import Order as Neo4jOrder, Member as Neo4jMember, Product as Neo4jProduct
from ...utils.neo4j import safe_connect
from neomodel import db

class Neo4jOrderRepository:

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

                predict_order_list=order_info_normalized.get("predict_order_list")
            ).save()
        return order

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
    def get_orders_before_product(products: list[Neo4jProduct]) -> list[Neo4jOrder]:
        """
        유사한 여러 상품 리스트에 대해 해당 상품이 포함된 주문의 이전 주문들을 모두 수집
        """
        orders = []
        
        for product in products:
             # 이 상품이 포함된 최근 주문들
            recent_orders = Neo4jOrderRepository.get_recent_orders_for_product(product.product_id)
            if not recent_orders:
                continue
            
            for order in recent_orders:
                # 각 주문의 이전 주문 가져오기
                prev_order = Neo4jOrderRepository.get_previous_order_for_order(order)
                if prev_order:
                    orders.append(prev_order)

        return orders if orders else None
    
    @staticmethod
    def get_recent_orders_for_product(product_id: int, limit: int = 5):
        query = """
        MATCH (p:Product {product_id: $product_id})<-[:CONTAINS]-(o:Order)
        RETURN o
        ORDER BY o.order_id DESC
        LIMIT $limit
        """
        results, meta = db.cypher_query(query, {"product_id": product_id, "limit": limit})
        if not results:
            return []
        return [Neo4jOrder.inflate(row[0]) for row in results]
    
    @staticmethod
    def get_previous_order_for_order(order: Neo4jOrder) -> Optional[Neo4jOrder]:
        query = """
        MATCH (prev:Order)-[:NEXT]->(curr:Order {order_id: $order_id})
        RETURN prev
        LIMIT 1
        """
        results, _ = db.cypher_query(query, {"order_id": order.order_id})
        if results:
            return Neo4jOrder.inflate(results[0][0])
        return None


