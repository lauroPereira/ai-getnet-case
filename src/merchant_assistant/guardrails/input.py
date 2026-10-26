"""Deterministic input guard: masks sensitive data and blocks clear prompt-injection attempts before any model call."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class GuardResult:
    masked: str
    findings: list[str] = field(default_factory=list)
    blocked: bool = False
    category: str | None = None


def _luhn(digits: str) -> bool:
    total, parity = 0, len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_CPF = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)|(?<![\d.])\d{11}(?![\d.])")
_CNPJ = re.compile(r"(?<!\d)\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_SECRET = re.compile(
    r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}\b|\bBearer\s+[A-Za-z0-9._-]{16,}|"
    r"\b(?:senha|password|passwd|token|cvv|cvc)\s*[:=]?\s*\S+",
    re.IGNORECASE,
)
_INJECTION = re.compile(
    r"ignore (?:all |any |the )?(?:previous|prior|above|earlier) (?:instructions|rules|prompts?)|"
    r"disregard (?:all |the )?(?:previous|prior|system) (?:instructions|rules)|"
    r"(?:reveal|show|print|repeat) (?:me )?(?:your|the) (?:system )?(?:prompt|instructions)|"
    r"\bsystem prompt\b|\bdeveloper mode\b|\bjailbreak\b|\bDAN mode\b|"
    r"ignor[ea] (?:todas )?as instruç(?:ões|oes)(?: anteriores)?|esqueç[ae] (?:todas )?as (?:suas )?instruç|"
    r"(?:revele|mostre|repita) (?:o )?(?:seu |teu )?(?:prompt|instruç)",
    re.IGNORECASE,
)


def mask_sensitive(text: str) -> tuple[str, list[str]]:
    findings: list[str] = []

    def card(match: re.Match) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if 13 <= len(digits) <= 19 and _luhn(digits):
            findings.append("card_number")
            return "[card number removed]"
        return match.group(0)

    masked = _CARD.sub(card, text)
    for pattern, label, token in (
        (_SECRET, "credential", "[credential removed]"),
        (_CNPJ, "cnpj", "[CNPJ removed]"),
        (_CPF, "cpf", "[CPF removed]"),
        (_EMAIL, "email", "[e-mail removed]"),
    ):
        masked, n = pattern.subn(token, masked)
        findings += [label] * n
    return masked, findings


def check_input(text: str) -> GuardResult:
    masked, findings = mask_sensitive(text)
    if _INJECTION.search(text):
        return GuardResult(masked, findings + ["prompt_injection"], blocked=True, category="injection")
    return GuardResult(masked, findings)
