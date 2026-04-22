"""Layout-aware fallback extraction for receipt-like finance documents."""

from __future__ import annotations

import re
from typing import Any

from .document import Block
from .text_processing import is_punctuation_noise


EMPTY_VALUES = {None, "", 0}

REQUIRED_FIELDS = {
    "receipt": ["total", "date", "transaction_id", "currency"],
    "payment_slip": ["amount", "reference_number", "transfer_date", "currency"],
}

AMOUNT_RE = re.compile(
    r"(?:Rp|IDR)?\s*([0-9OoIl|SＢB][0-9OoIl|SＢB.,\s]{2,})",
    re.IGNORECASE,
)

DATE_RE = re.compile(
    r"(\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4}"
    r"|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    re.IGNORECASE,
)

TIME_RE = re.compile(r"\b(\d{1,2}[:.]\d{2}(?::\d{2})?)\b")
LONG_ID_RE = re.compile(r"\b([0-9OoIl|SＢB]{10,})\b")


def enrich_finance_data(
    doc_type: str,
    data: dict[str, Any],
    blocks: list[Block],
) -> dict[str, Any]:
    """Fill missing receipt/payment-slip fields from nearby OCR blocks."""
    if doc_type not in REQUIRED_FIELDS:
        return {
            "data": data,
            "evidence": [],
            "required_fields": [],
            "missing_fields": [],
        }

    enriched = dict(data)
    evidence = []
    rows = _build_rows(blocks)

    if doc_type == "receipt":
        _fill(enriched, evidence, "total", _find_amount_near(rows, ["total", "totalpayment", "grandtotal"], True))
        _fill(enriched, evidence, "subtotal", _find_amount_near(rows, ["subtotal", "sub total"]))
        _fill(enriched, evidence, "tax", _find_amount_near(rows, ["tax", "ppn", "pajak"]))
        _fill(enriched, evidence, "amount_paid", _find_amount_near(rows, ["cash", "tunai", "amountpaid"]))
        _fill(enriched, evidence, "change", _find_amount_near(rows, ["change", "kembali"]))
        _fill(enriched, evidence, "transaction_id", _find_id_near(rows, ["transactionid", "transaksi", "trx", "orderid"]))
        _fill(enriched, evidence, "date", _find_date(blocks))
        _fill(enriched, evidence, "time", _find_time(blocks))
        _fill(enriched, evidence, "currency", "IDR" if _has_currency(blocks) else None)
        _fill(enriched, evidence, "payment_method", _find_payment_method(blocks))

    if doc_type == "payment_slip":
        _fill(enriched, evidence, "amount", _find_amount_near(rows, ["amount", "nominal", "jumlah", "totalpayment"], True))
        _fill(enriched, evidence, "reference_number", _find_id_near(rows, ["reference", "referensi", "transactionid", "trx"]))
        _fill(enriched, evidence, "transfer_date", _find_date(blocks))
        _fill(enriched, evidence, "transfer_time", _find_time(blocks))
        _fill(enriched, evidence, "currency", "IDR" if _has_currency(blocks) else None)
        _fill(enriched, evidence, "status", _find_status(blocks))

    required = REQUIRED_FIELDS[doc_type]
    missing = [field for field in required if _is_empty(enriched.get(field))]
    return {
        "data": enriched,
        "evidence": evidence,
        "required_fields": required,
        "missing_fields": missing,
    }


def _fill(data: dict[str, Any], evidence: list[dict[str, Any]], field: str, value: Any) -> None:
    if value is None or not _is_empty(data.get(field)):
        return
    data[field] = value
    evidence.append({"field": field, "value": value, "source": "layout_fallback"})


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == 0 or value == [] or value == {}


def _build_rows(blocks: list[Block]) -> list[list[Block]]:
    rows: list[list[Block]] = []
    useful_blocks = [block for block in blocks if not is_punctuation_noise(block.text)]
    sorted_blocks = sorted(useful_blocks, key=lambda block: (block.page, _center_y(block), block.bbox.get("x", 0)))

    for block in sorted_blocks:
        if not rows:
            rows.append([block])
            continue

        current = rows[-1]
        row_center = sum(_center_y(item) for item in current) / len(current)
        tolerance = max(16, max(item.bbox.get("height", 0) for item in current + [block]) * 0.75)
        if block.page == current[0].page and abs(_center_y(block) - row_center) <= tolerance:
            current.append(block)
        else:
            rows.append([block])

    for row in rows:
        row.sort(key=lambda block: block.bbox.get("x", 0))
    return rows


