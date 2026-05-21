import json
import csv
import os
import io
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from .models import FileFormat


class FormatDetector:
    MIME_MAP = {
        "text/csv": FileFormat.CSV,
        "application/json": FileFormat.JSON,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileFormat.DOCX,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileFormat.XLSX,
        "text/xml": FileFormat.XML,
        "application/xml": FileFormat.XML,
        "text/plain": FileFormat.TXT,
    }

    @staticmethod
    def detect_format(filepath: str) -> FileFormat:
        ext = os.path.splitext(filepath)[1].lower()
        ext_map = {
            ".csv": FileFormat.CSV,
            ".json": FileFormat.JSON,
            ".docx": FileFormat.DOCX,
            ".xlsx": FileFormat.XLSX,
            ".xml": FileFormat.XML,
            ".txt": FileFormat.TXT,
        }
        return ext_map.get(ext, FileFormat.TXT)

    @staticmethod
    def extract(filepath: str, file_format: Optional[FileFormat] = None) -> List[Dict[str, Any]]:
        fmt = file_format or FormatDetector.detect_format(filepath)
        extractors = {
            FileFormat.CSV: FormatDetector._extract_csv,
            FileFormat.JSON: FormatDetector._extract_json,
            FileFormat.DOCX: FormatDetector._extract_docx,
            FileFormat.XLSX: FormatDetector._extract_xlsx,
            FileFormat.XML: FormatDetector._extract_xml,
            FileFormat.TXT: FormatDetector._extract_txt,
        }
        extractor = extractors.get(fmt)
        if not extractor:
            raise ValueError(f"Unsupported format: {fmt}")
        return extractor(filepath)

    @staticmethod
    def _extract_csv(filepath: str) -> List[Dict[str, Any]]:
        records = []
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({k.strip(): v.strip() if v else "" for k, v in row.items()})
        return records

    @staticmethod
    def _extract_json(filepath: str) -> List[Dict[str, Any]]:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return [data]
        return data

    @staticmethod
    def _extract_docx(filepath: str) -> List[Dict[str, Any]]:
        from docx import Document
        doc = Document(filepath)
        records = []
        headers = []
        for i, table in enumerate(doc.tables):
            for j, row in enumerate(table.rows):
                cells = [cell.text.strip() for cell in row.cells]
                if j == 0:
                    headers = cells
                else:
                    if len(cells) == len(headers):
                        records.append(dict(zip(headers, cells)))
        if not records:
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            records.append({"content": text})
        return records

    @staticmethod
    def _extract_xlsx(filepath: str) -> List[Dict[str, Any]]:
        import openpyxl
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        ws = wb.active
        records = []
        headers = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                headers = [str(cell).strip() if cell else f"col_{j}" for j, cell in enumerate(row)]
            else:
                record = {}
                for j, cell in enumerate(row):
                    if j < len(headers):
                        record[headers[j]] = str(cell) if cell is not None else ""
                if record:
                    records.append(record)
        wb.close()
        return records

    @staticmethod
    def _extract_xml(filepath: str) -> List[Dict[str, Any]]:
        import defusedxml.ElementTree as safe_ET
        tree = safe_ET.parse(filepath)
        root = tree.getroot()
        records = []
        for child in root:
            record = {}
            for sub in child:
                record[sub.tag] = sub.text or ""
            if record:
                records.append(record)
        if not records:
            record = {}
            for sub in root:
                record[sub.tag] = sub.text or ""
            if record:
                records.append(record)
        return records

    @staticmethod
    def _extract_txt(filepath: str) -> List[Dict[str, Any]]:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return [{"content": content}]