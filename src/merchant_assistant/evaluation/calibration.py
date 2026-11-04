"""Human calibration of the judge (spec v0.8.0 D10 and D19, RF-91).

`eval-calibrate --sample` draws answers from a campaign report and writes a CSV the owner fills in with the rubric of
`judge.v3`, without seeing the judge's scores. `eval-calibrate --import` validates the filled file line by line, links
each rating to the judgement of the same `request_id` in `run_evaluations`, stores it in `calibrations` and measures,
per criterion, how far the human and the judge agree: exact agreement, agreement within one point and the quadratic
weighted kappa. With a sample this small the numbers are an indication, not proof (D19), so every one carries an
interval and the report states the caveat.

Nothing here calls a model. The CSV holds masked synthetic data only."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import random
import re
import sqlite3
import statistics
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from merchant_assistant.evaluation import evidence
from merchant_assistant.evaluation.judge import CAMPAIGN_PRINCIPAL, CRITERIA, RUBRIC, RUBRIC_VERSION
from merchant_assistant.guardrails.input import mask_sensitive

DEFAULT_SAMPLE = 24  # RF-91: at least 24 answers
DEFAULT_SEED = 20261104
EVIDENCE_SUMMARY_CHARS = 2000  # the judge reads up to 6 000; the human gets a summary
SCALE = (1, 2, 3, 4, 5)
VERDICT = "unsupported_claim"
HUMAN_COLUMNS = (*CRITERIA, VERDICT, "note")
# What the owner sees. Nothing of the judge's output is in this list, and the writer reads nothing else.
COLUMNS = (
    "sample_id",
    "route",
    "split",
    "status",
    "message",
    "answer",
    "sources",
    "evidence",
    *HUMAN_COLUMNS,
    "request_id",
    "case_id",
)
REQUIRED = ("sample_id", "request_id", *CRITERIA, VERDICT)
RATING_COLUMNS = (*CRITERIA, VERDICT)
DELIMITERS = (";", ",", "\t")
BOOTSTRAP_RESAMPLES = 2000
MIN_VALID_RESAMPLES = 100
Z95 = 1.959964
BIG_GAP = 2  # a difference of this many points or more is listed in the report
MAX_REPORTED_ERRORS = 25

INSTRUCTIONS = (
    "Calibração humana do juiz (v0.8.0). Avalie cada resposta com a mesma rubrica do juiz; as notas dele não estão "
    "neste arquivo.",
    "Por linha, preencha groundedness, factual_correctness, relevance e usefulness com um inteiro de 1 (ruim) a 5 "
    "(excelente) e unsupported_claim com sim ou nao. A coluna note é opcional. Linha com os cinco campos vazios é "
    "ignorada; linha preenchida pela metade é recusada na importação.",
    "groundedness (fundamentação): todo fato, valor, data, status ou passo da resposta se apoia na evidência ou na "
    "mensagem do lojista. 5 = tudo apoiado; 1 = quase tudo inventado.",
    "factual_correctness (correção factual): o que a resposta afirma concorda com a evidência e não se contradiz. "
    "Penalize contradição, valor, data ou código errado e conclusão que a evidência não permite.",
    "relevance (relevância): a resposta trata do que o lojista perguntou, ou recusa, pede esclarecimento ou "
    "encaminha quando esse é o desfecho certo para o status.",
    "usefulness (utilidade): o lojista consegue agir com a resposta; ela é clara, objetiva, educada, no idioma da "
    "mensagem e diz as lacunas em vez de escondê-las.",
    "unsupported_claim (afirmação sem suporte): sim só quando a resposta afirma fato, valor, data, status ou promessa "
    "que a evidência não sustenta ou contradiz. Recusar, pedir esclarecimento ou dizer que algo não foi confirmado "
    "não conta.",
    "Julgue só a resposta contra a evidência mostrada, sem conhecimento externo. Resultado de ferramenta "
    "(tool_result) vem da conta sintética do lojista e vale mesmo que ele não o tenha citado. Dados sensíveis estão "
    "mascarados.",
    "Se a evidência diz que a resposta veio de busca web sem o texto gravado, só há os títulos das fontes: não "
    "baixe a fundamentação só porque falta um trecho; marque afirmação sem suporte se a resposta contradiz as "
    "fontes, se contradiz a si mesma ou afirma dado da conta do lojista que nenhuma ferramenta mostra.",
    "A coluna evidence é um resumo (o juiz recebeu até 6000 caracteres; [...cut] marca um corte). Salve como CSV "
    "UTF-8, com o mesmo separador, e não apague as colunas sample_id e request_id nem a linha 'amostra:'.",
)
NOTES_PT = {
    evidence.WEB_NOTE: "A resposta vem de busca web e o texto da busca não foi gravado: julgue só a coerência com as "
    "fontes listadas e diga isso na nota."
}
CRITERIA_LABELS = {
    "groundedness": "fundamentação",
    "factual_correctness": "correção factual",
    "relevance": "relevância",
    "usefulness": "utilidade",
}


class CalibrationError(Exception):
    """The calibration cannot go on. `messages` are one problem per line, each saying where it is."""

    def __init__(self, messages: list[str] | str) -> None:
        self.messages = [messages] if isinstance(messages, str) else list(messages)
        super().__init__("\n".join(self.messages))


# --- the sample -----------------------------------------------------------------------------------------------------


def load_source(path: Path) -> tuple[list[dict], str]:
    """The answers of the first execution of a campaign report that were judged and can be shown with their evidence.
    Returns them with the report's name (the campaign name unless one is given)."""
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        cases = report["cases"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CalibrationError(f"não consegui ler o relatório {path}: {type(exc).__name__}") from None
    rows = [
        row
        for row in cases
        if row.get("repetition", 1) == 1
        and "judge_input" in row
        and (row.get("judge") or {}).get("state") == "completed"
    ]
    if not rows:
        raise CalibrationError(
            f"o relatório {path.name} não tem respostas julgadas com a evidência gravada: rode a campanha com --judge "
            "(ou --repeat) antes de sortear a amostra."
        )
    return rows, path.stem


def _rank(seed: int, label: str, key: str) -> str:
    return hashlib.sha256(f"{seed}|{label}|{key}".encode()).hexdigest()


def draw_sample(rows: list[dict], size: int, seed: int) -> list[dict]:
    """A sample balanced over the strata (route, split): one answer from each stratum in turn, in an order that only
    the seed decides, until `size` answers are drawn or the population is used up. Every stratum shows up before any
    stratum shows up twice, so a rare route is represented (a proportional draw of 24 would skip it). The order of the
    rows in the report does not matter, and the draw does not depend on the random generator of the Python version:
    the same report and the same seed give the same sample anywhere. The sample is returned in a seeded order that
    does not group the strata."""
    if size < 1:
        raise CalibrationError("o tamanho da amostra precisa ser de pelo menos 1.")
    strata: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        strata.setdefault((row["route"], row["split"]), []).append(row)
    members = {key: sorted(group, key=lambda r: _rank(seed, "case", r["request_id"])) for key, group in strata.items()}
    order = sorted(members, key=lambda key: _rank(seed, "stratum", "|".join(key)))
    chosen: list[dict] = []
    depth = 0
    while len(chosen) < size and any(depth < len(group) for group in members.values()):
        for key in order:
            if len(chosen) < size and depth < len(members[key]):
                chosen.append(members[key][depth])
        depth += 1
    return sorted(chosen, key=lambda r: _rank(seed, "order", r["request_id"]))


def _safe(text: str) -> str:
    """Masks sensitive values once more and keeps a spreadsheet from reading the cell as a formula."""
    masked = mask_sensitive(text)[0]
    return " " + masked if masked[:1] in "=+-@\t\r" else masked


def summarize_evidence(judge_input: dict, limit: int = EVIDENCE_SUMMARY_CHARS) -> str:
    """The evidence the judge read, shortened to `limit` characters (long items share the room, as for the judge)."""
    items = [item | {"text": " ".join(item["text"].split())} for item in judge_input.get("evidence", [])]
    kept, _ = evidence.fit_items(items, limit)
    lines = [f"[{item['kind']}] {item['label']}: {item['text']}" for item in kept]
    lines += [f"Nota: {NOTES_PT.get(note, note)}" for note in judge_input.get("evidence_notes", [])]
    truncation = judge_input.get("evidence_truncation") or {}
    if truncation.get("truncated"):
        lines.append(f"(O juiz recebeu a evidência já cortada em {truncation.get('limit_chars')} caracteres.)")
    return "\n".join(lines) or "(sem evidência: nenhuma ferramenta nem trecho foi usado)"


def sample_rows(sample: list[dict]) -> list[dict]:
    """The CSV rows of a sample. Only the question, the reply, the outcome labels and the evidence the judge was given
    are read from the report; the judge's own record (`judge`, `judge_runs`) is never touched."""
    rows = []
    for number, row in enumerate(sample, start=1):
        given = row["judge_input"]
        rows.append(
            {
                "sample_id": f"S{number:02d}",
                "route": row["route"],
                "split": row["split"],
                "status": given["status"],
                "message": _safe(given["merchant_message"]),
                "answer": _safe(given["reply"]),
                "sources": _safe("; ".join(given.get("sources", []))),
                "evidence": _safe(summarize_evidence(given)),
                **dict.fromkeys(HUMAN_COLUMNS, ""),
                "request_id": row["request_id"],
                "case_id": row["id"],
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict], meta: dict, *, delimiter: str = ";") -> None:
    """UTF-8 with a BOM (a spreadsheet then reads the accents), the instructions as `#` lines and the sample line."""
    if delimiter not in DELIMITERS:
        raise CalibrationError(f"separador inválido: {delimiter!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = (
        f"amostra: campanha={meta['campaign']}; semente={meta['seed']}; origem={meta['source']}; "
        f"sorteadas={len(rows)}; pedidas={meta['requested']}; elegiveis={meta['eligible']}; "
        f"rubrica={RUBRIC}.v{RUBRIC_VERSION}"
    )
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=delimiter, lineterminator="\r\n")
        for line in (*INSTRUCTIONS, stamp):
            writer.writerow([f"# {line}"])
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow([row[column] for column in COLUMNS])


