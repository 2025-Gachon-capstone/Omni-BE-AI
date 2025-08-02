from typing import Any, Dict, Generator
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
    
    @staticmethod
    def get_orders_by_product_id(product_id: int, limit: int =100) -> list:
        """
        특정 상품 ID에 해당하는 주문 목록을 조회합니다.
        인덱스 캐싱 전: 115.8872초 소요 => 인덱스 캐싱 후 : 0.1 ~ 0.2862초 소요
        """
        with db.engine.connect() as connection:
            sql = text(
               """
                SELECT
                    o.orderId, o.orderDow, o.orderHour, o.createdAt,
                    order_info.reordered,
                    p.productId, p.productName
                FROM Orders o
                JOIN (
                    SELECT
                        oi.order_id,
                        oi.reordered
                    FROM OrderItem oi
                    WHERE oi.productId = :product_id
                    ORDER BY oi.order_id DESC
                    LIMIT :limit
                ) AS order_info ON o.orderId = order_info.order_id
                JOIN Product p ON p.productId = :product_id
                ORDER BY o.createdAt DESC;
                """
            )
            result = connection.execute(sql, {"product_id": product_id, "limit": limit}).fetchall()            

            # 각 row를 딕셔너리로 변환
            return [dict(row._mapping) for row in result]
        
    @staticmethod
    def get_orders_by_product_id_new(product_id: int, limit: int =100) -> Generator[Dict[str, Any], None, None]:
        """
        특정 상품 ID에 해당하는 주문 목록을 조회합니다.
        결과를 제너레이터(Generator)로 반환하여 메모리 효율적으로 스트리밍 처리합니다.
        인덱스 캐싱 전 : 135.6092초 소요
        인덱스 캐싱 후  0.3021초 소요
        """
        with db.engine.connect() as connection:
            sql = text(
                """
                SELECT
                    o.orderId, o.orderDow, o.orderHour, o.createdAt,
                    order_info.reordered,
                    p.productId, p.productName
                FROM Orders o
                JOIN (
                    SELECT
                        oi.order_id,
                        oi.reordered
                    FROM OrderItem oi
                    WHERE oi.productId = :product_id
                    ORDER BY oi.order_id DESC
                    LIMIT :limit
                ) AS order_info ON o.orderId = order_info.order_id
                JOIN Product p ON p.productId = :product_id
                ORDER BY o.createdAt DESC;
                """
            )
            
            # 이 Result 객체는 데이터베이스 커서를 통해 필요할 때마다 데이터를 가져옵니다.
            result_proxy = connection.execute(sql, {"product_id": product_id, "limit": limit})
            
            column_names = None
            # Result 객체를 직접 순회하며 각 로우를 하나씩 처리합니다.
            for row in result_proxy:
                # 컬럼 이름은 첫 번째 로우가 들어올 때 한 번만 가져옵니다.
                if column_names is None:
                    column_names = row._fields 
                
                # 각 로우(튜플 형태)를 딕셔너리로 변환하여 호출자에게 yield합니다.
                # yield는 함수 실행을 일시 중지하고 값을 반환하며, 다음 요청 시 중지된 지점부터 다시 시작합니다.
                yield dict(zip(column_names, row))