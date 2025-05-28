from sqlalchemy import text
from ...utils import db

class MysqlOrderRepository:

    @staticmethod
    def get_order_with_items(order_id: int) -> dict:
        """
        주문 ID에 해당하는 주문 정보 및 주문 아이템 목록을 조회하여 Order 객체 형태로 반환합니다.
        """
        with db.engine.connect() as connection:
            sql = text(
                """
                SELECT o.orderId, o.daysSincePrior, o.memberId, o.orderCount, o.orderDow, o.orderHour, o.status,
                oi.addToCartOrder, oi.reordered,
                p.productId, p.productName, pc.name AS categoryName

                FROM Orders o
                JOIN OrderItem oi ON o.orderId = oi.order_id
                JOIN Product p ON oi.productId = p.productId
                JOIN ProductCategory pc ON p.product_category_id = pc.productCategoryId
                WHERE o.orderId = :order_id
                ORDER BY oi.addToCartOrder ASC
                """
            )
            result = connection.execute(sql, {"order_id": order_id}).fetchall()
            if not result:
                return None

            order_info = {}
            order_items = []
            products = []
            member_id = 0

            # 첫 번째 행에서 주문 정보 추출
            first_row = result[0]
            column_names = result[0]._fields # 컬럼 이름 목록 가져오기

            for index, col in enumerate(column_names):
                if col == "memberId":
                    member_id = first_row[index]
                    continue
                order_info[col] = first_row[index]

            order_info["orderId"] = str(order_info.get("orderId"))  # orderId를 문자열로 변환
            
            # 나머지 행에서 주문 아이템 정보 추출
            print('//--------------------테스트------------------//')
            print(f'result-length: {len(result)}')
            print(f': {order_info}')
            for row in result:
                row_dict = dict(zip(column_names, row))  # 컬럼 이름과 값을 딕셔너리로 매핑
                product = {
                    "productId": str(row_dict.get("productId")), # productId를 문자열로 변환
                    "productName": row_dict.get("productName"),
                    "category": row_dict.get("categoryName")
                }
                order_item = {
                    "addToCartOrder": row_dict.get("addToCartOrder"),
                    "reordered": row_dict.get("reordered"),
                }
                products.append(product)
                order_items.append(order_item)

                print(f'product: {product}, order: {order_item}')

            return str(member_id), order_info, order_items, products