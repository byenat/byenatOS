"""
ByenatOS Layered Storage Engine
个性化数据文件系统 - 虚拟系统的核心存储组件

作为byenatOS虚拟系统的"虚拟文件系统"，专门用于个性化数据管理。
相当于传统OS中的文件系统，但专门优化用于HiNATA数据的分层存储、多维索引和快速检索。
运行在现有操作系统的文件系统之上，提供虚拟化的个性化数据存储服务。
"""

import asyncio
import json
import time
import hashlib
import gzip
import pickle
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import struct

import aioredis
import asyncpg
import aiofiles
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import chromadb
from elasticsearch import AsyncElasticsearch


class StorageTier(Enum):
    """存储层级"""
    HOT = "hot"      # 热数据层 - Redis
    WARM = "warm"    # 温数据层 - SQLite/PostgreSQL  
    COLD = "cold"    # 冷数据层 - 文件系统


class IndexType(Enum):
    """索引类型"""
    VECTOR = "vector"        # 向量索引
    FULLTEXT = "fulltext"    # 全文索引
    COMPOSITE = "composite"  # 复合索引
    TEMPORAL = "temporal"    # 时间索引


@dataclass
class StorageMetrics:
    """存储指标"""
    total_hinata_count: int = 0
    hot_tier_count: int = 0
    warm_tier_count: int = 0
    cold_tier_count: int = 0
    total_size_bytes: int = 0
    cache_hit_rate: float = 0.0
    average_retrieval_time: float = 0.0
    index_build_time: float = 0.0


@dataclass
class RetrievalQuery:
    """检索查询"""
    user_id: str
    query_type: str
    query_text: Optional[str] = None
    semantic_vector: Optional[List[float]] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    time_range: Optional[Tuple[datetime, datetime]] = None
    limit: int = 10
    min_relevance_score: float = 0.5


