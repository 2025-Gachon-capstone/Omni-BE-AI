# API 테스트
from flask import Blueprint
from flasgger import swag_from

from ..services import test as test_service
<<<<<<< HEAD
from ..services.embeddingService import EmbeddingService
=======
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2

test_routes = Blueprint("test_routes", __name__, url_prefix='/flask/v1')

@test_routes.route("/test", methods=["GET"])
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
    response_data = test_service()
    if isinstance(response_data, tuple):
        return response_data
<<<<<<< HEAD
    return str(response_data), 200

@test_routes.route("/embedding", methods=["PATCH"])
@swag_from({
    'tags': ['Test'],
    'summary': '모든 Product 임베딩',
    'description': 'Neo4j에 저장된 모든 Product 노드의 name, category를 임베딩하고 저장합니다.',
    'responses': {
        '200': {
            'description': 'Product 임베딩 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': 'Product 임베딩 완료'}
                }
            }
        },
        '500': {
            'description': 'Product 임베딩 실패',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'message': {'type': 'string', 'example': 'Product 임베딩 실패: 오류 메시지'}
                }
            }
        }
    }
})
def test_embed_products():
    try:
        service = EmbeddingService()
        service.embed_all_products()
        return {
            "isSuccess": True,
            "message": "Product 임베딩 완료"
        }, 200
    except Exception as e:
        return {
            "isSuccess": False,
            "message": f"Product 임베딩 실패: {str(e)}"
        }, 500
=======
    return str(response_data), 200
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
