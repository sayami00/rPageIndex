from __future__ import annotations

import logging
from pathlib import Path

from src.ingestion.base import BaseParser, derive_doc_id, generate_block_id
from src.models.ingestion import RawBlock

logger = logging.getLogger(__name__)

_OCR_DPI = 200


class OCRParser(BaseParser):
    def parse(self, path: str) -> list[RawBlock]:
        try:
            import pytesseract
            from pdf2image import convert_from_path
            from pytesseract import Output
        except ImportError as exc:
            logger.error("OCR dependencies not installed: %s", exc)
            return []

        try:
            pytesseract.get_tesseract_version()
        except Exception as exc:
            logger.error("Tesseract not found: %s", exc)
            return []

        doc_id = derive_doc_id(path)
        source_file = str(Path(path).resolve())
        blocks: list[RawBlock] = []

        try:
            images = convert_from_path(path, dpi=_OCR_DPI)
        except Exception as exc:
            logger.error("pdf2image failed on %s: %s", path, exc)
            return []

        for page_num, image in enumerate(images, start=1):
            try:
                page_blocks = _ocr_page(image, doc_id, source_file, page_num)
                blocks.extend(page_blocks)
            except Exception as exc:
                logger.warning("OCR failed on %s page %d: %s", path, page_num, exc)

        return blocks


def _ocr_page(image, doc_id: str, source_file: str, page_num: int) -> list[RawBlock]:
    import pytesseract
    from pytesseract import Output

    data = pytesseract.image_to_data(image, output_type=Output.DICT)

    para_groups: dict[int, list[dict]] = {}
    n = len(data["text"])
    for i in range(n):
        text = data["text"][i].strip()
        if not text:
            continue
        conf = int(data["conf"][i])
        if conf < 0:
            continue
        block_num = data["block_num"][i]
        para_num = data["par_num"][i]
        key = (block_num, para_num)
        if key not in para_groups:
            para_groups[key] = []
        para_groups[key].append({"text": text, "conf": conf})

    blocks: list[RawBlock] = []
    for seq, (_, words) in enumerate(sorted(para_groups.items())):
        para_text = " ".join(w["text"] for w in words)
        if not para_text.strip():
            continue
        confs = [w["conf"] for w in words if w["conf"] >= 0]
        mean_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
        mean_conf = max(0.0, min(1.0, mean_conf))

        blocks.append(RawBlock(
            block_id=generate_block_id(doc_id, page_num, seq),
            doc_id=doc_id,
            source_file=source_file,
            source_format="ocr",
            page_number=page_num,
            sequence=seq,
            raw_text=para_text,
            block_type_hint="paragraph",
            ocr_confidence=mean_conf,
        ))

    return blocks
