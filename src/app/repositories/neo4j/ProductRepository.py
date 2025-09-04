from typing import Any, Dict, List, Optional,Tuple

from ...models.graphModels import Product
from ...models import Product as Neo4jProduct
from ...utils.neo4j import safe_connect
from neomodel import db

class Neo4jProductRepository:

    @staticmethod
    def create_product_if_not_exist(product_mysql: dict) -> Neo4jProduct:
        product_id = str(product_mysql.get("productId"))
        product = Neo4jProduct.nodes.get_or_none(product_id=product_id)

        if not product:
            product = Neo4jProduct(
                product_id=product_id,
                name=product_mysql.get("productName"),
                category=product_mysql.get("category"),

                # name_vector=product_name_vecotor, 
                # category_vector=product_category_vecotor
                )
            product.save()

        return product
    
    @staticmethod
    def find_products_by_name_vector(target_vector: list[float], top_k: int = 5) -> list[Product]:
        """
        Neo4j 벡터 인덱스를 이용해 name_vector가 주어진 벡터와 가장 유사한 Product 노드 top_k개를 찾는다.
        """
        try:
            query = """
            CALL db.index.vector.queryNodes('productNameVectorIndex', $top_k, $vector)
            YIELD node, score
            RETURN node
            """
            results, _ = db.cypher_query(query, {
                'top_k': top_k,
                'vector': target_vector
            })
            return [Product.inflate(row[0]) for row in results]

        except Exception as e:
            print(f"[Neo4jProductRepository] 벡터 유사도 검색 오류: {e}")
            return []
        
    @staticmethod
    def fetch_products_batch_after(last_product_id: Optional[str], limit: int) -> List[Tuple[int, int, str]]:
        """
        Keyset pagination (권장): product_id가 int PK라고 가정.
        last_product_id 이후의 배치를 가져옵니다.
        반환: [(product_id, name), ...]
        """
        if last_product_id is None:
            q = """
            MATCH (p:Product)
            WHERE p.product_id IS NOT NULL AND (p.name_vector IS NULL OR size(p.name_vector) = 0)
            RETURN p.product_id as product_id, p.name as name
            ORDER BY p.product_id ASC
            LIMIT $limit
            """
            rows, _ = db.cypher_query(q, {"limit": limit})
        else:
            q = """
            MATCH (p:Product)
            WHERE p.product_id IS NOT NULL AND toInteger(p.product_id) > $last_id AND (p.name_vector IS NULL OR size(p.name_vector) = 0)
            RETURN p.product_id as product_id, p.name as name
            ORDER BY p.product_id ASC
            LIMIT $limit
            """
            rows, _ = db.cypher_query(q, {"limit": limit, "last_id": int(last_product_id)})

        return [(r[0], r[1]) for r in rows]
    
    @staticmethod
    def bulk_update_name_vectors(rows: List[Dict[str, Any]]) -> None:
        """
        rows 예시: [{"product_id": '123', "vec": [..]}, ...]
        """
        if not rows:
            return
        q = """
        UNWIND $rows AS row
        MATCH (p:Product {product_id: row.product_id})
        SET p.name_vector = row.vec
        """
        db.cypher_query(q, {"rows": rows})