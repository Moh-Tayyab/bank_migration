from typing import Any, Dict, Iterator, List

from .detector import FormatDetector
from .infrastructure.tasks import run_data_migration_task


class MigrationDispatcher:
    def __init__(self, chunk_size: int = 5000):
        self.chunk_size = chunk_size

    def _get_record_chunks(self, filename: str) -> Iterator[List[Dict[str, Any]]]:
        file_format = FormatDetector.detect_format(filename)
        records = FormatDetector.extract(filename, file_format)
        chunk = []
        for row in records:
            chunk.append(row)
            if len(chunk) >= self.chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    def dispatch_migration(self, filename: str, source_bank: str, target_bank: str, output_format: str = "json"):
        print(f"Dispatching migration for {filename}...")

        chunk_id = 0
        total_dispatched = 0

        for chunk in self._get_record_chunks(filename):
            chunk_id += 1
            run_data_migration_task.delay(
                records=chunk,
                source_bank=source_bank,
                target_bank=target_bank,
                output_format=output_format,
            )
            total_dispatched += len(chunk)
            if chunk_id % 10 == 0:
                print(f"Dispatched {chunk_id} chunks... ({total_dispatched} records)")

        print(f"Successfully dispatched {total_dispatched} records in {chunk_id} chunks.")
        return chunk_id
