# src/app/bert/preprocess.py
from collections import OrderedDict
from typing import Dict, List, Any, Optional, Tuple

def _clip_recent(seq: List[Dict[str, Any]], max_len: int) -> List[Dict[str, Any]]:
    return seq[-max_len:] if len(seq) > max_len else seq

def _validate_ranges(args, reordered, hour, aisle, dept, count_bucket):
    if reordered and (min(reordered) < 0 or max(reordered) > 2):
        raise ValueError(f"reordered out of range (0..2): min={min(reordered)}, max={max(reordered)}")
    if hour and (min(hour) < 0 or max(hour) > 25):
        raise ValueError(f"hour out of range (0..25): min={min(hour)}, max={max(hour)}")
    if aisle and max(aisle) >= getattr(args, "aisle_size", 135):
        raise ValueError("aisle index >= aisle_size")
    if dept and max(dept) >= getattr(args, "dept_size", 22):
        raise ValueError("dept index >= dept_size")
    if count_bucket and max(count_bucket) >= getattr(args, "count_bucket_size", 6):
        raise ValueError("count_bucket index >= count_bucket_size")

def _user_token_id(user_id: int, vocab) -> int:
    return vocab.convert_tokens_to_ids([f"[USR_{int(user_id)}]"])[0]

def build_instance(
    user_id: Optional[int],
    tranxs: List[Dict[str, Any]],
    vocab,
    args,
) -> Dict[str, List[int]]:
    """
    시퀀스 구성: [USR_*] → 본문
    - reordered/hour는 +1 (pad=0)
    - padding 없음
    - tranxs[*]["product_id"]는 이미 토큰 id라고 가정
    """
    max_body = max(0, int(getattr(args, "max_seq_length", 100)) - 1)
    body = _clip_recent(tranxs, max_body)

    seq: List[Dict[str, int]] = []

    # [USR_*]
    if user_id is not None:
        try:
            uid_id = int(_user_token_id(int(user_id), vocab))
        except Exception:
            uid_id = int(getattr(vocab, "[NO_USE]", 0))
        seq.append({
            "product_id": uid_id, "reordered": 0, "hour": 0,
            "aisle": 0, "department": 0, "count_bucket": 0
        })

    # 본문
    for t in body:
        seq.append({
            "product_id":   int(t["product_id"]),
            "reordered":    int(t.get("reordered", 0)),
            "hour":         int(t.get("hour", 0)),
            "aisle":        int(t.get("sponsor_id", 0)),
            "department":   int(t.get("category_id", 0)),
            "count_bucket": int(t.get("count_bucket", 0)),
        })

    input_ids    = [x["product_id"] for x in seq]
    reordered    = [x["reordered"] + 1 for x in seq]
    hour         = [x["hour"] + 1 for x in seq]
    aisle        = [x["aisle"] for x in seq]
    dept         = [x["department"] for x in seq]
    count_bucket = [x["count_bucket"] for x in seq]

    _validate_ranges(args, reordered, hour, aisle, dept, count_bucket)

    inst = {
        "input_ids": input_ids,
        "reordered": reordered,
        "hour": hour,
        "aisle": aisle,
        "dept": dept,
        "count_bucket": count_bucket,
    }
    if user_id is not None:
        inst["user_id"] = int(user_id)
    return inst

def build_batch(items: List[Dict[str, Any]], vocab, args) -> List[Dict[str, List[int]]]:
    return [build_instance(it.get("user_id"), it["tranxs"], vocab, args) for it in items]

# ✅ 전체 rows 평탄화 → 슬라이딩 subsequence 생성
def rows_to_instances_sliding(
    rows: List[Dict[str, Any]],
    vocab,
    args,
    *,
    include_user: bool = False,
    user_key: str = "userId",
    hour_key: str = "orderHour",
    item_reordered_key: Optional[str] = None,
    aisle_key: str = "aisle",
    dept_key: str = "dept",
    window_size: int = 100,
    overlap_ratio: float = 0.6,
    drop_last_partial: bool = True,
    assume_sorted: bool = True,
    time_keys: Tuple[str, ...] = ("orderNumber", "orderSequence", "orderId")
) -> List[Dict[str, List[int]]]:
    """
    - Instacart 전 데이터(식료품 도메인)를 주문 경계 무시하고 시간순으로 연결
    - 고정 길이 window_size로 자르고 overlap_ratio만큼 겹치게 이동 (stride = max(1, int(round(window_size*(1-overlap)))))
    - 각 subsequence는 [USR]가 앞에 붙음
    """
    flat = list(rows)
    if not assume_sorted:
        def sort_key(r):
            for k in time_keys:
                if k in r: return r[k]
            return 0
        flat.sort(key=sort_key)

    tranxs: List[Dict[str, Any]] = []
    users: List[Optional[int]] = []

    for r in flat:
        pid_raw = r["productId"]
        try:
            pid = vocab.convert_tokens_to_ids([pid_raw])[0]
        except Exception:
            pid = getattr(vocab, "[NO_USE]", 0)

        r01 = int(r.get(item_reordered_key, 0)) if item_reordered_key else 0

        tranxs.append({
            "product_id": pid,
            "reordered":  r01,
            "hour":       int(r.get(hour_key, 0)),
            "sponsor_id": int(r.get(aisle_key, 0)) if aisle_key else 0,
            "category_id":int(r.get(dept_key, 0)) if dept_key else 0,
        })
        users.append(int(r[user_key]) if include_user and user_key in r else None)

    n = len(tranxs)
    if n == 0:
        return []

    overlap_ratio = max(0.0, min(0.9999, float(overlap_ratio)))
    stride = max(1, int(round(window_size * (1.0 - overlap_ratio))))

    instances: List[Dict[str, List[int]]] = []
    start = 0
    while start < n:
        end = start + window_size
        if end > n:
            if drop_last_partial:
                break
            end = n

        sub_tranxs = tranxs[start:end]

        uid = None
        if include_user:
            window_users = users[start:end]
            first = window_users[0]
            uid = first if all(u == first for u in window_users) else None

        # build_instance가 [CLS]를 붙이고, max_seq_length에서 스페셜 토큰만큼 자동 보정
        instances.append(build_instance(uid, sub_tranxs, vocab, args))
        start += stride

    return instances

# ▶ Instacart 전용 헬퍼(편의)
def split_all_orders_to_subsequences(
    rows: List[Dict[str, Any]],
    vocab,
    args,
    *,
    window_size: int = 100,
    overlap_ratio: float = 0.6,
    include_user: bool = False
) -> List[Dict[str, List[int]]]:
    """
    Instacart(식료품) 데이터 전체를 하나의 시간축으로 보고 subsequence로 분할
    """
    # 권장: args.max_seq_length는 window_size + (include_user?1:0)로 세팅
    return rows_to_instances_sliding(
        rows, vocab, args,
        include_user=include_user,
        window_size=window_size,
        overlap_ratio=overlap_ratio,
        drop_last_partial=True,
        assume_sorted=True
    )
