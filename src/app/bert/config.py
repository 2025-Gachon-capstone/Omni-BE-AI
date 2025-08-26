# src/app/bert/config_infer.py
from dataclasses import dataclass

@dataclass
class InferArgs:
    # 모델에 실제로 필요한 필드들만 유지
    vocab_size: int
    aisle_size: int
    dept_size: int
    count_bucket_size: int
    max_seq_length: int
    hidden_size: int
    num_hidden_layers: int
    num_attention_heads: int
    hidden_dropout_prob: float

def get_infer_args() -> InferArgs:
    # === 기존 set_template(args)값을 그대로 반영 ===
    hidden_size = 64
    aisle_size = 135
    dept_size = 22
    hour_size = 25            # (model에서는 고정 25로 사용)
    count_bucket_size = 6
    num_hidden_layers = 8
    num_attention_heads = 2
    hidden_dropout_prob = 0.2
    product_size = 50815
    user_size = 204808
    vocab_size = product_size + user_size + 3  # 중요: padding idx=0 포함 설계와 일치해야 함
    max_seq_length = 100

    return InferArgs(
        vocab_size=vocab_size,
        aisle_size=aisle_size,
        dept_size=dept_size,
        count_bucket_size=count_bucket_size,
        max_seq_length=max_seq_length,
        hidden_size=hidden_size,
        num_hidden_layers=num_hidden_layers,
        num_attention_heads=num_attention_heads,
        hidden_dropout_prob=hidden_dropout_prob,
    )