# --- reading the filled file ----------------------------------------------------------------------------------------


@dataclass
class Rating:
    sample_id: str
    request_id: str
    case_id: str
    route: str
    split: str
    scores: dict[str, int]
    unsupported_claim: bool
    note: str
    line: int


@dataclass
class Filled:
    meta: dict[str, str]
    ratings: list[Rating]
    skipped: list[str]  # sample ids with no rating at all


_HEADER = re.compile(r'^"?sample_id"?([;,\t])')
_META = re.compile(r"(\w+)=([^;]*)")
# The sample line is in Portuguese for the owner; the code reads it under these names.
META_KEYS = {
    "campanha": "campaign",
    "semente": "seed",
    "origem": "source",
    "sorteadas": "drawn",
    "pedidas": "requested",
    "elegiveis": "eligible",
    "rubrica": "rubric",
}
_YES = {"sim", "s", "true", "verdadeiro", "yes", "y", "1"}
_NO = {"nao", "n", "false", "falso", "no", "0"}


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().strip().casefold()


def read_filled(text: str) -> Filled:
    """Parses and validates the filled CSV. Every problem is collected with its line, so one pass shows them all."""
    lines = text.lstrip("﻿").splitlines()
    found = next((_HEADER.match(line) for line in lines if _HEADER.match(line)), None)
    if found is None:
        raise CalibrationError(
            "não encontrei o cabeçalho com a coluna sample_id: use o arquivo gerado por eval-calibrate --sample."
        )
    reader = csv.reader(io.StringIO(text.lstrip("﻿"), newline=""), delimiter=found.group(1))
    meta: dict[str, str] = {}
    header: list[str] | None = None
    errors: list[str] = []
    ratings: list[Rating] = []
    skipped: list[str] = []
    seen: dict[str, int] = {}
    last = 0
    for cells in reader:
        start, last = last + 1, reader.line_num
        cells = [cell.strip() for cell in cells]
        if not any(cells):
            continue
        if cells[0].startswith("#"):
            if cells[0].lstrip("# ").startswith("amostra:"):
                meta |= {META_KEYS[k]: v.strip() for k, v in _META.findall(cells[0]) if k in META_KEYS}
            continue
        if header is None:
            header = [_plain(cell) for cell in cells]
            missing = [column for column in REQUIRED if column not in header]
            if missing:
                raise CalibrationError(f"linha {start}: faltam as colunas {', '.join(missing)} no cabeçalho.")
            continue
        values = dict(zip(header, cells, strict=False))
        if any(cells[len(header) :]):
            errors.append(
                f"linha {start}: {len(cells)} colunas para um cabeçalho de {len(header)} (o texto de alguma coluna "
                "tem o separador sem aspas?)."
            )
            continue
        _rate_row(values, start, ratings, skipped, errors, seen)
    if header is None:
        raise CalibrationError("não encontrei o cabeçalho com a coluna sample_id: use o arquivo gerado por --sample.")
    if errors:
        raise CalibrationError(errors)
    return Filled(meta, ratings, skipped)


