# src/app/routes.py
from flask import Blueprint, make_response, request
import json
from ..services import test as test_service
from ..services import readChatroom as read_chat_room_service
from ..services import readChatMessage as read_chat_message_service
from ..services import postChatMessage as post_chat_message_service

api_blueprints = Blueprint("api", __name__, url_prefix="/flask/v1")

# API 경로 테스트
@api_blueprints.route("/test", methods=["GET"])
def test():
    response = test_service.test()
    return response

# 채팅방 조회
@api_blueprints.route("/benefits/<int:sponsorId>", methods=["GET"])
def read_chat_room(sponsorId):
    print(f'/flask/v1/benefits/{sponsorId}')
    response = read_chat_room_service(sponsorId)
    return response

# 채팅 메시지 조회
@api_blueprints.route('/benefits/messages/<int:benefitId>', methods=['GET'])
def read_chat_message(benefitId):
    page = request.args.get('page', default=1, type=int)
    size = request.args.get('size', default=10, type=int)
    print(f'/flask/v1/benefits/messages/{benefitId}')
    print(f'page: {page}, size: {size}')
    response = read_chat_message_service(benefitId,page,size)
    return response


# 채팅 입력
@api_blueprints.route("/benefits/chat/<int:benefitId>", methods=["POST"])
def post_chat_message(benefitId):
    print(f'/flask/v1/benefits/chat/{benefitId}')
    response = post_chat_message_service(benefitId)
    return response


