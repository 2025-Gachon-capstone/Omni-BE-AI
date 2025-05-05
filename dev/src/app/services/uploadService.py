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
                'loss': None  # FloatProperty는 None으로 초기화 가능
            })[0]
            # 정규화 값 저장 (정규화 구간은 0~1로 가정, 실제 min/max는 데이터셋에 맞게 조정 필요)
            order.order_count_vector = min_max_normalize(order_count, 0, 1)
            order.order_dow_vector = min_max_normalize(order_dow, 0, 1)
            order.order_hour_of_day_vector = min_max_normalize(order_hour_of_day, 0, 1)
            order.days_since_prior_order_vector = min_max_normalize(days_since_prior_order, 0, 1)
            # predict_order_list, next_order_list, loss는 get_or_create에서 초기화됨
            order.save()