def _parse_rating(values: dict[str, str]) -> tuple[dict[str, int], bool, list[str]]:
    """The four scores and the verdict of one row, and what is wrong with them."""
    scores: dict[str, int] = {}
    problems = []
    for criterion in CRITERIA:
        raw = values.get(criterion, "")
        if not raw:
            problems.append(f"{criterion} está vazio")
        elif raw in {str(point) for point in SCALE}:
            scores[criterion] = int(raw)
        else:
            problems.append(f"{criterion} precisa ser um inteiro de 1 a 5, recebi {raw!r}")
    raw, claim = values.get(VERDICT, ""), False
    if not raw:
        problems.append(f"{VERDICT} está vazio")
    elif _plain(raw) in _YES | _NO:
        claim = _plain(raw) in _YES
    else:
        problems.append(f"{VERDICT} precisa ser sim ou nao, recebi {raw!r}")
    return scores, claim, problems


def _rate_row(
    values: dict[str, str], line: int, ratings: list[Rating], skipped: list[str], errors: list[str], seen: dict
) -> None:
    """One data row: skipped when no rating was filled in, an error line (one per row, all its problems) when the row
    is wrong or half filled, a `Rating` otherwise."""
    sample_id = values.get("sample_id", "")
    problems = []
    if not sample_id:
        problems.append("sample_id vazio")
    elif sample_id in seen:
        problems.append(f"sample_id repetido (já aparece na linha {seen[sample_id]})")
    else:
        seen[sample_id] = line
    if not values.get("request_id"):
        problems.append("request_id vazio (não apague essa coluna)")
    blank = not any(values.get(column) for column in RATING_COLUMNS)
    scores, claim = {}, False
    if not blank:
        scores, claim, rating_problems = _parse_rating(values)
        problems += rating_problems
    if problems:
        hint = (
            " Preencha os cinco campos ou deixe todos vazios para pular a linha."
            if any("está vazio" in problem for problem in problems)
            else ""
        )
        errors.append(f"linha {line} ({sample_id or 'sem sample_id'}): {'; '.join(problems)}.{hint}")
    elif blank:
        skipped.append(sample_id)
    else:
        ratings.append(
            Rating(
                sample_id,
                values["request_id"],
                values.get("case_id", ""),
                values.get("route", ""),
                values.get("split", ""),
                scores,
                claim,
                values.get("note", ""),
                line,
            )
        )


