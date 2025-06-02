import pandas as pd
<<<<<<< HEAD
import os
=======
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
from src.app.repositories.neo4j.OrderRepository import Neo4jOrderRepository 
from src.app.models.graphModels import Member, Product, Order, Benefit, Sponsor
from neomodel.exceptions import NeomodelException
from neomodel import config as neomodel_config
from src.app.config import config  # config/__init__.py에서 config 객체를 export함
<<<<<<< HEAD
from neomodel import db  # Cypher 쿼리 실행을 위해 추가
=======
from src.app.utils import ts
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
from src.app.utils.text_embedding import get_text_embedding
from src.app.utils.normalizaiton import min_max_normalize


host = config.NEO4J_HOST
port = config.NEO4J_PORT
neomodel_config.DATABASE_URL = f'bolt://{config.NEO4J_USER}:{config.DB_PASSWORD}@{host}:{port}'

<<<<<<< HEAD
# 로그 디렉토리 설정
LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

=======
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
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
<<<<<<< HEAD
            member_ids = Neo4jOrderRepository.create_next_order_relations()
            print(f"[SUCCESS] 관계 생성된 멤버 수: {len(member_ids)}")
            for mid in member_ids:
                print(f" - member_id: {mid}")
            return True, member_ids
        except Exception as e:
            print(f"[ERROR] NEXT 관계 생성 실패: {e}")
            return False, []
        
    @staticmethod
    def upload_csv_to_neo4j(csv_path, start_index=0):
        # 로그 파일 경로 설정
        log_file = os.path.join(LOG_DIR, 'upload_progress.txt')
        failed_rows = []
        current_batch_start = start_index
        batch_size = 10000

        try:
            print("[INFO] 기존 모든 노드와 관계를 삭제합니다...")
            db.cypher_query("MATCH (n) DETACH DELETE n;")
            print("[INFO] 삭제 완료. 데이터 업로드를 시작합니다.")
        except Exception as e:
            print(f"[ERROR] 전체 삭제 중 오류 발생: {e}")
            return

        try:
            df = pd.read_csv(csv_path)
            total_rows = len(df)
            if start_index >= total_rows:
                print(f"[ERROR] 시작 인덱스({start_index})가 전체 행 수({total_rows})보다 큽니다.")
                return
            
            # start_index부터 시작
            df = df.iloc[start_index:]
            
=======
            total_count = 0
            batch_num = 1

            while True:
                member_ids = Neo4jOrderRepository.create_next_order_relations()
                count = len(member_ids)

                if count == 0:
                    print("[INFO] 더 이상 생성할 NEXT 관계가 없습니다.")
                    break

                total_count += count
                print(f"[BATCH {batch_num}] 생성된 멤버 수: {count}")
                batch_num += 1

            print(f"[SUCCESS] 전체 NEXT 관계 생성 완료 — 총 {batch_num - 1}회 배치, 총 멤버 수: {total_count}")
            return {
                "isSuccess": True,
                "code": "NEO4J-200",
                "message": "NEXT 관계 생성 완료",
                "timestamp": ts(),
            }, 200

        except Exception as e:
            print(f"[ERROR] NEXT 관계 생성 중 예외 발생: {e}")
            return {
                "isSuccess": False,
                "code": "NETWORK-ERR",
                "message": f"Neo4j DB 통신 실패: {e}",
                "timestamp": ts(),
            }, 500
        
    @staticmethod
    def delete_next_relations() -> bool:
        try:
            total_deleted = 0
            batch_num = 1
            batch_size = 100  # 필요시 조절 가능

            while True:
                deleted = Neo4jOrderRepository.delete_next_relations_in_batches(batch_size=batch_size)
                if deleted == 0:
                    print("[INFO] 더 이상 삭제할 NEXT 관계가 없습니다.")
                    break

                total_deleted += deleted
                print(f"[BATCH {batch_num}] 삭제된 NEXT 수: {deleted}")
                batch_num += 1

            print(f"[SUCCESS] 전체 NEXT 관계 삭제 완료 — 총 {batch_num - 1}회 배치, 총 삭제 수: {total_deleted}")
            return {
                "isSuccess": True,
                "code": "NEO4J-202",
                "message": "NEXT 관계 삭제 완료",
                "timestamp": ts(),
            }, 202

        except Exception as e:
            print(f"[ERROR] NEXT 관계 삭제 중 예외 발생: {e}")
            return {
                "isSuccess": False,
                "code": "NETWORK-ERR",
                "message": f"Neo4j DB 통신 실패: {e}",
                "timestamp": ts(),
            }, 500
        
    @staticmethod
    def upload_csv_to_neo4j(csv_path):
        # try:
        #     print("[INFO] 기존 모든 노드와 관계를 삭제합니다...")
        #     db.cypher_query("MATCH (n) DETACH DELETE n;")
        #     print("[INFO] 삭제 완료. 데이터 업로드를 시작합니다.")
        # except Exception as e:
        #     print(f"[ERROR] 전체 삭제 중 오류 발생: {e}")
        #     return

        try:
            df = pd.read_csv(csv_path)
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
        except Exception as e:
            print(f"[ERROR] CSV 파일을 읽는 중 오류 발생: {e}")
            return

        for idx, row in df.iterrows():
            try:
