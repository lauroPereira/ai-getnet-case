"""Helpers shared by the agents: language names, prompt loading and fixed policy texts."""

from __future__ import annotations

import re

from merchant_assistant.llm.prompts import Prompt, load_prompt
from merchant_assistant.orchestration.run import RunContext

LANGUAGE_NAME = {"pt": "Brazilian Portuguese", "en": "English"}

_PT_HINTS = re.compile(
    r"\b(?:minha|meu|não|nao|vendas?|quando|como|posso|preciso|maquininha|dinheiro|ontem|hoje|"
    r"qual|quais|está|esta|uma|para|com|que|de|da|do|quero|falar|em|na|no|entre|e|é|o|os|as|sobre|pelo|pela)\b",
    re.IGNORECASE,
)
_EN_HINTS = re.compile(
    r"\b(?:the|what|how|does|do|my|can|will|when|with|is|are|from|should|i|want|to|of|an|it|yesterday|today)\b",
    re.IGNORECASE,
)


def guess_language(text: str) -> str:
    """Heuristic used only when the Router model is unavailable (and by the scripted test model)."""
    pt, en = len(_PT_HINTS.findall(text)), len(_EN_HINTS.findall(text))
    if pt == en:
        return "pt" if re.search(r"[ãõçâêô]", text) else "en"
    return "pt" if pt > en else "en"


def prompt(ctx: RunContext, name: str) -> Prompt:
    return load_prompt(ctx.settings.prompts_dir, name)


POLICY = {
    "refused": {
        "pt": "Não posso ajudar com esse pedido. Posso ajudar com dúvidas sobre produtos Getnet, suas vendas, "
        "recebimentos, maquininha e transações.",
        "en": "I can't help with that request. I can help with questions about Getnet products, your sales, "
        "payouts, card machine and transactions.",
    },
    "account_not_found": {
        "pt": "Não localizei sua conta no ambiente de demonstração, então não consigo consultar dados do seu "
        "negócio. Confira se o identificador de usuário está correto ou peça para falar com um atendente. Enquanto "
        "isso, posso responder dúvidas gerais sobre os produtos Getnet.",
        "en": "I couldn't find your account in the demo environment, so I can't check your business data. "
        "Please check that your user ID is correct, or ask to talk to an agent. Meanwhile, I can answer general "
        "questions about Getnet products.",
    },
    "no_evidence": {
        "pt": "Não encontrei essa informação nas fontes oficiais da Getnet que consultei.",
        "en": "I couldn't find this information in the official Getnet sources I checked.",
    },
    "unavailable": {
        "pt": "Não consegui concluir a consulta agora. Tente novamente em alguns minutos ou peça para falar "
        "com um atendente.",
        "en": "I couldn't complete the check right now. Please try again in a few minutes or ask to talk to an agent.",
    },
    "clarify": {
        "pt": "Pode me contar um pouco mais sobre o que você precisa?",
        "en": "Could you tell me a bit more about what you need?",
    },
}


def policy(key: str, language: str) -> str:
    return POLICY[key]["pt" if language == "pt" else "en"]
