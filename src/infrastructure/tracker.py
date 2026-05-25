
import redis
import json
from typing import Dict, Any, Optional
from .celery_app import app

class MigrationTracker:
    def __init__(self, redis_url: str = 'redis://localhost:6379/0'):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.prefix = "migration_status:"

    def init_migration(self, migration_id: str, total_chunks: int, total_records: int):
        """Initialize tracking metadata for a new migration."""
        key = f"{self.prefix}{migration_id}"
        data = {
            "total_chunks": total_chunks,
            "processed_chunks": 0,
            "total_records": total_records,
            "processed_records": 0,
            "failed_records": 0,
            "status": "RUNNING"
        }
        self.redis.hset(key, mapping=data)
        # Also set an expiration to prevent Redis from filling up over time
        self.redis.expire(key, 86400) # 24 hours

    def update_chunk_status(self, migration_id: str, chunk_id: str, processed: int, failed: int):
        """Update progress as each worker finishes a chunk."""
        key = f"{self.prefix}{migration_id}"
        
        # Use Redis pipeline for atomic updates
        pipe = self.redis.pipeline()
        pipe.hincrby(key, "processed_chunks", 1)
        pipe.hincrby(key, "processed_records", processed)
        pipe.hincrby(key, "failed_records", failed)
        pipe.execute()
        
        # Check if migration is complete
        status = self.get_status(migration_id)
        if status['processed_chunks'] >= status['total_chunks']:
            self.redis.hset(key, "status", "COMPLETED")

    def get_status(self, migration_id: str) -> Dict[str, Any]:
        """Retrieve current progress for a specific migration."""
        key = f"{self.prefix}{migration_id}"
        data = self.redis.hgetall(key)
        
        if not data:
            return {"status": "NOT_FOUND"}
            
        # Convert string numbers to ints
        return {
            "migration_id": migration_id,
            "status": data.get("status"),
            "progress_percent": (float(data.get("processed_chunks", 0)) / float(data.get("total_chunks", 1)) * 100) if data.get("total_chunks") else 0,
            "processed_records": int(data.get("processed_records", 0)),
            "failed_records": int(data.get("failed_records", 0)),
            "total_records": int(data.get("total_records", 0)),
            "processed_chunks": int(data.get("processed_chunks", 0)),
            "total_chunks": int(data.get("total_chunks", 0))
        }
