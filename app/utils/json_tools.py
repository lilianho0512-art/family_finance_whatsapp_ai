import json
import re

JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str):
    """Robustly extract a JSON object from arbitrary AI output."""
    if not text:
        return None
    text = text.strip()
    m = JSON_FENCE.search(text)
    if m:
        text = m.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        cleaned = re.sub(r",\s*([}\]])", r"\1", candidate)
        cleaned = cleaned.replace("\n", " ").replace("\t", " ")
        try:
            return json.loads(cleaned)
        except Exception:
            try:
                return json.loads(cleaned.replace("'", '"'))
            except Exception:
                return None


def safe_json_dumps(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return "{}"
