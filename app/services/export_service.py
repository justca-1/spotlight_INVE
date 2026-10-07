"""Exporting the current Inventory view to a file (CSV) or a print/PDF
report. Deliberately avoids adding any new dependency:

- CSV uses Python's stdlib `csv` module.
- The print/PDF report uses QTextDocument + QtPrintSupport, both already
  part of the PySide6 install -- no openpyxl, no reportlab, nothing new
  to fail to install on a machine that's already had enough dependency
  trouble in this project.
"""

from __future__ import annotations

import csv
import html
from datetime import datetime
from pathlib import Path

from app.models.models import Item
from app.services.item_service import FilterState, fetch_items

EXPORT_COLUMNS = [
    "Inventory #",
    "Item",
    "Category",
    "Owner",
    "Location",
    "Status",
    "Serial Number",
    "Date Acquired",
    "Notes",
]


def fetch_items_for_export(filters: FilterState) -> list[Item]:
    """Everything matching the current filter, uncapped -- exporting a
    silently-truncated 500-row page when someone has 12,000 items and no
    filter applied would be a real correctness bug, not just an
    inconvenience.
    """
    result = fetch_items(filters, limit=None)
    return result.items


def _row_for(item: Item) -> list[str]:
    return [
        item.inventory_number,
        item.name,
        item.category.name if item.category else "",
        item.owner.name if item.owner else "",
        item.location.name if item.location else "",
        item.status.value if item.status else "",
        item.serial_number or "",
        item.date_acquired.isoformat() if item.date_acquired else "",
        item.notes or "",
    ]


def export_to_csv(items: list[Item], filepath: str) -> None:
    path = Path(filepath)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(EXPORT_COLUMNS)
        for item in items:
            writer.writerow(_row_for(item))


def build_html_report(items: list[Item], title: str = "Spotlight Inventory Report") -> str:
    """An HTML table for QTextDocument -- rendered for print/PDF export.
    Styled for paper (black text on white) regardless of the app's dark
    theme; a printed dark-background report would waste a lot of toner
    and look wrong on paper.
    """
    generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    rows_html = []
    for item in items:
        cells = [html.escape(str(v)) for v in _row_for(item)]
        rows_html.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")

    header_html = "".join(f"<th>{html.escape(c)}</th>" for c in EXPORT_COLUMNS)

    return f"""
    <html>
    <head>
    <style>
        body {{ font-family: Arial, Helvetica, sans-serif; color: #111; }}
        h1 {{ font-size: 18px; margin-bottom: 2px; }}
        .meta {{ font-size: 10px; color: #555; margin-bottom: 14px; }}
        table {{ border-collapse: collapse; width: 100%; font-size: 9px; }}
        th {{ background-color: #eee; text-align: left; padding: 4px 6px;
              border: 1px solid #999; }}
        td {{ padding: 4px 6px; border: 1px solid #ccc; }}
        tr:nth-child(even) {{ background-color: #f7f7f7; }}
    </style>
    </head>
    <body>
        <h1>{html.escape(title)}</h1>
        <div class="meta">Generated {generated} &middot; {len(items)} item(s)</div>
        <table>
            <thead><tr>{header_html}</tr></thead>
            <tbody>{"".join(rows_html)}</tbody>
        </table>
    </body>
    </html>
    """
