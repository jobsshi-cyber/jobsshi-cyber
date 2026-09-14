"""Generate a renewable-resource template without rewriting other workbook data."""

from __future__ import annotations

import math
import random
import zipfile
from pathlib import Path
from xml.etree import ElementTree


BASE_DIR = Path(__file__).resolve().parent
SRC_FILE = BASE_DIR / "8760小时模拟原始数据.xlsx"
DST_FILE = BASE_DIR / "8760小时模拟模板.xlsx"

PV_SHEET = "光伏逐小时数据"
WIND_SHEET = "风电逐小时数据"
N_HOURS = 8760
DATA_START_ROW = 4
DATA_COLUMN = "F"

PV_SUNRISE = 6
PV_SUNSET = 18
PV_PEAK = 1.0
RANDOM_SEED = 20260914
WIND_MIN = 0.0
WIND_MAX = 1.0

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _make_pv_values() -> list[float]:
    daylight_hours = PV_SUNSET - PV_SUNRISE
    values = []
    for index in range(N_HOURS):
        hour = index % 24
        if PV_SUNRISE <= hour < PV_SUNSET:
            value = PV_PEAK * math.sin(
                math.pi * (hour - PV_SUNRISE) / daylight_hours
            )
        else:
            value = 0.0
        values.append(round(max(0.0, value), 4))
    return values


def _make_wind_values() -> list[float]:
    rng = random.Random(RANDOM_SEED)
    return [round(rng.uniform(WIND_MIN, WIND_MAX), 4) for _ in range(N_HOURS)]


def _get_sheet_paths(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook_root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    rels_root = ElementTree.fromstring(
        archive.read("xl/_rels/workbook.xml.rels")
    )
    relationships = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels_root.findall(f"{{{PKG_REL_NS}}}Relationship")
    }
    paths = {}
    for sheet in workbook_root.findall(f"{{{MAIN_NS}}}sheets/{{{MAIN_NS}}}sheet"):
        name = sheet.attrib["name"]
        relationship_id = sheet.attrib[f"{{{REL_NS}}}id"]
        target = relationships[relationship_id].lstrip("/")
        paths[name] = target if target.startswith("xl/") else f"xl/{target}"
    return paths


def _patch_sheet(xml_bytes: bytes, values: list[float], sheet_name: str) -> bytes:
    root = ElementTree.fromstring(xml_bytes)
    first_row = DATA_START_ROW
    last_row = DATA_START_ROW + N_HOURS - 1
    changed_rows = set()
    for cell in root.iter(f"{{{MAIN_NS}}}c"):
        reference = cell.attrib.get("r", "")
        if not reference.startswith(DATA_COLUMN):
            continue
        row_text = reference[len(DATA_COLUMN):]
        if not row_text.isdigit():
            continue
        row = int(row_text)
        if not first_row <= row <= last_row:
            continue
        value_node = cell.find(f"{{{MAIN_NS}}}v")
        if value_node is None:
            raise ValueError(f"{sheet_name} 的 {reference} 单元格没有数值节点")
        value_node.text = f"{values[row - first_row]:.4f}"
        changed_rows.add(row)

    expected_rows = set(range(first_row, last_row + 1))
    if changed_rows != expected_rows:
        missing = sorted(expected_rows - changed_rows)[:5]
        raise ValueError(f"{sheet_name} 未完整找到 8760 个数据单元格，缺少行: {missing}")
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def _print_summary(name: str, values: list[float]) -> None:
    print(
        f"{name}: 最大出力={max(values):.4f}, "
        f"平均出力={sum(values) / len(values):.4f}, "
        f"年等效利用小时数={sum(values):.1f} h"
    )


def generate_template() -> Path:
    if not SRC_FILE.exists():
        raise FileNotFoundError(f"找不到源文件: {SRC_FILE}")

    pv_values = _make_pv_values()
    wind_values = _make_wind_values()
    replacements = {PV_SHEET: pv_values, WIND_SHEET: wind_values}

    print(f"读取源文件: {SRC_FILE}")
    with zipfile.ZipFile(SRC_FILE, "r") as source_zip:
        sheet_paths = _get_sheet_paths(source_zip)
        missing = [name for name in replacements if name not in sheet_paths]
        if missing:
            raise ValueError(f"工作簿缺少工作表: {missing}")

        with zipfile.ZipFile(DST_FILE, "w") as output_zip:
            for info in source_zip.infolist():
                content = source_zip.read(info.filename)
                for sheet_name, values in replacements.items():
                    if info.filename == sheet_paths[sheet_name]:
                        content = _patch_sheet(content, values, sheet_name)
                output_zip.writestr(info, content)

    _print_summary("光伏正弦曲线", pv_values)
    _print_summary("风电随机出力", wind_values)
    print(f"已生成模板文件: {DST_FILE}")
    print(f"原始文件未修改: {SRC_FILE}")
    return DST_FILE


if __name__ == "__main__":
    generate_template()
