from flask import Blueprint, request
from flasgger import swag_from
from datetime import datetime

from ..services import UploadService
from ..services import OrderService

ml_routes = Blueprint('ml_routes', __name__, url_prefix='/flask/v1/ml')

@ml_routes.route("/uploads", methods=["GET"])
@swag_from({
    'tags': ['Service-ML'],
    'summary': 'CSV 파일을 Neo4j로 업로드',
    'description': 'resources/csv/uploads.csv 파일의 데이터를 Neo4j에 일괄 업로드합니다. 기존 노드와 관계는 모두 삭제됩니다.',
    'responses': {
        '200': {
            'description': 'Neo4j 저장 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'code': {'type': 'string', 'example': 'FLASK-200'},
                    'message': {'type': 'string', 'example': '업로드 완료'},
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
                    'message': {'type': 'string', 'example': '업로드 중 오류 발생'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        }
    }
})
def upload_csv():
    print("ml.uploads")
    if request.method == "GET":
        try:
            result = UploadService.upload_csv_to_neo4j("resources/csv/uploads.csv")
            # 성공 시
            return {
                "isSuccess": True,
                "code": "FLASK-200",
                "message": "업로드 완료",
                "timestamp": datetime.now().isoformat()
            }, 200
        except Exception as e:
            # 실패 시
            return {
                "isSuccess": False,
                "code": "NEO4J-500",
                "message": f"업로드 중 오류 발생: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }, 500

@ml_routes.route("/metadata", methods=["GET"])
@swag_from({
    'tags': ['Service-ML'],
    'summary': '모든 멤버 metadata 일괄 갱신',
    'description': 'Neo4j에 저장된 모든 멤버의 최근 5개 주문을 기반으로 Gemini를 활용해 metadata를 일괄 갱신합니다. 이미 metadata가 존재하는 멤버는 건너뜁니다.',
    'responses': {
        '200': {
            'description': 'metadata 일괄 갱신 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'updated_count': {'type': 'integer', 'example': 42}
                }
            }
        },
        '500': {
            'description': 'metadata 갱신 중 오류',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'message': {'type': 'string', 'example': 'metadata 갱신 중 오류 발생'}
                }
            }
        },
        '503': {
            'description': 'AI 서비스 호출 중단',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'code': {'type': 'string', 'example': 'AI-503'},
                    'message': {'type': 'string', 'example': 'AI 서비스 호출 중단: ...'},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                    'result': {'type': 'object', 'example': {'updated_count': 10}}
                }
            }
        }
    }
})
def metadata():
    print("ml.metadata")
    if request.method == "GET":
        try:
            updated_count = OrderService.update_every_member_metadata_by_gemini()
            return {"isSuccess": True, "updated_count": updated_count}, 200
        except RuntimeError as e:
            # AI 서비스 호출 중단(429 등) 발생 시 503 반환
            return {
                "isSuccess": False,
                "code": "AI-503",
                "message": str(e),
                "timestamp": datetime.now().isoformat(),
                "result": None
            }, 503
        except Exception as e:
            return {
                "isSuccess": False,
                "message": f"metadata 갱신 중 오류 발생: {str(e)}"
            }, 500

