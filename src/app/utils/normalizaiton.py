def min_max_normalize(value, min_val, max_val):
    if value is not None and max_val > min_val:
        normalized_value = (value - min_val) / (max_val - min_val)
        return normalized_value
    elif value is not None and max_val == min_val:
        return 0.0  # 또는 다른 적절한 처리 (최대와 최소가 같으면 0으로 처리)
    return None