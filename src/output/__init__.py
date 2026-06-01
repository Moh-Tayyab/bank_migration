from .csv_writer import CSVWriter
from .docx_writer import DOCXWriter
from .html_writer import HTMLWriter
from .json_writer import JSONWriter
from .sqlldr_writer import SQLLoaderWriter
from .xlsx_writer import XLSXWriter


def get_writer(format_name: str):
    writers = {
        "json": JSONWriter,
        "csv": CSVWriter,
        "docx": DOCXWriter,
        "html": HTMLWriter,
        "xlsx": XLSXWriter,
        "sqlldr": SQLLoaderWriter,
    }
    cls = writers.get(format_name.lower())
    if not cls:
        raise ValueError(f"Unsupported output format: {format_name}")
    return cls()


__all__ = [
    "JSONWriter",
    "CSVWriter",
    "DOCXWriter",
    "HTMLWriter",
    "XLSXWriter",
    "SQLLoaderWriter",
    "get_writer",
]
