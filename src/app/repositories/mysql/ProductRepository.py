from sqlalchemy import text
from ...utils import db

class MysqlProductRepository:

    @staticmethod
    def get_product_name_by_id(product_id: int) -> str:
        """
        상품 ID에 해당하는 상품 이름을 조회합니다.
        """
        with db.engine.connect() as connection:
            sql = text(
                "SELECT productName FROM Product WHERE productId = :product_id"
            )
            result = connection.execute(sql, {"product_id": product_id}).fetchone()
            if result:
                # result는 튜플이므로 첫 번째 요소 (인덱스 0)가 실제 상품 이름입니다.
                return result[0]
            else:
                ValueError(f"상품 ID {product_id}에 해당하는 상품이 없습니다.")   