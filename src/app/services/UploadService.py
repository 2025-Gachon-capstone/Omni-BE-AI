import pandas as pd
from src.app.repositories.neo4j.OrderRepository import Neo4jOrderRepository 
from src.app.models.graphModels import Member, Product, Order, Benefit, Sponsor
from neomodel.exceptions import NeomodelException
from neomodel import config as neomodel_config
from src.app.config import config  # config/__init__.py에서 config 객체를 export함
from neomodel import db  # Cypher 쿼리 실행을 위해 추가
from src.app.utils.text_embedding import get_text_embedding
from src.app.utils.normalizaiton import min_max_normalize


host = config.NEO4J_HOST
port = config.NEO4J_PORT
neomodel_config.DATABASE_URL = f'bolt://{config.NEO4J_USER}:{config.DB_PASSWORD}@{host}:{port}'

def safe_float(val, default=0.0): 
    try:
        if pd.isna(val):
            return default
        return float(val)
    except Exception:
        return default

def safe_int(val, default=0):
    try:
        if pd.isna(val):
            return default
        return int(val)
    except Exception:
        return default

# 주의! 업로드 시작 시 모든 노드와 관계를 삭제함
# 이렇게 할 수 있는 이유는 neo4j는 관계형 DB이기에 테이블 스키마가 필요 없음

class UploadService:
    @staticmethod
    def setup_next_relations() -> bool:
        try:
            member_ids = Neo4jOrderRepository.create_next_order_relations()
            print(f"[SUCCESS] 관계 생성된 멤버 수: {len(member_ids)}")
            for mid in member_ids:
                print(f" - member_id: {mid}")
            return True, member_ids
        except Exception as e:
            print(f"[ERROR] NEXT 관계 생성 실패: {e}")
            return False, []
        
    @staticmethod
    def upload_csv_to_neo4j(csv_path):
        '''
        try:
            print("[INFO] 기존 모든 노드와 관계를 삭제합니다...")
            db.cypher_query("MATCH (n) DETACH DELETE n;")
            print("[INFO] 삭제 완료. 데이터 업로드를 시작합니다.")
        except Exception as e:
            print(f"[ERROR] 전체 삭제 중 오류 발생: {e}")
            return
        '''
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f"[ERROR] CSV 파일을 읽는 중 오류 발생: {e}")
            return

        for idx, row in df.iterrows():
            try:
                print(f"[INFO] {idx+1}/{len(df)}번째 row 처리 중...")

                # 1. Member 노드 생성/조회 및 속성 할당
                member_id = safe_int(row['user_id'])
                member = Member.get_or_create({'member_id': member_id})[0]
                print(f"  [DEBUG] Member({member_id}) 생성/조회 완료")
                # predict_order_list는 빈 리스트로 초기화 (나중에 모델 학습 후 채움)
                member.predict_order_list = []
                print(f"  [DEBUG] Member({member_id}) 생성/조회 및 속성 저장 완료")
                member.metadata = ''
                member.metadata_vector = []
                member.predict_order_list = []
                member.save()
                
                # 2. Product 노드 생성/조회 및 속성 할당
                product_id = safe_int(row['product_id'])
                product_name = str(row['product_name']) if 'product_name' in row and not pd.isna(row['product_name']) else ''
                department = str(row['department']) if 'department' in row and not pd.isna(row['department']) else ''
                product = Product.get_or_create({
                    'product_id': product_id,
                    'name': product_name,
                    'category': department
                })[0]
                product.name_vector = get_text_embedding(product_name, task="상품명 임베딩") if product_name else []
                product.category_vector = get_text_embedding(department, task="카테고리 임베딩") if department else []
                product.node_embedding = []
                product.save()
                print(f"  [DEBUG] Product({product_id}) 생성/조회 및 속성 저장 완료")

                # 3. Order 노드 생성/조회 및 속성 할당
                order_id = safe_int(row['order_id'])
                # CSV의 eval_set 값을 대문자로 변환 (prior -> PRIOR, train -> TRAIN, test -> TEST)
                eval_set_value = str(row['eval_set']).upper() if not pd.isna(row['eval_set']) else ""
                order_count = safe_float(row['order_number'])
                order_dow = safe_float(row['order_dow'])
                order_hour_of_day = safe_float(row['order_hour_of_day'])
                days_since_prior_order = safe_float(row['days_since_prior_order'])
                order = Order.get_or_create({
                    'order_id': order_id,
                    'eval_set': eval_set_value, # 대문자로 변환된 값 사용
                    'order_count': order_count,
                    'order_dow': order_dow,
                    'order_hour_of_day': order_hour_of_day,
                    'days_since_prior_order': days_since_prior_order,
                    'node_embedding': [],
                    'predict_order_list': [],
                    'next_order_list': [],
                    'loss': 0.0  # FloatProperty는 None으로 초기화 가능
                })[0]
                # 정규화 값 저장 (정규화 구간은 0~1로 가정, 실제 min/max는 데이터셋에 맞게 조정 필요)
                order.order_count_vector = min_max_normalize(order_count, 0, 1)
                order.order_dow_vector = min_max_normalize(order_dow, 0, 1)
                order.order_hour_of_day_vector = min_max_normalize(order_hour_of_day, 0, 1)
                order.days_since_prior_order_vector = min_max_normalize(days_since_prior_order, 0, 1)
                order.save()
                print(f"  [DEBUG] Order({order_id}) 생성/조회 및 속성 저장 완료")

                # 4. Member-Order 관계 생성
                if not member.ordered.is_connected(order):
                    member.ordered.connect(order)
                    print(f"  [DEBUG] Member({member_id})-ORDERED->Order({order_id}) 관계 생성 완료")
                else:
                    print(f"  [DEBUG] Member({member_id})-ORDERED->Order({order_id}) 이미 연결됨")

                # 5. Order-Product(Contains) 관계 생성 (속성 포함)
                add_to_cart_order = safe_float(row['add_to_cart_order'])
                reordered = bool(safe_int(row['reordered']))
                if not order.contains.is_connected(product):
                    order.contains.connect(product, {
                        'add_to_cart_order': add_to_cart_order,
                        'reordered': reordered
                    })
                    print(f"  [DEBUG] Order({order_id})-CONTAINS->Product({product_id}) 관계 생성 완료")
                else:
                    print(f"  [DEBUG] Order({order_id})-CONTAINS->Product({product_id}) 이미 연결됨")
            except NeomodelException as ne:
                print(f"[ERROR] Neo4j 작업 중 오류 발생: {ne}")
                print("[TIP] Neo4j 서버가 실행 중인지, 연결 정보가 올바른지 확인하세요.")
                return
            except Exception as e:
                print(f"[ERROR] {idx+1}번째 row 처리 중 예외 발생: {e}")
                continue