import pandas as pd
from src.app.models.graphModels import Member, Product, Order

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

def upload_csv_to_neo4j(csv_path):
    df = pd.read_csv(csv_path)

    for _, row in df.iterrows():
        # 1. Member 노드 생성/조회
        member_id = safe_int(row['user_id'])
        member, _ = Member.get_or_create({'member_id': member_id})

        # 2. Product 노드 생성/조회 (product_id만 사용)
        product_id = safe_int(row['product_id'])
        department_id = safe_float(row['department_id'])
        product, _ = Product.get_or_create({
            'product_id': product_id,
            'name': [0.0],  # 실제 임베딩/이름 대신 더미값
            'category': department_id
        })

        # 3. Order 노드 생성/조회
        order_id = safe_int(row['order_id'])
        eval_set = str(row['eval_set']) if not pd.isna(row['eval_set']) else ""
        order_count = safe_float(row['order_number'])
        order_dow = safe_float(row['order_dow'])
        order_hour_of_day = safe_float(row['order_hour_of_day'])
        days_since_prior_order = safe_float(row['days_since_prior_order'])
        order, _ = Order.get_or_create({
            'order_id': order_id,
            'eval_set': eval_set,
            'order_count': order_count,
            'order_dow': order_dow,
            'order_hour_of_day': order_hour_of_day,
            'days_since_prior_order': days_since_prior_order
        })

        # 4. Member-Order 관계 생성
        if not member.ordered.is_connected(order):
            member.ordered.connect(order)

        # 5. Order-Product(Contains) 관계 생성 (속성 포함)
        add_to_cart_order = safe_float(row['add_to_cart_order'])
        reordered = bool(safe_int(row['reordered']))
        if not order.contains.is_connected(product):
            order.contains.connect(product, {
                'add_to_cart_order': add_to_cart_order,
                'reordered': reordered
            })

if __name__ == "__main__":
    upload_csv_to_neo4j("src/resources/master_dataset_head(100).csv")