from flask import Blueprint, make_response, request, Response
import json
import datetime
import pytz # 시간대 사용 위해 임포트
from flasgger import swag_from

from ..services import PromptService

prompt_routes = Blueprint("prompt_routes", __name__, url_prefix='/flask/v1/benefits')

# 시간대 설정 (오류 응답 생성 시 사용)
kst = pytz.timezone('Asia/Seoul')


# 채팅방 조회
@prompt_routes.route("/", methods=["GET"])
@swag_from({
    'tags': ['Prompt'], # 태그 추가
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
                    'code': {'type': 'string', 'example': 'MYSQL-500 or FLASK-500'},
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
        return json.dumps({
            "isSuccess": False,
            "code": "REQ-400",
            "message": "sponsorId가 필요합니다.",
            "timestamp": datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        }, ensure_ascii=False), 400

    return PromptService.get_chat_room(sponsorId)

# 채팅 메시지 조회
@prompt_routes.route('/<int:benefitId>/messages', methods=['GET'])
@swag_from({
    'tags': ['Prompt'], 
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
                                        'authorType': {'type': 'string', 'enum': ['AI', 'USER'], 'example': 'USER'},
                                        'content': {'type': 'string', 'example': '이거 어때?'},
                                        'createdAt': {'type': 'string', 'format': 'date-time'} # createdAt 필드 변경
                                    }
                                }
                            },
                            'hasNext': {'type': 'boolean', 'example': True},
                            'hasPrev': {'type': 'boolean', 'example': False},
                            'currentPage': {'type': 'integer', 'example': 1}
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
                    'code': {'type': 'string', 'example': 'MYSQL-500 or FLASK-500'},
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
    return PromptService.get_chat_message(benefitId, page, size)

# 채팅 입력
@prompt_routes.route("/<int:benefitId>/messages", methods=["POST"])
@swag_from({
    'tags': ['Prompt'], 
    'summary': '채팅 메시지 전송',
    'description': '사용자 메시지를 받아 AI 응답을 생성하고 저장합니다.',
    'parameters': [
        {
            'name': 'benefitId',
            'in': 'path',
            'required': True,
            'schema': {
                'type': 'integer'
            },
            'description': '채팅을 전송할 혜택 ID'
        }
    ],
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'content': {
                            'type': 'string',
                            'description': '사용자가 입력한 메시지',
                            'example': '안녕하세요!'
                        },
                        'benefit': {
                            'type': 'object',
                            'description': '협찬 혜택 정보',
                            'properties': {
                                'title': {
                                    'type': 'string',
                                    'description': '혜택명',
                                    'example': '버거 프로모션'
                                },
                                'discountRate': {
                                    'type': 'number',
                                    'format': 'float',
                                    'description': '할인율 (%)',
                                    'example': 15.0
                                },
                                'targetMember': {
                                    'type': 'string',
                                    'description': '타겟 고객 설명',
                                    'example': '햄버거를 자주 구매하는 직장인'
                                },
                                'targetProduct': {
                                    'type': 'string',
                                    'description': '타겟 상품 설명',
                                    'example': '버거킹, 맘스터치'
                                }
                            },
                        }
                    },
                    'required': ['content']
                }
            }
        }
    },
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
                            'authorType': {'type': 'string', 'enum': ['AI'], 'example': 'AI'},
                            'content': {'type': 'string', 'example': '안녕하세요! 무엇을 도와드릴까요?'}
                        }
                    }
                }
            }
        },
        '400': { # 잘못된 요청
            'description': '잘못된 요청 (message 누락)',
             'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'code': {'type': 'string', 'example': 'REQ-400'},
                    'message': {'type': 'string', 'example': 'content가 요청 본문에 포함되어야 합니다.'},
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
                    'code': {'type': 'string', 'example': 'MYSQL-500 or FLASK-500'},
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
    if not data or 'content' not in data or not data['content']:
        return {
            "isSuccess": False,
            "code": "REQ-400",
            "message": "content가 요청 본문에 포함되어야 합니다.",
            "timestamp": datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        }, 400

    return PromptService.post_chat_message(benefitId, data)

# 혜택 제출 (Spring 서버에 매칭 결과 전송)
@prompt_routes.route("/<int:benefitId>/submit", methods=["POST"])
@swag_from({
    'tags': ['Prompt'],
    'summary': '혜택 제출 및 혜택에 맞는 유저 매칭',
    'description': '혜택 정보를 기반으로 유사 회원을 탐색하고 결과를 Spring 서버로 전송합니다.',
    'parameters': [
        {
            'name': 'benefitId',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'},
            'description': '제출할 혜택 ID'
        }
    ],
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'title': {'type': 'string', 'example': '버거 프로모션'},
                        'discountRate': {'type': 'number', 'example': 15.0},
                        'targetMember': {'type': 'string', 'example': '햄버거를 자주 구매하는 직장인'},
                        'targetProduct': {'type': 'string', 'example': '버거킹, 맘스터치'},
                        'amount': {'type': 'number', 'example': 2},
                        'status': {'type': 'string', 'example': 'BEFORE'}
                    },
                    'required': ['targetMember', 'amount']
                }
            }
        }
    },
    'responses': {
        '200': {
            'description': 'Spring 서버로 매칭 결과 전송 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'code': {'type': 'string', 'example': 'FLASK-200'},
                    'message': {'type': 'string', 'example': 'Spring 서버로 매칭 결과 전송 성공'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        },
        '400': {
            'description': '입력 데이터 오류 또는 제출 불가능한 상태',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'code': {'type': 'string', 'example': 'FLASK-400'},
                    'message': {'type': 'string', 'example': '제출하지 않은 혜택입니다.'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        },
        '500': {
            'description': '서버 오류',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'code': {'type': 'string', 'example': 'NETWORK-ERR'},
                    'message': {'type': 'string', 'example': 'Spring 서버 통신 실패: ...'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        }
    }
})
def submit_benefit(benefitId):
    data = request.get_json()
    if not data or 'status' not in data:
        return {
            "isSuccess": False,
            "code": "REQ-400",
            "message": "혜택 status가 필요합니다.",
            "timestamp": datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        }, 400

    data['benefitId'] = benefitId
    return PromptService.submit_benefit(data)