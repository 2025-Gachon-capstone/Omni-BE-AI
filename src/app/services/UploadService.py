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
    def upload_csv_to_neo4j(csv_path, start_row=0):
        '''
        try:
            print("[INFO] 기존 모든 노드와 관계를 삭제합니다...")
            db.cypher_query("MATCH (n) DETACH DELETE n;")
            print("[INFO] 삭제 완료. 데이터 업로드를 시작합니다.")
        except Exception as e:
            print(f"[ERROR] 전체 삭제 중 오류 발생: {e}")
            return

        # start_row: 업로드를 시작할 행 번호 (0부터 시작)
        '''
        log_path = './resources/upload_log.txt'
        batch_size = 10000
        failed_rows = []
        batch_start = start_row
        
        try:
            df = pd.read_csv(csv_path, skiprows=range(1, start_row+1))
        except Exception as e:
            print(f"[ERROR] CSV 파일을 읽는 중 오류 발생: {e}")
            return
            
        processed = 0
        for idx, row in enumerate(df.itertuples(index=False), start=start_row):
            try:
                print(f"[INFO] {idx+1}/{len(df)+start_row}번째 row 처리 중...")
                member_id = safe_int(row[0])
                member = Member.get_or_create({'member_id': member_id})[0]
                member.predict_order_list = []
                member.metadata = ''
                member.metadata_vector = []
                member.predict_order_list = []
                member.save()
                product_id = safe_int(row[1])
                product_name = str(row[2]) if len(row) > 2 and not pd.isna(row[2]) else ''
                department = str(row[3]) if len(row) > 3 and not pd.isna(row[3]) else ''
                product = Product.get_or_create({
                    'product_id': product_id,
                    'name': product_name,
                    'category': department
                })[0]
                product.name_vector = get_text_embedding(product_name, task="상품명 임베딩") if product_name else []
                product.category_vector = get_text_embedding(department, task="카테고리 임베딩") if department else []
                product.node_embedding = []
                product.save()
                order_id = safe_int(row[4])
                eval_set_value = str(row[5]).upper() if len(row) > 5 and not pd.isna(row[5]) else ""
                order_count = safe_float(row[6]) if len(row) > 6 else 0.0
                order_dow = safe_float(row[7]) if len(row) > 7 else 0.0
                order_hour_of_day = safe_float(row[8]) if len(row) > 8 else 0.0
                days_since_prior_order = safe_float(row[9]) if len(row) > 9 else 0.0
                order = Order.get_or_create({
                    'order_id': order_id,
                    'eval_set': eval_set_value,
                    'order_count': order_count,
                    'order_dow': order_dow,
                    'order_hour_of_day': order_hour_of_day,
                    'days_since_prior_order': days_since_prior_order,
                    'node_embedding': [],
                    'predict_order_list': [],
                    'next_order_list': [],
                    'loss': 0.0
                })[0]
                order.order_count_vector = min_max_normalize(order_count, 0, 1)
                order.order_dow_vector = min_max_normalize(order_dow, 0, 1)
                order.order_hour_of_day_vector = min_max_normalize(order_hour_of_day, 0, 1)
                order.days_since_prior_order_vector = min_max_normalize(days_since_prior_order, 0, 1)
                order.save()
                if not member.ordered.is_connected(order):
                    member.ordered.connect(order)
                    print(f"  [DEBUG] Member({member_id})-ORDERED->Order({order_id}) 관계 생성 완료")
                else:
                    print(f"  [DEBUG] Member({member_id})-ORDERED->Order({order_id}) 이미 연결됨")
                add_to_cart_order = safe_float(row[10]) if len(row) > 10 else 0.0
                reordered = bool(safe_int(row[11])) if len(row) > 11 else False
                if not order.contains.is_connected(product):
                    order.contains.connect(product, {
                        'add_to_cart_order': add_to_cart_order,
                        'reordered': reordered
                    })
            except NeomodelException as ne:
                print(f"[ERROR] Neo4j 작업 중 오류 발생: {ne}")
                print("[TIP] Neo4j 서버가 실행 중인지, 연결 정보가 올바른지 확인하세요.")
                failed_rows.append(idx+1)
            except Exception as e:
                print(f"[ERROR] {idx+1}번째 row 처리 중 예외 발생: {e}")
                failed_rows.append(idx+1)
            processed += 1
            # 10000개 단위로 로그 기록
            if processed % batch_size == 0:
                batch_end = idx + 1
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(f"[{batch_start+1} ~ {batch_end}번째 행 작업 기록]\n")
                    if failed_rows:
                        f.write("실패한 행: " + ", ".join(map(str, failed_rows)) + "\n\n")
                    else:
                        f.write("실패한 행: (없음)\n\n")
                batch_start = batch_end
                failed_rows = []
        # 마지막 남은 구간도 기록
        if processed % batch_size != 0:
            batch_end = start_row + processed
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"[{batch_start+1} ~ {batch_end}번째 행 작업 기록]\n")
                if failed_rows:
                    f.write("실패한 행: " + ", ".join(map(str, failed_rows)) + "\n\n")
                else:
                    f.write("실패한 행: (없음)\n\n")