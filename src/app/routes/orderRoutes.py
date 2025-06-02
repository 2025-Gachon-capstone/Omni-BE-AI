from flask import Blueprint
from flasgger import swag_from

from ..services import OrderService

order_routes = Blueprint('order_routes', __name__, url_prefix='/flask/v1/orders')

@order_routes.route("/<int:order_id>", methods=["POST"])
@swag_from({
    'tags': ['Service-Order'],
    'summary': '주문 저장 (Neo4j)',
    'description': 'MySQL에서 주문 ID를 조회하고, 주문 및 상품 정보를 Neo4j에 저장합니다.',
    'parameters': [
        {
            'name': 'order_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': 'Neo4j에 저장할 주문 ID'
        }
    ],
    'responses': {
        '200': {
            'description': 'Neo4j 저장 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'code': {'type': 'string', 'example': 'FLASK-200'},
                    'message': {'type': 'string', 'example': '주문 저장 성공'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        },
        '404': {
            'description': 'MySQL에 해당 주문 없음',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'code': {'type': 'string', 'example': 'MYSQL-404'},
                    'message': {'type': 'string', 'example': '해당 주문 없음'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        },
        '500': {
            'description': 'Neo4j 저장 실패',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'code': {'type': 'string', 'example': 'NEO4J-500'},
                    'message': {'type': 'string', 'example': '저장 중 오류 발생'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        }
    }
})
def post_order(order_id):
    # order_id가 없으면 매칭이 안되므로 에러 리턴 처리할 필요가 없음
<<<<<<< HEAD
    return OrderService.post_order_with_items(order_id)
=======
    return OrderService.post_order_with_items(str(order_id))
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2

