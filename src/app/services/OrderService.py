import json
from neomodel import db as neo4j_db

from app.utils.neo4j import safe_connect

from ..repositories.mysql.OrderRepository import MysqlOrderRepository
from ..repositories.neo4j.OrderRepository import Neo4jOrderRepository
from ..utils import ts
from ..config import config
from ..utils.normalizaiton import min_max_normalize

# Neo4j 연결 설정 (app 설정에 따라 변경 필요)

class OrderService:

    @staticmethod
    def post_order_with_items(order_id: int) -> tuple[str, int]:
        '''
        주문서 및 주문내역 조회 후 Neo4j에 저장하고 이전 주문과 연결
        '''
        try:
            order_data = MysqlOrderRepository.get_order_with_items(order_id)

            if not order_data:
                body = {
                    "isSuccess": False,
                    "code": "MYSQL-404",
                    "message": f"주문 ID '{order_id}'에 해당하는 주문을 찾을 수 없습니다.",
                    "timestamp": ts(),
                }
                print(json.dumps(body, ensure_ascii=False, indent=2, default=str))
                return body, 404

            member_id, order_info, order_items, products = order_data

            # Neo4j에 저장
            try:
                neo4j_member = Neo4jOrderRepository.create_member_if_not_exist(member_id)
                
                order_info_normalized = {
                    # TODO: 정규화 MAX값 조정해야함
                    "orderId": order_info.get("orderId"),
                    "daysSincePrior": min_max_normalize(order_info.get("daysSincePrior"), 0, 100),
                    "orderDow": min_max_normalize(order_info.get("orderDow"), 0, 6),
                    "orderHour": min_max_normalize(order_info.get("orderHour"), 0, 23),
                    "orderCount": min_max_normalize(order_info.get("orderCount"), 0, 100),
                    "status": order_info.get('status')
                }

                previous_order = Neo4jOrderRepository.get_previous_order(neo4j_member, order_id)
                new_order = Neo4jOrderRepository.create_order_if_not_exist(order_info_normalized)
                safe_connect(neo4j_member.ordered, new_order)
                # safe_connect(new_order.ordered_by, neo4j_member)

                for item, product in zip(order_items, products):
                    new_product = Neo4jOrderRepository.create_product_if_not_exist(
                        product.get("productId"),
                        product.get("productName") #TODO: 텍스트 임베딩
                    )
                    safe_connect(
                        rel_manager=new_order.contains,
                        target_node=new_product,
                        add_to_cart_order=item["addToCartOrder"],
                        reordered= (item["reordered"] == 1)
                    )

                # 이전 주문 찾아서 next_order_list 저장 및 연결
                if previous_order:
                    Neo4jOrderRepository.update_previous_order(previous_order, new_order)

                body = {
                    "isSuccess": True,
                    "code": "FLASK-200",
                    "message": f"주문 ID '{order_info.get('orderId')}' 저장 및 이전 주문 업데이트 성공",
                    "timestamp": ts(),
                    "result": order_data
                }
                print(json.dumps(body, ensure_ascii=False, indent=2, default=str))
                return body, 200

            except Exception as neo4j_error:
                neo4j_db.rollback()
                body = {
                    "isSuccess": False,
                    "code": "NEO4J-500",
                    "message": f"Neo4j 저장 오류: {str(neo4j_error)}",
                    "timestamp": ts(),
                    "result": order_data
                }
                print(json.dumps(body, ensure_ascii=False, indent=2, default=str))
                return body, 500

        except Exception as e:
            body = {
                "isSuccess": False,
                "code": "FLASK-500",
                "message": f"서버 오류: {str(e)}",
                "timestamp": ts(),
            }
            print(json.dumps(body, ensure_ascii=False, indent=2, default=str))
            return body, 500