# --- the judgement each rating is compared with, and the table `calibrations` ---------------------------------------


def judgement_for(conn: sqlite3.Connection, request_id: str) -> dict | None:
    """The first judgement (repetition 1) that the campaign wrote for this request, with its scores and verdict."""
    row = conn.execute(
        "SELECT evaluation_id, rubric_version, evaluator, scores, unsupported_claim FROM run_evaluations "
        "WHERE request_id=? AND principal_id=? AND rubric=? AND state='completed' AND repetition=1 "
        "AND scores IS NOT NULL ORDER BY created_at, evaluation_id LIMIT 1",
        (request_id, CAMPAIGN_PRINCIPAL, RUBRIC),
    ).fetchone()
    if row is None:
        return None
    evaluator = json.loads(row["evaluator"])
    return {
        "evaluation_id": row["evaluation_id"],
        "rubric_version": row["rubric_version"],
        "judge": f"{evaluator.get('provider')}/{evaluator.get('model')}",
        "scores": json.loads(row["scores"]),
        "unsupported_claim": bool(row["unsupported_claim"]),
    }


@dataclass
class Pair:
    rating: Rating
    judgement: dict


def link(conn: sqlite3.Connection, filled: Filled) -> list[Pair]:
    pairs, errors = [], []
    for rating in filled.ratings:
        judgement = judgement_for(conn, rating.request_id)
        if judgement is None:
            errors.append(
                f"linha {rating.line} ({rating.sample_id}): não há julgamento da requisição {rating.request_id} em "
                "run_evaluations deste banco. Importe no banco em que a campanha gravou os julgamentos."
            )
        else:
            pairs.append(Pair(rating, judgement))
    if errors:
        raise CalibrationError(errors)
    return pairs


