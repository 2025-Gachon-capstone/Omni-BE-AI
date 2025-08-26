from sqlalchemy import text
from src.app.utils import db


class MysqlBenefitRepository:
    @staticmethod
    def delete_benefit_by_id(benefit_id: int) -> int:
        """
        benefitId(기본키)로 Benefit 레코드를 삭제합니다.
        반환값: 삭제된 행 수(rowcount)
        """
        # 트랜잭션 자동 커밋/롤백
        with db.engine.begin() as connection:
            result = connection.execute(
                text("DELETE FROM Benefit WHERE benefitId = :benefit_id"),
                {"benefit_id": benefit_id},
            )
            return result.rowcount