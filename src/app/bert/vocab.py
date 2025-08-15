# src/app/bert/vocab.py
import sys

# 👇 이 모듈을 'vocab'이라는 이름으로도 노출 (피클 호환)
sys.modules.setdefault('vocab', sys.modules[__name__])


from collections import Counter

def convert_by_vocab(vocab, tokens):
    return [vocab[token] for token in tokens]

class FreqVocab:
    def __init__(self):
        self.counter = Counter()
        self.frequency = []

    def update(self, user2seq):
        for user_id, seq in user2seq.items():
            self.counter[f"[USR_{user_id}]"] = 0
            self.counter.update([t["product_id"] for t in seq])

    def generate_vocab(self):
        self.token_count = len(self.counter)
        self.special_tokens = ["[PAD]", "[MASK]", "[NO_USE]"]
        self.token_to_ids = {}

        # 1. assign special tokens first
        for token in self.special_tokens:
            self.token_to_ids[token] = len(self.token_to_ids) + 1

        # 2. Assign [USR_xxx] tokens next
        user_tokens = sorted([t for t in self.counter if str(t).startswith("[USR_")])
        for token in user_tokens:
            self.token_to_ids[token] = len(self.token_to_ids) + 1

        # 3. assign remaining tokens
        for token, _ in self.counter.most_common():
            if token not in self.token_to_ids:
                self.token_to_ids[token] = len(self.token_to_ids) + 1

        # 4. Ensure special/user tokens have zero count
        for token in self.special_tokens:
            self.counter[token] = 0
        for token in user_tokens:
            self.counter[token] = 0

        self.id_to_tokens = {v: k for k, v in self.token_to_ids.items()}
        self.vocab_words = list(self.token_to_ids.keys())

        id_list = sorted(self.id_to_tokens.keys())
        self.frequency = [self.counter[self.id_to_tokens[i]] for i in id_list]

        # BERT4ETH-style token ID attributes
        self.mask_token_id = self.token_to_ids["[MASK]"]
        self.pad_token_id = self.token_to_ids["[pad]"]
        self.no_use_token_id = self.token_to_ids["[NO_USE]"]

    def convert_tokens_to_ids(self, tokens):
        return convert_by_vocab(self.token_to_ids, tokens)

    def convert_ids_to_tokens(self, ids):
        return convert_by_vocab(self.id_to_tokens, ids)
    
# src/app/bert/vocab_io.py
from pathlib import Path
import pickle as pkl

def load_vocab(vocab_path: str | Path):
    path = Path(vocab_path).expanduser().resolve()
    if not path.exists():
        # checkpoints / checkpoint 둘 다 시도
        alt = path.parent / path.name.replace("checkpoint", "checkpoints")
        if alt.exists():
            path = alt
        else:
            raise FileNotFoundError(f"vocab file not found: {vocab_path}")
    with open(path, "rb") as f:
        vocab = pkl.load(f)
    # 최소 인터페이스 체크
    assert hasattr(vocab, "convert_tokens_to_ids"), "vocab must have convert_tokens_to_ids()"
    return vocab

