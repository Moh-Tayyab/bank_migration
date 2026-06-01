import html as _html
from ..models import MigrationResult


class HTMLWriter:
    def write(self, result: MigrationResult, output_path: str):
        rows_html = ""
        for entry in result.audit_trail:
            rows_html += (
                f"<tr><td>{_html.escape(entry.event.value)}</td>"
                f"<td>{_html.escape(entry.record_id)}</td>"
                f"<td>{_html.escape(entry.bank_pair)}</td>"
                f"<td>{_html.escape(entry.details)}</td>"
                f"<td>{_html.escape(str(entry.timestamp))}</td></tr>"
            )
        records_html = ""
        if result.records:
            fieldnames = list(result.records[0].keys())
            records_html += "<tr>" + "".join(f"<th>{_html.escape(k)}</th>" for k in fieldnames) + "</tr>"
            for record in result.records:
                records_html += "<tr>" + "".join(f"<td>{_html.escape(str(record.get(k, '')))}</td>" for k in fieldnames) + "</tr>"
        html = f"""<!DOCTYPE html>
<html>
<head><title>Migration Report</title>
<style>
body {{ font-family: Arial; margin: 40px; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #4CAF50; color: white; }}
tr:nth-child(even) {{ background-color: #f2f2f2; }}
</style></head>
<body>
<h1>Migration Report</h1>
<p><strong>Success:</strong> {'Yes' if result.success else 'No'}</p>
<p><strong>Total:</strong> {result.total_records} | <strong>Processed:</strong> {result.processed} | <strong>Failed:</strong> {result.failed}</p>
{'<hr><h2>Migrated Records</h2><table>' + records_html + '</table>' if records_html else ''}
<hr>
<h2>Audit Trail</h2>
<table>
<tr><th>Event</th><th>Record ID</th><th>Bank Pair</th><th>Details</th><th>Timestamp</th></tr>
{rows_html}
</table>
</body></html>"""
        with open(output_path, "w") as f:
            f.write(html)