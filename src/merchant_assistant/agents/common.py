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


def history_coverage_instruction(incomplete: bool) -> str:
    if not incomplete:
        return ""
    return (
        "\n\nConversation history coverage: Some older messages are omitted from the context shown below. Do not imply "
        "that you have complete recall. Continue with the information available, and if a missing detail is necessary, "
        "tell the merchant and ask them to repeat it."
    )


def format_history(
    history: list[dict],
    limit: int | None = None,
    *,
    summary: str | None = None,
    facts: list[dict] | None = None,
    uncovered: list[dict] | None = None,
    incomplete: bool = False,
) -> str:
    """Conversation turns as a data block (oldest first). In a long conversation (task 92) the block starts with the
    summary of what left the short history and, for the agents that write the reply, the unsummarized messages outside
    that window and the facts recorded before the turns they read. If older unsummarized messages were omitted to keep
    the context bounded, the notice tells the agent to ask for missing details instead of claiming complete recall."""
    turns = history[-limit:] if limit else history
    lines = [f"- {t['role']}: {t['text']}" for t in turns] or ["- (new conversation)"]
    uncovered_only = list(uncovered or [])
    for turn in turns:
        if turn in uncovered_only:
            uncovered_only.remove(turn)
    if not summary and not facts and not uncovered_only and not incomplete:
        return "\n".join(lines)
    parts = []
    if incomplete:
        parts.append("History coverage note: Some older conversation messages are not shown here.")
    if summary:
        parts.append(f"Earlier in this conversation (summary):\n<<<\n{summary}\n>>>")
    if facts:
        recorded = [f"- {f['kind']}: {f['value']} (from {f['source_tool']})" for f in facts]
        parts.append("Facts recorded earlier in this conversation (tool results and cases):\n" + "\n".join(recorded))
    if uncovered_only:
        pending = "\n".join(f"- {t['role']}: {t['text']}" for t in uncovered_only)
        parts.append("Older messages not yet included in the summary (data):\n<<<\n" + pending + "\n>>>")
    parts.append("Recent turns:\n" + "\n".join(lines))
    return "\n\n".join(parts)


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
    "unconfirmed": {
        "pt": "Não consegui confirmar uma parte do que você perguntou, então não posso afirmar essa parte.",
        "en": "I could not confirm part of what you asked, so I can't state that part.",
    },
    "unavailable": {
        "pt": "Não consegui concluir a consulta agora. Tente novamente em alguns minutos ou peça para falar "
        "com um atendente.",
        "en": "I couldn't complete the check right now. Please try again in a few minutes or ask to talk to an agent.",
    },
    "ack": {
        "pt": "Combinado. Se precisar de mais alguma coisa, é só me chamar.",
        "en": "Got it. If you need anything else, just let me know.",
    },
    "ack_resolved": {
        "pt": "Que bom que deu certo! Se precisar de mais alguma coisa, é só me chamar.",
        "en": "Great, glad it worked! If you need anything else, just let me know.",
    },
    "clarify": {
        "pt": "Pode me contar um pouco mais sobre o que você precisa?",
        "en": "Could you tell me a bit more about what you need?",
    },
}


def policy(key: str, language: str) -> str:
    return POLICY[key]["pt" if language == "pt" else "en"]
