"""Output guard: amounts, dates and percentages in the final answer must appear in the evidence of this request.

Evidence = tool results, retrieved passages, web answer, policy texts and the merchant's own message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

_MONTHS = {
    **{
        m: i + 1
        for i, m in enumerate(
            [
                "january",
                "february",
                "march",
                "april",
                "may",
                "june",
                "july",
                "august",
                "september",
                "october",
                "november",
                "december",
            ]
        )
    },
    **{
        m: i + 1
        for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])
    },
    **{
        m: i + 1
        for i, m in enumerate(
            [
                "janeiro",
                "fevereiro",
                "março",
                "abril",
                "maio",
                "junho",
                "julho",
                "agosto",
                "setembro",
                "outubro",
                "novembro",
                "dezembro",
            ]
        )
    },
    "marco": 3,
    "sept": 9,
}
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))

_AMOUNT = re.compile(r"(?:R\$|BRL)\s?(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)", re.IGNORECASE)
_PERCENT = re.compile(r"(\d+(?:[.,]\d+)?)\s?%")
_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_SLASH = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?![\d/])")
_EN = re.compile(rf"\b({_MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?", re.IGNORECASE)
_EN_DMY = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH_RE})(?:,?\s+(\d{{4}}))?", re.IGNORECASE)
_PT = re.compile(rf"\b(\d{{1,2}})\s+de\s+({_MONTH_RE})(?:\s+de\s+(\d{{4}}))?", re.IGNORECASE)


def _cents(raw: str) -> int:
    m = re.search(r"[.,](\d{1,2})$", raw)
    if m and not re.search(r"[.,]\d{3}$", raw):
        integer = re.sub(r"\D", "", raw[: m.start()])
        return int(integer or 0) * 100 + int(m.group(1).ljust(2, "0"))
    return int(re.sub(r"\D", "", raw)) * 100


def amounts(text: str) -> set[int]:
    return {_cents(m.group(1)) for m in _AMOUNT.finditer(text)}


def percents(text: str) -> set[float]:
    return {round(float(m.group(1).replace(",", ".")), 2) for m in _PERCENT.finditer(text)}


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def date_candidates(text: str, ref_year: int) -> list[set[date]]:
    """Each date mention becomes a set of possible dates (numeric slashes can be d/m or m/d)."""
    found: list[set[date]] = []

    def year(y: str | None) -> int:
        if not y:
            return ref_year
        return int(y) + 2000 if len(y) == 2 else int(y)

    for m in _ISO.finditer(text):
        d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            found.append({d})
    for m in _SLASH.finditer(text):
        a, b, y = int(m.group(1)), int(m.group(2)), year(m.group(3))
        if (a, b) == (24, 7) and not m.group(3):  # "24/7" availability, not a date
            continue
        options = {x for x in (_safe_date(y, b, a), _safe_date(y, a, b)) if x}
        if options:
            found.append(options)
    for pattern, order in ((_EN, "md"), (_EN_DMY, "dm"), (_PT, "dm")):
        for m in pattern.finditer(text):
            if order == "md":
                month, day = _MONTHS[m.group(1).lower()], int(m.group(2))
            else:
                day, month = int(m.group(1)), _MONTHS[m.group(2).lower()]
            d = _safe_date(year(m.group(3)), month, day)
            if d:
                found.append({d})
    return found


def evidence_dates(texts: list[str], ref_year: int) -> set[date]:
    out: set[date] = set()
    for t in texts:
        for options in date_candidates(t, ref_year):
            out |= options
    return out


@dataclass(frozen=True)
class Violation:
    kind: str
    value: str


def unsupported(answer: str, evidence: list[str], ref: date) -> list[Violation]:
    ev_amounts = set().union(*(amounts(t) for t in evidence)) if evidence else set()
    ev_percents = set().union(*(percents(t) for t in evidence)) if evidence else set()
    ev_dates = evidence_dates(evidence, ref.year)
    violations = [Violation("amount", str(a)) for a in amounts(answer) if a not in ev_amounts]
    violations += [Violation("percent", str(p)) for p in percents(answer) if p not in ev_percents]
    for options in date_candidates(answer, ref.year):
        if not options & ev_dates:
            violations.append(Violation("date", min(options).isoformat()))
    return violations


def drop_unsupported_sentences(answer: str, evidence: list[str], ref: date) -> str:
    sentences = re.split(r"(?<=[.!?])\s+|\n+", answer)
    kept = [s for s in sentences if s.strip() and not unsupported(s, evidence, ref)]
    return " ".join(kept).strip()
