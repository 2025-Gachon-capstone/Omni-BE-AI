from flask import Blueprint, make_response, request, Response
import json
import datetime

from ..services import test as test_service
from ..services.getChatroom import get_chat_room as get_chat_room_service
from ..services.getChatMessage import get_chat_message as get_chat_message_service
from ..services.postChatMessage import post_chat_message as post_chat_message_service

api_blueprints = Blueprint("api", __name__, url_prefix="/flask/v1")

# API 테스트
@api_blueprints.route("/test", methods=["GET"])
def test():
    response = test_service.test()
    return response

# 채팅방 조회
@api_blueprints.route("/benefits/<int:sponsorId>", methods=["GET"])
def get_chat_room(sponsorId):
    json_string= get_chat_room_service(sponsorId)
    response = make_response(json_string)
    response.mimetype = 'application/json; charset=utf-8'
    return response

# 채팅 메시지 조회
@api_blueprints.route('/benefits/<int:benefitId>/messages', methods=['GET'])
def get_chat_message(benefitId):
    page = request.args.get('page', default=1, type=int)
    size = request.args.get('size', default=10, type=int)
    json_string = get_chat_message_service(benefitId, page, size)
    response = make_response(json_string)
    response.mimetype = 'application/json; charset=utf-8'
    return response


# 채팅 입력
@api_blueprints.route("/benefits/<int:benefitId>/messages", methods=["POST"])
def post_chat_message(benefitId):
    data = request.get_json()
    user_message = data.get("user_message")

    if not user_message:
        error_response = {
            "isSuccess": False,
            "code": "REQ-400",
            "message": "user_message가 요청 본문에 포함되어야 합니다.",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return make_response(json.dumps(error_response, ensure_ascii=False), 400)

    json_string = post_chat_message_service(benefitId, user_message)
    response = make_response(json_string)
    response.mimetype = 'application/json; charset=utf-8'
    return response