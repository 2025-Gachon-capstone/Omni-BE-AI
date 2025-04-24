from flask import Blueprint, make_response, request, Response
import json
import datetime
import pytz # 시간대 사용 위해 임포트
from flasgger import swag_from

from ..services import test as test_service
from ..services.getChatroom import get_chat_room as get_chat_room_service
from ..services.getChatMessage import get_chat_message as get_chat_message_service
from ..services.postChatMessage import post_chat_message as post_chat_message_service


api_blueprints = Blueprint("api", __name__, url_prefix="/flask/v1")

# 시간대 설정 (오류 응답 생성 시 사용)
kst = pytz.timezone('Asia/Seoul')

# API 테스트
@api_blueprints.route("/test", methods=["GET"])
@swag_from({
    'tags': ['Test'], # 태그 추가
    'summary': 'API 경로 테스트',
    'description': '서버의 생존 여부를 확인합니다',
    'responses': {
        '200': {
            'description': '이게 보인다면 서버가 살아 있다는 뜻입니다. 아마도요.',
            'schema': {
                'type': 'string'
            }
        }
    }
})
def test():
    # test_service가 상태 코드를 반환하지 않으면 직접 설정
    response_data = test_service.test()
    if isinstance(response_data, tuple):
         json_string, status_code = response_data
         response = make_response(json_string)
         response.mimetype = 'application/json; charset=utf-8'
         return response, status_code
    else:
        # 기본 성공 응답 처리
        response = make_response(str(response_data)) # 문자열 응답 가정
        return response, 200

# 채팅방 조회
@api_blueprints.route("/benefits", methods=["GET"])
@swag_from({
    'tags': ['Chat'], # 태그 추가
    'summary': '채팅방 목록 조회',
    'description': '특정 스폰서 ID에 해당하는 채팅방 목록을 조회합니다.',
    'parameters': [
        {
            'name': 'sponsorId',
            'in': 'query',
            'type': 'integer',
            'required': True,
            'description': '조회할 스폰서 ID'
        }
    ],
    'responses': {
        '200': { # 성공 응답
            'description': '채팅방 조회 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'code': {'type': 'string', 'example': 'FLASK-200'},
                    'message': {'type': 'string', 'example': '채팅방 조회 성공'},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                    'result': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'benefitId': {'type': 'integer', 'example': 1},
                                'name': {'type': 'string', 'example': 'Sample Benefit'}
                            }
                        }
                    }
                }
            }
        },
        '400': { # 잘못된 요청
            'description': '잘못된 요청 (sponsorId 누락)',
             'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'code': {'type': 'string', 'example': 'REQ-400'},
                    'message': {'type': 'string', 'example': 'sponsorId가 필요합니다.'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        },
        '500': { # 서버 오류
            'description': '서버 오류 (DB 연결 실패 등)',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'code': {'type': 'string', 'example': 'MYSQL-500 or SYS-500'},
                    'message': {'type': 'string', 'example': '데이터베이스 연결 실패 or 오류 메시지'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        }
    }
})
def get_chat_room():
    sponsorId = request.args.get('sponsorId', type=int)
    if sponsorId is None:
        error_response = {
            "isSuccess": False,
            "code": "REQ-400",
            "message": "sponsorId가 필요합니다.",
            "timestamp": datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S") # 시간대 적용
        }
        # 상태 코드 400 반환
        return make_response(json.dumps(error_response, ensure_ascii=False), 400)

    # 서비스 함수 호출 및 상태 코드 받기
    json_string, status_code = get_chat_room_service(sponsorId)
    response = make_response(json_string)
    response.mimetype = 'application/json; charset=utf-8'
    # 서비스에서 반환된 상태 코드 사용
    return response, status_code

