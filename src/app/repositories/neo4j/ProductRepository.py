from typing import List

from ...models.graphModels import Product
from ...models import Product as Neo4jProduct
from ...utils.neo4j import safe_connect
from neomodel import db

class Neo4jProductRepository:

    @staticmethod
    def create_product_if_not_exist(product_mysql: dict, product_name_vecotor: List[float], product_category_vecotor: List[float]) -> Neo4jProduct:
        product_id = str(product_mysql.get("productId"))
        product = Neo4jProduct.nodes.get_or_none(product_id=product_id)

        if not product:
            product = Neo4jProduct(
                product_id=product_id,
                name=product_mysql.get("productName"),
                category=product_mysql.get("category"),

                name_vector=product_name_vecotor, 
                category_vector=product_category_vecotor)
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