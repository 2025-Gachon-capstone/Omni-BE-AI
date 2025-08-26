# src/app/service/BenefitService.py
from typing import List, Dict, Any
import numpy as np
import time
from flask import Request

from src.app.repositories.mysql.ProductRepository import MysqlProductRepository
from ..config import config
import requests
from src.app.repositories.neo4j.MemberRepository import Neo4jMemberRepository
from src.app.utils import ts
from src.app.bert.preprocess import split_all_orders_to_subsequences

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class BenefitService:
    def __init__(self, *, vocab, predictor, order_repo, member_repo=None):
        """
        vocab: FreqVocab 객체
        predictor: load_predictor(...) 로드한 추론기
        order_repo: get_infered_orders_by_product_id(product_id, limit) 메서드를 가진 repo
        member_repo: Neo4j 관련 조회/선발용 레포 (기본: Neo4jMemberRepository)
        """
        self.vocab = vocab
        self.predictor = predictor
        self.args = predictor.args
        self.order_repo = order_repo
        self.member_repo = member_repo or Neo4jMemberRepository

    def post_benefits(self, sponsor_id: int, req):
        start_time = time.time()
        try:
            print(f"[post_benefits] 요청 수신 - sponsor_id={sponsor_id}", )
            body = req.get_json(force=True)
            print(f"[post_benefits] 요청 body: {body}")

            target_product_id = body.get("targetProductId")
            excluded_product_ids = set(map(int, body.get("excludedProductIdList", [])))
            reordered_ratio = body.get("reorderedRatio", None)

            if target_product_id is None:
                print("[post_benefits] targetProductId 누락")
                return {"isSuccess": False, "code": "INVALID-REQUEST",
                        "message": "targetProductId가 필요합니다.", "timestamp": ts()}, 400

            print(f"[post_benefits] targetProductId={target_product_id}, excluded_ids={excluded_product_ids}")
            targt_product_name = MysqlProductRepository.get_product_name_by_id(int(target_product_id))

            # 1) MySQL 조회
            t0 = time.time()
            rows: List[Dict[str, Any]] = self.order_repo.get_infered_orders_by_product_id(
                int(target_product_id), limit=100, reordered_ratio=reordered_ratio
            )
            print(f"[post_benefits] MySQL 조회 완료 - 주문 수: {len(rows)} ({time.time() - t0}초)")

            # 2) 제외 상품 필터
            if excluded_product_ids:
                t0 = time.time()
                before_count = len(rows)
                tmp = []
                for r in rows:
                    try:
                        pid = int(r["productId"])
                    except Exception:
                        pid = None
                    if pid is not None and pid in excluded_product_ids:
                        continue
                    tmp.append(r)
                rows = tmp
                print(f"[post_benefits] 제외 필터 적용: {before_count} → {len(rows)} ({time.time() - t0}초)")

            if not rows:
                total_elapsed = time.time() - start_time
                print(f"[post_benefits] 필터 후 주문 없음 - 총 처리 시간: {total_elapsed}초", )
                return {"isSuccess": True, "code": "SUCCESS",
                        "result": {"orderCount": 0, "embeddings": [], "centroid": []},
                        "timestamp": ts()}, 200

            # 3) rows → 모델 인스턴스
            t0 = time.time()

            # args.max_seq_length는 스페셜 토큰을 포함한 총 길이
            self.args.max_seq_length = 100

            instances = split_all_orders_to_subsequences(
                rows, self.vocab, self.args,
                window_size=100,      # 본문 길이
                overlap_ratio=0.6,    # stride=40
                include_user=False    # 필요 시 True로
            )

            print(f"[post_benefits] rows_to_instances 변환 완료 - 인스턴스 수: {len(instances)} ({time.time() - t0}초)")

            if not instances:
                total_elapsed = time.time() - start_time
                print("[post_benefits] 변환 후 인스턴스 없음 - 총 처리 시간: %.3f초", total_elapsed)
                return {"isSuccess": True, "code": "SUCCESS",
                        "result": {"orderCount": 0, "embeddings": [], "centroid": []},
                        "timestamp": ts()}, 200

            # 4) 임베딩 추론
            t0 = time.time()
            _, embs_t = self.predictor.embed(instances)
            embs = embs_t.numpy()
            centroid = embs.mean(axis=0).astype(np.float32)
            print(f"[post_benefits] 임베딩 추론 완료 - shape={embs.shape}, centroid_shape={centroid.shape} ({time.time() - t0}초)")


            # 5) Neo4j 벡터 인덱스로 대상자 선발 (20% 확정 + 30% 확률 + 50% 랜덤)
            #    - 새 API 스펙에 맞춰 입력을 단순화: amount만 사용
            coupon_count = int(body.get("amount", 100))  # 총 쿠폰 수량
            # 기본 배분 비율(정책값): 확정/확률/랜덤 = 0.2 / 0.3 / 0.5
            det_r, prob_r, rand_r = 0.2, 0.3, 0.5
            temperature = 0.07  # 확률 샘플링 온도(정책값)
            exclude_member_ids = set()  # 새 스펙에서는 외부 제외 리스트 없음
  
            selected_member_ids = self.member_repo.allocate_coupons_mixed(
                centroid=centroid,
                total=coupon_count,
                index_name="member_node_embedding_vec",   # 인덱스명 (64차원)
                ratios=(det_r, prob_r, rand_r),
                deterministic_top_oversample=50,
                prob_oversample_factor=5.0,
                temperature=temperature,
                exclude_member_ids=exclude_member_ids,
                extra_where_knn=None,                     # 필요 시 정책 조건 추가 가능
                extra_where_rand=None,
                require_embedding_for_random=False,
            )
            print(f"[post_benefits] 대상자 선발 완료 - selected={len(selected_member_ids)} / requested={coupon_count}")


            total_elapsed = time.time() - start_time
            print(f"[post_benefits] 전체 처리 완료 - 총 처리 시간: {total_elapsed}초")

            # 6) Spring 서버로 요청 전송
            spring_sponsor_url = f"{config.SPONSOR_SERVER_ADDRESS}/sponsor/v2/benefits?sponsorId={sponsor_id}"

            try:
                body = {
                    "title": body.get("title"),
                    "startDate":body.get("startDate"),
                    "endDate":body.get("endDate"),
                    "discountRate": body.get("discountRate"),  # 기본값: 10%
                    "targetProduct": targt_product_name,  # 행사(타겟) 상품명
                    "amount":body.get("amount"),  # 발행할 총 쿠폰 수량
                    "status":body.get("status") # PENDING, COMPLETED   
                }
                            
                response = requests.post(spring_sponsor_url, json=body)
                if response.status_code != 200:
                    return response.json(), 500
                
                benefitId = response.json().get("benefitId")
                
            except requests.exceptions.RequestException as e:
                print(f"Spring 서버 통신 실패: {e}")
                return {
                    "isSuccess": False,
                    "code": "NETWORK-ERR",
                    "message": f"Spring 서버 통신 실패: {e}",
                    "timestamp": ts(),
                }, 500
            
            spring_card_url = f"{config.CARD_SERVER_ADDRESS}/card/v1/cardBenefits?sponsorId={sponsor_id}"

            body = {
                "benefitId": benefitId,
                "memberIdList": selected_member_ids,
            }

            try:
                response = requests.post(spring_card_url, json=body)
                if response.status_code == 200:
                    return response.json(), 200
                else:
                    return response.json(), 500
            except requests.exceptions.RequestException as e:
                print(f"Spring 서버 통신 실패: {e}")
                return {
                    "isSuccess": False,
                    "code": "NETWORK-ERR",
                    "message": f"Spring 서버 통신 실패: {e}",
                    "timestamp": ts(),
                }, 500

        except Exception as e:
            print("[post_benefits] 예외 발생 - 총 경과 시간: %.3f초", time.time() - start_time)
            return {"isSuccess": False, "code": "SERVER-ERR 500",
                    "message": f"Flask 서버 에러: {e}", "timestamp": ts()}, 500
