# src/app/api/users.py
import time
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

from src.app.repositories.mysql.OrderRepository import MysqlOrderRepository
from src.app.repositories.neo4j.MemberRepository import Neo4jMemberRepository
from src.app.utils import db, ts

class EmbeddingService:

    def __init__(self, vocab, predictor, args):
        self.vocab = vocab
        self.predictor = predictor
        self.args = args

    def _rows_to_user_instance(self, member_id: int, rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """해당 유저의 최신 구매 rows(최대 100개) → 단일 instance (맨 앞 [USR_<id>])"""
        if not rows:
            return None

        tranxs: List[Dict[str, Any]] = []
        for r in rows:
            pid_raw = r["productId"]
            try:
                pid = self.vocab.convert_tokens_to_ids([pid_raw])[0]
            except Exception:
                pid = self.vocab.convert_tokens_to_ids(["[NO_USE]"])[0]

            tranxs.append({
                "product_id":   int(pid),
                "reordered":    int(r.get("reordered", 0)),   # 필터링 없음
                "hour":         int(r.get("orderHour", 0)),
                "sponsor_id":   int(r.get("sponsor_id", 0)),
                "category_id":  int(r.get("category_id", 0)),
                "count_bucket": int(r.get("count_bucket", 0)),
            })

        from src.app.bert.preprocess import build_instance
        # 시퀀스 맨 앞에 [USR_<id>]만 붙이는 설계(별도 CLS 없음)
        return build_instance(member_id, tranxs, self.vocab, self.args)

    def post_missing_user_embeddings(
        self,
        limit_users: Optional[int] = None,     # 전부 말고 상한을 두고 싶을 때
        page_size: int = 2048,                 # 유저 ID 페이징 크기
        batch_embed: int = 16,  
        save_page_size: int = 1000,             # embed()에 넣는 인스턴스 배치 크기
        dry_run: bool = False                  # 저장 없이 개수만 확인
    ) -> Tuple[Dict[str, Any], int]:
        """
        node_embedding 없는 user만 임베딩 생성하여 저장(UPSERT).
        - 각 유저: 최신 구매 99개 사용, 필터링 없음
        - 멱등: UNIQUE(user_id) + ON CONFLICT DO UPDATE
        - 반환: 처리 통계
        """
        start = time.time()
        produced = 0
        skipped_empty = 0
        failed_users: List[int] = []

        # 권장: 본문 99 + USR 1
        if getattr(self.args, "max_seq_length", None) is None:
            self.args.max_seq_length = 100

        # 1) node_embedding 미보유 유저 ID 스트리밍
        seen = 0
        id_buffer: List[int] = []

        for user_ids_page in Neo4jMemberRepository.get_member_ids_missing_embedding(page_size=page_size):
            for uid in user_ids_page:
                id_buffer.append(int(uid))
                seen += 1
                if limit_users and seen >= limit_users:
                    break
            if limit_users and seen >= limit_users:
                break

        if not id_buffer:
            return {
                "isSuccess": True, "code": "SUCCESS",
                "result": {"toProcess": 0, "produced": 0, "skippedEmpty": 0, "failed": []},
                "timestamp": ts()
            }, 200

        # 2) 배치로 나눠 임베딩
        from math import ceil
        n_batches = ceil(len(id_buffer) / batch_embed)

        for bi in range(n_batches):
            batch_ids = id_buffer[bi*batch_embed : (bi+1)*batch_embed]
            instances: List[Dict[str, Any]] = []
            idx_map: List[int] = []  # instances → user_id 매핑

            # 2-1) 입력 구성
            for uid in batch_ids:
                mid = int(uid)
                try:
                    rows = MysqlOrderRepository.fetch_recent_products_by_member(mid, limit=99)  # 최신순 100
                    if not rows:
                        skipped_empty += 1
                        continue
                    inst = self._rows_to_user_instance(mid, rows)
                    if inst is None:
                        skipped_empty += 1
                        continue
                    instances.append(inst)
                    idx_map.append(mid)
                except Exception as e:
                    print(f"[user_embed/missing] fetch/build fail uid={mid}: {e}")
                    failed_users.append(int(mid))

            if not instances:
                continue

            # 2-2) 임베딩 수행
            t0 = time.time()
            member_ids_out, embs_t = self.predictor.embed(instances)
            embs = embs_t.numpy()  # [U_in_batch, H]
            # build_instance에 user_id가 있으므로 embed()는 user별 평균 분기 → user_ids_out 존재
            if member_ids_out is None:
                # 안전장치: None이면 idx_map 순서로 매핑
                member_ids_out = idx_map

            # 2-3) 저장 (UPSERT)
            if not dry_run:
                for sp in range(0, len(member_ids_out), save_page_size):
                    ids_slice = list(map(int, member_ids_out[sp: sp + save_page_size]))
                    embs_slice = embs[sp: sp + save_page_size]

                    try:
                        rows_payload = []
                        for u, vec in zip(ids_slice, embs_slice):
                            # member_id는 Neo4j 스키마상 StringProperty → 항상 문자열로 저장
                            rows_payload.append({
                                "member_id": str(u),
                                # numpy → list(float) 변환 (float32 등 직렬화 이슈 방지)
                                "vector": [float(x) for x in vec.tolist()]
                            })
                        Neo4jMemberRepository.upsert_member_embeddings(rows_payload)
                    except Exception as e:
                        print(f"[user_embed/missing] upsert fail batch={bi}, slice={sp}:{sp+save_page_size}: {e}")
                        # 슬라이스 실패 시 개별 재도전
                        for u, vec in zip(ids_slice, embs_slice):
                            try:
                                Neo4jMemberRepository.upsert_member_embeddings([{
                                    "member_id": str(u),
                                    "vector": [float(x) for x in vec.reshape(-1).tolist()]
                                }])
                            except Exception as ee:
                                print(f"[user_embed/missing] single upsert fail uid={u}: {ee}")
                                failed_users.append(int(u))

            produced += len(embs)
            print(f"[user_embed/missing] batch {bi+1}/{n_batches} done: users={len(embs)}, "
                f"H={embs.shape[1]}, time={time.time()-t0:.3f}s")


            produced += len(embs)
            print(f"[user_embed/missing] batch {bi+1}/{n_batches} done: users={len(embs)}, H={embs.shape[1]}, time={time.time()-t0:.3f}s")

        elapsed = time.time() - start
        print(f'[user_embed/missing] 전체 처리 완료: {elapsed:.3f}s')
        return {
            "isSuccess": True, "code": "SUCCESS",
            "result": {
                "toProcess": len(id_buffer),
                "produced": produced,
                "skippedEmpty": skipped_empty,
                "failed": sorted(set(failed_users)),
            },
            "timestamp": ts()
        }, 200
