"""Mede tokens, custo equivalente e tempo dos subagentes do ai-getnet-case, por passagem e por tarefa.

Adaptado do ampeli-sdd em 2026-11-03. Tarefas são reconhecidas como "tarefa 63", "T63" ou "63-assunto"
na descrição do despacho.

Uso:
  python tools/scripts/medir-agentes.py                      # todas as sessões do projeto
  python tools/scripts/medir-agentes.py --desde 2026-11-01   # só passagens iniciadas a partir da data (UTC)
  python tools/scripts/medir-agentes.py --csv saida.csv      # também grava as passagens em CSV

Leitura dos números em docs/wiki/agents/README.md (modelo e esforço por papel).
Lê só os registros locais do Claude Code (~/.claude/projects/<projeto>/<sessão>/subagents). Não chama API nenhuma.
"""
import argparse
import csv
import glob
import json
import os
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime

# Preço de API por milhão de tokens (US$), da skill claude-api em 02/11/2026.
# Escrita de cache: 1,25x a entrada (5 min) e 2x (1 h). Leitura de cache: preço próprio.
PRECOS = {
    "claude-sonnet-5-5": {"entrada": 2.00, "leitura_cache": 0.20, "saida": 10.00},
    "claude-opus-5-5": {"entrada": 4.00, "leitura_cache": 0.20, "saida": 20.00},
    "claude-haiku-5-5": {"entrada": 0.10, "leitura_cache": 0.01, "saida": 0.50},
}
PAUSA_MAX_S = 15 * 60  # intervalos maiores contam como espera (agente parado aguardando retomada), não como trabalho
TAREFA = re.compile(r"(?:\btarefas?\s+|\bT)(\d{2,3})\b|\b(\d{2,3})-[a-z]", re.IGNORECASE)

PROJETO = os.path.expanduser(r"~/.claude/projects/C--workspace-ai-getnet-case")


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def custo(modelo, u):
    p = PRECOS.get(modelo)
    if not p:
        return None
    cc = u.get("cache_creation") or {}
    w5 = cc.get("ephemeral_5m_input_tokens")
    w1 = cc.get("ephemeral_1h_input_tokens")
    if w5 is None and w1 is None:
        w5, w1 = u.get("cache_creation_input_tokens", 0), 0
    tot = (
        u.get("input_tokens", 0) * p["entrada"]
        + (w5 or 0) * p["entrada"] * 1.25
        + (w1 or 0) * p["entrada"] * 2.0
        + u.get("cache_read_input_tokens", 0) * p["leitura_cache"]
        + u.get("output_tokens", 0) * p["saida"]
    )
    return tot / 1_000_000


def _tarefas(texto):
    return sorted({"T" + (a or b) for a, b in TAREFA.findall(texto)})


