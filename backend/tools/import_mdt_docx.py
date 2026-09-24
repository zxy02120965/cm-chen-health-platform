"""Convert the reviewed V1.0 Word tables into knowledge-item API payloads.

Usage:
  python tools/import_mdt_docx.py "菜品与食谱组件库.docx" FOOD
  python tools/import_mdt_docx.py "运动处方生成规则与动作库.docx" EXERCISE
  python tools/import_mdt_docx.py "肺预康复知识库.docx" PULMONARY

The tool emits JSON lines for PUT /api/ai-governance/knowledge/{item_id}.
It intentionally marks every imported row DRAFT.  An MDT reviewer must check
the source table, attach any approved video IDs, and explicitly promote it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from docx import Document


def normalized_header(value: str) -> str:
    aliases = {"ID": "item_id", "组件": "display_name", "菜品": "display_name", "动作": "display_name",
               "食材/重量": "ingredients", "估算营养": "estimated_nutrition", "估算能量": "estimated_energy",
               "做法": "method", "标签": "tags", "适用/优先": "indications", "目的": "purpose",
               "标准要点": "steps", "项目剂量草案": "draft_dose", "项目起始剂量草案": "draft_dose",
               "停止/慎用": "cautions", "慎用/限制": "cautions", "替代": "replacement", "备用": "replacement"}
    return aliases.get(value.strip(), value.strip())


def main() -> None:
    path, item_type = Path(sys.argv[1]), sys.argv[2].upper()
    doc = Document(path)
    for table in doc.tables:
        rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        if len(rows) < 2 or "ID" not in rows[0]:
            continue
        headers = [normalized_header(x) for x in rows[0]]
        for values in rows[1:]:
            raw = dict(zip(headers, values))
            item_id = raw.pop("item_id", "")
            if not item_id or item_id.startswith("配置"):
                continue
            print(json.dumps({"item_id": item_id, "item_type": item_type,
                "display_name": raw.pop("display_name", item_id), "content_json": raw,
                "source_document": path.name, "source_version": "V1.0", "status": "DRAFT"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