def store(conn: sqlite3.Connection, campaign: str, rater: str, pairs: list[Pair]) -> dict[str, int]:
    """Writes the ratings in one transaction. Importing the same file again (a corrected rating) updates the rows of
    the same campaign, sample and rater instead of adding new ones."""
    created = updated = 0
    now = datetime.now(UTC).isoformat(timespec="seconds")
    conn.execute("BEGIN")
    try:
        for pair in pairs:
            rating, judgement = pair.rating, pair.judgement
            exists = conn.execute(
                "SELECT 1 FROM calibrations WHERE campaign=? AND sample_id=? AND rater=?",
                (campaign, rating.sample_id, rater),
            ).fetchone()
            conn.execute(
                "INSERT INTO calibrations (calibration_id,campaign,sample_id,case_id,request_id,evaluation_id,route,"
                "split,rater,rubric_version,scores,unsupported_claim,note,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(campaign, sample_id, rater) DO UPDATE SET case_id=excluded.case_id, "
                "request_id=excluded.request_id, evaluation_id=excluded.evaluation_id, route=excluded.route, "
                "split=excluded.split, rubric_version=excluded.rubric_version, scores=excluded.scores, "
                "unsupported_claim=excluded.unsupported_claim, note=excluded.note, created_at=excluded.created_at",
                (
                    f"cal_{uuid.uuid4().hex[:20]}",
                    campaign,
                    rating.sample_id,
                    rating.case_id,
                    rating.request_id,
                    judgement["evaluation_id"],
                    rating.route or None,
                    rating.split or None,
                    rater,
                    judgement["rubric_version"],
                    json.dumps(rating.scores, sort_keys=True),
                    int(rating.unsupported_claim),
                    rating.note or None,
                    now,
                ),
            )
            updated += exists is not None
            created += exists is None
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {"created": created, "updated": updated}


# --- agreement ------------------------------------------------------------------------------------------------------


def exact_agreement(human: list[int], judge: list[int]) -> float | None:
    return sum(a == b for a, b in zip(human, judge, strict=True)) / len(human) if human else None


def within_one(human: list[int], judge: list[int]) -> float | None:
    return sum(abs(a - b) <= 1 for a, b in zip(human, judge, strict=True)) / len(human) if human else None


def quadratic_kappa(human: list[int], judge: list[int], categories: tuple[int, ...] = SCALE) -> float | None:
    """Cohen's kappa with quadratic weights: 1 - observed / expected weighted disagreement, the weight of a pair being
    ((a - b) / (largest - smallest category)) squared and the expected table the one the two marginals would give by
    chance. None when it is not defined: fewer than two ratings, or no disagreement could even happen by chance (both
    raters gave one and the same value every time)."""
    n = len(human)
    if n < 2:
        return None
    span = (max(categories) - min(categories)) ** 2
    rows = {c: sum(1 for a in human if a == c) for c in categories}
    cols = {c: sum(1 for b in judge if b == c) for c in categories}
    observed = sum((a - b) ** 2 for a, b in zip(human, judge, strict=True)) / span
    expected = sum(rows[i] * cols[j] * (i - j) ** 2 for i in categories for j in categories) / (n * span)
    return None if expected == 0 else 1 - observed / expected


def kappa_note(human: list[int], judge: list[int], kappa: float | None) -> str | None:
    if len(human) < 2:
        return "uma linha só: o kappa não é definido"
    if kappa is None:
        return (
            "as notas são iguais e sem variação dos dois lados: o kappa não é definido (a concordância exata é total)"
        )
    if len(set(human)) == 1 or len(set(judge)) == 1:
        return "um dos lados não varia: o kappa é 0 por construção; leia a concordância exata"
    return None


