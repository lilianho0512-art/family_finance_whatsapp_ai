from pathlib import Path
from PIL import Image
import pytesseract
from app.config import settings
from app.utils.logger import logger

if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


def ocr_image(file_path: str) -> str:
    p = Path(file_path)
    if not p.exists():
        logger.warning(f"OCR file not found: {file_path}")
        return ""
    try:
        img = Image.open(p)
        try:
            text = pytesseract.image_to_string(img, lang="eng+chi_sim")
        except Exception:
            text = pytesseract.image_to_string(img)
        return (text or "").strip()
    except pytesseract.pytesseract.TesseractNotFoundError as e:
        logger.error(f"Tesseract not installed: {e}")
        return ""
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return ""


def ocr_pdf(file_path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    except ImportError:
        logger.info("pypdf not installed; PDF text extraction skipped")
        return ""
    except Exception as e:
        logger.warning(f"PDF parse failed: {e}")
        return ""
