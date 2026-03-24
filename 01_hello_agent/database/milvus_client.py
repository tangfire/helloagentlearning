"""
Milvus 向量数据库连接管理

提供 Milvus 客户端的连接池和向量操作封装
"""

from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType
from typing import List, Dict, Any, Optional
import os


class MilvusClient:
    """Milvus 向量数据库客户端封装"""
    
    def __init__(self, collection_name: str = "document_chunks"):
        """
        初始化 Milvus 客户端
        
        Args:
            collection_name: 集合名称
        """
        self.host = os.getenv("MILVUS_HOST", "localhost")
        self.port = os.getenv("MILVUS_PORT", "19530")
        self.collection_name = collection_name
        
        # 连接 Milvus
        self._connect()
        
        # 初始化集合
        self._init_collection()
    
    def _connect(self):
        """连接到 Milvus 服务器"""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            print(f"✅ Milvus 连接成功：{self.host}:{self.port}")
        except Exception as e:
            print(f"❌ Milvus 连接失败：{e}")
            raise
    
    def _init_collection(self):
        """初始化集合（如果不存在）"""
        try:
            if not utility.has_collection(self.collection_name):
                # 定义 Schema
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=36),
                    FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=36),
                    FieldSchema(name="workspace_id", dtype=DataType.VARCHAR, max_length=36),
                    FieldSchema(name="chunk_index", dtype=DataType.INT64),
                    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
                    FieldSchema(name="metadata", dtype=DataType.JSON),
                ]
                
                schema = CollectionSchema(fields=fields, description="文档分块向量集合")
                
                # 创建集合
                collection = Collection(name=self.collection_name, schema=schema)
                print(f"✅ Milvus 集合已创建：{self.collection_name}")
                
                # 创建索引
                self._create_indexes(collection)
            else:
                print(f"ℹ️ Milvus 集合已存在：{self.collection_name}")
        except Exception as e:
            print(f"❌ 集合初始化失败：{e}")
            raise
    
    def _create_indexes(self, collection: Collection):
        """创建索引以加速向量检索"""
        try:
            # 主键索引（自动创建）
            
            # 文档 ID 索引（Trie 用于字符串精确匹配）
            collection.create_index(
                field_name="document_id",
                index_params={"index_type": "Trie"}
            )
            
            # 工作空间 ID 索引（Trie 用于字符串精确匹配）
            collection.create_index(
                field_name="workspace_id",
                index_params={"index_type": "Trie"}
            )
            
            # chunk_index 索引
            collection.create_index(
                field_name="chunk_index",
                index_params={"index_type": "STL_SORT"}
            )
            
            # 向量索引（IVF_FLAT）
            collection.create_index(
                field_name="embedding",
                index_params={
                    "index_type": "IVF_FLAT",
                    "metric_type": "COSINE",
                    "params": {"nlist": 1024}
                }
            )
            
            print("✅ Milvus 索引已创建")
        except Exception as e:
            print(f"❌ 索引创建失败：{e}")
            raise
    
    def insert_vectors(self, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        插入向量数据
        
        Args:
            vectors: 向量数据列表，每个元素包含：
                - id: 唯一 ID
                - document_id: 文档 ID
                - workspace_id: 工作空间 ID
                - chunk_index: 分块索引
                - content: 文本内容
                - embedding: 向量（1536 维）
                - metadata: 元数据（JSON）
        
        Returns:
            插入结果
        """
        try:
            collection = Collection(self.collection_name)
            
            # 逐条插入（避免类型不匹配问题）
            inserted_ids = []
            for vector_data in vectors:
                # 准备单条数据
                data = {
                    "id": vector_data["id"],
                    "document_id": vector_data["document_id"],
                    "workspace_id": vector_data["workspace_id"],
                    "chunk_index": vector_data["chunk_index"],
                    "content": vector_data["content"],
                    "embedding": vector_data["embedding"],
                    "metadata": vector_data.get("metadata", {}),
                }
                
                # 插入单条数据
                result = collection.insert([data])
                inserted_ids.extend(result.primary_keys)
            
            # 刷新集合（立即可查）
            collection.flush()
            
            print(f"✅ 插入 {len(vectors)} 个向量到 Milvus")
            return {"success": True, "count": len(vectors), "ids": inserted_ids}
            
        except Exception as e:
            print(f"❌ Milvus 插入失败：{e}")
            return {"success": False, "error": str(e)}
    
    def search_vectors(
        self,
        query_vector: List[float],
        workspace_id: Optional[str] = None,
        limit: int = 5,
        filter_expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        向量相似度搜索
        
        Args:
            query_vector: 查询向量（1536 维）
            workspace_id: 工作空间 ID（可选，用于过滤）
            limit: 返回结果数量
            filter_expr: 过滤表达式（可选）
        
        Returns:
            搜索结果列表
        """
        try:
            collection = Collection(self.collection_name)
            
            # 加载集合到内存
            collection.load()
            
            # 构建搜索参数
            search_params = {
                "data": [query_vector],
                "anns_field": "embedding",
                "param": {
                    "metric_type": "COSINE",
                    "params": {"nprobe": 32}
                },
                "limit": limit,
                "output_fields": ["id", "document_id", "chunk_index", "content", "metadata"]
            }
            
            # 添加过滤条件
            if workspace_id:
                search_params["expr"] = f"workspace_id == '{workspace_id}'"
            
            if filter_expr:
                if workspace_id:
                    search_params["expr"] = f"({search_params['expr']}) and ({filter_expr})"
                else:
                    search_params["expr"] = filter_expr
            
            # 执行搜索
            results = collection.search(**search_params)
            
            # 格式化结果
            formatted_results = []
            for hits in results:
                for hit in hits:
                    formatted_results.append({
                        "id": hit.entity.get("id"),
                        "document_id": hit.entity.get("document_id"),
                        "chunk_index": hit.entity.get("chunk_index"),
                        "content": hit.entity.get("content"),
                        "metadata": hit.entity.get("metadata"),
                        "score": hit.score,
                        "distance": 1 - hit.score  # COSINE 距离
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ Milvus 搜索失败：{e}")
            return []
    
    def delete_by_document_id(self, document_id: str) -> bool:
        """
        根据文档 ID 删除向量
        
        Args:
            document_id: 文档 ID
        
        Returns:
            是否删除成功
        """
        try:
            collection = Collection(self.collection_name)
            collection.load()
            
            # 删除表达式
            expr = f"document_id == '{document_id}'"
            collection.delete(expr)
            collection.flush()
            
            print(f"✅ 删除文档 {document_id} 的向量")
            return True
            
        except Exception as e:
            print(f"❌ Milvus 删除失败：{e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            collection = Collection(self.collection_name)
            return {
                "name": self.collection_name,
                "count": collection.num_entities
            }
        except Exception as e:
            print(f"❌ 获取统计失败：{e}")
            return {"error": str(e)}
    
    def drop_collection(self):
        """删除集合（危险操作！）"""
        try:
            if utility.has_collection(self.collection_name):
                utility.drop_collection(self.collection_name)
                print(f"✅ 集合已删除：{self.collection_name}")
        except Exception as e:
            print(f"❌ 删除集合失败：{e}")
            raise


# 全局单例
milvus_client = None


def get_milvus_client() -> MilvusClient:
    """获取 Milvus 客户端单例"""
    global milvus_client
    if milvus_client is None:
        milvus_client = MilvusClient()
    return milvus_client


# ==================== 使用示例 ====================
if __name__ == "__main__":
    client = get_milvus_client()
    
    # 查看统计
    stats = client.get_collection_stats()
    print(f"📊 Milvus 统计：{stats}")
    
    # 测试搜索
    # results = client.search_vectors(
    #     query_vector=[0.1] * 1536,
    #     workspace_id="test",
    #     limit=5
    # )
    # print(f"🔍 搜索结果：{results}")
