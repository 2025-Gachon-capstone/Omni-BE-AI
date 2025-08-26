# src/app/routes/benefitRoutes.py
from flask import Blueprint, request
from flasgger import swag_from

def create_benefits_bp(benefit_service):
    bp = Blueprint('benefit_routes', __name__, url_prefix='/flask/v2/benefits')

    @bp.route("", methods=["POST"])
    @swag_from({
        'tags': ['Benefit'],
        'summary': '맞춤 혜택 발행',
        'description': (
            'MySQL에서 행사 상품 주문 목록으로 BERT 임베딩을 추론하고, '
            'Neo4j 벡터 인덱스를 이용해 타겟 고객을 선발합니다. '
            '간결 스펙에 맞춘 요청 본문만 사용합니다.'
        ),
        'parameters': [
            {
                'name': 'sponsorId',
                'in': 'query',
                'type': 'integer',
                'required': False,
                'description': '협찬사 ID (로그/추적용)'
            }
        ],
        'requestBody': {
            'required': True,
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'reorderedRatio': {
                                'type': 'number',
                                'description': '재구매 비율(0~1). 예: 0.6 → 재구매 60%, 첫구매 40%',
                                'minimum': 0.0,
                                'maximum': 1.0,
                                'example': 0.6
                            },
                            'excludedProductIdList': {
                                'type': 'array',
                                'items': {'type': 'integer'},
                                'description': '같이 구매된 상품 중 제외할 상품 ID 목록',
                                'example': [1, 2, 3]
                            },
                            'title': {
                                'type': 'string',
                                'description': '캠페인/쿠폰 제목',
                                'example': '신규런칭 기획전 X 협찬'
                            },
                            'startDate': {
                                'type': 'string',
                                'format': 'date',
                                'description': '캠페인 시작 일 (시간 없음, 한국 시간대))',
                                'example': '2025-08-20'
                            },
                            'endDate': {
                                'type': 'string',
                                'format': 'date',
                                'description': '캠페인 종료 일 (시간 없음, 한국 시간대)',
                                'example': '2025-08-27'
                            },
                            'discountRate': {
                                'type': 'number',
                                'description': '할인율(소수, 예: 0.1 → 10%)',
                                'example': 0.1
                            },
                            'targetProductId': {
                                'type': 'integer',
                                'description': '행사(타겟) 상품 ID',
                                'example': 12345
                            },
                            'amount': {
                                'type': 'integer',
                                'description': '발행할 총 쿠폰 수량',
                                'minimum': 1,
                                'example': 100
                            },
                            'status': {
                                'type': 'string',
                                'description': '상태값 (PENDING, COMPLETED)',
                                'example': 'PENDING',
                                'enum': ['PENDING', 'COMPLETED']
                            }
                        },
                        'required': ['targetProductId', 'amount']
                    }
                }
            }
        },
        'responses': {
            '200': {
                'description': '성공',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'isSuccess': {'type': 'boolean', 'example': True},
                        'code': {'type': 'string', 'example': 'SUCCESS'},
                        'result': {
                            'type': 'object',
                            'properties': {
                                'orderCount': {'type': 'integer', 'example': 100},
                                'embeddings': {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'number'}}},
                                'centroid': {'type': 'array', 'items': {'type': 'number'}},
                                'selectedMemberIds': {'type': 'array', 'items': {'type': 'string'}},
                                'selectedCount': {'type': 'integer', 'example': 100}
                            }
                        }
                    }
                }
            },
            '404': {'description': 'MySQL에 해당 주문 없음'},
            '500': {'description': '서버 오류'}
        }
    })
    def post_benefit():
        sponsor_id = request.args.get('sponsorId', type=int)
        return benefit_service.post_benefits(sponsor_id, req=request)

    return bp