<<<<<<< HEAD
                print(f"[INFO] {idx+1}/{total_rows}번째 row 처리 중...")
=======
                print(f"[INFO] {idx+1}/{len(df)}번째 row 처리 중...")
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2

                # 1. Member 노드 생성/조회 및 속성 할당
                member_id = safe_int(row['user_id'])
                member = Member.get_or_create({'member_id': member_id})[0]
                print(f"  [DEBUG] Member({member_id}) 생성/조회 완료")
<<<<<<< HEAD
=======
                # predict_order_list는 빈 리스트로 초기화 (나중에 모델 학습 후 채움)
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
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
<<<<<<< HEAD
                
                # get_or_create는 (node, created) 튜플을 반환함
                product, created = Product.get_or_create({
                    'product_id': product_id,
                    'name': product_name,
                    'category': department
                })
                
                # 새로 생성된 제품의 경우에만 임베딩 생성
                if created:
                    product.name_vector = get_text_embedding(product_name, task="상품명 임베딩") if product_name else []
                    product.category_vector = get_text_embedding(department, task="카테고리 임베딩") if department else []
                    product.node_embedding = []
                    product.save()
                    print(f"  [DEBUG] Product({product_id}) 생성 및 임베딩 생성 완료")
                else:
                    print(f"  [DEBUG] Product({product_id}) 기존 제품 조회 완료")

                # 3. Order 노드 생성/조회 및 속성 할당
                order_id = safe_int(row['order_id'])
                eval_set_value = str(row['eval_set']).upper() if not pd.isna(row['eval_set']) else ""
                order_count = safe_float(row['order_number'])
=======
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
                order_number = safe_float(row['order_number'])
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
                order_dow = safe_float(row['order_dow'])
                order_hour_of_day = safe_float(row['order_hour_of_day'])
                days_since_prior_order = safe_float(row['days_since_prior_order'])
                order = Order.get_or_create({
                    'order_id': order_id,
<<<<<<< HEAD
                    'eval_set': eval_set_value,
                    'order_count': order_count,
=======
                    'eval_set': eval_set_value, # 대문자로 변환된 값 사용
                    'order_number': order_number,
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
                    'order_dow': order_dow,
                    'order_hour_of_day': order_hour_of_day,
                    'days_since_prior_order': days_since_prior_order,
                    'node_embedding': [],
                    'predict_order_list': [],
                    'next_order_list': [],
<<<<<<< HEAD
                    'loss': 0.0
                })[0]
                # 정규화 값 저장 (정규화 구간은 0~1로 가정, 실제 min/max는 데이터셋에 맞게 조정 필요)
                order.order_count_norm = min_max_normalize(order_count, 0, 1)
=======
                    'loss': 0.0  # FloatProperty는 None으로 초기화 가능
                })[0]
                # 정규화 값 저장 (정규화 구간은 0~1로 가정, 실제 min/max는 데이터셋에 맞게 조정 필요)
                order.order_number_norm = min_max_normalize(order_number, 0, 1)
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
                order.order_dow_norm = min_max_normalize(order_dow, 0, 1)
                order.order_hour_of_day_norm = min_max_normalize(order_hour_of_day, 0, 1)
                order.days_since_prior_order_norm = min_max_normalize(days_since_prior_order, 0, 1)
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
<<<<<<< HEAD

                # 배치 단위로 진행상황 저장
                if (idx - start_index + 1) % batch_size == 0 or idx == total_rows - 1:
                    current_batch_end = idx
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(f"[{current_batch_start + 1}~{current_batch_end + 1}] 작업 완료\n")
                        if failed_rows:
                            f.write(f"실패한 행: {', '.join(map(str, failed_rows))}\n")
                        f.write("\n")
                    # 다음 배치를 위한 초기화
                    current_batch_start = current_batch_end + 1
                    failed_rows = []

            except NeomodelException as ne:
                print(f"[ERROR] Neo4j 작업 중 오류 발생: {ne}")
                print("[TIP] Neo4j 서버가 실행 중인지, 연결 정보가 올바른지 확인하세요.")
                failed_rows.append(idx + 1)
                return
            except Exception as e:
                print(f"[ERROR] {idx+1}번째 row 처리 중 예외 발생: {e}")
                failed_rows.append(idx + 1)
=======
            except NeomodelException as ne:
                print(f"[ERROR] Neo4j 작업 중 오류 발생: {ne}")
                print("[TIP] Neo4j 서버가 실행 중인지, 연결 정보가 올바른지 확인하세요.")
                return
            except Exception as e:
                print(f"[ERROR] {idx+1}번째 row 처리 중 예외 발생: {e}")
>>>>>>> bfb0f725114b66322e31b7805753f7784badc2f2
                continue