# 채팅 메시지 조회
@api_blueprints.route('/benefits/<int:benefitId>/messages', methods=['GET'])
@swag_from({
    'tags': ['Chat'], 
    'summary': '채팅 메시지 목록 조회',
    'description': '특정 혜택 ID에 대한 채팅 메시지 목록을 페이지네이션하여 조회합니다.',
    'parameters': [
        {
            'name': 'benefitId',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '조회할 혜택 ID'
        },
        {
            'name': 'page',
            'in': 'query',
            'type': 'integer',
            'default': 1,
            'description': '조회할 페이지 번호 (1부터 시작)'
        },
        {
            'name': 'size',
            'in': 'query',
            'type': 'integer',
            'default': 30, 
            'description': '페이지당 메시지 수'
        }
    ],
    'responses': {
        '200': { # 성공 응답
            'description': '메시지 조회 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'code': {'type': 'string', 'example': 'FLASK-200'},
                    'message': {'type': 'string', 'example': '메시지 조회 성공'},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                    'userMessageId': {'type': 'string', 'example': 'msg-004'},
                    'result': {
                        'type': 'object',
                        'properties': {
                            'messages': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'messageId': {'type': 'integer', 'example': 123},
                                        'author': {'type': 'string', 'enum': ['AI', 'USER'], 'example': 'USER'},
                                        'content': {'type': 'string', 'example': '이거 어때?'},
                                        'sendAt': {'type': 'string', 'format': 'date-time'} # sendAt 필드 추가됨
                                    }
                                }
                            },
                            'hasNext': {'type': 'boolean', 'example': True},
                            'hasPrev': {'type': 'boolean', 'example': False}
                        }
                    }
                }
            }
        },
        '500': { # 서버 오류
            'description': '서버 오류 (DB 연결 실패 등)',
             'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'code': {'type': 'string', 'example': 'MYSQL-500 or SYS-500'},
                    'message': {'type': 'string', 'example': '데이터베이스 연결 실패 or 오류 메시지'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        }
    }
})
def get_chat_message(benefitId):
    page = request.args.get('page', default=1, type=int)
    size = request.args.get('size', default=30, type=int) # 기본값 30으로 수정
    # 서비스 함수 호출 및 상태 코드 받기
    json_string, status_code = get_chat_message_service(benefitId, page, size)
    response = make_response(json_string)
    response.mimetype = 'application/json; charset=utf-8'
    # 서비스에서 반환된 상태 코드 사용
    return response, status_code

# 채팅 입력
@api_blueprints.route("/benefits/<int:benefitId>/chat", methods=["POST"])
@swag_from({
    'tags': ['Chat'], 
    'summary': '채팅 메시지 전송',
    'description': '사용자 메시지를 받아 AI 응답을 생성하고 저장합니다.',
    'parameters': [
        {
            'name': 'benefitId',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '채팅을 전송할 혜택 ID'
        },
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'user_message': {
                        'type': 'string',
                        'description': '사용자가 입력한 메시지',
                        'example': '안녕하세요!'
                    }
                },
                'required': ['user_message']
            }
        }
    ],
    'responses': {
        '201': { # 성공 응답
            'description': 'AI 응답 생성 및 저장 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'code': {'type': 'string', 'example': 'FLASK-201'},
                    'message': {'type': 'string', 'example': 'AI 응답 생성 및 저장 성공'},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                    'userMessageId': {'type': 'string', 'example': 'msg-005'}, 
                    'result': {
                        'type': 'object',
                        'properties': {
                            'author': {'type': 'string', 'enum': ['AI'], 'example': 'AI'},
                            'content': {'type': 'string', 'example': '안녕하세요! 무엇을 도와드릴까요?'}
                        }
                    }
                }
            }
        },
        '400': { # 잘못된 요청
            'description': '잘못된 요청 (user_message 누락)',
             'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'code': {'type': 'string', 'example': 'REQ-400'},
                    'message': {'type': 'string', 'example': 'user_message가 요청 본문에 포함되어야 합니다.'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        },
        '500': { # 서버 오류
            'description': '서버 오류 (DB 연결 실패, 시스템 오류 등)',
             'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'code': {'type': 'string', 'example': 'MYSQL-500 or SYS-500'},
                    'message': {'type': 'string', 'example': '데이터베이스 연결 실패 or 오류 메시지'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        },
        '503': { # AI 서비스 오류
            'description': 'AI 서비스 호출 오류',
            'schema': {
                 'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'code': {'type': 'string', 'example': 'AI-503'},
                    'message': {'type': 'string', 'example': 'AI 서비스 호출 중 오류 발생 (...) '},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                    'userMessageId': {'type': 'string', 'example': 'msg-005'} # 3자리 포맷팅 반영
                }
            }
        }
    }
})
def post_chat_message(benefitId):
    data = request.get_json()
    if not data or 'user_message' not in data or not data['user_message']:
        error_response = {
            "isSuccess": False,
            "code": "REQ-400",
            "message": "user_message가 요청 본문에 포함되어야 합니다.",
            "timestamp": datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S") # KTC 사용
        }
        # 상태 코드 400 반환
        return make_response(json.dumps(error_response, ensure_ascii=False), 400)

    user_message = data["user_message"]
    # 서비스 함수 호출 및 상태 코드 받기
    json_string, status_code = post_chat_message_service(benefitId, user_message)
    response = make_response(json_string)
    response.mimetype = 'application/json; charset=utf-8'
    # 서비스에서 반환된 상태 코드 사용
    return response, status_code