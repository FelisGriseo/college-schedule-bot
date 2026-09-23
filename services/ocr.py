import asyncio
import io
import logging

logger = logging.getLogger(__name__)
_reader = None


def _read_table(image_bytes: bytes, confidence_threshold: float = 0.05) -> str:
    global _reader
    import easyocr
    import numpy as np
    from PIL import Image, ImageEnhance, ImageOps

    image = Image.open(io.BytesIO(image_bytes)).convert("L")
    image = ImageOps.autocontrast(image)
    image = ImageEnhance.Sharpness(image).enhance(1.5)
    image = image.resize((image.width * 2, image.height * 2))

    if _reader is None:
        _reader = easyocr.Reader(["uk", "en"], gpu=False, verbose=False)

    results = _reader.readtext(np.asarray(image), detail=1, paragraph=False)
    row_tolerance = 22
    rows: list[list[tuple[float, float, str]]] = []
    for box, text, confidence in results:
        if confidence < confidence_threshold or not text.strip():
            continue
        y = sum(point[1] for point in box) / len(box)
        x = min(point[0] for point in box)
        target = next((row for row in rows if abs(row[0][0] - y) < row_tolerance), None)
        if target is None:
            rows.append([(y, x, text)])
        else:
            target.append((y, x, text))

    lines = []
    for row in sorted(rows, key=lambda value: value[0][0]):
        cells = ["" for _ in range(6)]
        for _, x, text in sorted(row, key=lambda value: value[1]):
            relative_x = x / image.width
            column = next(
                (index for index, boundary in enumerate((0.18, 0.26, 0.43, 0.66, 0.90))
                 if relative_x < boundary),
                5,
            )
            cells[column] = f"{cells[column]} {text}".strip()
        if any(cells):
            lines.append(" | ".join(cells))
    return "\n".join(lines)


async def extract_table_text(client, message, backend: str) -> str:
    if backend != "easyocr" or not message.media:
        return ""
    try:
        image_bytes = await client.download_media(message, file=bytes)
        if not image_bytes or len(image_bytes) < 256:
            logger.warning("OCR skipped Telegram post %s: empty or invalid media", message.id)
            return ""
        text = await asyncio.to_thread(_read_table, image_bytes, 0.10)
        if not text:
            text = await asyncio.to_thread(_read_table, image_bytes, 0.05)
        logger.info("OCR completed for Telegram post %s: %s characters", message.id, len(text))
        return text
    except Exception:
        logger.exception("OCR failed for Telegram post %s", message.id)
        return ""