def _center_y(block: Block) -> float:
    return block.bbox.get("y", 0) + block.bbox.get("height", 0) / 2


def _norm_label(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _row_text(row: list[Block]) -> str:
    return " ".join(block.text for block in row)


def _find_amount_near(
    rows: list[list[Block]],
    labels: list[str],
    fallback_to_largest: bool = False,
) -> float | None:
    normalized_labels = [_norm_label(label) for label in labels]

    for index, row in enumerate(rows):
        row_label = _norm_label(_row_text(row))
        if not any(label in row_label for label in normalized_labels):
            continue

        candidates = row + (rows[index + 1] if index + 1 < len(rows) else [])
        for block in sorted(candidates, key=lambda item: item.bbox.get("x", 0), reverse=True):
            amount = _parse_amount(block.text)
            if amount is not None:
                return amount

    if fallback_to_largest:
        return _largest_amount([block for row in rows for block in row])
    return None


def _largest_amount(blocks: list[Block]) -> float | None:
    amounts = [amount for block in blocks if (amount := _parse_amount(block.text)) is not None]
    return max(amounts) if amounts else None


def _parse_amount(text: str) -> float | None:
    if not re.search(r"(Rp|IDR|\d[.,]\d{3})", text, re.IGNORECASE):
        return None

    match = AMOUNT_RE.search(text)
    if not match:
        return None

    value = _normalize_number(match.group(1))
    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def _normalize_number(text: str) -> str:
    value = text.translate(str.maketrans({
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "|": "1",
        "S": "5",
        "Ｂ": "8",
        "B": "8",
    }))
    value = re.sub(r"[^0-9,.]", "", value)
    if not value:
        return ""

    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "." in value:
        parts = value.split(".")
        value = "".join(parts) if len(parts[-1]) == 3 else value
    elif "," in value:
        parts = value.split(",")
        value = "".join(parts) if len(parts[-1]) == 3 else value.replace(",", ".")
    return value


def _find_id_near(rows: list[list[Block]], labels: list[str]) -> str | None:
    normalized_labels = [_norm_label(label) for label in labels]
    for index, row in enumerate(rows):
        row_label = _norm_label(_row_text(row))
        if not any(label in row_label for label in normalized_labels):
            continue

        candidates = row + (rows[index + 1] if index + 1 < len(rows) else [])
        for block in candidates:
            value = _extract_long_id(block.text)
            if value:
                return value

    ids = [_extract_long_id(block.text) for row in rows for block in row]
    return next((value for value in ids if value), None)


def _extract_long_id(text: str) -> str | None:
    match = LONG_ID_RE.search(_normalize_id_text(text))
    return match.group(1) if match else None


def _normalize_id_text(text: str) -> str:
    return text.translate(str.maketrans({
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "|": "1",
        "S": "5",
        "Ｂ": "8",
        "B": "8",
    }))


def _find_date(blocks: list[Block]) -> str | None:
    text = "\n".join(block.text for block in blocks)
    match = DATE_RE.search(text)
    return re.sub(r"\s+", "", match.group(1)) if match else None


def _find_time(blocks: list[Block]) -> str | None:
    text = "\n".join(block.text for block in blocks)
    match = TIME_RE.search(text)
    return match.group(1).replace(".", ":") if match else None


def _has_currency(blocks: list[Block]) -> bool:
    return any(re.search(r"\b(IDR|Rp|Rupiah)\b", block.text, re.IGNORECASE) for block in blocks)


def _find_payment_method(blocks: list[Block]) -> str | None:
    text = " ".join(block.text for block in blocks).lower()
    methods = {
        "DANA": ["dana balance", "dana"],
        "QRIS": ["qris"],
        "CASH": ["cash", "tunai"],
        "CARD": ["card", "debit", "credit", "kartu"],
    }
    for method, keywords in methods.items():
        if any(keyword in text for keyword in keywords):
            return method
    return None


def _find_status(blocks: list[Block]) -> str | None:
    text = " ".join(block.text for block in blocks).lower()
    if any(keyword in text for keyword in ["success", "berhasil", "completed"]):
        return "SUCCESS"
    if any(keyword in text for keyword in ["pending", "process"]):
        return "PENDING"
    if any(keyword in text for keyword in ["failed", "gagal"]):
        return "FAILED"
    return None
