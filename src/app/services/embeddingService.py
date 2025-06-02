import time
from neomodel import config as neomodel_config, db
from src.app.models.graphModels import Product  # Product 모델 경로 가정
from src.app.utils.text_embedding import get_text_embedding  # 임베딩 함수 경로 가정
from src.app.config import config  # Neo4j 설정 정보 경로 가정
from neomodel.exceptions import DoesNotExist, NeomodelException

class EmbeddingService:
    def __init__(self):
        self.connect_to_neo4j()

    def connect_to_neo4j(self):
        """Neo4j 데이터베이스에 연결합니다."""
        try:
            host = config.NEO4J_HOST
            port = config.NEO4J_PORT
            user = config.NEO4J_USER
            password = config.DB_PASSWORD # 설정 파일의 변수명에 따라 변경될 수 있음
            neomodel_config.DATABASE_URL = f'bolt://{user}:{password}@{host}:{port}'
            db.cypher_query("RETURN 1") # 간단한 쿼리로 연결 테스트
            print("[SUCCESS] Neo4j에 성공적으로 연결되었습니다.")
        except Exception as e:
            print(f"[ERROR] Neo4j 연결 실패: {e}")
            print("[TIP] Neo4j 서버가 실행 중인지, 연결 정보(.env 또는 config 파일)가 올바른지 확인하세요.")
            raise  # 연결 실패 시 더 이상 진행하지 않도록 예외 발생

    def embed_all_products(self):
        """모든 Product 노드의 name과 category를 임베딩하고 저장합니다."""
        print("[INFO] Product 임베딩 작업을 시작합니다...")
        start_time = time.time()

        try:
            products = Product.nodes.all()
            total_products = len(products)
            print(f"[INFO] 총 {total_products}개의 Product 노드를 찾았습니다.")

            if total_products == 0:
                print("[INFO] 임베딩할 Product가 없습니다. 작업을 종료합니다.")
                return

            for i, product_node in enumerate(products):
                product_id = product_node.product_id
                product_name = product_node.name
                product_category = product_node.category

                # 이미 임베딩된 노드는 건너뜀
                if product_node.name_vector and product_node.category_vector:
                    print(f"  [DEBUG] Product ID: {product_id}는 이미 임베딩되어 있어 건너뜁니다.")
                    continue

                print(f"--- [PROGRESS] {i+1}/{total_products} ---")
                print(f"  [DEBUG] Product ID: {product_id}, Name: '{product_name}', Category: '{product_category}' 임베딩 시작...")

                try:
                    # Name 임베딩
                    if product_name and isinstance(product_name, str) and product_name.strip():
                        print(f"    [DEBUG] Name ('{product_name}') 임베딩 중...")
                        name_embedding_start = time.time()
                        product_node.name_vector = get_text_embedding(product_name, task="상품명 임베딩")
                        name_embedding_end = time.time()
                        print(f"    [SUCCESS] Name 임베딩 완료 (소요 시간: {name_embedding_end - name_embedding_start:.2f}초). Vector 일부: {str(product_node.name_vector)[:50]}...")
                    else:
                        print(f"    [WARN] Name이 비어있거나 유효하지 않아 임베딩을 건너뜁니다. Name: {product_name}")
                        product_node.name_vector = []

                    # Category 임베딩
                    if product_category and isinstance(product_category, str) and product_category.strip():
                        print(f"    [DEBUG] Category ('{product_category}') 임베딩 중...")
                        category_embedding_start = time.time()
                        product_node.category_vector = get_text_embedding(product_category, task="카테고리 임베딩")
                        category_embedding_end = time.time()
                        print(f"    [SUCCESS] Category 임베딩 완료 (소요 시간: {category_embedding_end - category_embedding_start:.2f}초). Vector 일부: {str(product_node.category_vector)[:50]}...")
                    else:
                        print(f"    [WARN] Category가 비어있거나 유효하지 않아 임베딩을 건너뜁니다. Category: {product_category}")
                        product_node.category_vector = []
                    
                    # node_embedding은 여기서 초기화하지 않거나, 필요시 별도 로직으로 채워야 합니다.
                    # 현재는 name_vector와 category_vector만 업데이트합니다.
                    if not hasattr(product_node, 'node_embedding') or product_node.node_embedding is None:
                         product_node.node_embedding = []


                    product_node.save()
                    print(f"  [SUCCESS] Product ID: {product_id}의 임베딩 벡터 저장 완료.")

                except Exception as e_node:
                    print(f"  [ERROR] Product ID: {product_id} 처리 중 오류 발생: {e_node}")
                    # 개별 노드 오류 시 계속 진행할지, 전체 중단할지 결정 (여기서는 계속 진행)
                    continue
            
            end_time = time.time()
            print(f"[SUCCESS] 모든 Product 임베딩 작업 완료! 총 소요 시간: {end_time - start_time:.2f}초")

        except NeomodelException as ne:
            print(f"[ERROR] Neo4j 작업 중 오류 발생: {ne}")
        except Exception as e:
            print(f"[ERROR] 전체 Product 임베딩 작업 중 예기치 않은 오류 발생: {e}")
