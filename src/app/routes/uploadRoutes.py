from flask import Blueprint, current_app, request
from flasgger import swag_from
from datetime import datetime

from src.app.services.EmbeddingService import EmbeddingService
from src.app.services.OrderService import OrderService

from ..services import UploadService
from ..services.UploadService import UploadService

upload_routes = Blueprint('upload_routes', __name__, url_prefix='/flask/v1/upload')

# uploadRoutes.py
from types import SimpleNamespace
from src.app.services.EmbeddingService import EmbeddingService

def _get_embedding_service() -> EmbeddingService:
    container = current_app.extensions["container"]  # create_app에서 넣어둠

    # 기존에 넣어둔 값이 있으면 사용, 없거나 필수 필드 없으면 기본값 구성
    bert_args = current_app.config.get("bert_args")
    if not bert_args or not hasattr(bert_args, "max_seq_length"):
        bert_args = SimpleNamespace(
            # 🔧 EmbeddingService/post_missing_user_embeddings에서 사용하는 값들 기본 제공
            max_seq_length=100,      # 본문 100 길이 시퀀스
            user_token_prefix="USR_",# [USR_<id>] 프리픽스
            device="cpu",            # 필요하다면 "cuda"
            batch_size=16            # 기본 배치
        )

    return EmbeddingService(
        vocab=container.vocab,
        predictor=container.predictor,
        args=bert_args
    )

@upload_routes.post("/members/embeddings/missing")
@swag_from({
    'tags': ['Service-Upload'],
    'summary': 'node_embedding 없는 멤버만 임베딩 생성 후 Neo4j 저장',
    'description': (
        'Neo4j의 Member 중 node_embedding이 비어있는 멤버만 대상으로, '
        'MySQL에서 각 멤버의 최신 100개 구매를 가져와 [USR_<id>] + 본문 100 길이 시퀀스로 임베딩합니다. '
        '결과 벡터는 Member.node_embedding에 저장합니다.'
    ),
    'parameters': [
        {'name': 'limit_users', 'in': 'query', 'type': 'integer', 'required': False, 'description': '최대 처리 멤버 수 상한'},
        {'name': 'page_size', 'in': 'query', 'type': 'integer', 'required': False, 'description': '멤버 페이징(조회) 크기, 기본 2048'},
        {'name': 'embed_batch', 'in': 'query', 'type': 'integer', 'required': False, 'description': '임베딩 배치 크기, 기본 16(CPU/노트북 권장)'},
        {'name': 'save_page_size', 'in': 'query', 'type': 'integer', 'required': False, 'description': 'Neo4j 업서트 슬라이스 크기, 기본 1000'},
        {'name': 'dry_run', 'in': 'query', 'type': 'boolean', 'required': False, 'description': 'True면 저장하지 않고 카운트만 반환'}
    ],
    'responses': {
        '200': {
            'description': '처리 통계',
            'schema': {
                'type': 'object',
                'properties': {
                    'isSuccess': {'type': 'boolean', 'example': True},
                    'code': {'type': 'string', 'example': 'SUCCESS'},
                    'result': {
                        'type': 'object',
                        'properties': {
                            'toProcess': {'type': 'integer', 'example': 2048},
                            'produced': {'type': 'integer', 'example': 2048},
                            'skippedEmpty': {'type': 'integer', 'example': 10},
                            'failed': {'type': 'array', 'items': {'type': 'integer'}}
                        }
                    },
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            }
        }
    }
})
def create_missing_member_embeddings():
    svc = _get_embedding_service()

    limit_users     = request.args.get('limit_users', default=None, type=int)
    page_size       = request.args.get('page_size', default=2048, type=int)
    embed_batch     = request.args.get('embed_batch', default=16, type=int)      # ✅ 기본 16
    save_page_size  = request.args.get('save_page_size', default=1000, type=int)
    dry_run         = request.args.get('dry_run', default=False, type=lambda v: str(v).lower() in ('1','true','yes'))

    # EmbeddingService.post_missing_user_embeddings 시그니처에 맞춰 전달
    resp, status = svc.post_missing_user_embeddings(
        limit_users=limit_users,
        page_size=page_size,
        batch_embed=embed_batch,
        save_page_size=save_page_size,
        dry_run=dry_run
    )
    return resp, status

@upload_routes.route("", methods=["GET"])
@swag_from({
    'tags': ['Service-Upload'],
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

@upload_routes.route("/metadata", methods=["GET"])
@swag_from({
    'tags': ['Service-Upload'],
    'summary': '모든 멤버 metadata 일괄 갱신',
    'description': 'Neo4j에 저장된 모든 멤버의 최근 5개 주문을 기반으로 Gemini를 활용해 metadata를 일괄 갱신합니다. 이미 metadata가 존재하는 멤버는 건너뜁니다.',
    'parameters': [
        {
            'name': 'max_count',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'description': '최대 갱신할 멤버 수 (기본값: 100)'
        }
    ],
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
