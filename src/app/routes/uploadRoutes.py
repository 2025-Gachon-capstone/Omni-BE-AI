from flask import Blueprint, request
from flasgger import swag_from
from datetime import datetime

from src.app.services.OrderService import OrderService

from ..services import UploadService
from ..services.UploadService import UploadService

upload_routes = Blueprint('upload_routes', __name__, url_prefix='/flask/v1/upload')

<<<<<<< HEAD
"""
### 미사용
=======
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
@upload_routes.route("", methods=["GET"])
@swag_from({
    'tags': ['Service-Upload'],
    'summary': 'CSV 파일을 Neo4j로 업로드',
    'description': 'resources/csv/uploads.csv 파일의 데이터를 Neo4j에 일괄 업로드합니다. 기존 노드와 관계는 모두 삭제됩니다.',
<<<<<<< HEAD
    'parameters': [
        {
            'name': 'start_index',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'default': 0,
            'description': '데이터 업로드를 시작할 행 번호 (0부터 시작)'
        }
    ],
=======
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
    'responses': {
        '200': {
            'description': 'Neo4j 저장 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'code': {'type': 'string', 'example': 'FLASK-200'},
                    'message': {'type': 'string', 'example': '업로드 완료'},
<<<<<<< HEAD
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                    'start_index': {'type': 'integer', 'example': 0}
=======
                    'timestamp': {'type': 'string', 'format': 'date-time'}
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
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
<<<<<<< HEAD
            # start_index 파라미터 가져오기 (기본값 0)
            start_index = request.args.get('start_index', default=0, type=int)
            
            result = UploadService.upload_csv_to_neo4j("resources/csv/uploads.csv", start_index=start_index)
=======
            result = UploadService.upload_csv_to_neo4j("resources/csv/uploads.csv")
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
            # 성공 시
            return {
                "isSuccess": True,
                "code": "FLASK-200",
                "message": "업로드 완료",
<<<<<<< HEAD
                "timestamp": datetime.now().isoformat(),
                "start_index": start_index
=======
                "timestamp": datetime.now().isoformat()
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
            }, 200
        except Exception as e:
            # 실패 시
            return {
                "isSuccess": False,
                "code": "NEO4J-500",
                "message": f"업로드 중 오류 발생: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }, 500
<<<<<<< HEAD
"""
=======
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2

@upload_routes.route("/metadata", methods=["GET"])
@swag_from({
    'tags': ['Service-Upload'],
    'summary': '모든 멤버 metadata 일괄 갱신',
    'description': 'Neo4j에 저장된 모든 멤버의 최근 5개 주문을 기반으로 Gemini를 활용해 metadata를 일괄 갱신합니다. 이미 metadata가 존재하는 멤버는 건너뜁니다.',
<<<<<<< HEAD
=======
    'parameters': [
        {
            'name': 'max_count',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'description': '최대 갱신할 멤버 수 (기본값: 100)'
        }
    ],
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
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
def create_metadata():
<<<<<<< HEAD
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
=======
    try:
        max_count = request.args.get("max_count", default=100, type=int)
        updated_count = OrderService.update_every_member_metadata_by_gemini(max_count=max_count)
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
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2

@upload_routes.patch("/orders/create-next-edges")
@swag_from({
    'tags': ['Service-Upload'],
    'summary': 'Order 간 NEXT 관계 생성',
    'description': 'Neo4j에 저장된 각 멤버별 주문(Order) 간 시간 순서를 기준으로 NEXT 관계를 생성합니다.',
    'responses': {
        '200': {
            'description': 'NEXT 관계 생성 완료 여부',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': 'NEXT 관계 생성 완료'}
                }
            }
        },
        '500': {
            'description': 'NEXT 관계 생성 실패',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'message': {'type': 'string', 'example': 'NEXT 관계 생성 실패: 오류 메시지'}
                }
            }
        }
    }
})
def create_next_edges():
<<<<<<< HEAD
    success = UploadService.setup_next_relations()
    return {
        "isSuccess": success,
        "message": "NEXT 관계 생성 완료" if success else "NEXT 관계 생성 실패"
    }, 200

=======
    result = UploadService.setup_next_relations()
    return result

@upload_routes.delete("/orders/next-edges")
@swag_from({
    'tags': ['Service-Upload'],
    'summary': 'Order 간 NEXT 관계 전체 삭제',
    'description': 'Neo4j에 저장된 NEXT간선을 배치로 전체 삭제합니다.',
    'responses': {
        '200': {
            'description': 'NEXT 삭제 여부',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': 'NEXT 삭제 완료'}
                }
            }
        },
        '500': {
            'description': 'NEXT 삭제 실패',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': False},
                    'message': {'type': 'string', 'example': 'NEXT 관계 생성 실패: 오류 메시지'}
                }
            }
        }
    }
})
def delete_next_edges():
    result = UploadService.delete_next_relations()
    return result
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
