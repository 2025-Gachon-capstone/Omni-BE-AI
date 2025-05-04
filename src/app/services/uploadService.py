import pandas as pd
from src.app.models.graphModels import Member, Product, Order
from neomodel.exceptions import NeomodelException
from neomodel import config as neomodel_config
from src.app.config import config  # config/__init__.py에서 config 객체를 export함
from neomodel import db  # Cypher 쿼리 실행을 위해 추가


host = config.NEO4J_HOST.split(':')[0] if ':' in str(config.NEO4J_HOST) else config.NEO4J_HOST
port = config.NEO4J_PORT if hasattr(config, 'NEO4J_PORT') else 7687
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
# 이렇게 할 수 있는 이유는 neo4j는 관계형 DB이기에 테이블 설계가 필요 없음

def upload_csv_to_neo4j(csv_path):
    try:
        print("[INFO] 기존 모든 노드와 관계를 삭제합니다...")
        db.cypher_query("MATCH (n) DETACH DELETE n;")
        print("[INFO] 삭제 완료. 데이터 업로드를 시작합니다.")
    except Exception as e:
        print(f"[ERROR] 전체 삭제 중 오류 발생: {e}")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[ERROR] CSV 파일을 읽는 중 오류 발생: {e}")
        return

    for idx, row in df.iterrows():
        try:
            print(f"[INFO] {idx+1}/{len(df)}번째 row 처리 중...")
            # 1. Member 노드 생성/조회
            member_id = safe_int(row['user_id'])
            member = Member.get_or_create({'member_id': member_id})[0]
            print(f"  [DEBUG] Member({member_id}) 생성/조회 완료")

            # 2. Product 노드 생성/조회 (product_id만 사용)
            product_id = safe_int(row['product_id'])
            department_id = safe_float(row['department_id'])
            product = Product.get_or_create({
                'product_id': product_id,
                'category': department_id
            })[0]
            print(f"  [DEBUG] Product({product_id}) 생성/조회 완료")

            # 3. Order 노드 생성/조회
            order_id = safe_int(row['order_id'])
            eval_set = str(row['eval_set']) if not pd.isna(row['eval_set']) else ""
            order_count = safe_float(row['order_number'])
            order_dow = safe_float(row['order_dow'])
            order_hour_of_day = safe_float(row['order_hour_of_day'])
            days_since_prior_order = safe_float(row['days_since_prior_order'])
            order = Order.get_or_create({
                'order_id': order_id,
                'eval_set': eval_set,
                'order_count': order_count,
                'order_dow': order_dow,
                'order_hour_of_day': order_hour_of_day,
                'days_since_prior_order': days_since_prior_order
            })[0]
            print(f"  [DEBUG] Order({order_id}) 생성/조회 완료")

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



if __name__ == "__main__":
    try:
        upload_csv_to_neo4j("src/resources/master_dataset_head(100).csv")
    except Exception as e:
        print(f"[FATAL] 업로드 전체 실패: {e}")
        print("[TIP] Neo4j 서버가 실행 중인지, 연결 정보가 올바른지 확인하세요.")