@dataclass
class RetrievalResult:
    """检索结果"""
    hinata_id: str
    relevance_score: float
    storage_tier: StorageTier
    retrieval_time: float
    content_summary: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class HotStorageManager:
    """热数据层管理器 - Redis"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_pool = None
        self.hot_data_ttl = 7 * 24 * 3600  # 7天TTL
        
    async def initialize(self):
        """初始化Redis连接"""
        self.redis_pool = aioredis.from_url(self.redis_url, decode_responses=False)
        
    async def store_hinata(self, hinata_data: Dict[str, Any], user_id: str):
        """存储HiNATA到热数据层"""
        hinata_id = hinata_data['id']
        
        # 压缩存储完整数据
        compressed_data = gzip.compress(json.dumps(hinata_data, ensure_ascii=False).encode())
        
        # 存储完整数据
        await self.redis_pool.setex(
            f"hinata:full:{hinata_id}",
            self.hot_data_ttl,
            compressed_data
        )
        
        # 用户热数据索引
        influence_weight = hinata_data.get('psp_influence_weight', 0)
        await self.redis_pool.zadd(
            f"user:hot_hinata:{user_id}",
            {hinata_id: influence_weight}
        )
        
        # 主题热数据索引
        enhanced_tags = hinata_data.get('enhanced_tags', [])
        for tag in enhanced_tags:
            await self.redis_pool.zadd(
                f"topic:hot_hinata:{tag}",
                {hinata_id: influence_weight}
            )
        
        # 时间序列索引
        timestamp = int(datetime.fromisoformat(hinata_data['timestamp'].replace('Z', '')).timestamp())
        await self.redis_pool.zadd(
            f"timeline:hot_hinata:{user_id}",
            {hinata_id: timestamp}
        )
        
        # 来源应用索引
        source = hinata_data.get('source', '')
        await self.redis_pool.sadd(
            f"source:hot_hinata:{source}",
            hinata_id
        )
    
    async def get_hinata(self, hinata_id: str) -> Optional[Dict[str, Any]]:
        """从热数据层获取HiNATA"""
        compressed_data = await self.redis_pool.get(f"hinata:full:{hinata_id}")
        
        if compressed_data:
            try:
                decompressed_data = gzip.decompress(compressed_data)
                return json.loads(decompressed_data.decode())
            except Exception:
                return None
        
        return None
    
    async def query_by_user_weight(self, user_id: str, limit: int = 10, min_weight: float = 0.5) -> List[str]:
        """按用户权重查询"""
        hinata_ids = await self.redis_pool.zrevrangebyscore(
            f"user:hot_hinata:{user_id}",
            max='+inf',
            min=min_weight,
            start=0,
            num=limit
        )
        return [hid.decode() if isinstance(hid, bytes) else hid for hid in hinata_ids]
    
    async def query_by_topic(self, topic: str, limit: int = 10) -> List[str]:
        """按主题查询"""
        hinata_ids = await self.redis_pool.zrevrange(
            f"topic:hot_hinata:{topic}",
            start=0,
            end=limit-1
        )
        return [hid.decode() if isinstance(hid, bytes) else hid for hid in hinata_ids]
    
    async def query_by_time_range(self, user_id: str, start_time: datetime, end_time: datetime) -> List[str]:
        """按时间范围查询"""
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())
        
        hinata_ids = await self.redis_pool.zrangebyscore(
            f"timeline:hot_hinata:{user_id}",
            min=start_timestamp,
            max=end_timestamp
        )
        return [hid.decode() if isinstance(hid, bytes) else hid for hid in hinata_ids]
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """获取热存储统计"""
        info = await self.redis_pool.info('memory')
        
        # 统计HiNATA数量
        keys = await self.redis_pool.keys("hinata:full:*")
        hinata_count = len(keys)
        
        return {
            'hinata_count': hinata_count,
            'memory_used_bytes': info.get('used_memory', 0),
            'memory_peak_bytes': info.get('used_memory_peak', 0),
            'memory_fragmentation_ratio': info.get('mem_fragmentation_ratio', 1.0)
        }
    
    async def cleanup_expired(self):
        """清理过期数据"""
        # Redis会自动清理过期数据，这里可以添加额外的清理逻辑
        pass


class WarmStorageManager:
    """温数据层管理器 - PostgreSQL"""
    
    def __init__(self, postgres_dsn: str):
        self.postgres_dsn = postgres_dsn
        self.db_pool = None
        
    async def initialize(self):
        """初始化数据库连接"""
        self.db_pool = await asyncpg.create_pool(self.postgres_dsn)
        await self._create_tables()
        
    async def _create_tables(self):
        """创建数据库表"""
        async with self.db_pool.acquire() as conn:
            # HiNATA数据表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS hinata_data (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    source TEXT NOT NULL,
                    highlight TEXT NOT NULL,
                    note TEXT NOT NULL,
                    address TEXT NOT NULL,
                    tags JSONB,
                    access_level TEXT NOT NULL,
                    enhanced_tags JSONB,
                    recommended_highlights JSONB,
                    semantic_analysis JSONB,
                    quality_score REAL,
                    attention_weight REAL,
                    psp_influence_weight REAL,
                    embedding_vector JSONB,
                    processing_metadata JSONB,
                    storage_tier TEXT DEFAULT 'warm',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    INDEX (user_id, timestamp DESC),
                    INDEX (user_id, psp_influence_weight DESC),
                    INDEX (user_id, source),
                    INDEX (enhanced_tags USING GIN),
                    INDEX (timestamp DESC)
                )
            ''')
            
            # 复合索引表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS hinata_index (
                    hinata_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    timestamp BIGINT NOT NULL,
                    source TEXT NOT NULL,
                    psp_influence_weight REAL NOT NULL,
                    attention_weight REAL NOT NULL,
                    quality_score REAL NOT NULL,
                    storage_tier TEXT NOT NULL,
                    tags JSONB,
                    content_hash TEXT NOT NULL,
                    INDEX (user_id, timestamp DESC),
                    INDEX (user_id, psp_influence_weight DESC),
                    INDEX (quality_score DESC, psp_influence_weight DESC),
                    INDEX (content_hash),
                    INDEX (tags USING GIN)
                )
            ''')
    
    async def store_hinata(self, hinata_data: Dict[str, Any], user_id: str):
        """存储HiNATA到温数据层"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO hinata_data 
                (id, user_id, timestamp, source, highlight, note, address, tags, access_level,
                 enhanced_tags, recommended_highlights, semantic_analysis,
                 quality_score, attention_weight, psp_influence_weight, 
                 embedding_vector, processing_metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (id) DO UPDATE SET
                    timestamp = EXCLUDED.timestamp,
                    enhanced_tags = EXCLUDED.enhanced_tags,
                    quality_score = EXCLUDED.quality_score,
                    attention_weight = EXCLUDED.attention_weight,
                    psp_influence_weight = EXCLUDED.psp_influence_weight,
                    processing_metadata = EXCLUDED.processing_metadata
            ''', 
                hinata_data['id'], user_id, hinata_data['timestamp'], hinata_data['source'],
                hinata_data['highlight'], hinata_data['note'], hinata_data['address'],
                json.dumps(hinata_data.get('tag', [])), hinata_data['access'],
                json.dumps(hinata_data.get('enhanced_tags', [])),
                json.dumps(hinata_data.get('recommended_highlights', [])),
                json.dumps(hinata_data.get('semantic_analysis', {})),
                hinata_data.get('quality_score'), hinata_data.get('attention_weight'),
                hinata_data.get('psp_influence_weight'),
                json.dumps(hinata_data.get('embedding_vector', [])),
                json.dumps(hinata_data.get('processing_metadata', {}))
            )
            
            # 同时更新索引表
            await self._update_index_table(conn, hinata_data, user_id)
    
    async def _update_index_table(self, conn, hinata_data: Dict[str, Any], user_id: str):
        """更新索引表"""
        timestamp = int(datetime.fromisoformat(hinata_data['timestamp'].replace('Z', '')).timestamp())
        content_hash = hashlib.md5(f"{hinata_data['highlight']}{hinata_data['note']}".encode()).hexdigest()
        
        all_tags = (hinata_data.get('tag', []) + hinata_data.get('enhanced_tags', []))
        
        await conn.execute('''
            INSERT INTO hinata_index 
            (hinata_id, user_id, timestamp, source, psp_influence_weight, 
             attention_weight, quality_score, storage_tier, tags, content_hash)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (hinata_id) DO UPDATE SET
                timestamp = EXCLUDED.timestamp,
                psp_influence_weight = EXCLUDED.psp_influence_weight,
                attention_weight = EXCLUDED.attention_weight,
                quality_score = EXCLUDED.quality_score,
                tags = EXCLUDED.tags
        ''',
            hinata_data['id'], user_id, timestamp, hinata_data['source'],
            hinata_data.get('psp_influence_weight', 0), hinata_data.get('attention_weight', 0),
            hinata_data.get('quality_score', 0), StorageTier.WARM.value,
            json.dumps(all_tags), content_hash
        )
    
    async def get_hinata(self, hinata_id: str) -> Optional[Dict[str, Any]]:
        """从温数据层获取HiNATA"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM hinata_data WHERE id = $1', hinata_id
            )
            
            if row:
                return dict(row)
            return None
    
    async def query_by_criteria(self, user_id: str, criteria: Dict[str, Any]) -> List[str]:
        """基于复合条件查询"""
        async with self.db_pool.acquire() as conn:
            base_query = "SELECT hinata_id FROM hinata_index WHERE user_id = $1"
            params = [user_id]
            conditions = []
            param_count = 1
            
            # 动态构建查询条件
            if criteria.get('min_influence_weight'):
                param_count += 1
                conditions.append(f"psp_influence_weight >= ${param_count}")
                params.append(criteria['min_influence_weight'])
            
            if criteria.get('source_filter'):
                param_count += 1
                conditions.append(f"source = ANY(${param_count})")
                params.append(criteria['source_filter'])
            
            if criteria.get('time_range'):
                start_time, end_time = criteria['time_range']
                param_count += 1
                conditions.append(f"timestamp >= ${param_count}")
                params.append(int(start_time.timestamp()))
                param_count += 1
                conditions.append(f"timestamp <= ${param_count}")
                params.append(int(end_time.timestamp()))
            
            if criteria.get('tags'):
                param_count += 1
                tag_conditions = []
                for tag in criteria['tags']:
                    tag_conditions.append(f"tags ? '{tag}'")
                conditions.append(f"({' OR '.join(tag_conditions)})")
            
            # 组合查询
            if conditions:
                full_query = f"{base_query} AND {' AND '.join(conditions)}"
            else:
                full_query = base_query
            
            # 添加排序和限制
            full_query += " ORDER BY psp_influence_weight DESC, timestamp DESC"
            if criteria.get('limit'):
                param_count += 1
                full_query += f" LIMIT ${param_count}"
                params.append(criteria['limit'])
            
            rows = await conn.fetch(full_query, *params)
            return [row['hinata_id'] for row in rows]
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """获取温存储统计"""
        async with self.db_pool.acquire() as conn:
            # 统计HiNATA数量
            count_row = await conn.fetchrow('SELECT COUNT(*) as count FROM hinata_data')
            hinata_count = count_row['count']
            
            # 统计数据大小
            size_row = await conn.fetchrow('''
                SELECT pg_total_relation_size('hinata_data') + 
                       pg_total_relation_size('hinata_index') as total_size
            ''')
            total_size = size_row['total_size']
            
            return {
                'hinata_count': hinata_count,
                'total_size_bytes': total_size,
                'table_size_bytes': total_size
            }


class ColdStorageManager:
    """冷数据层管理器 - 文件系统"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """初始化冷存储"""
        # 创建目录结构
        (self.storage_path / "data").mkdir(exist_ok=True)
        (self.storage_path / "index").mkdir(exist_ok=True)
        (self.storage_path / "archive").mkdir(exist_ok=True)
    
    async def store_hinata_batch(self, hinata_batch: List[Dict[str, Any]], user_id: str):
        """批量存储HiNATA到冷数据层"""
        # 按日期分组存储
        date_groups = {}
        for hinata in hinata_batch:
            date_str = hinata['timestamp'][:10]  # YYYY-MM-DD
            if date_str not in date_groups:
                date_groups[date_str] = []
            date_groups[date_str].append(hinata)
        
        # 分组写入文件
        for date_str, hinata_list in date_groups.items():
            await self._store_date_batch(hinata_list, user_id, date_str)
    
    async def _store_date_batch(self, hinata_list: List[Dict[str, Any]], user_id: str, date_str: str):
        """存储特定日期的HiNATA批次"""
        file_path = self.storage_path / "data" / user_id / f"{date_str}.gz"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 读取现有数据
        existing_data = []
        if file_path.exists():
            async with aiofiles.open(file_path, 'rb') as f:
                compressed_data = await f.read()
                try:
                    decompressed_data = gzip.decompress(compressed_data)
                    existing_data = json.loads(decompressed_data.decode())
                except Exception:
                    existing_data = []
        
        # 合并新数据
        hinata_dict = {h['id']: h for h in existing_data}
        for hinata in hinata_list:
            hinata_dict[hinata['id']] = hinata
        
        # 压缩写入
        merged_data = list(hinata_dict.values())
        json_data = json.dumps(merged_data, ensure_ascii=False)
        compressed_data = gzip.compress(json_data.encode())
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(compressed_data)
        
        # 更新索引
        await self._update_cold_index(user_id, date_str, list(hinata_dict.keys()))
    
    async def _update_cold_index(self, user_id: str, date_str: str, hinata_ids: List[str]):
        """更新冷数据索引"""
        index_path = self.storage_path / "index" / user_id / f"{date_str}.idx"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建简单的二进制索引
        index_data = {
            'date': date_str,
            'hinata_count': len(hinata_ids),
            'hinata_ids': hinata_ids,
            'file_path': str(self.storage_path / "data" / user_id / f"{date_str}.gz"),
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # 使用pickle序列化索引
        async with aiofiles.open(index_path, 'wb') as f:
            await f.write(pickle.dumps(index_data))
    
    async def get_hinata(self, hinata_id: str, user_id: str, date_hint: str = None) -> Optional[Dict[str, Any]]:
        """从冷数据层获取HiNATA"""
        if date_hint:
            # 有日期提示，直接查找
            return await self._get_hinata_from_date_file(hinata_id, user_id, date_hint)
        else:
            # 没有日期提示，遍历索引查找
            return await self._search_hinata_in_cold_storage(hinata_id, user_id)
    
    async def _get_hinata_from_date_file(self, hinata_id: str, user_id: str, date_str: str) -> Optional[Dict[str, Any]]:
        """从指定日期文件获取HiNATA"""
        file_path = self.storage_path / "data" / user_id / f"{date_str}.gz"
        
        if not file_path.exists():
            return None
        
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                compressed_data = await f.read()
                decompressed_data = gzip.decompress(compressed_data)
                hinata_list = json.loads(decompressed_data.decode())
                
                for hinata in hinata_list:
                    if hinata['id'] == hinata_id:
                        return hinata
        except Exception:
            pass
        
        return None
    
    async def _search_hinata_in_cold_storage(self, hinata_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """在冷存储中搜索HiNATA"""
        index_dir = self.storage_path / "index" / user_id
        
        if not index_dir.exists():
            return None
        
        # 遍历索引文件
        for index_file in index_dir.glob("*.idx"):
            try:
                async with aiofiles.open(index_file, 'rb') as f:
                    index_data = pickle.loads(await f.read())
                    
                    if hinata_id in index_data['hinata_ids']:
                        # 找到了，加载对应的数据文件
                        date_str = index_data['date']
                        return await self._get_hinata_from_date_file(hinata_id, user_id, date_str)
            except Exception:
                continue
        
        return None
    
    async def query_by_date_range(self, user_id: str, start_date: str, end_date: str) -> List[str]:
        """按日期范围查询"""
        hinata_ids = []
        index_dir = self.storage_path / "index" / user_id
        
        if not index_dir.exists():
            return hinata_ids
        
        for index_file in index_dir.glob("*.idx"):
            date_str = index_file.stem
            if start_date <= date_str <= end_date:
                try:
                    async with aiofiles.open(index_file, 'rb') as f:
                        index_data = pickle.loads(await f.read())
                        hinata_ids.extend(index_data['hinata_ids'])
                except Exception:
                    continue
        
        return hinata_ids
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """获取冷存储统计"""
        total_files = 0
        total_size = 0
        hinata_count = 0
        
        # 遍历数据目录
        data_dir = self.storage_path / "data"
        if data_dir.exists():
            for file_path in data_dir.rglob("*.gz"):
                total_files += 1
                total_size += file_path.stat().st_size
                
                # 计算HiNATA数量（从索引）
                relative_path = file_path.relative_to(data_dir)
                user_id = relative_path.parts[0]
                date_str = file_path.stem
                
                index_path = self.storage_path / "index" / user_id / f"{date_str}.idx"
                if index_path.exists():
                    try:
                        async with aiofiles.open(index_path, 'rb') as f:
                            index_data = pickle.loads(await f.read())
                            hinata_count += index_data['hinata_count']
                    except Exception:
                        pass
        
        return {
            'hinata_count': hinata_count,
            'total_files': total_files,
            'total_size_bytes': total_size
        }


class VectorIndexManager:
    """向量索引管理器"""
    
    def __init__(self, chroma_persist_dir: str):
        self.chroma_persist_dir = chroma_persist_dir
        self.chroma_client = None
        self.collections = {}
        
    async def initialize(self):
        """初始化向量数据库"""
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_persist_dir)
        
    def get_user_collection(self, user_id: str):
        """获取用户向量集合"""
        collection_name = f"user_{user_id}_vectors"
        
        if collection_name not in self.collections:
            try:
                collection = self.chroma_client.get_collection(collection_name)
            except:
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            self.collections[collection_name] = collection
        
        return self.collections[collection_name]
    
    async def add_hinata_vector(self, hinata_data: Dict[str, Any], user_id: str):
        """添加HiNATA向量"""
        if not hinata_data.get('embedding_vector'):
            return
        
        collection = self.get_user_collection(user_id)
        
        # 准备元数据
        metadata = {
            "hinata_id": hinata_data['id'],
            "timestamp": hinata_data['timestamp'],
            "source": hinata_data['source'],
            "psp_influence_weight": hinata_data.get('psp_influence_weight', 0),
            "attention_weight": hinata_data.get('attention_weight', 0),
            "quality_score": hinata_data.get('quality_score', 0),
            "tags": ','.join(hinata_data.get('enhanced_tags', []))
        }
        
        # 准备文档内容
        document = f"{hinata_data['highlight']} {hinata_data['note']}"
        
        # 添加到集合
        collection.add(
            embeddings=[hinata_data['embedding_vector']],
            documents=[document],
            metadatas=[metadata],
            ids=[hinata_data['id']]
        )
    
    async def semantic_search(self, query_vector: List[float], user_id: str, 
                            top_k: int = 10, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """语义搜索"""
        collection = self.get_user_collection(user_id)
        
        # 构建查询过滤器
        where_filter = {}
        if filters:
            if filters.get('min_influence_weight'):
                where_filter['psp_influence_weight'] = {'$gte': filters['min_influence_weight']}
            if filters.get('source'):
                where_filter['source'] = filters['source']
        
        # 执行查询
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where_filter if where_filter else None
        )
        
        # 格式化结果
        formatted_results = []
        if results['ids'] and results['ids'][0]:
            for i, hinata_id in enumerate(results['ids'][0]):
                result = {
                    'hinata_id': hinata_id,
                    'similarity_score': 1 - results['distances'][0][i],  # 转换为相似度
                    'metadata': results['metadatas'][0][i],
                    'document': results['documents'][0][i] if results['documents'] else ''
                }
                formatted_results.append(result)
        
        return formatted_results


class FullTextIndexManager:
    """全文搜索索引管理器"""
    
    def __init__(self, elasticsearch_url: str):
        self.elasticsearch_url = elasticsearch_url
        self.es_client = None
        
    async def initialize(self):
        """初始化Elasticsearch客户端"""
        self.es_client = AsyncElasticsearch([self.elasticsearch_url])
        
        # 创建索引模板
        await self._create_index_template()
    
    async def _create_index_template(self):
        """创建索引模板"""
        template = {
            "index_patterns": ["hinata_*"],
            "template": {
                "mappings": {
                    "properties": {
                        "hinata_id": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "timestamp": {"type": "date"},
                        "source": {"type": "keyword"},
                        "highlight": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "note": {
                            "type": "text",
                            "analyzer": "standard"
                        },
                        "enhanced_tags": {"type": "keyword"},
                        "psp_influence_weight": {"type": "float"},
                        "attention_weight": {"type": "float"},
                        "quality_score": {"type": "float"}
                    }
                }
            }
        }
        
        try:
            await self.es_client.indices.put_index_template(
                name="hinata_template",
                body=template
            )
        except Exception:
            pass  # 模板可能已存在
    
    async def index_hinata(self, hinata_data: Dict[str, Any], user_id: str):
        """索引HiNATA文档"""
        index_name = f"hinata_{user_id}"
        
        doc = {
            "hinata_id": hinata_data['id'],
            "user_id": user_id,
            "timestamp": hinata_data['timestamp'],
            "source": hinata_data['source'],
            "highlight": hinata_data['highlight'],
            "note": hinata_data['note'],
            "enhanced_tags": hinata_data.get('enhanced_tags', []),
            "psp_influence_weight": hinata_data.get('psp_influence_weight', 0),
            "attention_weight": hinata_data.get('attention_weight', 0),
            "quality_score": hinata_data.get('quality_score', 0)
        }
        
        await self.es_client.index(
            index=index_name,
            id=hinata_data['id'],
            body=doc
        )
    
    async def search_text(self, query_text: str, user_id: str, 
                         top_k: int = 10, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """全文搜索"""
        index_name = f"hinata_{user_id}"
        
        # 构建查询
        query = {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query_text,
                            "fields": ["highlight^2", "note"],
                            "type": "best_fields"
                        }
                    }
                ]
            }
        }
        
        # 添加过滤器
        if filters:
            filter_clauses = []
            
            if filters.get('min_influence_weight'):
                filter_clauses.append({
                    "range": {
                        "psp_influence_weight": {"gte": filters['min_influence_weight']}
                    }
                })
            
            if filters.get('source'):
                filter_clauses.append({
                    "term": {"source": filters['source']}
                })
            
            if filters.get('tags'):
                filter_clauses.append({
                    "terms": {"enhanced_tags": filters['tags']}
                })
            
            if filter_clauses:
                query["bool"]["filter"] = filter_clauses
        
        # 执行搜索
        response = await self.es_client.search(
            index=index_name,
            body={
                "query": query,
                "size": top_k,
                "sort": [
                    {"psp_influence_weight": {"order": "desc"}},
                    {"_score": {"order": "desc"}}
                ]
            }
        )
        
        # 格式化结果
        results = []
        for hit in response['hits']['hits']:
            result = {
                'hinata_id': hit['_source']['hinata_id'],
                'relevance_score': hit['_score'],
                'metadata': hit['_source'],
                'highlights': hit.get('highlight', {})
            }
            results.append(result)
        
        return results


class StorageEngine:
    """存储引擎主类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 存储层管理器
        self.hot_storage = HotStorageManager(config['redis_url'])
        self.warm_storage = WarmStorageManager(config['postgres_dsn'])
        self.cold_storage = ColdStorageManager(config['cold_storage_path'])
        
        # 功能开关：默认关闭向量/全文索引，便于最小可跑
        self.enable_vector_index: bool = bool(config.get('enable_vector_index', False))
        self.enable_fulltext_index: bool = bool(config.get('enable_fulltext_index', False))
        
        # 索引管理器（按需启用）
        self.vector_index = VectorIndexManager(config['chroma_persist_dir']) if self.enable_vector_index else None
        self.fulltext_index = FullTextIndexManager(config['elasticsearch_url']) if self.enable_fulltext_index else None
        
        # 缓存和性能
        self.cache = {}
        self.cache_ttl = config.get('cache_ttl', 3600)
        self.metrics = StorageMetrics()
        
    async def initialize(self):
        """初始化存储引擎"""
        await self.hot_storage.initialize()
        await self.warm_storage.initialize()
        await self.cold_storage.initialize()
        if self.vector_index:
            await self.vector_index.initialize()
        if self.fulltext_index:
            await self.fulltext_index.initialize()
    
    async def store_hinata(self, hinata_data: Dict[str, Any], user_id: str):
        """存储HiNATA数据"""
        start_time = time.time()
        
        # 确定存储层级
        storage_tier = self._determine_storage_tier(hinata_data)
        
        # 存储到对应层级
        if storage_tier == StorageTier.HOT:
            await self.hot_storage.store_hinata(hinata_data, user_id)
        elif storage_tier == StorageTier.WARM:
            await self.warm_storage.store_hinata(hinata_data, user_id)
        else:
            await self.cold_storage.store_hinata_batch([hinata_data], user_id)
        
        # 建立索引（按需）
        await self._build_indexes(hinata_data, user_id)
        
        # 更新指标
        self.metrics.total_hinata_count += 1
        if storage_tier == StorageTier.HOT:
            self.metrics.hot_tier_count += 1
        elif storage_tier == StorageTier.WARM:
            self.metrics.warm_tier_count += 1
        else:
            self.metrics.cold_tier_count += 1
        
        processing_time = time.time() - start_time
        self.metrics.index_build_time = (self.metrics.index_build_time * 0.9 + processing_time * 0.1)
    
    def _determine_storage_tier(self, hinata_data: Dict[str, Any]) -> StorageTier:
        """确定存储层级"""
        influence_weight = hinata_data.get('psp_influence_weight', 0)
        created_time = datetime.fromisoformat(hinata_data['timestamp'].replace('Z', '+00:00'))
        recency_days = (datetime.now(timezone.utc) - created_time).days
        
        if influence_weight > 0.7 or recency_days < 7:
            return StorageTier.HOT
        elif influence_weight > 0.3 or recency_days < 30:
            return StorageTier.WARM
        else:
            return StorageTier.COLD
    
    async def _build_indexes(self, hinata_data: Dict[str, Any], user_id: str):
        """建立所有索引（若启用）"""
        tasks = []
        if self.vector_index:
            tasks.append(self.vector_index.add_hinata_vector(hinata_data, user_id))
        if self.fulltext_index:
            tasks.append(self.fulltext_index.index_hinata(hinata_data, user_id))
        if tasks:
            await asyncio.gather(*tasks)
    
    async def retrieve_hinata(self, hinata_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """检索单个HiNATA"""
        start_time = time.time()
        
        # 检查缓存
        cache_key = f"{user_id}:{hinata_id}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                self.metrics.cache_hit_rate = (self.metrics.cache_hit_rate * 0.9 + 1.0 * 0.1)
                return cached_data
        
        # 按存储层级顺序查找
        hinata_data = None
        
        # 1. 热数据层
        hinata_data = await self.hot_storage.get_hinata(hinata_id)
        
        # 2. 温数据层
        if not hinata_data:
            hinata_data = await self.warm_storage.get_hinata(hinata_id)
        
        # 3. 冷数据层
        if not hinata_data:
            hinata_data = await self.cold_storage.get_hinata(hinata_id, user_id)
        
        # 更新缓存
        if hinata_data:
            self.cache[cache_key] = (hinata_data, time.time())
        
        # 更新指标
        retrieval_time = time.time() - start_time
        self.metrics.average_retrieval_time = (
            self.metrics.average_retrieval_time * 0.9 + retrieval_time * 0.1
        )
        
        if not hinata_data:
            self.metrics.cache_hit_rate = (self.metrics.cache_hit_rate * 0.9 + 0.0 * 0.1)
        
        return hinata_data
    
    async def multi_strategy_search(self, query: RetrievalQuery) -> List[RetrievalResult]:
        """多策略检索"""
        start_time = time.time()
        all_candidates = set()
        
        # 策略1: 语义相似性检索（若启用向量索引且提供向量）
        if self.vector_index and query.semantic_vector:
            semantic_results = await self.vector_index.semantic_search(
                query.semantic_vector, query.user_id, top_k=20, filters=query.filters
            )
            all_candidates.update(result['hinata_id'] for result in semantic_results)
        
        # 策略2: 全文搜索（若启用全文索引且提供查询文本）
        if self.fulltext_index and query.query_text:
            text_results = await self.fulltext_index.search_text(
                query.query_text, query.user_id, top_k=20, filters=query.filters
            )
            all_candidates.update(result['hinata_id'] for result in text_results)
        
        # 策略3: 高权重内容检索
        high_weight_ids = await self.warm_storage.query_by_criteria(
            query.user_id, {'min_influence_weight': 0.7, 'limit': 15}
        )
        all_candidates.update(high_weight_ids)
        
        # 策略4: 最近内容检索
        if query.time_range:
            recent_ids = await self.hot_storage.query_by_time_range(
                query.user_id, query.time_range[0], query.time_range[1]
            )
            all_candidates.update(recent_ids)
        
        # 对候选结果进行排序和过滤
        ranked_results = await self._rank_and_filter_results(
            list(all_candidates), query
        )
        
        # 更新检索时间指标
        retrieval_time = time.time() - start_time
        self.metrics.average_retrieval_time = (
            self.metrics.average_retrieval_time * 0.9 + retrieval_time * 0.1
        )
        
        return ranked_results[:query.limit]
    
    async def _rank_and_filter_results(self, hinata_ids: List[str], query: RetrievalQuery) -> List[RetrievalResult]:
        """对检索结果进行排序和过滤"""
        results = []
        
        for hinata_id in hinata_ids:
            # 获取HiNATA数据
            hinata_data = await self.retrieve_hinata(hinata_id, query.user_id)
            if not hinata_data:
                continue
            
            # 计算相关性分数
            relevance_score = self._calculate_relevance_score(hinata_data, query)
            
            # 过滤低相关性结果
            if relevance_score < query.min_relevance_score:
                continue
            
            # 确定存储层级
            storage_tier = self._determine_storage_tier(hinata_data)
            
            result = RetrievalResult(
                hinata_id=hinata_id,
                relevance_score=relevance_score,
                storage_tier=storage_tier,
                retrieval_time=0.0,  # 这里可以记录具体的检索时间
                content_summary=hinata_data['highlight'][:100],
                metadata={
                    'psp_influence_weight': hinata_data.get('psp_influence_weight', 0),
                    'attention_weight': hinata_data.get('attention_weight', 0),
                    'quality_score': hinata_data.get('quality_score', 0),
                    'source': hinata_data.get('source', ''),
                    'timestamp': hinata_data.get('timestamp', '')
                }
            )
            results.append(result)
        
        # 按相关性分数排序
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results
    
    def _calculate_relevance_score(self, hinata_data: Dict[str, Any], query: RetrievalQuery) -> float:
        """计算相关性分数"""
        factors = {
            'psp_influence_weight': hinata_data.get('psp_influence_weight', 0) * 0.3,
            'attention_weight': hinata_data.get('attention_weight', 0) * 0.25,
            'quality_score': hinata_data.get('quality_score', 0) * 0.2,
            'recency': self._calculate_recency_score(hinata_data.get('timestamp', '')) * 0.15,
            'source_preference': 0.1  # 可以基于用户偏好调整
        }
        
        return sum(factors.values())
    
    def _calculate_recency_score(self, timestamp: str) -> float:
        """计算时效性分数"""
        try:
            created_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            days_ago = (datetime.now(timezone.utc) - created_time).days
            
            # 指数衰减
            return max(0.1, 1.0 * (0.95 ** days_ago))
        except:
            return 0.5
    
    async def get_storage_metrics(self) -> StorageMetrics:
        """获取存储指标"""
        # 更新各层统计
        hot_stats = await self.hot_storage.get_storage_stats()
        warm_stats = await self.warm_storage.get_storage_stats()
        cold_stats = await self.cold_storage.get_storage_stats()
        
        self.metrics.hot_tier_count = hot_stats['hinata_count']
        self.metrics.warm_tier_count = warm_stats['hinata_count']
        self.metrics.cold_tier_count = cold_stats['hinata_count']
        self.metrics.total_hinata_count = (
            self.metrics.hot_tier_count + 
            self.metrics.warm_tier_count + 
            self.metrics.cold_tier_count
        )
        self.metrics.total_size_bytes = (
            hot_stats.get('memory_used_bytes', 0) + 
            warm_stats.get('total_size_bytes', 0) + 
            cold_stats.get('total_size_bytes', 0)
        )
        
        return self.metrics
    
    async def optimize_storage(self):
        """优化存储性能"""
        # 1. 清理过期缓存
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        for key in expired_keys:
            del self.cache[key]
        
        # 2. 清理过期热数据
        await self.hot_storage.cleanup_expired()
        
        # 3. 可以添加其他优化逻辑，如数据迁移等
    
    async def close(self):
        """关闭存储引擎"""
        if self.hot_storage.redis_pool:
            await self.hot_storage.redis_pool.close()
        if self.warm_storage.db_pool:
            await self.warm_storage.db_pool.close()
        if self.fulltext_index.es_client:
            await self.fulltext_index.es_client.close()


# 使用示例
async def main():
    """使用示例"""
    config = {
        'redis_url': 'redis://localhost:6379',
        'postgres_dsn': 'postgresql://user:password@localhost/byenatos',
        'cold_storage_path': '/data/cold_storage',
        'chroma_persist_dir': '/data/chroma',
        'elasticsearch_url': 'http://localhost:9200',
        'cache_ttl': 3600
    }
    
    storage_engine = StorageEngine(config)
    await storage_engine.initialize()
    
    # 示例存储
    sample_hinata = {
        "id": "hinata_20241201_001",
        "timestamp": "2024-12-01T10:30:00Z",
        "source": "browser_extension",
        "highlight": "Machine learning models require careful validation",
        "note": "This is crucial for ensuring our models work well in production.",
        "enhanced_tags": ["machine-learning", "validation"],
        "attention_weight": 0.8,
        "psp_influence_weight": 0.9,
        "quality_score": 0.85,
        "embedding_vector": [0.1, 0.2, 0.3] * 256
    }
    
    await storage_engine.store_hinata(sample_hinata, "user_123")
    
    # 示例检索
    query = RetrievalQuery(
        user_id="user_123",
        query_type="semantic_search",
        query_text="machine learning validation",
        limit=10
    )
    
    results = await storage_engine.multi_strategy_search(query)
    
    for result in results:
        print(f"Found: {result.hinata_id} (score: {result.relevance_score:.3f})")
    
    # 获取指标
    metrics = await storage_engine.get_storage_metrics()
    print(f"Storage metrics: {metrics}")
    
    await storage_engine.close()


if __name__ == "__main__":
    asyncio.run(main())