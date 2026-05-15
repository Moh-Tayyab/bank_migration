
import csv
from typing import List, Dict, Any, Iterator
from .infrastructure.tasks import process_migration_chunk
from .infrastructure.celery_app import app

class MigrationDispatcher:
    def __init__(self, chunk_size: int = 5000):
        self.chunk_size = chunk_size

    def _get_record_chunks(self, filename: str) -> Iterator[List[Dict[str, Any]]]:
        """
        Reads a massive file and yields chunks of records.
        This ensures we never load the whole file into RAM.
        """
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            chunk = []
            for row in reader:
                chunk.append(row)
                if len(chunk) >= self.chunk_size:
                    yield chunk
                    chunk = []
            if chunk:
                yield chunk

    def dispatch_migration(self, filename: str, source_bank: str, target_bank: str):
        """
        Splits the file into chunks and pushes each chunk to Celery workers.
        """
        print(f"Dispatching migration for {filename}...")
        
        chunk_id = 0
        total_dispatched = 0
        
        for chunk in self._get_record_chunks(filename):
            chunk_id += 1
            # Push to Celery queue
            process_migration_chunk.delay(
                chunk_id=f"CHUNK-{chunk_id:05d}",
                records=chunk,
                source_bank=source_bank,
                target_bank=target_bank
            )
            total_dispatched += len(chunk)
            if chunk_id % 10 == 0:
                print(f"Dispatched {chunk_id} chunks... ({total_dispatched} records)")
                
        print(f"Successfully dispatched {total_dispatched} records in {chunk_id} chunks.")
        return chunk_id
