import json
from ..config import config

import requests
from sqlalchemy import text

from ..repositories.neo4j.OrderRepository import Neo4jOrderRepository
from ..repositories.mysql.ChatMessage import MysqlChatMessageRepository
from ..repositories.neo4j.MemberRepository import Neo4jMemberRepository
from ..repositories.neo4j.ProductRepository import Neo4jProductRepository

from ..utils.gemini import  post_gemini
from ..utils.text_embedding import get_text_embedding
from ..utils import db, ts

from ..models.chatMessage import AuthorType  # ✅ 모델 가져오기


class PromptService: 

    @staticmethod
    def post_chat_message(benefit_id: int, request: str) -> tuple[str, int]:
        '''
        채팅 메시지 입력
        '''

        user_content:str = request["content"]
        product_name = request["productName"]

        try:
            # 사용자 메시지 먼저 DB에 저장
            user_content_obj = MysqlChatMessageRepository.save_message(
                benefit_id=benefit_id,
                author_type=AuthorType.USER,
                content=user_content,
            )
            user_message_id = user_content_obj.chat_message_id

            # AI 응답 생성
            ai_content, ai_error = PromptService.chat_gemini(product_name, user_content)
            if ai_error:
                error_response = {
                    "isSuccess": False,
                    "code": ai_error.split(":")[0],
                    "message": ai_error.split(":")[1].strip(),
                    "timestamp": ts(),
                    "chatMessageId": f"msg-{user_message_id}"
                }
                print(f'{json.dumps(error_response, ensure_ascii=False, indent=2)}')
                return error_response, 503

            # AI 메시지 저장
            ai_message_obj = MysqlChatMessageRepository.save_message(
                benefit_id=benefit_id,
                author_type=AuthorType.AI,
                content=ai_content,
            )

            success_response = {
                "isSuccess": True,
                "code": "FLASK-201",
                "message": "AI 응답 생성 및 저장 성공",
                "timestamp": ts(),
                "chatMessageId": f"msg-{user_message_id}",
                "result": {
                    "chatMessageId": ai_message_obj.chat_message_id,
                    "authorType": AuthorType.AI.value,
                    "content": ai_content
                }
            }
            return success_response, 201

        except Exception as e:
            db.session.rollback()
            error_response = {
                "isSuccess": False,
                "code": "FLASK-500",
                "message": f"메시지 처리 중 오류: {e}",
                "timestamp": ts()
            }
            print(f'{json.dumps(error_response, ensure_ascii=False, indent=2)}')
            return error_response, 500
        
    @staticmethod
    def get_chat_room(sponsorId) -> tuple[str, int]:
        '''
        채팅방(작성한 헤택)리스트 조회
        '''
        chatrooms = []
        try:
            with db.engine.connect() as connection:
                sql = text("SELECT * FROM Benefit WHERE sponsor_id = :sponsor_id ORDER BY benefitId DESC")
                result = connection.execute(sql, {"sponsor_id": sponsorId})
                chatrooms = [dict(row) for row in result.mappings()]  # ✅ SQLAlchemy 2.0 스타일
                
                body = {
                    "isSuccess": True,
                    "code": "FLASK-200",
                    "message": "채팅방 조회 성공",
                    "timestamp": ts(),
                    "result": chatrooms
                }
                return body, 200
        
        except Exception as e:
            # DB 조회 실패
            error_response = {
                "isSuccess": False,
                "code": "MYSQL-500",
                "message": str(e), # 오류 메시지 문자열로 변환
                "timestamp": ts()
            }
            # 상태 코드 500 반환 (튜플 형태)
            print(f'{json.dumps(error_response, ensure_ascii=False, indent=2)}')
            return error_response, 500
        
    @staticmethod
    def get_chat_message(benefitId, page, size=30) -> tuple[str, int]:
        '''
        채팅 메시지 조회
        '''
        try:
            # 딕셔너리 형태로 변환
            result = MysqlChatMessageRepository.get_sliced_messages(benefitId, page, size)

            body = {
                "isSuccess": True,
                "code": "FLASK-200",
                "message": "메시지 조회 성공",
                "timestamp": ts(),
                "result": result
            }

            return body, 200

        except Exception as e:
            error_response = {
                "isSuccess": False,
                "code": "MYSQL-500",
                "message": str(e),
                "timestamp": ts()
            }
            print(f'{json.dumps(error_response, ensure_ascii=False, indent=2)}')
            return error_response, 500
        
    @staticmethod
    def submit_benefit(benefit) -> tuple[str, int]:
        '''
        협찬 제출 (사용자 혜택 매칭)
        '''
        # if benefit['status'] in ['PENDING', 'DELETED']:
        #     error_response = {
        #         "isSuccess": False,
        #         "code": "FLASK-400",
        #         "message": "제출하지 않은 혜택입니다.",
        #         "timestamp": ts(),
        #     }
        #     print(f'{json.dumps(error_response, ensure_ascii=False, indent=2)}')
        #     return error_response, 400
        
        target_member = benefit['targetMember']
        amount = int(benefit['amount'])

        target_member_vector = get_text_embedding(target_member)
        matched_members = Neo4jMemberRepository.find_members_by_target_member(target_member_vector, amount)
        num_of_target_member = len(matched_members)
        
        if num_of_target_member < amount:
            error_response = {
                "isSuccess": False,
                "code": "FLASK-400",
                "message": f"매칭된 타겟 고객군({num_of_target_member} 명)이 혜택 발행량({amount} 개)보다 적습니다.",
                "timestamp": ts(),
            }
            print(f'{json.dumps(error_response, ensure_ascii=False, indent=2)}')
            return error_response, 400

        # 3. Spring 서버로 요청 전송
        spring_url = f"{config.CARD_SERVER_ADDRESS}/card/v1/cardBenefits"
        print(f"spring_url: {spring_url}")

        body = {
            "benefitId": benefit['benefitId'],
            "memberIdList": [m.member_id for m in matched_members],
        }

        try:
            response = requests.post(spring_url, json=body)
            if response.status_code == 200:
                return response.json(), 200
            else:
                return response.json(), 500
        except requests.exceptions.RequestException as e:
            return {
                "isSuccess": False,
                "code": "NETWORK-ERR",
                "message": f"Spring 서버 통신 실패: {e}",
                "timestamp": ts(),
            }, 500
    
    @staticmethod
    def chat_gemini(product_name, user_message: str) -> str:
        """
        협찬 혜택 정보와 사용자의 채팅 메시지를 기반으로 프롬프트를 생성
        """
        try:
            print(f'//-----RAG start----//')
            # 1. 상품 임베딩
            name_vector = get_text_embedding(product_name)
            print(f'step1: {product_name}')
            
            # 2. 유사한 상품 노드 탐색
            matched_products = Neo4jProductRepository.find_products_by_name_vector(name_vector)
            matched_product_names = [p.name for p in matched_products if hasattr(p, 'name')]
            if not matched_products:
                return None, "AI-404: 유사한 상품을 찾을 수 없습니다."

            print(f'step2: {matched_product_names}')

            product_ids = [p.product_id for p in matched_products]
            # 3) (변경) 상품별 구매자 메타데이터 조회
            grouped = Neo4jMemberRepository.find_buyers_by_product_ids(
                product_ids=product_ids, top_k=10, min_total_orders=10
            )
            if grouped.get("total_orders", 0) < 10:
                return None, "AI-404: 유사 상품의 구매내역이 10건 미만입니다."

            # 4) 상품별 metadata 정리
            grouped_context = []  # [{product_id, buyer_metas: [...]}, ...]
            for bucket in grouped.get("by_product", []):
                seen = set()
                metas = []
                for item in bucket.get("members", []):
                    mem = item.get("member")
                    if not mem:
                        continue
                    mid = getattr(mem, "member_id", None)
                    meta = getattr(mem, "metadata", None)
                    if not mid or not meta:
                        continue
                    if mid in seen:
                        continue
                    seen.add(mid)
                    m = meta.strip()
                    if m:
                        metas.append(m)
                if metas:
                    grouped_context.append({
                        "product_id": bucket.get("product_id"),
                        "buyer_metas": metas
                    })

            if not grouped_context:
                return None, "AI-404: 구매자 metadata가 없습니다."

            # 5) 프롬프트 구성 (상품별 섹션)
            prompt = PromptService.compose_rag_buyers_by_similar_products(
                user_message=user_message,
                matched_products=matched_product_names,
                grouped_context=grouped_context,
                total_orders=grouped.get("total_orders", 0),
            )

            # 6) LLM 호출
            answer, err = post_gemini(prompt)
            if err:
                return None, err
            return answer, None


        except Exception as e:
            return None, f"AI-500: 예외 발생 - {e}"
    
    @staticmethod
    def compose_rag_buyers_by_similar_products(
        user_message: str,
        matched_products: list[str],          # 유사 상품명 리스트 (없으면 빈 리스트)
        grouped_context: list[dict],          # [{ "product_id": str, "product_name": str|None, "buyer_metas": [str, ...] }, ...]
        total_orders: int,                     # 유사 상품 전체 주문 수 (기간 제한 없음)       # 최근 대화 기록 위해 사용 (없으면 무시)
    ) -> str:
        """
        목적:
        - 협찬사가 '이 상품을 누가 사는지' 물으면,
            해당 상품의 '유사 상품' 구매자 메타데이터를 상품별로 정리하여
            요약/타겟팅 인사이트/카피/쿠폰 조건까지 제안하도록 지시.
        """

        # 1) 유사 상품 목록
        product_reasoning_str = ""
        if matched_products:
            product_reasoning_str = "유사 상품 목록:\n" + "\n".join(f"- {p}" for p in matched_products)

        # 2) 상품별 구매자 메타데이터 블록
        blocks = []
        for g in grouped_context:
            pname = (g.get("product_name") or g.get("product_id") or "상품").strip()
            metas = g.get("buyer_metas", []) or []
            if not metas:
                continue
            metas_str = "\n".join(f"- {m}" for m in metas)
            blocks.append(f"[{pname}] 구매자 메타데이터 샘플:\n{metas_str}")
        grouped_str = "\n\n".join(blocks) if blocks else "※ 유사 상품별 구매자 메타데이터가 비어있습니다."

        # 3) 최종 프롬프트
        prompt = (
            "다음 정보를 바탕으로, 질의한 상품과 유사한 상품들의 **실제 구매자 특성**을 상품별로 요약하고 "
            "이 특성을 근거로 타겟팅 인사이트와 실행 가능한 마케팅 제안을 제시하세요.\n\n"
            f"{product_reasoning_str}\n\n"
            f"[데이터 근거] 유사 상품 전체 주문 수: {total_orders}건 (기간 제한 없음)\n\n"
            f"{grouped_str}\n\n"
            "요청사항:\n"
            f"{user_message}\n\n"
            "작성 지침:\n"
            "- 각 상품별로 아래 순서로 작성:\n"
            "  1) 핵심 구매자 특징 요약(연령대/성별/지역/구매 패턴/채널/시간대 등, 개인정보 금지)\n"
            "- 문단은 \\n 로 구분하고, 한글 4줄 정도로 불필요한 서론은 최소화하세요.\n"
        )

        return prompt

