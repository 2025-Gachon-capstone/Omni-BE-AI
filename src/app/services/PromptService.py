import json

from sqlalchemy import text
from ..utils.gemini import post_gemini

from ..utils import db, ts
from ..models.chatMessage import ChatMessage, AuthorType  # ✅ 모델 가져오기

class PromptService: 

    @staticmethod
    def post_chat_message(benefit_id: int, request: str) -> tuple[str, int]:
        '''
        채팅 메시지 입력
        '''

        user_content:str = request["content"]
        benefit = request["benefit"]

        try:
            # 사용자 메시지 먼저 DB에 저장
            user_content_obj = ChatMessage(
                benefit_id=benefit_id,
                author_type=AuthorType.USER,
                content=user_content,
            )
            # 사용자 메시지 저장
            db.session.add(user_content_obj)
            db.session.flush()  # 바로 DB에 반영해서 user_message_id 얻기
            user_message_id = user_content_obj.chat_message_id

            # AI 응답 생성
            ai_content, ai_error = PromptService.chat_gemini(benefit, user_content)
            if ai_error:
                db.session.commit()  # 사용자 메시지는 커밋
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
            ai_message_obj = ChatMessage(
                benefit_id=benefit_id,
                author_type=AuthorType.AI,
                content=ai_content,
                version=1,
                created_by="flask"
            )
            db.session.add(ai_message_obj)

            # 트랜잭션 최종 커밋
            db.session.commit()

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
            # 총 메시지 수 조회
            total_messages = db.session.query(ChatMessage).filter_by(benefit_id=benefitId).count()

            # OFFSET과 LIMIT을 사용하여 페이징 조회
            offset = (page - 1) * size
            chat_messages = (
                db.session.query(ChatMessage)
                .filter_by(benefit_id=benefitId)
                .order_by(ChatMessage.chat_message_id.desc())
                .offset(offset)
                .limit(size)
                .all()
            )

            # 딕셔너리 형태로 변환
            messages = [
                {
                    "chatMessageId": msg.chat_message_id,
                    "authorType": msg.author_type.value,  # author 필드가 author_type으로 바뀌었지?
                    "content": msg.content
                }
                for msg in chat_messages
            ]

            hasNext = (offset + size) < total_messages
            hasPrev = page > 1

            body = {
                "isSuccess": True,
                "code": "FLASK-200",
                "message": "메시지 조회 성공",
                "timestamp": ts(),
                "result": {
                    "messages": messages,
                    "currentPage": page,
                    "hasNext": hasNext,
                    "hasPrev": hasPrev
                }
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
        
    def chat_gemini(benefit, user_message: str) -> str:
        """
        협찬 혜택 정보와 사용자의 채팅 메시지를 기반으로 프롬프트를 생성
        """
        lines = []

        if title := benefit.get("title"):
            lines.append(f"[혜택명]: {title}")
        if discount_rate := benefit.get("discountRate"):
            lines.append(f"[할인율]: {discount_rate}%")
        if target_member := benefit.get("targetMember"):
            lines.append(f"[타겟 고객]: {target_member}")
        if target_product := benefit.get("targetProduct"):
            lines.append(f"[타겟 상품]: {target_product}")

        prompt_context = "\n".join(lines)
        full_prompt = (
            f"다음은 협찬사가 작성한 혜택 정보입니다:\n\n"
            f"{prompt_context}\n\n"
            f"위의 정보를 참고하여 아래 사용자의 질문에 답하세요:\n"
            f"단 위의 정보가 없을 경우, 아래 사용자의 질문만을 이용하여 답하세요:\n\n"
            f"{user_message}"
        )

        return post_gemini(full_prompt)



