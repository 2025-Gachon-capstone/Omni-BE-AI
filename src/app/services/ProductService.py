import time
from typing import Counter
from src.app.repositories.mysql.OrderRepository import MysqlOrderRepository
from src.app.repositories.mysql.ProductRepository import MysqlProductRepository
from src.app.repositories.neo4j.OrderRepository import Neo4jOrderRepository
from src.app.utils import ts
from src.app.utils.gemini import post_gemini


class ProductService:

    @staticmethod
    def get_products_by_sponsor_id(sponsor_id: int) -> list[dict]:
        """
        특정 스폰서 ID에 해당하는 상품 목록을 조회합니다.
        """
        try:
            products = MysqlProductRepository.get_products_by_sponsor_id(sponsor_id)
            return {
                "isSuccess": True,
                "code": "SUCCESS",
                "result": {"products": products},
                "timestamp": ts()
            }, 200
        except Exception as e:
            print(f"[ERROR] 상품 목록 조회 중 예외 발생:\n {e}")
            return {
                "isSuccess": False,
                "code": "SERVER-ERR 500",
                "message": f"Flask 서버 에러: {e}",
                "timestamp": ts(),
            }, 500      
        

    @staticmethod
    def get_product_orders_statiscis(product_id: int) -> tuple[str, int]:
        """
        특정 상품 ID에 해당하는 주문 통계 정보를 조회합니다.
        """
        try:
            # 1. 기존 fetchall 방식 시간 측정
            start_time = time.time()
            orders = Neo4jOrderRepository.get_orders_by_product_id(product_id)

            product_name = MysqlProductRepository.get_product_name_by_id(product_id)
            if not orders:
                return {
                    "isSuccess": False,
                    "code": "NOT-FOUND",
                    "message": f"상품 ID {product_id}에 해당하는 주문이 없습니다.",
                    "timestamp": ts(),
                }, 404
            
            reordered_counter = Counter()
            order_hour_counter = Counter()
            order_dow_counter = Counter()
            product_counter = Counter()
            # created_dates = []

            for row in orders:
                reordered_counter[row["reordered"]] += 1
                order_hour_counter[row["orderHour"]] += 1
                order_dow_counter[row["orderDow"]] += 1
                key = (row["productId"], row["productName"])
                product_counter[key] += 1
                # created_dates.append(row['createdAt'])
            
            end_time = time.time()
            print(f" generatable 방식 (모두 로드): {end_time - start_time:.4f}초 소요")
            

            statistics = {
                "reordered": [{"label": k, "count": v} for k, v in reordered_counter.items()],
                "orderHour": [{"label": k, "count": v} for k, v in order_hour_counter.items()],
                "orderDow": [{"label": k, "count": v} for k, v in order_dow_counter.items()],
                "relatedProduct": [
                    {"productId": pid, "label": name, "count": count}
                    for (pid, name), count in product_counter.most_common(20)
                ],
                "report": f"{sum(reordered_counter.values())}건의 주문에서 분석되었습니다.",
                "period": {
                    "min": ts(),
                    "max": ts()
                }
            }

            prompt = ProductService.get_prompt(orders_info=statistics, product_name=product_name)
            answer, err = post_gemini(prompt)

            if err:
                # err가 문자열이든 코드든 그대로 메시지에 넣어줌
                return {
                    "isSuccess": False,
                    "code": "LLM-ERR",
                    "message": f"리포트 생성 실패: {err}",
                    "timestamp": ts(),
                    # 실패해도 통계 자체는 계산돼 있으니 같이 내려주면 UI가 fallback 가능
                    "result": statistics
                }, 403  # Bad Gateway(업스트림 LLM 오류 성격)
            
            # answer를 report로 추가
            statistics["report"] = answer  

            return {
                "isSuccess": True,
                "code": "SUCCESS",
                "result": statistics,
                "timestamp": ts(),
            }, 200

        except Exception as e:
            print(f"[ERROR] 상품 주문 통계 조회 중 예외 발생:\n {e}")
            return {
                "isSuccess": False,
                "code": "SERVER-ERR 500",
                "message": f"Flask 서버 에러: {e}",
                "timestamp": ts(),
            }, 500
    
    @staticmethod
    def get_prompt(orders_info, product_name) -> tuple[str, int]:
        return f"당신은 B2B 상품 마케팅 전문가입니다.\n" \
                f"상품명: {product_name}\n" \
                f"주문 통계 정보: {orders_info}\n" \
                "위 상품 정보를 바탕으로 협찬사가 어떤 혜택(쿠폰)을 제공해야할지 아래 지침을 고려하여 답변해주세요" \
                "1. reorderd 수치에서는 신규 고객과 충성고객(재구매) 마케팅을 고려하기 위해 reordered 수치(비율) 어떻게 조정하기" \
                "2. orderHour, orderDow 수치(비율)에서 어떤 시간대에 마케팅을 집중할지에 대한 답변을 포함하기.\n" \
                f"3. relatedProduct 중에서 {product_name}과 무관해 보이는 상품명 찾아서 제외해달라 요청하기 \n" \
                "답변은 한글로 약 4줄 작성해주세요."   