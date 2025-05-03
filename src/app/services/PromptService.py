import json
from logging import config

from sqlalchemy import text

from ..repositories.neo4j.OrderRepository import Neo4jOrderRepository
from ..repositories.mysql.ChatMessage import MysqlChatMessageRepository
from ..repositories.neo4j.MemberRepository import Neo4jMemberRepository
from ..repositories.neo4j.ProductRepository import Neo4jProductRepository

from ..utils.gemini import  post_gemini
from ..utils.text_embedding import CustomE5Embedding, get_text_embedding
from ..utils import db, ts

from ..models.chatMessage import AuthorType  # ✅ 모델 가져오기

from .RagService import full_rag_dag


class PromptService: 

    @staticmethod
    def post_chat_message(benefit_id: int, request: str) -> tuple[str, int]:
        '''
        채팅 메시지 입력
        '''

        user_content:str = request["content"]
        benefit = request["benefit"]
        benefit["benefitId"] = benefit_id

        try:
            # 사용자 메시지 먼저 DB에 저장
            user_content_obj = MysqlChatMessageRepository.save_message(
                benefit_id=benefit_id,
                author_type=AuthorType.USER,
                content=user_content,
            )
            user_message_id = user_content_obj.chat_message_id

            # AI 응답 생성
            ai_content, ai_error = PromptService.chat_gemini(benefit, user_content)
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
    def chat_gemini(benefit, user_message: str) -> str:
        """
        협찬 혜택 정보와 사용자의 채팅 메시지를 기반으로 프롬프트를 생성
        """
        try:
            print(f'//-----RAG start----//')
            # 1. 상품 임베딩
            product_name = benefit.get("targetProduct", "")
            name_vector = get_text_embedding(product_name)
            print(f'step1: {product_name}')
            
            # 2. 유사한 상품 노드 탐색
            matched_products = Neo4jProductRepository.find_products_by_name_vector(name_vector)
            matched_product_names = [p.name for p in matched_products if hasattr(p, 'name')]
            # if not matched_products:
            #     return None, "AI-404: 유사한 상품을 찾을 수 없습니다."

            print(f'step2: {matched_product_names}')


            # 3. 해당 상품을 포함한 주문 → 그 이전 주문 찾기
            orders = Neo4jOrderRepository.get_orders_before_product(matched_products)
            # if not orders:
            #     return None, "AI-404: 관련된 주문 경로가 없습니다."
            
            print(f'step3: {orders}')
            if not orders:
                 prompt = PromptService.compose_rag_prompt(benefit, user_message, matched_product_names)
                 return post_gemini(prompt)
            
            # 4. 해당 주문들의 predict_order_list 추출
            predict_vectors = [o.predict_order_list for o in orders if o.predict_order_list]
            # if not predict_vectors:
            #     return None, "AI-404: 예측값이 없습니다."
            print(f'step4: {len(predict_vectors)}')
            if not predict_vectors:
                 prompt = PromptService.compose_rag_prompt(benefit, user_message, matched_product_names)
                 return post_gemini(prompt)


            # 5. 유사한 회원 탐색
            matched_members = Neo4jMemberRepository.find_members_by_predict_order(predict_vectors, top_k=5)
            # if not matched_members:
            #     return None, "AI-404: 유사한 고객을 찾을 수 없습니다."
            print(f'step5: {matched_members}')
            if not predict_vectors:
                 prompt = PromptService.compose_rag_prompt(benefit, user_message, matched_product_names)
                 return post_gemini(prompt)
        

            # 6. 고객 metadata_text 수집
            context_chunks = [m.metadata for m in matched_members if m.metadata]
            # if not context_chunks:
            #     return None, "AI-404: 고객 설명이 없습니다."
            print(f'step6: {context_chunks}')
            if not context_chunks:
                 prompt = PromptService.compose_rag_prompt(benefit, user_message, matched_product_names)
                 return post_gemini(prompt)

            # 7. 프롬프트 구성
            prompt = PromptService.compose_rag_prompt(benefit, user_message, matched_product_names, context_chunks)

            # 8. LLM 호출
            answer, err = post_gemini(prompt)
            if err:
                return None, err
            return answer, None

        except Exception as e:
            return None, f"AI-500: 예외 발생 - {e}"
    
    @staticmethod
    def compose_rag_prompt(
        benefit: dict, 
        user_message: str,  
        matched_products: list[str] = [], 
        context_chunks: list[str]=[]
    ) -> str:
        benefit_lines = []
        if title := benefit.get("title"):
            benefit_lines.append(f"[혜택명]: {title}")
        if discount := benefit.get("discountRate"):
            benefit_lines.append(f"[할인율]: {discount}%")
        if target := benefit.get("targetMemberText"):
            benefit_lines.append(f"[타겟 고객]: {target}")
        if product := benefit.get("targetProductText"):
            benefit_lines.append(f"[타겟 상품]: {product}")

        benefit_str = "\n".join(benefit_lines)
        customer_str = "\n".join(f"- {c}" for c in context_chunks)

        product_reasoning_str = ""
        if matched_products:
            product_reasoning_str = (
                "다음은 유사한 상품명으로 판단된 제품 목록입니다:\n"
                + "\n".join(f"- {p}" for p in matched_products)
            )

        prompt = (
            f"다음은 협찬사가 등록한 혜택 정보입니다:\n\n{benefit_str}\n\n"
            f"{product_reasoning_str}\n\n"
            f"이 혜택과 관련된 유사 고객들의 성향 요약:\n\n{customer_str}\n\n"
            f"위 정보를 고려하여, 유사 상품과 고객 성향을 기반으로 한 설명과 함께 아래의 사용자의 질문에 답변해주세요.:\n\n"
            f"{user_message}"
        )

        recent_messages = MysqlChatMessageRepository.get_messages(benefit.get("benefitId"), limit=10)
        history_str = "\n".join([f"[{m['author']}]: {m['content']}" for m in recent_messages])

        prompt += (
            f"\n\n추가로, 사용자의 최근 대화 기록은 다음과 같습니다:\n"
            f"{history_str}\n\n"
            f"이전 문맥과 일관되게 답변해주세요."
        )
        print(f'prompt: {prompt}')


        return prompt
