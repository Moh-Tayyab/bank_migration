import csv

from ..models import MigrationResult


class CSVWriter:
    def write(self, result: MigrationResult, output_path: str):
        with open(output_path, "w", newline="") as f:
            if result.records:
                writer = csv.DictWriter(f, fieldnames=result.records[0].keys())
                writer.writeheader()
                writer.writerows(result.records)
            else:
                rows = []
                for entry in result.audit_trail:
                    rows.append(
                        {
                            "event": entry.event.value,
                            "record_id": entry.record_id,
                            "bank_pair": entry.bank_pair,
                            "details": entry.details,
                            "timestamp": str(entry.timestamp),
                        }
                    )
                if not rows:
                    rows.append(
                        {
                            "success": str(result.success),
                            "total": str(result.total_records),
                            "processed": str(result.processed),
                            "failed": str(result.failed),
                        }
                    )
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