def wilson(successes: int, n: int) -> tuple[float, float] | None:
    """95% interval of a proportion (Wilson score): closed form, sensible at the edges and for small samples."""
    if n == 0:
        return None
    p, z2 = successes / n, Z95**2
    centre = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def kappa_interval(
    human: list[int], judge: list[int], categories: tuple[int, ...], seed: int
) -> tuple[float, float] | None:
    """95% percentile interval of the kappa by bootstrap: the pairs are resampled with replacement, seeded so the
    report repeats. None when too few resamples have a defined kappa (a constant rating, a handful of lines)."""
    n = len(human)
    if n < 2:
        return None
    rng = random.Random(seed)
    values = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        picks = rng.choices(range(n), k=n)
        value = quadratic_kappa([human[i] for i in picks], [judge[i] for i in picks], categories)
        if value is not None:
            values.append(value)
    if len(values) < MIN_VALID_RESAMPLES:
        return None
    values.sort()
    return values[round(0.025 * (len(values) - 1))], values[round(0.975 * (len(values) - 1))]


def _measure(human: list[int], judge: list[int], categories: tuple[int, ...], seed: int, *, close: bool) -> dict:
    n = len(human)
    kappa = quadratic_kappa(human, judge, categories)
    note = kappa_note(human, judge, kappa)
    exact = sum(a == b for a, b in zip(human, judge, strict=True))
    near = sum(abs(a - b) <= 1 for a, b in zip(human, judge, strict=True))
    return {
        "n": n,
        "exact": exact_agreement(human, judge),
        "exact_ci": wilson(exact, n),
        "within_one": within_one(human, judge) if close else None,
        "within_one_ci": wilson(near, n) if close else None,
        "kappa": kappa,
        # A kappa that is 0 because one rater never varies has no interval worth showing: every resample gives 0.
        "kappa_ci": kappa_interval(human, judge, categories, seed) if kappa is not None and note is None else None,
        "kappa_note": note,
        "human_mean": statistics.mean(human) if human else None,
        "judge_mean": statistics.mean(judge) if judge else None,
    }


def analyze(pairs: list[Pair], seed: int) -> dict:
    """Agreement of the human ratings with the judge, per criterion and for the verdict, plus the large gaps."""
    criteria = {}
    for criterion in CRITERIA:
        human = [p.rating.scores[criterion] for p in pairs]
        judge = [int(p.judgement["scores"][criterion]) for p in pairs]
        criteria[criterion] = _measure(human, judge, SCALE, seed, close=True)
    said = [int(p.rating.unsupported_claim) for p in pairs]
    flagged = [int(p.judgement["unsupported_claim"]) for p in pairs]
    verdict = _measure(said, flagged, (0, 1), seed, close=False)
    verdict["table"] = {
        "both": sum(a and b for a, b in zip(said, flagged, strict=True)),
        "human_only": sum(a and not b for a, b in zip(said, flagged, strict=True)),
        "judge_only": sum(b and not a for a, b in zip(said, flagged, strict=True)),
        "neither": sum(not a and not b for a, b in zip(said, flagged, strict=True)),
    }
    gaps = []
    for p in pairs:
        where = (p.rating.sample_id, p.rating.case_id, p.rating.route, p.rating.split)
        for criterion in CRITERIA:
            human, judge = p.rating.scores[criterion], int(p.judgement["scores"][criterion])
            if abs(human - judge) >= BIG_GAP:
                gaps.append((*where, criterion, str(human), str(judge)))
        if p.rating.unsupported_claim != p.judgement["unsupported_claim"]:
            gaps.append((*where, VERDICT, _yes(p.rating.unsupported_claim), _yes(p.judgement["unsupported_claim"])))
    return {"n": len(pairs), "criteria": criteria, "verdict": verdict, "gaps": gaps}


# --- the report -----------------------------------------------------------------------------------------------------


def _yes(value: bool) -> str:
    return "sim" if value else "não"


def _interval(interval: tuple[float, float] | None) -> str:
    return "" if interval is None else f" (IC 95%: {interval[0]:.2f} a {interval[1]:.2f})"


