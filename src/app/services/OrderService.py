import json
from neomodel import db as neo4j_db

from app.utils.gemini import get_text_embedding, post_gemini

from ..utils.neo4j import safe_connect

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
                    "daysSincePrior": min_max_normalize(order_info.get("daysSincePrior"), 0, 100),
                    "orderDow": min_max_normalize(order_info.get("orderDow"), 0, 6),
                    "orderHour": min_max_normalize(order_info.get("orderHour"), 0, 23),
                    "orderCount": min_max_normalize(order_info.get("orderCount"), 0, 100),
                }
                
                previous_order = Neo4jOrderRepository.get_previous_order(neo4j_member, order_id)
                new_order = Neo4jOrderRepository.create_order_if_not_exist(
                        order_info=order_info, 
                        order_info_normalized=order_info_normalized
                )
                safe_connect(neo4j_member.ordered, new_order)

                for item, product in zip(order_items, products):
                    product_name=product.get("productName")
                    category=product.get("category")
                    print(f'name: {product_name}')
                    print(f'category: {category}')
                    product_name_vector = get_text_embedding(product.get("productName"))
                    product_category_vector = get_text_embedding(product.get("category"))

                    new_product = Neo4jOrderRepository.create_product_if_not_exist(
                        product,
                        product_name_vector,
                        product_category_vector
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

                metadata = OrderService.update_member_metadata_by_gemini(neo4j_member, new_order)

                body = {
                    "isSuccess": True,
                    "code": "FLASK-200",
                    "message": f"주문 ID '{order_info.get('orderId')}' 저장 및 이전 주문 업데이트 성공",
                    "timestamp": ts(),
                    "result": {
                        "metadata": metadata
                    }
                }
                print(json.dumps(body, ensure_ascii=False, indent=2, default=str))
                return body, 200

            except Exception as neo4j_error:
                body = {
                    "isSuccess": False,
                    "code": "NEO4J-500",
                    "message": f"Neo4j 저장 오류: {str(neo4j_error)}",
                    "timestamp": ts(),
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
        
    @staticmethod
    def update_member_metadata_by_gemini(member, last_node):
        orders = Neo4jOrderRepository.get_last_n_orders(last_node, 5)
        if not orders:
            return

        summaries = []
        weekday_names = ['일', '월', '화', '수', '목', '금', '토']
        summaries = []
        for order in orders:
            products = order.contains.all()
            product_names = [getattr(p, 'name', '이름없음') for p in products]
            categories = [getattr(p, 'category', '분류없음') for p in products]
            unique_categories = list(dict.fromkeys(categories))  # ✅ 순서 유지하며 중복 제거

            product_names_str = ', '.join(product_names) if product_names else '없음'
            unique_categories_str = ', '.join(unique_categories) if unique_categories else '없음'

            weekday = weekday_names[order.order_dow % 7] if isinstance(order.order_dow, int) else "알수없음"

            summaries.append(
                f"- 구매 요일: {weekday}요일\n"
                f"- 구매 시간: {order.order_hour_of_day}시\n"
                f"- 상품명: {product_names_str}\n"
                f"- 카테고리: {unique_categories_str}\n"
            )

        prompt = "다음은 한 고객의 최근 구매 내역입니다. 이 고객의 구매 성향을 2줄 이내의 한글로 요약해 주세요.\n\n"
        prompt += "\n\n".join(summaries)
        print(prompt)

        metadata, message = post_gemini(prompt)

        if message:
            raise ConnectionError(message)

        metadata_vector = get_text_embedding(metadata)
        print(f'metadata_vector: {metadata_vector}')

        Neo4jOrderRepository.update_member_fields(member, {
            "metadata": metadata,
            "metadata_vector": metadata_vector
        })

        return metadata
