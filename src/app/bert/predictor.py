# src/app/bert/predictor.py
import torch
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from pathlib import Path
import threading  # ✅ 동시성용

from .config import get_infer_args            # ← 파일명: config
from .modeling import InstacartBERT           # ← 파일명: modeling.py

def _strip_module_prefix(sd: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
    return { (k.replace("module.", "", 1) if k.startswith("module.") else k): v for k, v in sd.items() }

def _ensure_batch(instances_or_one: Dict[str, Any] | List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # 단일 dict가 오면 리스트로 감싼다
    if isinstance(instances_or_one, dict):
        return [instances_or_one]
    return instances_or_one  # 이미 list

def _pad_batch(instances: List[Dict[str, List[int]]], T: int) -> Dict[str, torch.Tensor]:
    def pad(seq, t, pad_value=0):
        return (seq + [pad_value] * max(0, t - len(seq)))[:t]

    B = len(instances)
    tens = {k: [] for k in ["input_ids", "reordered", "hour", "aisle", "dept", "count_bucket"]}
    for inst in instances:
        for k in tens.keys():
            if k not in inst:
                raise ValueError(f"missing key: {k}")
            tens[k].append(pad(inst[k], T, 0))

    device = torch.device("cpu")
    out = {k: torch.tensor(v, dtype=torch.long, device=device) for k, v in tens.items()}
    out["positions"] = torch.arange(T, device=device).unsqueeze(0).repeat(B, 1).long()
    return out

class Predictor:
    """
    - CPU 전용 추론기
    - 입력: 단일 시퀀스(dict) 또는 배치(list[dict])
    - 출력:
        * user 단위 평균 임베딩 (trainer와 동일 정책: CLS 위치 사용)
        * user_id 미제공 시 시퀀스 단위로 반환
    """
    def __init__(self, args, ckpt_path: str, num_threads: int = 4):
        self.args = args
        self.device = torch.device("cpu")
        torch.set_num_threads(max(1, num_threads))

        self.model = InstacartBERT(args).to(self.device).eval()
        self._lock = threading.Lock()  # ✅ 동시성 보호 추가

        # ✅ 체크포인트 로딩 개선: 다양한 키 대응 + strict fallback
        state = torch.load(ckpt_path, map_location="cpu")
        if isinstance(state, dict):
            if "state_dict" in state:
                state = state["state_dict"]
            elif "core" in state:
                state = state["core"]
            elif "model" in state:
                state = state["model"]
        state = _strip_module_prefix(state)
        try:
            self.model.load_state_dict(state, strict=True)
        except Exception:
            # 일부 버전/키 미스매치가 있어도 로딩되도록
            self.model.load_state_dict(state, strict=False)

    @torch.inference_mode()
    def embed(self, data: Dict[str, Any] | List[Dict[str, Any]]) -> Tuple[List[int] | None, torch.Tensor]:
        """
        필수 키: input_ids, reordered, hour, aisle, dept, count_bucket
        선택 키: user_id (있으면 같은 user_id끼리 평균)
        return:
          (user_ids_or_None, embeddings)  # embeddings: [N, H] (N=user 수 or 시퀀스 수)
        """
        instances = _ensure_batch(data)
        T = min(self.args.max_seq_length, max(len(x["input_ids"]) for x in instances))
        tens = _pad_batch(instances, T)

        # ✅ 멀티스레드 안전 추론
        with self._lock:
            h = self.model(
                tens["input_ids"], tens["reordered"], tens["hour"], tens["aisle"],
                tens["dept"], tens["count_bucket"], tens["positions"]
            )

        cls = h[:, 0, :]  # [B, H]  # trainer 동일: CLS 위치(0번 토큰)

        if all(("user_id" in inst) for inst in instances):
            buckets = defaultdict(list)
            for emb, inst in zip(cls, instances):
                uid = int(inst["user_id"])
                buckets[uid].append(emb.unsqueeze(0))
            user_ids, embs = [], []
            for uid, chunks in buckets.items():
                user_ids.append(uid)
                embs.append(torch.cat(chunks, dim=0).mean(dim=0, keepdim=True))
            return user_ids, torch.cat(embs, dim=0).cpu()
        else:
            return None, cls.cpu()

# ---- 싱글톤 생성 유틸 (Flask에서 import 시 1회 로드) ----
def load_predictor(num_threads: int = 4, epoch: int = 8) -> Predictor:
    args = get_infer_args()
    base_dir = Path(__file__).resolve().parent
    ckpt_path = base_dir / "checkpoints" / f"epoch_{epoch}.pth"
    return Predictor(args, str(ckpt_path), num_threads=num_threads)