def _share(value: float | None, interval) -> str:
    return "-" if value is None else f"{value:.3f}{_interval(interval)}"


def _kappa(measure: dict) -> str:
    if measure["kappa"] is None:
        return "n/d"
    if measure["kappa_ci"] is None:
        return f"{measure['kappa']:.3f} (sem intervalo)"
    return f"{measure['kappa']:.3f}{_interval(measure['kappa_ci'])}"


def _cell(value) -> str:
    return " ".join(str(value).replace("|", "\\|").split())


def caveat(n: int) -> str:
    return (
        f"Ressalva de amostra pequena (D19): {n} respostas avaliadas por uma pessoa. A concordância e o kappa têm "
        "margem grande com tão poucas linhas (os intervalos abaixo mostram o tamanho dela) e cada recorte por rota ou "
        "split tem poucos casos. Leia como indicação de quanto confiar no juiz, não como prova."
    )


def render_report(
    meta: dict, rater: str, pairs: list[Pair], analysis: dict, *, skipped: list[str], now: datetime | None = None
) -> str:
    stamp = (now or datetime.now(UTC)).isoformat(timespec="seconds")
    n = analysis["n"]
    judges = sorted({p.judgement["judge"] for p in pairs})
    rubrics = sorted({p.judgement["rubric_version"] for p in pairs})
    lines = [
        "# Calibração humana do juiz (v0.8.0)",
        "",
        f"Gerado em {stamp}. Campanha `{_cell(meta['campaign'])}`, avaliador humano `{_cell(rater)}`, rubrica "
        f"`judge.v{', '.join(rubrics)}`, juiz {', '.join(f'`{_cell(j)}`' for j in judges)}.",
        f"Amostra de `{_cell(meta.get('source', '-'))}` com a semente {_cell(meta.get('seed', '-'))} "
        f"({_cell(meta.get('drawn', '-'))} sorteadas de {_cell(meta.get('eligible', '-'))} respostas elegíveis, "
        f"estratificadas por rota e split). Avaliadas: {n}. Sem avaliação (linhas puladas): {len(skipped)}.",
        "",
        f"> {caveat(n)}",
        "",
        "## Concordância por critério",
        "",
        "| Critério | n | Exata | ±1 | Kappa quadrático | Média humano | Média juiz | Viés (juiz − humano) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for criterion in CRITERIA:
        m = analysis["criteria"][criterion]
        bias = "-" if m["human_mean"] is None else f"{m['judge_mean'] - m['human_mean']:+.2f}"
        lines.append(
            f"| {criterion} ({CRITERIA_LABELS[criterion]}) | {m['n']} | {_share(m['exact'], m['exact_ci'])} | "
            f"{_share(m['within_one'], m['within_one_ci'])} | {_kappa(m)} | "
            f"{_fmt(m['human_mean'])} | {_fmt(m['judge_mean'])} | {bias} |"
        )
    verdict = analysis["verdict"]
    table = verdict["table"]
    lines += [
        "",
        "## Afirmação sem suporte (veredito)",
        "",
        f"Concordância exata: {_share(verdict['exact'], verdict['exact_ci'])}. Kappa (com dois valores, o kappa "
        f"quadrático é o kappa de Cohen): {_kappa(verdict)}.",
        "",
        "| | Juiz: sim | Juiz: não |",
        "| --- | --- | --- |",
        f"| Humano: sim | {table['both']} | {table['human_only']} |",
        f"| Humano: não | {table['judge_only']} | {table['neither']} |",
    ]
    notes = sorted(
        {
            f"{name}: {measure['kappa_note']}"
            for name, measure in [*analysis["criteria"].items(), (VERDICT, verdict)]
            if measure["kappa_note"]
        }
    )
    if notes:
        lines += ["", "Casos de borda no kappa:", *[f"- {_cell(note)}" for note in notes]]
    lines += ["", f"## Divergências grandes (diferença de {BIG_GAP} pontos ou mais, ou veredito oposto)", ""]
    if analysis["gaps"]:
        lines += [
            "| Amostra | Caso | Rota | Split | Critério | Humano | Juiz |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            *["| " + " | ".join(_cell(cell) for cell in gap) + " |" for gap in analysis["gaps"]],
        ]
    else:
        lines.append("Nenhuma.")
    by_route: dict[str, int] = {}
    by_split: dict[str, int] = {}
    for p in pairs:
        by_route[p.rating.route or "-"] = by_route.get(p.rating.route or "-", 0) + 1
        by_split[p.rating.split or "-"] = by_split.get(p.rating.split or "-", 0) + 1
    lines += [
        "",
        "## Cobertura da amostra avaliada",
        "",
        "Rotas: "
        + ", ".join(f"{_cell(k)} {v}" for k, v in sorted(by_route.items()))
        + ". Splits: "
        + ", ".join(f"{_cell(k)} {v}" for k, v in sorted(by_split.items()))
        + ".",
        "",
        "## Como ler",
        "",
        "- Exata: parte das respostas em que humano e juiz deram a mesma nota. ±1: parte em que a diferença é de até "
        "um ponto. Os intervalos de ambas são de Wilson (95%).",
        "- Kappa quadrático ponderado: 1 é concordância perfeita; 0 é o que o acaso daria com as mesmas distribuições "
        "de notas; negativo é pior que o acaso. Diferenças maiores pesam mais (peso = quadrado da diferença). O "
        "intervalo é por reamostragem (bootstrap) das respostas, com a semente da amostra. Quando quase todas as "
        "notas são 4 ou 5, o kappa fica baixo mesmo com concordância exata alta; por isso as três medidas aparecem "
        "juntas.",
        "- Viés: média das notas do juiz menos a média das notas humanas; positivo é um juiz mais generoso.",
        "- Dados: respostas do sistema sobre a conta sintética, mascaradas; o arquivo da amostra não traz nenhuma "
        "nota do juiz.",
    ]
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


# --- the two commands -----------------------------------------------------------------------------------------------


def _token(text: str) -> str:
    """A name safe to put in the sample line (no `;`, `=` or spaces) and in a table cell."""
    return re.sub(r"[^\w.\-]+", "-", text).strip("-") or "campanha"


def make_sample(report: Path, size: int, seed: int, campaign: str | None = None) -> tuple[list[dict], dict]:
    """`eval-calibrate --sample`: the CSV rows and the sample line for `size` answers of the report."""
    rows, stem = load_source(report)
    meta = {
        "campaign": _token(campaign or stem),
        "seed": seed,
        "source": _token(report.name),
        "requested": size,
        "eligible": len(rows),
    }
    return sample_rows(draw_sample(rows, size, seed)), meta


def import_filled(
    conn: sqlite3.Connection, path: Path, *, rater: str = "owner", campaign: str | None = None, now=None
) -> dict:
    """`eval-calibrate --import`: validates the file, stores the ratings and measures the agreement. Nothing is
    written unless every line is valid and has its judgement in `run_evaluations`."""
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CalibrationError(
            f"{path.name} não está em UTF-8: salve a planilha como 'CSV UTF-8' e importe de novo."
        ) from None
    except OSError as exc:
        raise CalibrationError(f"não consegui ler {path}: {type(exc).__name__}") from None
    filled = read_filled(text)
    meta = dict(filled.meta)
    if campaign:
        meta["campaign"] = _token(campaign)
    if not meta.get("campaign"):
        raise CalibrationError(
            "falta a linha 'amostra:' do cabeçalho de instruções, que traz a campanha: use o arquivo gerado por "
            "eval-calibrate --sample ou informe --campaign."
        )
    if not filled.ratings:
        raise CalibrationError(
            f"nenhuma linha de {path.name} tem avaliação: preencha as notas e a coluna unsupported_claim."
        )
    rater = rater.strip()
    if not rater:
        raise CalibrationError("o avaliador (--rater) não pode ficar vazio.")
    pairs = link(conn, filled)
    counts = store(conn, meta["campaign"], rater, pairs)
    seed = int(meta["seed"]) if str(meta.get("seed", "")).lstrip("-").isdigit() else DEFAULT_SEED
    analysis = analyze(pairs, seed)
    return {
        "meta": meta,
        "rater": rater,
        "counts": counts,
        "skipped": filled.skipped,
        "analysis": analysis,
        "report": render_report(meta, rater, pairs, analysis, skipped=filled.skipped, now=now),
    }
