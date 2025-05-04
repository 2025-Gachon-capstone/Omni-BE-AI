# API 테스트
from flask import Blueprint
from flasgger import swag_from

from ..services import test as test_service

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
    return str(response_data), 200