"""Export a clean, public signal table from the private replay workbooks.

Read-only over the source Excel files. It keeps only the "current" sheet layout
(2H/4H + VOLUME headers) and only indicator-generated signals (SIGNAL=Sí),
excluding manual entries. It writes a minimal, anonymized CSV: no account
values, no position sizes, and no personal execution flags.

Point ``TRADING_SOURCE_DIR`` at the folder that holds the ``ATR 20xx.xlsx``
workbooks (these stay private and are not distributed with this repository).

    TRADING_SOURCE_DIR=/path/to/workbooks python analysis/build_dataset.py

Output: data/signals-2023-2024.csv
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import pandas as pd

SOURCE_DIR = Path(os.environ.get("TRADING_SOURCE_DIR", "workbooks"))
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "signals-2023-2024.csv"
YEARS = {"2023", "2024"}
SKIP_SHEETS = {"DATA", "Análisis", "Análisis2", "Backup Análisis"}

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _col_index(ref: str) -> int:
    letters = "".join(filter(str.isalpha, ref)).upper()
    value = 0
    for ch in letters:
        value = value * 26 + ord(ch) - 64
    return value


def _cell_value(cell, shared: list[str]):
    value_el = cell.find("m:v", NS)
    if value_el is None:
        return None
    raw = value_el.text
    if cell.attrib.get("t") == "s":
        try:
            return shared[int(raw)]
        except (ValueError, IndexError):
            return None
    return raw


def _read_sheet(zip_file: ZipFile, target: str, shared: list[str]):
    path = target.lstrip("/") if target.startswith("/") else f"xl/{target}"
    path = str(Path(path))
    doc = ET.fromstring(zip_file.read(path))
    for row in doc.findall(".//m:sheetData/m:row", NS):
        row_number = int(row.attrib["r"])
        values = {
            _col_index(cell.attrib.get("r", "")): _cell_value(cell, shared)
            for cell in row.findall("m:c", NS)
        }
        yield row_number, values


def _shared_strings(zip_file: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zip_file.namelist():
        return []
    root = ET.fromstring(zip_file.read("xl/sharedStrings.xml"))
    return [
        "".join(t.text or "" for t in si.findall(".//m:t", NS))
        for si in root.findall("m:si", NS)
    ]


def _excel_date(serial):
    try:
        return datetime(1899, 12, 30) + timedelta(days=float(serial))
    except (TypeError, ValueError):
        return None


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _hour(entry: str | None):
    if not entry:
        return None
    match = re.match(r"^\s*(\d{1,2})", str(entry))
    return int(match.group(1)) if match else None


def _pattern_tag(raw: str | None) -> str:
    text = (raw or "").lower()
    has_engulf = "engulf" in text
    has_pin = "pinbar" in text or "pin" in text
    if has_engulf and has_pin:
        return "Both"
    if has_engulf:
        return "Engulfing"
    if has_pin:
        return "Pinbar"
    return "None"


def build() -> pd.DataFrame:
    records: list[dict] = []
    for path in sorted(SOURCE_DIR.glob("*.xlsx")):
        year = path.stem[-4:]
        if year not in YEARS:
            continue
        with ZipFile(path) as zip_file:
            workbook = ET.fromstring(zip_file.read("xl/workbook.xml"))
            rels = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))
            rel_map = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
            shared = _shared_strings(zip_file)

            for sheet in workbook.findall("m:sheets/m:sheet", NS):
                name = sheet.attrib.get("name", "")
                if name in SKIP_SHEETS:
                    continue
                target = rel_map[sheet.attrib[f"{{{NS['r']}}}id"]]
                rows = list(_read_sheet(zip_file, target, shared))
                if not rows:
                    continue
                header = next((v for n, v in rows if n == 2), {})
                if header.get(7) != "2H/4H" or header.get(9) != "VOLUME":
                    continue

                for row_number, v in rows:
                    if row_number < 3 or v.get(4) not in {"W", "L"}:
                        continue
                    date = _excel_date(v.get(2))
                    records.append(
                        {
                            "asset": name,
                            "date": date.date().isoformat() if date else None,
                            "weekday": (v.get(3) or "").strip(),
                            "hour": _hour(v.get(6)),
                            "volume": (v.get(9) or "").strip(),
                            "pattern": _pattern_tag(v.get(10)),
                            "sl_pct": _to_float(v.get(11)),
                            "result": v.get(4),
                            "signal": (v.get(16) or "").strip(),
                        }
                    )

    frame = pd.DataFrame(records)
    # Publish only indicator-generated signals (SIGNAL=Sí), not manual entries.
    frame = frame[frame["signal"] == "Si"].drop(columns=["signal"])
    frame = frame.dropna(subset=["date", "hour"]).sort_values(["date", "hour", "asset"])
    frame["hour"] = frame["hour"].astype(int)
    return frame.reset_index(drop=True)


if __name__ == "__main__":
    if not SOURCE_DIR.is_dir():
        raise SystemExit(
            f"Source folder not found: {SOURCE_DIR}. "
            "Set TRADING_SOURCE_DIR to the folder with the ATR workbooks."
        )
    data = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUTPUT, index=False)
    print(f"wrote {OUTPUT} ({len(data)} rows, {len(data.columns)} columns)")