def ler_passagem(jsonl):
    meta_path = jsonl[: -len(".jsonl")] + ".meta.json"
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    mensagens = {}  # id da mensagem -> (modelo, usage); a mesma resposta aparece em várias linhas
    instantes = []
    primeiro_prompt = ""
    with open(jsonl, encoding="utf-8") as f:
        for linha in f:
            try:
                e = json.loads(linha)
            except json.JSONDecodeError:
                continue
            if e.get("timestamp"):
                instantes.append(ts(e["timestamp"]))
            m = e.get("message") or {}
            if not primeiro_prompt and e.get("type") == "user" and isinstance(m.get("content"), str):
                primeiro_prompt = m["content"]
            if m.get("role") == "assistant" and m.get("id") and m.get("usage"):
                mensagens[m["id"]] = (m.get("model", "?"), m["usage"])
    if not instantes or not mensagens:
        return None
    instantes.sort()
    ativo = sum(
        min((b - a).total_seconds(), PAUSA_MAX_S) if (b - a).total_seconds() <= PAUSA_MAX_S else 0
        for a, b in zip(instantes, instantes[1:], strict=False)
    )
    modelos = defaultdict(int)
    soma = defaultdict(int)
    usd = 0.0
    sem_preco = False
    for modelo, u in mensagens.values():
        modelos[modelo] += 1
        for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"):
            soma[k] += u.get(k, 0) or 0
        c = custo(modelo, u)
        if c is None:
            sem_preco = True
        else:
            usd += c
    descricao = meta.get("description", "")
    tarefas = _tarefas(descricao) or _tarefas(primeiro_prompt[:600])
    return {
        "agente": os.path.basename(jsonl)[len("agent-") : -len(".jsonl")],
        "papel": meta.get("agentType", "?"),
        "descricao": descricao,
        "tarefas": tarefas,
        "modelo": "+".join(sorted(modelos)),
        "inicio": instantes[0],
        "fim": instantes[-1],
        "min_ativos": round(ativo / 60, 1),
        "chamadas": len(mensagens),
        "entrada": soma["input_tokens"],
        "escrita_cache": soma["cache_creation_input_tokens"],
        "leitura_cache": soma["cache_read_input_tokens"],
        "saida": soma["output_tokens"],
        "usd": round(usd, 2),
        "sem_preco": sem_preco,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", help="AAAA-MM-DD (UTC)")
    ap.add_argument("--csv")
    a = ap.parse_args()
    desde = datetime.fromisoformat(a.desde).replace(tzinfo=UTC) if a.desde else None

    passagens = []
    for j in glob.glob(os.path.join(PROJETO, "*", "subagents", "agent-*.jsonl")):
        p = ler_passagem(j)
        if p and (not desde or p["inicio"] >= desde) and p["papel"] in ("developer", "reviewer", "qa"):
            passagens.append(p)
    passagens.sort(key=lambda p: p["inicio"])

    print("## Passagens\n")
    print("| Início (UTC) | Papel | Tarefas | Modelo | Min. ativos | Chamadas | Tokens de saída | US$ equiv. |")
    print("| --- | --- | --- | --- | ---: | ---: | ---: | ---: |")
    for p in passagens:
        aviso = " (modelo sem preço)" if p["sem_preco"] else ""
        print(
            f"| {p['inicio']:%d/%m %H:%M} | {p['papel']} | {', '.join(p['tarefas']) or '—'} | {p['modelo']} | "
            f"{p['min_ativos']} | {p['chamadas']} | {p['saida']:,} | {p['usd']:.2f}{aviso} |"
        )

    # Por tarefa: passagem com várias tarefas divide custo e tempo em partes iguais (marcado como rateado).
    por = defaultdict(lambda: {"usd": 0.0, "min": 0.0, "dev": 0, "rev": 0, "qa": 0, "rateado": False, "modelos": set()})
    for p in passagens:
        n = len(p["tarefas"]) or 1
        for t in p["tarefas"] or ["(sem tarefa)"]:
            r = por[t]
            r["usd"] += p["usd"] / n
            r["min"] += p["min_ativos"] / n
            r[{"developer": "dev", "reviewer": "rev", "qa": "qa"}[p["papel"]]] += 1
            r["rateado"] |= n > 1
            r["modelos"].add(p["modelo"])
    print("\n## Por tarefa\n")
    print("| Tarefa | Modelos | Passagens dev / rev / qa | Min. ativos | US$ equiv. |")
    print("| --- | --- | --- | ---: | ---: |")
    for t in sorted(por):
        r = por[t]
        nota = " (rateado)" if r["rateado"] else ""
        modelos = ", ".join(sorted(r["modelos"]))
        passagens_papel = f"{r['dev']} / {r['rev']} / {r['qa']}"
        print(f"| {t} | {modelos} | {passagens_papel} | {r['min']:.0f} | {r['usd']:.2f}{nota} |")
    total = sum(p["usd"] for p in passagens)
    minutos = sum(p["min_ativos"] for p in passagens)
    print(f"\nTotal: {len(passagens)} passagens, US$ {total:.2f} equivalentes de API, {minutos:.0f} min ativos.")

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[k for k in passagens[0] if k != "sem_preco"] if passagens else [])
            w.writeheader()
            for p in passagens:
                linha = {k: v for k, v in p.items() if k != "sem_preco"}
                linha["tarefas"] = " ".join(p["tarefas"])
                w.writerow(linha)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
