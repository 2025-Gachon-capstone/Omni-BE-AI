import datetime
import json
from flask import Blueprint, request
from flasgger import swag_from

import pytz

from src.app.services import ProductService


product_routes = Blueprint("product_routes", __name__, url_prefix='/flask/v1/products')

# 시간대 설정 (오류 응답 생성 시 사용)
kst = pytz.timezone('Asia/Seoul')

# 채팅방 조회
@product_routes.route("/<int:productId>/statistics", methods=["GET"])
@swag_from({
    'tags': ['Product'], # 태그 추가
    'summary': '상품 통계 조회',
    'description': '특정 상품 구매내역 100개에 대한 count 통계 정보를 조회합니다.',
    'parameters': [
        {
            'name': 'productId',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '조회할 상품 ID'
        }
    ],

    'responses': {
        '200': {
            'description': '상품 통계 조회 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'code': {'type': 'string', 'example': 'FLASK-200'},
                    'message': {'type': 'string', 'example': '상품 통계 조회 성공'},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                    'userMessageId': {'type': 'string', 'example': 'msg-001'},
                    'result': {
                        'type': 'object',
                        'properties': {
                            'reordered': {
                                'type': 'array',
                                'items': {'type': 'object', 'properties': {
                                    'label': {'type': 'integer', 'example': 1},
                                    'count': {'type': 'integer', 'example': 0}
                                }}
                            },
                            'orderHour': {
                                'type': 'array',
                                'items': {'type': 'object', 'properties': {
                                    'label': {'type': 'integer', 'example': 13},
                                    'count': {'type': 'integer', 'example': 12}
                                }}
                            },
                            'orderDow': {
                                'type': 'array',
                                'items': {'type': 'object', 'properties': {
                                    'label': {'type': 'integer', 'example': 0},
                                    'count': {'type': 'integer', 'example': 8}
                                }}
                            },
                            'relatedProduct': {
                                'type': 'array',
                                'items': {'type': 'object', 'properties': {
                                    'productId': {'type': 'integer', 'example': 12345},
                                    'label': {'type': 'string', 'example': '오이'},
                                    'count': {'type': 'integer', 'example': 7}
                                }}
                            },
                            'report': {'type': 'string', 'example': '해당 상품은 10시와 14시에 가장 많이 구매됩니다.'}
                        }
                    }
                }
            }
        }
    }
})
def get_product_statistics(productId: int):
    return ProductService.get_product_orders_statiscis(productId)

@product_routes.route("", methods=["GET"])
@swag_from({
    'tags': ['Product'],
    'summary': '상품 목록 조회',
    'description': '요청한 협찬사의 상품 목록을 조회합니다.',
    'parameters': [
        {
            'name': 'sponsorId',
            'in': 'query',
            'type': 'integer',
            'required': True,
            'description': '조회할 협찬사 ID'
        },
    ],
    'responses': {
        '200': {
            'description': '상품 목록 조회 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'code': {'type': 'string', 'example': 'FLASK-200'},
                    'message': {'type': 'string', 'example': '상품 목록 조회 성공'},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                    'userMessageId': {'type': 'string', 'example': 'msg-001'},
                    'result': {
                        'type': 'object',
                        'properties': {
                            'products': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'productId': {'type': 'integer', 'example': 12345},
                                        'productName': {'type': 'string', 'example': '오이'}
                                    }
                                }
                            },
                            'report': {
                                'type': 'string',
                                'example': '총 10개의 상품이 등록되어 있습니다.'
                            }
                        }
                    }
                }
            }
        }
    }
})
def get_products():
    sponsor_id = request.args.get('sponsorId', type=int)
    if not sponsor_id:
        return {
            "isSuccess": False,
            "code": "INVALID-REQUEST",
            "message": "sponsorId 파라미터가 필요합니다.",
            "timestamp": datetime.datetime.now(kst).isoformat()
        }, 400
    return ProductService.get_products_by_sponsor_id(sponsor_id)