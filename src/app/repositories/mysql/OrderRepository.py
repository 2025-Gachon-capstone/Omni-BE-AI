from typing import Any, Dict, List
from flask import json
import numpy as np
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
    def get_infered_orders_by_product_id(
        product_id: int,
        limit: int = 100,
        reordered_ratio: float = 0.6  # 항상 전달됨 (None 가정 없음)
    ) -> List[Dict]:
        """
        target product가 포함된 주문을 최신순으로 보돼,
        reordered_ratio 비율에 따라 '재구매:첫구매' 주문 수를 분할해서 뽑은 뒤,
        해당 주문에서 '같이 구매된 상품' 라인을 펼쳐 반환한다.
        
        - 부족한 쪽이 있으면 보충하지 않음(이후, 데이터 복제로 보충).
        - 반환 컬럼: orderId, orderDow, orderHour, reordered(아이템 단위), productId, aisle, department
        - oi2.productId <> :pid 로 타깃 상품 라인은 제외.
        """
        # 안전 클램프 (0~1)
        r = float(reordered_ratio)
        if r < 0.0: r = 0.0
        if r > 1.0: r = 1.0

        re_limit    = int(round(limit * r))
        first_limit = int(limit) - re_limit

        sql = text("""
            WITH
            re_orders AS (
                SELECT DISTINCT oi.order_id
                FROM OrderItem oi
                WHERE oi.productId = :pid
                  AND oi.reordered = 1
                ORDER BY oi.order_id DESC
                LIMIT :re_limit
            ),
            first_orders AS (
                SELECT DISTINCT oi.order_id
                FROM OrderItem oi
                WHERE oi.productId = :pid
                  AND oi.reordered = 0
                ORDER BY oi.order_id DESC
                LIMIT :first_limit
            ),
            target_orders AS (
                SELECT order_id FROM re_orders
                UNION ALL
                SELECT order_id FROM first_orders
            )
            SELECT
                o.orderId                 AS orderId,
                o.orderDow                AS orderDow,
                o.orderHour               AS orderHour,
                oi2.reordered             AS reordered,     -- 아이템 단위 플래그
                p2.productId              AS productId,     -- 같이 산 상품
                p2.sponsor_id             AS aisle,         -- 모델 feature: aisle (스키마에 맞게 사용)
                pc2.productCategoryId     AS dept     -- 모델 feature: department
            FROM target_orders t
            JOIN Orders o          ON o.orderId    = t.order_id
            JOIN OrderItem oi2     ON oi2.order_id = t.order_id
            JOIN Product p2        ON p2.productId = oi2.productId
            LEFT JOIN ProductCategory pc2 ON pc2.productCategoryId = p2.product_category_id
            WHERE oi2.productId <> :pid               -- 타깃 상품 제외
            ORDER BY o.orderId DESC
        """)

        with db.engine.connect() as con:
            rows = con.execute(sql, {
                "pid": int(product_id),
                "re_limit": int(re_limit),
                "first_limit": int(first_limit),
            }).fetchall()

        return [dict(r._mapping) for r in rows]

    @staticmethod
    def fetch_recent_products_by_member(member_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        해당 유저의 최신 구매상품을 최신순으로 최대 limit개 반환.
        필요한 컬럼: productId(필수), orderHour(선택), sponsor_id(선택), category_id(선택), count_bucket(선택)
        """
        sql = text("""
            SELECT
                oi.productId            AS productId,
                COALESCE(o.orderHour,0) AS orderHour,
                COALESCE(p.sponsor_id,0)  AS aisle,
                COALESCE(p.product_category_id,0) AS department
            FROM Orders o
            JOIN OrderItem oi ON oi.order_id = o.orderId
            LEFT JOIN Product p ON p.productId = oi.productId
            WHERE o.memberId = :mid
            ORDER BY o.orderId DESC, oi.orderItemId ASC
            LIMIT :lim
        """)
        with db.engine.connect() as conn:
            # .mappings().all() → 각 Row를 dict-like로 반환
            rows = conn.execute(sql, {"mid": int(member_id), "lim": int(limit)}).mappings().all()

        # 이미 dict 형태이므로 바로 리스트로 변환
        return [dict(r) for r in rows]