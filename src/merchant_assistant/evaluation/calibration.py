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
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path

from merchant_assistant.evaluation import aggregate, evidence
from merchant_assistant.evaluation import calibration_packets as packets
from merchant_assistant.evaluation.judge import (
    CAMPAIGN_PRINCIPAL,
    CLAIM_VERDICTS,
    CRITERIA,
    RUBRIC,
    RUBRIC_VERSION,
    RUBRIC_VERSIONS,
    TOKEN_KEYS,
    JudgeRefused,
    judge_usage,
    rubric_version,
)
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
MAX_UNDEFINED_SHARE = 0.10  # more resamples than this with no kappa: the series is too lopsided for an interval
Z95 = 1.959964
BIG_GAP = 2  # a difference of this many points or more is listed in the report
MAX_REPORTED_ERRORS = 25
# The v0.8.0 calibration sample came from the campaign of development only: the holdout_v080 was run once, last, by
# the QA (D17). The v0.11.0 sample (task 89 round 2, decision of the Supervisor) may also draw from the holdout_v080
# with `--split all`: the calibration measures the judge, not the agent, and new answers to those questions do not
# touch any measure of the agent. The default stays the development splits.
DEVELOPMENT_SPLITS = ("dev", "holdout")
ALL_SPLITS = ("dev", "holdout", "holdout_v080")
SPLIT_CHOICES = {
    "development": DEVELOPMENT_SPLITS,
    "dev": ("dev",),
    "holdout": ("holdout",),
    "all": ALL_SPLITS,
}

# The version a new sample names in its first line (`sample_instructions`). A sample written as in v0.8.0 keeps the
# v0.8.0 lines byte for byte (the golden of task 89 regenerates them), and a CSV already written keeps its own lines.
SAMPLE_VERSION = "v0.11.0"
# A new sample's `#` lines point to the labelling instruction the raters receive with the files and repeat none of its
# rules (review P2-1 of judge.v5 iteration 3): where they could differ, the instruction holds.
INSTRUCTIONS_NEW = (
    f"Calibração humana do juiz ({SAMPLE_VERSION}). Preencha este arquivo e o sample-claims.csv pela instrução de "
    f"rotulagem que acompanha estes arquivos ({packets.LABELLING_INSTRUCTION}); onde estas linhas diferirem dela, "
    "vale a instrução. As notas do juiz não estão neste arquivo.",
    "Notas de 1 a 5 nas colunas groundedness, factual_correctness, relevance e usefulness; unsupported_claim fica em "
    "branco (o veredito sai das marcas); note é opcional. Salve como CSV UTF-8, com o mesmo separador, e não apague "
    "as colunas sample_id e request_id nem a linha 'amostra:'.",
)
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
    "fontes listadas e diga isso na nota.",
    evidence.WEB_PAGE_NOTE: "A resposta vem de busca web; os itens web_page são o texto das páginas citadas, "
    "buscado na avaliação: julgue contra eles como contra um trecho (a página pode ter mudado desde a resposta).",
    evidence.WEB_SUMMARY_NOTE: "Página indisponível; o resumo da busca escrito pelo assistente vai no lugar, não é "
    "uma página: o item web_summary mostra o que a busca devolveu, não confirma nada por fonte independente.",
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


def load_source(path: Path, splits: tuple[str, ...] = DEVELOPMENT_SPLITS) -> tuple[list[dict], str, dict[str, int]]:
    """The answers of the first execution of a campaign report that were judged, can be shown with their evidence and
    belong to one of `splits`. Returns them with the report's name (the campaign name unless one is given) and how many
    judged answers of other splits were left out, by split."""
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        cases = report["cases"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CalibrationError(f"não consegui ler o relatório {path}: {type(exc).__name__}") from None
    judged = [
        row
        for row in cases
        if row.get("repetition", 1) == 1
        and "judge_input" in row
        and (row.get("judge") or {}).get("state") == "completed"
    ]
    if not judged:
        raise CalibrationError(
            f"o relatório {path.name} não tem respostas julgadas com a evidência gravada: rode a campanha com --judge "
            "(ou --repeat) antes de sortear a amostra."
        )
    rows = [row for row in judged if row["split"] in splits]
    left_out: dict[str, int] = {}
    for row in judged:
        if row["split"] not in splits:
            left_out[row["split"]] = left_out.get(row["split"], 0) + 1
    if not rows:
        hint = (
            ""
            if "holdout_v080" in splits
            else " O holdout_v080 não entra na calibração por padrão (ele é visto uma vez, no fim, pelo QA); --split "
            "all o inclui na amostra da v0.11.0, que mede o juiz e não o agente."
        )
        raise CalibrationError(
            f"o relatório {path.name} só tem respostas dos splits {', '.join(sorted(left_out))}, e a amostra de "
            f"calibração sai de {', '.join(splits)}.{hint}"
        )
    return rows, path.stem, left_out


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


def csv_bytes(rows: list[dict], meta: dict, *, delimiter: str = ";") -> bytes:
    """The sample CSV as written: UTF-8 with a BOM (a spreadsheet then reads the accents), the instructions as `#`
    lines and the sample line."""
    if delimiter not in DELIMITERS:
        raise CalibrationError(f"separador inválido: {delimiter!r}")
    handle = io.StringIO(newline="")
    writer = csv.writer(handle, delimiter=delimiter, lineterminator="\r\n")
    for line in (*sample_instructions(meta), sample_stamp(rows, meta)):
        writer.writerow([f"# {line}"])
    writer.writerow(COLUMNS)
    for row in rows:
        writer.writerow([row[column] for column in COLUMNS])
    return handle.getvalue().encode("utf-8-sig")


def write_csv(path: Path, rows: list[dict], meta: dict, *, delimiter: str = ";") -> None:
    data = csv_bytes(rows, meta, delimiter=delimiter)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def sample_instructions(meta: dict) -> tuple[str, ...]:
    """The `#` lines above the sample line. A sample that uses what task 89 added (the same keys as `sample_stamp`)
    gets the short lines of the current version, which point to the labelling instruction; one that does not is
    written as in v0.8.0. Reading a sample never looks at these lines."""
    if not any(meta.get(key) for key, _ in STAMP_EXTRAS):
        return INSTRUCTIONS
    return INSTRUCTIONS_NEW


def sample_stamp(rows: list[dict], meta: dict) -> str:
    """The sample line. What task 89 added (exclusions, enriched routes, the source of the claims, the seal) is written
    only when the sample used it, so a v0.8.0 sample is written as before."""
    stamp = (
        f"amostra: campanha={meta['campaign']}; semente={meta['seed']}; origem={meta['source']}; "
        f"sorteadas={len(rows)}; pedidas={meta['requested']}; elegiveis={meta['eligible']}; "
        f"splits={meta['splits']}; rubrica={RUBRIC}.v{RUBRIC_VERSION}"
    )
    for key, name in STAMP_EXTRAS:
        if meta.get(key):
            stamp += f"; {name}={meta[key]}"
    return stamp


# --- reading the filled file ----------------------------------------------------------------------------------------


@dataclass
class Rating:
    sample_id: str
    request_id: str
    case_id: str
    route: str
    split: str
    scores: dict[str, int]
    unsupported_claim: bool | None  # None while it waits for the claim marks (task 89), or a panel left it blank
    note: str
    line: int


@dataclass
class Filled:
    meta: dict[str, str]
    ratings: list[Rating]
    blank: dict[str, str]  # sample id -> request id of the rows with no rating at all
    rows: list[dict] = field(default_factory=list)  # the identity of every data row (IDENTITY), rated or not

    @property
    def skipped(self) -> list[str]:
        return list(self.blank)


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
    "splits": "splits",
    "rubrica": "rubric",
    "excluidas": "excluded",
    "enriquecidas": "enriched",
    "afirmacoes": "claims",
    "sha256_afirmacoes": "claims_sha256",
    "selo": "seal",
}
# Written into the sample line only when the sample has them (task 89): meta key -> name in the line.
STAMP_EXTRAS = (
    ("excluded", "excluidas"),
    ("enriched", "enriquecidas"),
    ("claims", "afirmacoes"),
    ("claims_sha256", "sha256_afirmacoes"),
    ("seal", "selo"),
)
IDENTITY = ("sample_id", "request_id", "case_id", "route", "split")
_YES = {"sim", "s", "true", "verdadeiro", "yes", "y", "1"}
_NO = {"nao", "n", "false", "falso", "no", "0"}


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().strip().casefold()


def read_filled(text: str, *, verdict_optional: bool = False, partial: bool = False) -> Filled:
    """Parses and validates the filled CSV. Every problem is collected with its line, so one pass shows them all. With
    `verdict_optional` (the rater also returned the claims CSV, task 89) the verdict may be left blank: it is computed
    from the marks, and a rating without it has `unsupported_claim` None. With `partial` (a panel of models, whose CSV
    is blank where its two members diverge, task 89 round 4) a rated row may leave any score or the verdict blank:
    the rating has only the scores given and `unsupported_claim` None when the verdict is blank."""
    lines = text.lstrip("\ufeff").splitlines()
    found = next((_HEADER.match(line) for line in lines if _HEADER.match(line)), None)
    if found is None:
        raise CalibrationError(
            "não encontrei o cabeçalho com a coluna sample_id: use o arquivo gerado por eval-calibrate --sample."
        )
    reader = csv.reader(io.StringIO(text.lstrip("\ufeff"), newline=""), delimiter=found.group(1))
    meta: dict[str, str] = {}
    header: list[str] | None = None
    errors: list[str] = []
    ratings: list[Rating] = []
    blank: dict[str, str] = {}
    identity: list[dict] = []
    seen: dict[str, dict[str, int]] = {"sample_id": {}, "request_id": {}}
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
        _rate_row(values, start, ratings, blank, errors, seen, verdict_optional, partial)
        identity.append({key: values.get(key, "") for key in IDENTITY})
    if header is None:
        raise CalibrationError("não encontrei o cabeçalho com a coluna sample_id: use o arquivo gerado por --sample.")
    if errors:
        raise CalibrationError(errors)
    return Filled(meta, ratings, blank, identity)


def _read_text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CalibrationError(
            f"{path.name} não está em UTF-8: salve a planilha como 'CSV UTF-8' e importe de novo."
        ) from None
    except OSError as exc:
        raise CalibrationError(f"não consegui ler {path}: {type(exc).__name__}") from None


def sample_request_ids(path: Path) -> list[str]:
    """The `request_id` of every data row of a calibration CSV, in the order of the file (`eval --only-sample`, spec
    v0.9.0 D1). The ratings are not read: a blank or a filled file gives the same ids."""
    text = _read_text(path).lstrip("\ufeff")
    found = next((match for line in text.splitlines() if (match := _HEADER.match(line))), None)
    if found is None:
        raise CalibrationError(f"{path.name}: não encontrei o cabeçalho com a coluna sample_id.")
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=found.group(1))
    at: int | None = None
    ids: list[str] = []
    for cells in reader:
        cells = [cell.strip() for cell in cells]
        if not any(cells) or cells[0].startswith("#"):
            continue
        if at is None:
            header = [_plain(cell) for cell in cells]
            if "request_id" not in header:
                raise CalibrationError(f"{path.name}: falta a coluna request_id no cabeçalho.")
            at = header.index("request_id")
            continue
        value = cells[at] if at < len(cells) else ""
        if not value:
            raise CalibrationError(f"{path.name}, linha {reader.line_num}: request_id vazio.")
        if value in ids:
            raise CalibrationError(f"{path.name}, linha {reader.line_num}: request_id {value} repetido.")
        ids.append(value)
    if not ids:
        raise CalibrationError(f"{path.name}: nenhuma linha de dados com request_id.")
    return ids


def _parse_rating(
    values: dict[str, str], verdict_optional: bool = False, partial: bool = False
) -> tuple[dict[str, int], bool | None, list[str]]:
    """The four scores and the verdict of one row, and what is wrong with them. With `partial`, a blank score is left
    out and a blank verdict is None."""
    scores: dict[str, int] = {}
    problems = []
    for criterion in CRITERIA:
        raw = values.get(criterion, "")
        if not raw and partial:
            continue
        if not raw:
            problems.append(f"{criterion} está vazio")
        elif raw in {str(point) for point in SCALE}:
            scores[criterion] = int(raw)
        else:
            problems.append(f"{criterion} precisa ser um inteiro de 1 a 5, recebi {raw!r}")
    raw, claim = values.get(VERDICT, ""), False
    if not raw and (verdict_optional or partial):
        claim = None
    elif not raw:
        problems.append(f"{VERDICT} está vazio")
    elif _plain(raw) in _YES | _NO:
        claim = _plain(raw) in _YES
    else:
        problems.append(f"{VERDICT} precisa ser sim ou nao, recebi {raw!r}")
    return scores, claim, problems


def _rate_row(
    values: dict[str, str],
    line: int,
    ratings: list[Rating],
    blank_rows: dict[str, str],
    errors: list[str],
    seen: dict[str, dict[str, int]],
    verdict_optional: bool = False,
    partial: bool = False,
) -> None:
    """One data row: skipped when no rating was filled in, an error line (one per row, all its problems) when the row
    is wrong or half filled, a `Rating` otherwise. A sample id or a request id may appear in one row only."""
    sample_id = values.get("sample_id", "")
    problems = []
    for key in ("sample_id", "request_id"):
        value = values.get(key, "")
        if not value:
            problems.append(f"{key} vazio" + (" (não apague essa coluna)" if key == "request_id" else ""))
        elif value in seen[key]:
            problems.append(f"{key} repetido (já aparece na linha {seen[key][value]})")
        else:
            seen[key][value] = line
    blank = not any(values.get(column) for column in RATING_COLUMNS)
    scores, claim = {}, False
    if not blank:
        scores, claim, rating_problems = _parse_rating(values, verdict_optional, partial)
        problems += rating_problems
    if problems:
        hint = (
            " Preencha os cinco campos ou deixe todos vazios para pular a linha."
            if any("está vazio" in problem for problem in problems)
            else ""
        )
        errors.append(f"linha {line} ({sample_id or 'sem sample_id'}): {'; '.join(problems)}.{hint}")
    elif blank:
        blank_rows[sample_id] = values["request_id"]
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


LEGACY_RUN = "legado"  # judgements written before v0.9.0 carry no execution name: together they are one execution


def _judge_name(evaluator_json: str) -> str:
    evaluator = json.loads(evaluator_json)
    return f"{evaluator.get('provider')}/{evaluator.get('model')}"


def _run_name(evaluator_json: str) -> str:
    """The execution that wrote a judgement (`eval --name`, kept in `evaluator.run` since v0.9.0)."""
    return json.loads(evaluator_json).get("run") or LEGACY_RUN


def _judgement(row) -> dict:
    return {
        "evaluation_id": row["evaluation_id"],
        "rubric_version": row["rubric_version"],
        "judge": _judge_name(row["evaluator"]),
        "run": _run_name(row["evaluator"]),
        "scores": json.loads(row["scores"]),
        "unsupported_claim": bool(row["unsupported_claim"]),
        # judge.v5 (0013): the claims and their verdicts, compared claim by claim in task 89; None for v3 and v4
        "claims": json.loads(row["claims"]) if row["claims"] else None,
    }


def judgement_for(
    conn: sqlite3.Connection,
    request_id: str,
    judge: str | None = None,
    run: str | None = None,
    rubric: str | None = None,
    *,
    majority: bool = False,
) -> dict | None:
    """The first judgement (repetition 1) that the campaign wrote for this request, with its scores and verdict. With
    `judge` (`<provider>/<model>`, spec v0.9.0 RF-108) only that judge's judgements count; without it, any judge's.
    With `run`, only the judgements of that execution (`LEGACY_RUN` for those without a name); with `rubric` (the
    stored version, "3" or "4", spec v0.10.0 D1), only those of that rubric. With `majority` (`eval-calibrate
    --judge-majority`, a tool of v0.11.0 outside D6(a)), every completed judgement of those, of any repetition, is a
    vote (`majority_judgement`)."""
    rows = conn.execute(
        "SELECT evaluation_id, rubric_version, evaluator, scores, unsupported_claim, claims, repetition "
        "FROM run_evaluations WHERE request_id=? AND principal_id=? AND rubric=? AND state='completed' "
        "AND scores IS NOT NULL ORDER BY created_at, evaluation_id",
        (request_id, CAMPAIGN_PRINCIPAL, RUBRIC),
    )
    votes = []
    for row in rows:
        if not majority and row["repetition"] != 1:
            continue
        if judge is not None and _judge_name(row["evaluator"]) != judge:
            continue
        if run is not None and _run_name(row["evaluator"]) not in ((run,) if isinstance(run, str) else run):
            continue
        if rubric is not None and row["rubric_version"] != rubric:
            continue
        if not majority:
            return _judgement(row)
        votes.append(_judgement(row))
    return majority_judgement(request_id, votes) if votes else None


def majority_judgement(request_id: str, votes: list[dict]) -> dict:
    """The verdict of the majority of the completed judgements of one answer (a tool of v0.11.0 outside D6(a)): each
    judgement's `unsupported_claim` is computed in code from its own claims, and the answer's is yes when more than
    half of them say yes. Each score is the median of the votes. The claims are those of the first judgement (in the
    order they were written) whose verdict is the majority's, so the claim table and the verdict agree; its id is the
    one a rating is linked to. An even number of votes is refused: a tie has no majority. One vote is that judgement."""
    if len(votes) % 2 == 0:
        raise CalibrationError(
            f"a requisição {request_id} tem {len(votes)} julgamentos completos na execução comparada: a maioria "
            "precisa de um número ímpar. Julgue-a de novo com o mesmo --name (uma repetição a mais) e importe de novo."
        )
    yes = sum(vote["unsupported_claim"] for vote in votes)
    verdict = yes * 2 > len(votes)
    first = next(vote for vote in votes if vote["unsupported_claim"] == verdict)
    scores = {name: statistics.median(vote["scores"][name] for vote in votes) for name in first["scores"]}
    return first | {"scores": scores, "unsupported_claim": verdict, "votes": {"judgements": len(votes), "yes": yes}}


def judgement_by_id(conn: sqlite3.Connection, evaluation_id: str) -> dict | None:
    row = conn.execute(
        "SELECT evaluation_id, rubric_version, evaluator, scores, unsupported_claim, claims FROM run_evaluations "
        "WHERE evaluation_id=? AND state='completed' AND scores IS NOT NULL",
        (evaluation_id,),
    ).fetchone()
    return None if row is None else _judgement(row)


@dataclass
class Pair:
    rating: Rating
    judgement: dict


def link(
    conn: sqlite3.Connection,
    filled: Filled,
    judge: str | None = None,
    run: str | None = None,
    rubric: str | None = None,
    *,
    majority: bool = False,
) -> list[Pair]:
    pairs, errors = [], []
    for rating in filled.ratings:
        try:
            judgement = judgement_for(conn, rating.request_id, judge, run, rubric, majority=majority)
        except CalibrationError as exc:
            errors += [f"linha {rating.line} ({rating.sample_id}): {message}" for message in exc.messages]
            continue
        if judgement is None:
            by = f" do juiz {judge}" if judge else ""
            wanted = "completo, de qualquer repetição" if majority else "repetição 1 completa"
            by += f" na execução {run!r} ({wanted})" if run else ""
            by += f" sob a rubrica judge.v{rubric}" if rubric not in (None, RUBRIC_VERSION) else ""
            errors.append(
                f"linha {rating.line} ({rating.sample_id}): não há julgamento{by} da requisição {rating.request_id} "
                "em run_evaluations deste banco. Importe no banco em que a campanha gravou os julgamentos."
            )
        else:
            pairs.append(Pair(rating, judgement))
    if errors:
        raise CalibrationError(errors)
    return pairs


def check_same_sample(conn: sqlite3.Connection, campaign: str, rater: str, pairs: list[Pair]) -> None:
    """A sample id of a campaign and rater that already has a rating belongs to one request. A file that brings the
    same id for another request is another sample under the same campaign name, and importing it would replace the
    first sample's human ratings without a word."""
    known = {
        row["sample_id"]: row["request_id"]
        for row in conn.execute(
            "SELECT sample_id, request_id FROM calibrations WHERE campaign=? AND rater=?", (campaign, rater)
        )
    }
    errors = [
        f"linha {pair.rating.line} ({pair.rating.sample_id}): a campanha {campaign!r} já tem a nota de {rater!r} para "
        f"{pair.rating.sample_id} sobre a requisição {known[pair.rating.sample_id]}, e este arquivo traz "
        f"{pair.rating.request_id}: parece outra amostra com o mesmo nome de campanha. Importe-a com "
        "--campaign <outro nome> (ou gere a amostra com --campaign) para guardá-la separada; nada foi alterado."
        for pair in pairs
        if known.get(pair.rating.sample_id, pair.rating.request_id) != pair.rating.request_id
    ]
    if errors:
        raise CalibrationError(errors)


@dataclass
class Stored:
    created: int
    updated: int
    removed: list[str]  # sample ids whose rating was withdrawn because the row came back empty
    outside: list[str]  # sample ids stored for this campaign and rater that are not in the file

    def counts(self) -> dict[str, int]:
        return {"created": self.created, "updated": self.updated}


def store(
    conn: sqlite3.Connection, campaign: str, rater: str, pairs: list[Pair], blank: dict[str, str] | None = None
) -> Stored:
    """Writes the ratings in one transaction. The file is the rater's statement for its sample: importing it again
    updates the rows of the same campaign, sample and rater, and a row that came back empty withdraws the rating it
    had (only when the stored rating is for the same request), so the database never keeps a note the report does not
    count."""
    conn.execute("BEGIN")
    try:
        created, updated, removed = _write_ratings(conn, campaign, rater, pairs, blank)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return Stored(created, updated, removed, _outside(conn, campaign, rater, pairs))


def store_many(conn: sqlite3.Connection, groups: list[tuple[str, str, list[Pair], dict[str, str]]]) -> list[Stored]:
    """`store` for several (campaign, rater) groups in one transaction (task 89: two raters, one or more files each):
    every rating is written, or none."""
    conn.execute("BEGIN")
    try:
        written = [_write_ratings(conn, campaign, rater, pairs, blank) for campaign, rater, pairs, blank in groups]
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return [
        Stored(created, updated, removed, _outside(conn, campaign, rater, pairs))
        for (created, updated, removed), (campaign, rater, pairs, _) in zip(written, groups, strict=True)
    ]


def _outside(conn: sqlite3.Connection, campaign: str, rater: str, pairs: list[Pair]) -> list[str]:
    in_file = {pair.rating.sample_id for pair in pairs}
    return [
        row["sample_id"]
        for row in conn.execute(
            "SELECT sample_id FROM calibrations WHERE campaign=? AND rater=? ORDER BY sample_id", (campaign, rater)
        )
        if row["sample_id"] not in in_file
    ]


def _write_ratings(
    conn: sqlite3.Connection, campaign: str, rater: str, pairs: list[Pair], blank: dict[str, str] | None
) -> tuple[int, int, list[str]]:
    """The writes of `store`, inside the caller's transaction."""
    created = updated = 0
    removed: list[str] = []
    now = datetime.now(UTC).isoformat(timespec="seconds")
    for sample_id, request_id in (blank or {}).items():
        gone = conn.execute(
            "DELETE FROM calibrations WHERE campaign=? AND sample_id=? AND rater=? AND request_id=?",
            (campaign, sample_id, rater, request_id),
        )
        if gone.rowcount:
            removed.append(sample_id)
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
                None if rating.unsupported_claim is None else int(rating.unsupported_claim),
                rating.note or None,
                now,
            ),
        )
        updated += exists is not None
        created += exists is None
    return created, updated, removed


# --- a second judge against the same human ratings (spec v0.9.0 D1, RF-108, CA-56) ---------------------------------


def original_pairs(conn: sqlite3.Connection, original: str, rater: str, ratings: list[Rating]) -> list[Pair]:
    """The ratings of this file paired with the judgement they were linked to when the original campaign imported them.
    The ratings must be the ones stored then, request and scores alike: the experiment reuses the human ratings, it
    does not take new ones."""
    errors, pairs = [], []
    for rating in ratings:
        row = conn.execute(
            "SELECT request_id, evaluation_id, scores, unsupported_claim FROM calibrations "
            "WHERE campaign=? AND sample_id=? AND rater=?",
            (original, rating.sample_id, rater),
        ).fetchone()
        where = f"linha {rating.line} ({rating.sample_id})"
        if row is None:
            errors.append(f"{where}: a campanha original {original!r} não tem nota de {rater!r} para esta amostra.")
            continue
        same = (
            row["request_id"] == rating.request_id
            and json.loads(row["scores"]) == rating.scores
            and bool(row["unsupported_claim"]) == rating.unsupported_claim
        )
        if not same:
            errors.append(
                f"{where}: a nota deste arquivo difere da gravada na campanha original {original!r}; o experimento "
                "compara juízes contra as mesmas notas humanas. Nada foi alterado."
            )
            continue
        judgement = judgement_by_id(conn, row["evaluation_id"])
        if judgement is None:
            errors.append(f"{where}: o julgamento {row['evaluation_id']} da campanha original não está no banco.")
            continue
        pairs.append(Pair(rating, judgement))
    if errors:
        raise CalibrationError(errors)
    return pairs


def _judge_rows(conn: sqlite3.Connection, request_ids: list[str], judge: str, rubric: str | None = RUBRIC_VERSION):
    """The judgements of `judge` on these requests under `rubric` (the stored version; `None` for any)."""
    wanted = set(request_ids)
    for row in conn.execute(
        "SELECT request_id, evaluator, state, scores, unsupported_claim, cost_usd, result, rubric_version "
        "FROM run_evaluations WHERE principal_id=? AND rubric=? ORDER BY created_at, evaluation_id",
        (CAMPAIGN_PRINCIPAL, RUBRIC),
    ):
        if rubric is not None and row["rubric_version"] != rubric:
            continue
        if row["request_id"] in wanted and _judge_name(row["evaluator"]) == judge:
            yield row


def judge_executions(
    conn: sqlite3.Connection, request_ids: list[str], judge: str, rubric: str | None = RUBRIC_VERSION
) -> dict[str, int]:
    """How many judgements (any state) each execution of `judge` wrote on these requests under `rubric`."""
    found: dict[str, int] = {}
    for row in _judge_rows(conn, request_ids, judge, rubric):
        name = _run_name(row["evaluator"])
        found[name] = found.get(name, 0) + 1
    return dict(sorted(found.items()))


def _listed(found: dict[str, int]) -> str:
    return ", ".join(f"{name!r} ({count} julgamentos)" for name, count in found.items())


def choose_run(
    conn: sqlite3.Connection,
    request_ids: list[str],
    judge: str,
    judge_run: str | None,
    rubric: str = RUBRIC_VERSION,
) -> str | None:
    """The execution of the requested judge that the comparison reads (task 79 round 2): the one named, or the only
    one there is, among those of `rubric` (spec v0.10.0 D1). Two executions on the same answers (the probe and the
    repetitions, say) and no name is an error: mixing them would change the agreement, the consistency and the cost.
    An execution named under another rubric is an error too. `None` when the judge has no judgement here (the link
    then says which requests lack one)."""
    found = judge_executions(conn, request_ids, judge, rubric)
    under = f" sob a rubrica judge.v{rubric}" if rubric != RUBRIC_VERSION else ""
    if judge_run is not None:
        if judge_run not in found:
            other = sorted(
                {
                    row["rubric_version"]
                    for row in _judge_rows(conn, request_ids, judge, None)
                    if _run_name(row["evaluator"]) == judge_run
                }
            )
            if other:
                raise CalibrationError(
                    f"a execução {judge_run!r} do juiz {judge} gravou julgamentos "
                    f"{', '.join('judge.v' + v for v in other)}, não judge.v{rubric}: confira --rubric "
                    "(cada --judge leva a rubrica da sua execução); nada foi alterado."
                )
            seen = _listed(found) if found else "nenhuma"
            raise CalibrationError(
                f"o juiz {judge} não tem julgamento da execução {judge_run!r} sobre estas respostas{under}. Execuções "
                f"encontradas: {seen}."
            )
        return judge_run
    if len(found) > 1:
        raise CalibrationError(
            f"o juiz {judge} tem mais de uma execução sobre estas respostas{under}: {_listed(found)}. Escolha a que "
            "entra na comparação com --judge-run <nome> (o --name do eval que a gravou); nada foi alterado."
        )
    return next(iter(found), None)


def judge_runs(
    conn: sqlite3.Connection,
    request_ids: list[str],
    judge: str,
    runs: Sequence[str] | None = None,
    rubric: str | None = RUBRIC_VERSION,
) -> dict:
    """Judgements of `judge` under `rubric` (the configured default unless `None` is given) on these requests, only
    those of `runs` when given: consistency between repetitions over the same answer (`aggregate`), failures, cost and
    tokens recorded."""
    entries: dict[str, dict] = {}
    cost = 0.0
    recorded: list[dict] = []
    for row in _judge_rows(conn, request_ids, judge, rubric):
        if runs is not None and _run_name(row["evaluator"]) not in runs:
            continue
        completed = row["state"] == "completed" and row["scores"] is not None
        record = {
            "state": "completed" if completed else "failed",
            "scores": json.loads(row["scores"]) if completed else {},
            "unsupported_claim": bool(row["unsupported_claim"]) if completed else None,
        }
        entries.setdefault(row["request_id"], {"route": "-", "split": "-", "records": []})["records"].append(record)
        cost += row["cost_usd"] or 0.0
        recorded.append({"usage": json.loads(row["result"] or "{}").get("usage")})
    block = aggregate._block(list(entries.values()))
    judgements = sum(len(entry["records"]) for entry in entries.values())
    return {
        "judge": judge,
        "runs": sorted(runs) if runs is not None else None,
        "answers": len(entries),
        "judgements": judgements,
        "failed": block["failed"],
        "cost_usd": round(cost, 6),
        "cost_per_judgement_usd": round(cost / judgements, 6) if judgements else None,
        "usage": judge_usage(recorded),
        "consistency": block,
    }


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


def cohen_kappa(first: list[int], second: list[int], categories: tuple[int, ...]) -> float | None:
    """Cohen's kappa without weights, for categories with no order (the four claim marks, task 89): 1 - (1 - observed
    agreement) / (1 - agreement by chance). None with fewer than two ratings or when chance alone agrees always."""
    n = len(first)
    if n < 2:
        return None
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / n
    chance = sum(first.count(c) * second.count(c) for c in categories) / (n * n)
    return None if chance >= 1 else (observed - chance) / (1 - chance)


def kappa_interval(
    human: list[int], judge: list[int], categories: tuple[int, ...], seed: int, kappa=quadratic_kappa
) -> tuple[float, float] | None:
    """95% percentile interval of the kappa by bootstrap: the pairs are resampled with replacement, seeded so the
    report repeats. None when more than MAX_UNDEFINED_SHARE of the resamples have no kappa (a constant rating, a
    series so lopsided that a resample often has one value on both sides), and when every resample gives the same
    kappa (a perfect agreement stays perfect in any resample: the interval would be a point, not a measure of doubt)."""
    n = len(human)
    if n < 2:
        return None
    rng = random.Random(seed)
    values = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        picks = rng.choices(range(n), k=n)
        value = kappa([human[i] for i in picks], [judge[i] for i in picks], categories)
        if value is not None:
            values.append(value)
    if BOOTSTRAP_RESAMPLES - len(values) > MAX_UNDEFINED_SHARE * BOOTSTRAP_RESAMPLES:
        return None
    values.sort()
    low, high = values[round(0.025 * (len(values) - 1))], values[round(0.975 * (len(values) - 1))]
    return None if high - low < 1e-9 else (low, high)


INTERVAL_NOTE = (
    "sem intervalo do kappa: reamostras demais sem kappa definido, ou todas com o mesmo valor (série degenerada); "
    "leia a concordância exata"
)


def _measure(human: list[int], judge: list[int], categories: tuple[int, ...], seed: int, *, close: bool) -> dict:
    n = len(human)
    kappa = quadratic_kappa(human, judge, categories)
    note = kappa_note(human, judge, kappa)
    interval = kappa_interval(human, judge, categories, seed) if kappa is not None and note is None else None
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
        "kappa_ci": interval,
        "kappa_note": note,
        "interval_note": INTERVAL_NOTE if kappa is not None and note is None and interval is None else None,
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
    meta: dict,
    rater: str,
    pairs: list[Pair],
    analysis: dict,
    *,
    skipped: list[str],
    removed: Sequence[str] = (),
    outside: Sequence[str] = (),
    now: datetime | None = None,
    comparison: dict | None = None,
) -> str:
    stamp = (now or datetime.now(UTC)).isoformat(timespec="seconds")
    n = analysis["n"]
    judges = sorted({p.judgement["judge"] for p in pairs})
    rubrics = sorted({p.judgement["rubric_version"] for p in pairs})
    lines = [
        _title(comparison),
        "",
        f"Gerado em {stamp}. Campanha `{_cell(meta['campaign'])}`, avaliador humano `{_cell(rater)}`, rubrica "
        f"`judge.v{', '.join(rubrics)}`, juiz {', '.join(f'`{_cell(j)}`' for j in judges)}.",
        f"Amostra de `{_cell(meta.get('source', '-'))}` com a semente {_cell(meta.get('seed', '-'))} "
        f"({_cell(meta.get('drawn', '-'))} sorteadas de {_cell(meta.get('eligible', '-'))} respostas elegíveis, "
        "balanceadas por estrato de rota e split, sem ponderar pelo tamanho de cada um). "
        f"Avaliadas: {n}. Sem avaliação (linhas puladas): {len(skipped)}.",
        *_import_notes(removed, outside),
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
            f"{name}: {measure[key]}"
            for name, measure in [*analysis["criteria"].items(), (VERDICT, verdict)]
            for key in ("kappa_note", "interval_note")
            if measure[key]
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
    if comparison and comparison.get("blocks"):
        lines += render_blocks(analysis, comparison)
    elif comparison:
        lines += render_comparison(pairs, analysis, comparison)
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
        "- Amostra: balanceada por estrato (rota e split), não ponderada. Cada estrato entra com quantidades "
        "parecidas, mesmo quando é raro na campanha; as médias e as concordâncias valem para estas respostas e não "
        "estimam as da campanha inteira.",
        "- Dados: respostas do sistema sobre a conta sintética, mascaradas; o arquivo da amostra não traz nenhuma "
        "nota do juiz.",
    ]
    return "\n".join(lines) + "\n"


def _title(comparison: dict | None) -> str:
    if comparison and comparison.get("blocks"):
        return "# Calibração humana do juiz: juízes e rubricas (v0.10.0)"
    return "# Calibração humana do juiz: dois juízes (v0.9.0)" if comparison else "# Calibração humana do juiz (v0.8.0)"


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def _bias(measure: dict) -> str:
    return "-" if measure["human_mean"] is None else f"{measure['judge_mean'] - measure['human_mean']:+.2f}"


def render_comparison(pairs: list[Pair], analysis: dict, comparison: dict) -> list[str]:
    """The requested judge (A) and the judge of the original campaign (B) side by side against the same ratings, the
    rows anyone marked as an unsupported claim, each judge's consistency between repetitions and its cost."""
    other, runs = comparison["analysis"], comparison["runs"]
    a, b = comparison["judge"], comparison["original_judge"]
    a_runs = ", ".join(f"`{_cell(name)}`" for name in runs["A"]["runs"] or ["-"])
    b_runs = ", ".join(f"`{_cell(name)}`" for name in runs["B"]["runs"] or ["-"])
    lines = [
        "",
        "## Dois juízes contra as mesmas notas humanas",
        "",
        f"A = `{_cell(a)}` (campanha `{_cell(comparison['campaign'])}`); B = `{_cell(b)}`, o juiz da campanha original "
        f"`{_cell(comparison['original_campaign'])}`. As {analysis['n']} notas humanas são as gravadas na campanha "
        f"original, conferidas linha a linha; não houve avaliação humana nova. A entra com {_compared(comparison)} "
        f"de cada resposta na execução {a_runs}; B, com o julgamento ao qual cada nota foi ligada na "
        f"campanha original (execução {b_runs}). Os dois julgaram a mesma evidência gravada.",
        "",
        "| Critério | Exata A | Exata B | ±1 A | ±1 B | Kappa A | Kappa B | Viés A | Viés B |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for criterion in CRITERIA:
        x, y = analysis["criteria"][criterion], other["criteria"][criterion]
        lines.append(
            f"| {criterion} ({CRITERIA_LABELS[criterion]}) | {_share(x['exact'], None)} | {_share(y['exact'], None)} | "
            f"{_share(x['within_one'], None)} | {_share(y['within_one'], None)} | {_kappa(x)} | {_kappa(y)} | "
            f"{_bias(x)} | {_bias(y)} |"
        )
    x, y = analysis["verdict"], other["verdict"]
    lines += [
        f"| {VERDICT} | {_share(x['exact'], None)} | {_share(y['exact'], None)} | - | - | {_kappa(x)} | {_kappa(y)} "
        "| - | - |",
        "",
        "Matriz do veredito `unsupported_claim` (humano × juiz):",
        "",
        "| Juiz | Ambos sim | Só humano | Só juiz | Nenhum |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, verdict in ((f"A `{_cell(a)}`", x), (f"B `{_cell(b)}`", y)):
        t = verdict["table"]
        lines.append(f"| {name} | {t['both']} | {t['human_only']} | {t['judge_only']} | {t['neither']} |")
    original = {p.rating.sample_id: p.judgement for p in comparison["pairs"]}
    marked = [
        p for p in pairs if p.rating.unsupported_claim or p.judgement[VERDICT] or original[p.rating.sample_id][VERDICT]
    ]
    lines += ["", "Respostas que o humano ou algum juiz marcou como afirmação sem suporte:", ""]
    if marked:
        lines += ["| Amostra | Caso | Rota | Humano | A | B |", "| --- | --- | --- | --- | --- | --- |"]
        lines += [
            f"| {_cell(p.rating.sample_id)} | {_cell(p.rating.case_id or '-')} | {_cell(p.rating.route or '-')} | "
            f"{_yes(p.rating.unsupported_claim)} | {_yes(p.judgement[VERDICT])} | "
            f"{_yes(original[p.rating.sample_id][VERDICT])} |"
            for p in marked
        ]
    else:
        lines.append("Nenhuma.")
    lines += [
        "",
        "## Julgamentos considerados",
        "",
        "Execuções de cada juiz que entram no relatório (o `--name` do `eval` que gravou os julgamentos) e quantos "
        "julgamentos entram em cada bloco. Outras execuções do mesmo juiz sobre estas respostas, como a sonda, ficam "
        "de fora.",
        "",
        "| Juiz | Execuções | Concordância | Consistência | Custo e tokens |",
        "| --- | --- | --- | --- | --- |",
        f"| A `{_cell(a)}` | {a_runs} | {analysis['n']} | {runs['A']['judgements']} | {runs['A']['judgements']} |",
        f"| B `{_cell(b)}` | {b_runs} | {other['n']} | {runs['B']['judgements']} | {runs['B']['judgements']} |",
    ]
    if LEGACY_RUN in (runs["A"]["runs"] or []) + (runs["B"]["runs"] or []):
        lines += [
            "",
            f"`{LEGACY_RUN}`: julgamentos gravados antes da v0.9.0, que não guardam o nome da execução; contam como "
            "uma execução só, então podem somar mais de uma rodada do mesmo juiz.",
        ]
    lines += [
        "",
        "## Consistência de cada juiz entre repetições",
        "",
        "Os julgamentos `judge.v3` de cada juiz sobre estas respostas, das execuções da tabela acima. Exata: parte dos "
        "pares de julgamentos da mesma resposta com a mesma nota; ±1: diferença de até 1 ponto. Sem pares, o juiz "
        "julgou cada resposta uma vez só.",
        "",
    ]
    named = [(f"A `{_cell(a)}`", runs["A"]), (f"B `{_cell(b)}`", runs["B"])]
    return lines + _run_tables(named)


def _run_tables(named: list[tuple[str, dict]]) -> list[str]:
    """Consistency between repetitions, cost and tokens of each judge (or block) of a comparison, one row each."""
    lines = [
        "| Juiz | Respostas | Julgamentos | Falhos | Critério | Exata | ±1 | Pares |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, run in named:
        block = run["consistency"]
        head = f"| {name} | {run['answers']} | {run['judgements']} | {run['failed']}"
        for criterion in CRITERIA:
            c = block["criteria"][criterion]
            lines.append(
                f"{head} | {criterion} | {aggregate._fmt(c['exact'])} | {aggregate._fmt(c['within_one'])} | "
                f"{c['pairs']} |"
            )
        u = block["unsupported_claim"]
        lines.append(f"{head} | {VERDICT} | {aggregate._fmt(u['exact'])} | - | {u['pairs']} |")
    lines += [
        "",
        "## Custo por julgamento",
        "",
        "Custo gravado em cada julgamento (`run_evaluations.cost_usd`; um julgamento falho custa o que foi reservado "
        "ou cobrado).",
        "",
        "| Juiz | Julgamentos | Falhos | Custo total (US$) | Custo por julgamento (US$) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, run in named:
        per = "-" if run["cost_per_judgement_usd"] is None else f"{run['cost_per_judgement_usd']:.6f}"
        lines.append(f"| {name} | {run['judgements']} | {run['failed']} | {run['cost_usd']:.6f} | {per} |")
    lines += [
        "",
        "Tokens gravados em cada julgamento (desde a v0.9.0; os anteriores não os guardam), total / média por "
        "julgamento. A entrada inclui o cache lido e o criado; a saída inclui o pensamento.",
        "",
        "| Juiz | Julgamentos com tokens | Entrada | Cache lido | Cache criado | Saída |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, run in named:
        usage = run["usage"]
        if usage is None:
            lines.append(f"| {name} | 0 | - | - | - | - |")
            continue
        cells = " | ".join(f"{usage['total'][key]} / {usage['mean'][key]}" for key in TOKEN_KEYS)
        lines.append(f"| {name} | {usage['judgements']} | {cells} |")
    return lines


# --- judges and rubrics against the same human ratings (spec v0.10.0 D1, D2, CA-57) -------------------------------

# The four answers of the v0.8.0 sample in which the owner marked a general claim with no source and no judge did
# (ADR 0021). `judge.v4` adds that case to the definition of an unsupported claim; D2 counts how many a judge marks.
GENERIC_SAMPLES = ("S01", "S13", "S16", "S21")
D2_MIN_GENERIC = 2  # at least 2 of the 4 marked
D2_TOLERANCE = 0.05  # the agreement within one point of no criterion may drop by more than this
_EPSILON = 1e-9
D2_JUDGE = "deepseek/deepseek-flash"  # the default judge (ADR 0021), the one D2 lets decide


def _block_name(block: dict) -> str:
    return f"{block['label']} `{_cell(block['judge'])}` judge.v{_cell(block['rubric'])}"


def d2_rule(block: dict, baseline: dict) -> dict:
    """The three conditions of the v0.10.0 rule (D2) for a `judge.v4` block against the `judge.v3` block of the same
    judge, computed over the same human ratings. Nothing is decided here: the report shows the numbers and whether
    each condition holds; task 86 records that v4 was not promoted, and task 91 selects v5 under D6(g)."""
    now, before = block["analysis"], baseline["analysis"]
    verdict = (now["verdict"]["exact"], before["verdict"]["exact"])
    present = [p for p in block["pairs"] if p.rating.sample_id in GENERIC_SAMPLES]
    marked = sum(bool(p.judgement[VERDICT]) for p in present)
    within = {
        criterion: (now["criteria"][criterion]["within_one"], before["criteria"][criterion]["within_one"])
        for criterion in CRITERIA
    }
    holds = {
        "verdict": verdict[0] >= verdict[1] - _EPSILON,
        "generic": marked >= D2_MIN_GENERIC,
        "within_one": all(a - b >= -D2_TOLERANCE - _EPSILON for a, b in within.values()),
    }
    return {
        "verdict": verdict,
        "generic": (marked, len(present)),
        "within_one": within,
        "holds": holds,
        "all": all(holds.values()),
    }


def _baseline(blocks: list[dict], block: dict) -> dict | None:
    """The `judge.v3` block of the same judge (the original one first), the reference D2 compares a v4 block with."""
    return next((b for b in blocks if b["judge"] == block["judge"] and b["rubric"] == "3"), None)


def _compared(comparison: dict) -> str:
    """Which judgement of each answer a compared block brings: the first (repetition 1), or the majority's."""
    if not comparison.get("majority"):
        return "o julgamento da repetição 1"
    return (
        "o veredito da maioria dos julgamentos completos (`unsupported_claim` sim quando mais da metade diz sim; cada "
        "nota é a mediana; as marcas por afirmação são as do primeiro julgamento que deu o veredito da maioria)"
    )


def render_blocks(analysis: dict, comparison: dict) -> list[str]:
    """One block per (judge, execution, rubric) asked for, beside the original judge (O), against the same ratings:
    agreement per criterion, the verdict, the four general claims with no source, the D2 line, and each block's
    consistency, cost and tokens."""
    blocks = comparison["blocks"]
    n = analysis["n"]
    lines = [
        "",
        "## Juízes e rubricas contra as mesmas notas humanas",
        "",
        f"As {n} notas humanas são as gravadas na campanha original `{_cell(comparison['original_campaign'])}`, "
        "conferidas linha a linha; não houve avaliação humana nova. O é o juiz ao qual cada nota foi ligada na "
        f"campanha original; cada outro bloco entra com {_compared(comparison)} de cada resposta na execução e "
        f"sob a rubrica indicadas. As notas desta campanha (`{_cell(comparison['campaign'])}`) ficam ligadas ao "
        "bloco A. Todos julgaram a mesma evidência gravada.",
        "",
        "| Bloco | Juiz | Rubrica | Execuções |",
        "| --- | --- | --- | --- |",
    ]
    for block in blocks:
        runs = ", ".join(f"`{_cell(name)}`" for name in block["runs"] or ["-"])
        lines.append(f"| {block['label']} | `{_cell(block['judge'])}` | `judge.v{_cell(block['rubric'])}` | {runs} |")
    lines += [
        "",
        "## Concordância de cada bloco com o humano",
        "",
        "| Critério | Bloco | Exata | ±1 | Kappa quadrático | Viés (juiz − humano) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for criterion in CRITERIA:
        for block in blocks:
            m = block["analysis"]["criteria"][criterion]
            lines.append(
                f"| {criterion} ({CRITERIA_LABELS[criterion]}) | {_block_name(block)} | {_share(m['exact'], None)} | "
                f"{_share(m['within_one'], None)} | {_kappa(m)} | {_bias(m)} |"
            )
    lines += [
        "",
        "Veredito `unsupported_claim` (humano × juiz):",
        "",
        "| Bloco | Exata | Kappa | Ambos sim | Só humano | Só juiz | Nenhum |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for block in blocks:
        v = block["analysis"]["verdict"]
        t = v["table"]
        lines.append(
            f"| {_block_name(block)} | {_share(v['exact'], None)} | {_kappa(v)} | {t['both']} | {t['human_only']} | "
            f"{t['judge_only']} | {t['neither']} |"
        )
    by_block = [{p.rating.sample_id: p.judgement for p in block["pairs"]} for block in blocks]
    rated = {p.rating.sample_id: p.rating for p in blocks[0]["pairs"]}
    head = "| Amostra | Caso | Rota | Humano | " + " | ".join(block["label"] for block in blocks) + " |"
    rule = "| --- | --- | --- | --- | " + " | ".join("---" for _ in blocks) + " |"

    def row(sample_id: str) -> str:
        rating = rated[sample_id]
        marks = " | ".join(_yes(judged[sample_id][VERDICT]) for judged in by_block)
        return (
            f"| {_cell(sample_id)} | {_cell(rating.case_id or '-')} | {_cell(rating.route or '-')} | "
            f"{_yes(rating.unsupported_claim)} | {marks} |"
        )

    present = [sample_id for sample_id in GENERIC_SAMPLES if sample_id in rated]
    missing = [sample_id for sample_id in GENERIC_SAMPLES if sample_id not in rated]
    lines += [
        "",
        f"## Frases genéricas sem fonte ({', '.join(GENERIC_SAMPLES)})",
        "",
        "As quatro respostas em que o humano marcou uma frase genérica sem fonte na calibração da v0.8.0 e nenhum "
        "juiz marcou (ADR 0021). A `judge.v4` acrescenta esse caso à definição de afirmação sem suporte.",
        "",
    ]
    if present:
        counts = " | ".join(
            f"{sum(bool(judged[sample_id][VERDICT]) for sample_id in present)} de {len(present)}"
            for judged in by_block
        )
        human = sum(rated[sample_id].unsupported_claim for sample_id in present)
        lines += [head, rule, *[row(sample_id) for sample_id in present]]
        lines.append(f"| Marcadas | - | - | {human} de {len(present)} | {counts} |")
    else:
        lines.append("Nenhuma delas está neste arquivo.")
    if missing:
        lines += ["", f"Fora deste arquivo: {', '.join(missing)}."]
    marked = [
        sample_id
        for sample_id, rating in rated.items()
        if rating.unsupported_claim or any(judged[sample_id][VERDICT] for judged in by_block)
    ]
    lines += ["", "Respostas que o humano ou algum bloco marcou como afirmação sem suporte:", ""]
    lines += [head, rule, *[row(sample_id) for sample_id in marked]] if marked else ["Nenhuma."]
    lines += [
        "",
        "## Regra histórica D2 da v0.10.0 (informativa)",
        "",
        "Calculada com os números acima, sem decidir. Pela D2, a `judge.v4` vira padrão se, com o juiz padrão "
        f"(`{D2_JUDGE}`), (a) a concordância do veredito com o humano não cair, (b) pelo menos "
        f"{D2_MIN_GENERIC} das {len(GENERIC_SAMPLES)} frases genéricas forem marcadas e (c) a concordância ±1 de "
        f"nenhum critério piorar mais de {D2_TOLERANCE:.2f}; os outros juízes são reportados e não decidem. Cada "
        "bloco `judge.v4` é comparado com o bloco `judge.v3` do mesmo juiz. "
        "A decisão histórica é registrada na tarefa 86. "
        "Esta regra só se aplica à promoção de `judge.v4` sobre `judge.v3` na v0.10.0; não governa `judge.v5`, "
        "cuja promoção foi medida pela D6(g) da v0.11.0 e registrada na ADR 0023.",
        "",
    ]
    candidates = [block for block in blocks if block["rubric"] == "4"]
    if not candidates:
        lines.append("Nenhum bloco `judge.v4` para comparar com a rubrica de referência `judge.v3`.")
    for block in candidates:
        base = _baseline(blocks, block)
        if base is None:
            lines.append(
                f"- {_block_name(block)}: sem bloco `judge.v3` do mesmo juiz neste relatório; condições não "
                "calculadas."
            )
            continue
        rule_d2 = d2_rule(block, base)
        (now, before), (hits, out_of) = rule_d2["verdict"], rule_d2["generic"]
        within = ", ".join(
            f"{criterion} {a:.3f} contra {b:.3f} ({a - b:+.3f})" for criterion, (a, b) in rule_d2["within_one"].items()
        )
        holds = rule_d2["holds"]
        lines.append(
            f"- {_block_name(block)} contra {_block_name(base)}: (a) veredito {now:.3f} contra {before:.3f}, não cai: "
            f"{_yes(holds['verdict'])}; (b) frases genéricas marcadas: {hits} de {out_of}, pelo menos "
            f"{D2_MIN_GENERIC}: {_yes(holds['generic'])}; (c) ±1 {within}, nenhum piora mais de {D2_TOLERANCE:.2f}: "
            f"{_yes(holds['within_one'])}. Três condições atendidas: {_yes(rule_d2['all'])}."
        )
        others = [b for b in blocks if b is not base and b["judge"] == base["judge"] and b["rubric"] == base["rubric"]]
        if others:  # review P3-4: say which judge.v3 block of this judge is the base when there is more than one
            runs = ", ".join(f"`{_cell(name)}`" for name in base["runs"] or ["-"])
            lines.append(
                f"  - Base: {base['label']} (execução {runs}), o primeiro bloco `judge.v3` deste juiz; "
                f"{', '.join(b['label'] for b in others)} {'fica' if len(others) == 1 else 'ficam'} fora desta linha."
            )
    lines += [
        "",
        "## Julgamentos considerados",
        "",
        "Execuções de cada bloco que entram no relatório (o `--name` do `eval` que gravou os julgamentos) e quantos "
        "julgamentos entram em cada medida. Outras execuções do mesmo juiz, ou da mesma execução sob outra rubrica, "
        "ficam de fora.",
        "",
        "| Bloco | Execuções | Concordância | Consistência | Custo e tokens |",
        "| --- | --- | --- | --- | --- |",
    ]
    for block in blocks:
        runs = ", ".join(f"`{_cell(name)}`" for name in block["runs"] or ["-"])
        count = block["usage"]["judgements"]
        lines.append(f"| {_block_name(block)} | {runs} | {block['analysis']['n']} | {count} | {count} |")
    if any(LEGACY_RUN in (block["runs"] or []) for block in blocks):
        lines += [
            "",
            f"`{LEGACY_RUN}`: julgamentos gravados antes da v0.9.0, que não guardam o nome da execução; contam como "
            "uma execução só, então podem somar mais de uma rodada do mesmo juiz.",
        ]
    lines += [
        "",
        "## Consistência de cada juiz entre repetições",
        "",
        "Os julgamentos de cada bloco sobre estas respostas, do juiz, da rubrica e das execuções da tabela acima. "
        "Exata: parte dos pares de julgamentos da mesma resposta com a mesma nota; ±1: diferença de até 1 ponto. Sem "
        "pares, o juiz julgou cada resposta uma vez só.",
        "",
    ]
    return lines + _run_tables([(_block_name(block), block["usage"]) for block in blocks])


def _import_notes(removed: list[str], outside: list[str]) -> list[str]:
    """What this import did to ratings stored before, so that the database and the report say the same thing."""
    notes = []
    if removed:
        notes.append(
            f"Notas retiradas do banco por linha esvaziada neste arquivo (o arquivo é a fonte): {', '.join(removed)}."
        )
    if outside:
        notes.append(
            f"Notas já gravadas para esta campanha e avaliador que não estão neste arquivo (continuam no banco e não "
            f"entram nestes números): {', '.join(outside)}."
        )
    return notes


# --- the two commands -----------------------------------------------------------------------------------------------

BLOCK_LABELS = "ABCDEFGH"  # the blocks asked for; O is the original judge


def _rubric(rubric: str | None) -> str:
    """The stored version of a rubric ("3", "4" or "5"; `v3`, `v4` and `v5` are accepted); `None` is the configured
    default.
    The same resolution as `eval --rubric` (`judge.rubric_version`), so both commands share one default."""
    try:
        return rubric_version(rubric)
    except JudgeRefused:
        raise CalibrationError(
            f"rubrica desconhecida: {rubric!r} (use {', '.join('v' + v for v in RUBRIC_VERSIONS)})."
        ) from None


def _other_blocks(
    conn: sqlite3.Connection,
    filled: Filled,
    request_ids: list[str],
    first: tuple[str | None, str | None, str],
    extra: list[tuple[str, str | None, str]],
    majority: bool = False,
) -> list[tuple[str, str, str, list[Pair]]]:
    """The blocks after the first: each judge's execution under its rubric, linked to the same ratings (and not
    stored). A block asked twice is an error: it would count the same judgements twice."""
    if len(extra) + 1 > len(BLOCK_LABELS):
        raise CalibrationError(f"no máximo {len(BLOCK_LABELS)} blocos (--judge) por relatório.")
    seen = {first}
    blocks = []
    for name, wanted, version in extra:
        run = choose_run(conn, request_ids, name, wanted, version)
        if (name, run, version) in seen:
            raise CalibrationError(
                f"o bloco {name} na execução {run!r} sob judge.v{version} foi pedido mais de uma vez; nada foi "
                "alterado."
            )
        seen.add((name, run, version))
        blocks.append((name, run, version, link(conn, filled, name, run, version, majority=majority)))
    return blocks


def _token(text: str) -> str:
    """A name safe to put in the sample line (no `;`, `=` or spaces) and in a table cell."""
    return re.sub(r"[^\w.\-]+", "-", text).strip("-") or "campanha"


def make_sample(
    report: Path | Sequence[Path],
    size: int,
    seed: int,
    campaign: str | None = None,
    split: str = "development",
    *,
    exclude: Sequence[Path] = (),
    enrich: Sequence[str] = (),
    exact: bool = False,
) -> tuple[list[dict], dict]:
    """`eval-calibrate --sample`: the CSV rows and the sample line for `size` answers of the report, drawn from the
    development splits (`split` can narrow that to `dev` or `holdout`, or widen it with `all` to the holdout_v080)."""
    drawn, meta = draw(report, size, seed, campaign, split, exclude=exclude, enrich=enrich, exact=exact)
    return sample_rows(drawn), meta


def _load_sources(reports: Sequence[Path], splits: tuple[str, ...]) -> tuple[list[dict], str, dict[str, int]]:
    """The answers of one or more reports of the same campaign (the development run and the holdout_v080 run are two
    reports); an answer in two of them is refused."""
    rows: list[dict] = []
    left_out: dict[str, int] = {}
    seen: dict[str, str] = {}
    stems = []
    for report in reports:
        found, stem, left = load_source(report, splits)
        stems.append(stem)
        for split_name, count in left.items():
            left_out[split_name] = left_out.get(split_name, 0) + count
        for row in found:
            if row["request_id"] in seen:
                raise CalibrationError(
                    f"a requisição {row['request_id']} está em {seen[row['request_id']]} e em {report.name}: cada "
                    "--from traz respostas diferentes."
                )
            seen[row["request_id"]] = report.name
        rows += found
    return rows, stems[0], left_out


def draw(
    report: Path | Sequence[Path],
    size: int,
    seed: int,
    campaign: str | None = None,
    split: str = "development",
    *,
    exclude: Sequence[Path] = (),
    enrich: Sequence[str] = (),
    exact: bool = False,
) -> tuple[list[dict], dict]:
    """The report rows of the sample and its sample line. `report` may be several reports of one campaign (task 89
    round 2: the development run and the holdout_v080 run). `exclude` (task 89, spec v0.11.0 D5) names earlier
    calibration CSVs: their answers (request ids) stay out. `enrich` names routes that must hold at least half of the
    sample: that half is drawn first from those routes, balanced as `draw_sample` does, and the rest from every answer
    left, balanced as before. With `enrich`, or `exact` (asked by `--seal`), a draw that falls short of `size` is
    refused: nothing is written."""
    if split not in SPLIT_CHOICES:
        raise CalibrationError(f"split inválido para a amostra: {split!r} (use {', '.join(SPLIT_CHOICES)}).")
    splits = SPLIT_CHOICES[split]
    reports = [report] if isinstance(report, Path) else list(report)
    if not reports:
        raise CalibrationError("--sample precisa de pelo menos um --from <relatório>.")
    rows, stem, left_out = _load_sources(reports, splits)
    meta = {
        "campaign": _token(campaign or stem),
        "seed": seed,
        "source": "+".join(_token(path.name) for path in reports),
        "requested": size,
        "eligible": len(rows),
        "splits": "+".join(splits),
        "left_out": left_out,
    }
    if exclude:
        try:
            requests = packets.excluded_ids(exclude, _read_text)
        except packets.ClaimsError as exc:
            raise CalibrationError(exc.messages) from None
        before = len(rows)
        rows = [row for row in rows if row["request_id"] not in requests]
        meta |= {"eligible": len(rows), "excluded": before - len(rows)}
        if not rows:
            raise CalibrationError("nenhuma resposta sobra depois de --exclude: todas já foram calibradas.")
    if not enrich:
        chosen = draw_sample(rows, size, seed)
        if exact:
            _check_size(chosen, size, meta, "--seal")
        return chosen, meta
    routes = tuple(dict.fromkeys(route.strip() for route in enrich if route.strip()))
    rich = [row for row in rows if row["route"] in routes]
    half = math.ceil(size / 2)
    if len(rich) < half:
        raise CalibrationError(
            f"--enrich {','.join(routes)}: só {len(rich)} respostas elegíveis nessas rotas; a amostra de {size} "
            f"precisa de pelo menos {half} delas (metade). Nada foi gravado."
        )
    first = draw_sample(rich, half, seed)
    taken = {row["request_id"] for row in first}
    left = [row for row in rows if row["request_id"] not in taken]
    rest = draw_sample(left, size - half, seed) if size > half and left else []
    chosen = sorted([*first, *rest], key=lambda r: _rank(seed, "order", r["request_id"]))
    _check_size(chosen, size, meta, "--enrich")
    meta["enriched"] = f"{'+'.join(routes)}-{sum(row['route'] in routes for row in chosen)}"
    return chosen, meta


def _check_size(chosen: list[dict], size: int, meta: dict, option: str) -> None:
    """With `--seal` or `--enrich`, the sample has exactly the size asked for (task 89 round 2, P2-1)."""
    if len(chosen) < size:
        excluded = f", depois de excluir {meta['excluded']} já calibradas" if meta.get("excluded") else ""
        wider = "" if meta["splits"] == "+".join(ALL_SPLITS) else "; --split all inclui o holdout_v080"
        raise CalibrationError(
            f"{option}: o sorteio deu {len(chosen)} respostas, e foram pedidas {size} ({meta['eligible']} elegíveis "
            f"nos splits {meta['splits']}{excluded}). Uma amostra {'selada' if option == '--seal' else 'enriquecida'} "
            f"não sai menor que o pedido: acrescente respostas (outro --from{wider}) ou peça menos. Nada foi gravado."
        )


def import_filled(
    conn: sqlite3.Connection,
    path: Path,
    *,
    rater: str = "owner",
    campaign: str | None = None,
    now=None,
    judge: str | None = None,
    judge_run: str | None = None,
    rubric: str | None = None,
    more: Sequence[tuple[str, str | None, str | None]] = (),
    majority: bool = False,
) -> dict:
    """`eval-calibrate --import`: validates the file, stores the ratings and measures the agreement. Nothing is
    written unless every line is valid and has its judgement in `run_evaluations`.

    With `judge` (`<provider>/<model>`, spec v0.9.0 RF-108) the ratings are compared with that judge's judgements and
    stored under `campaign`, which must differ from the campaign of the file (the original one keeps its link to its
    own judge). The ratings must equal those the original campaign stored; the report then shows that campaign's judge
    beside the requested one, against the same ratings. `judge_run` names the execution of the requested judge to
    read (required when it has more than one on these answers); the original judge is read in the executions of the
    judgements its ratings are linked to.

    `rubric` (the stored version; the configured default is v5) is the rubric of the requested judge's judgements;
    `more` adds other blocks, each a `(judge, execution, rubric)` (the execution may be `None` when the judge has one
    under that rubric). With a rubric other than judge.v3 or with `more`, the report has one block per judge,
    execution and rubric beside the original judge, the table of the four general claims with no source and the D2
    line (spec v0.10.0 D2); otherwise it is the v0.9.0 report, unchanged. The ratings are linked to the first block.

    `majority` (a tool of v0.11.0 outside D6(a)) compares each requested block by the majority of its completed
    judgements of each answer (`majority_judgement`) instead of the first one; the original judge stays as linked."""
    filled = read_filled(_read_text(path))
    meta = dict(filled.meta)
    original = meta.get("campaign")
    if judge_run is not None and judge is None:
        raise CalibrationError("--judge-run só vale com --judge: escolhe a execução do juiz comparado.")
    if majority and judge is None:
        raise CalibrationError("--judge-majority só vale com --judge: é a maioria dos julgamentos do juiz comparado.")
    if (rubric is not None or more) and judge is None:
        raise CalibrationError(
            "--rubric e os blocos a mais só valem com --judge: são a rubrica de cada juiz comparado."
        )
    version = _rubric(rubric)
    extra = [(other, other_run, _rubric(other_rubric)) for other, other_run, other_rubric in more]
    for name in [judge, *(other for other, _, _ in extra)] if judge is not None else []:
        if name.count("/") != 1 or not all(name.split("/")):
            raise CalibrationError(f"--judge precisa ser <provedor>/<modelo>, recebi {name!r}.")
    if judge is not None:
        if not original:
            raise CalibrationError(
                "com --judge, o arquivo precisa da linha 'amostra:' com a campanha original (a das notas humanas)."
            )
        if not campaign or _token(campaign) == original:
            raise CalibrationError(
                f"com --judge, informe --campaign com um nome novo (diferente de {original!r}): a campanha original "
                "continua ligada ao seu juiz."
            )
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
    before = original_pairs(conn, original, rater, filled.ratings) if judge is not None else None
    request_ids = [rating.request_id for rating in filled.ratings]
    run = choose_run(conn, request_ids, judge, judge_run, version) if judge is not None else None
    pairs = link(conn, filled, judge, run, version if judge is not None else None, majority=majority)
    others = _other_blocks(conn, filled, request_ids, (judge, run, version), extra, majority)
    check_same_sample(conn, meta["campaign"], rater, pairs)
    stored = store(conn, meta["campaign"], rater, pairs, filled.blank)
    seed = int(meta["seed"]) if str(meta.get("seed", "")).lstrip("-").isdigit() else DEFAULT_SEED
    analysis = analyze(pairs, seed)
    comparison = None
    if before is not None:
        original_judge = ", ".join(sorted({p.judgement["judge"] for p in before}))
        original_runs = sorted({p.judgement["run"] for p in before})
        original_rubrics = sorted({p.judgement["rubric_version"] for p in before})
        original_rubric = ", ".join(original_rubrics)
        original_version = original_rubrics[0] if len(original_rubrics) == 1 else None
        comparison = {
            "judge": judge,
            "judge_run": run,
            "majority": majority,
            "campaign": meta["campaign"],
            "original_judge": original_judge,
            "original_runs": original_runs,
            "original_campaign": original,
            "pairs": before,
            "analysis": analyze(before, seed),
            "runs": {
                "A": judge_runs(conn, request_ids, judge, [run], version),
                "B": judge_runs(conn, request_ids, original_judge, original_runs, original_version),
            },
        }
        if extra or version != "3":
            asked = [(judge, run, version, pairs), *others]
            comparison |= {
                "rubric": version,
                "blocks": [
                    {
                        "label": "O",
                        "judge": original_judge,
                        "rubric": original_rubric,
                        "runs": original_runs,
                        "pairs": before,
                        "analysis": comparison["analysis"],
                        "usage": comparison["runs"]["B"],
                    },
                    *[
                        {
                            "label": BLOCK_LABELS[index],
                            "judge": name,
                            "rubric": block_rubric,
                            "runs": [block_run],
                            "pairs": block_pairs,
                            "analysis": analysis if index == 0 else analyze(block_pairs, seed),
                            "usage": judge_runs(conn, request_ids, name, [block_run], block_rubric),
                        }
                        for index, (name, block_run, block_rubric, block_pairs) in enumerate(asked)
                    ],
                ],
            }
    return {
        "meta": meta,
        "rater": rater,
        "counts": stored.counts(),
        "skipped": filled.skipped,
        "removed": stored.removed,
        "outside": stored.outside,
        "analysis": analysis,
        "comparison": comparison,
        "report": render_report(
            meta,
            rater,
            pairs,
            analysis,
            skipped=filled.skipped,
            removed=stored.removed,
            outside=stored.outside,
            now=now,
            comparison=comparison,
        ),
    }


# --- two raters, the gold label and the claims (spec v0.11.0 D4, D5, D6; task 89) ----------------------------------

D6_KAPPA = 0.6  # D6(g): the verdict's kappa against the gold label on the sealed answers
D6_TOLERANCE = 0.05  # D6(g): the agreement within one point of no criterion may drop by more than this
GOLD = "ouro"
MARK_CODES = {verdict: index for index, verdict in enumerate(CLAIM_VERDICTS)}
UNSUPPORTED_MARKS = frozenset({"generic", "not_found"})
CLAIM_TEXT_CHARS = 90  # a claim is cut to this length in the report's tables
ADJUDICATION_REQUIRED = ("request_id", "gold_verdict", "gold_scores", "reason")
_PUNCTUATION = re.compile(r"[^\w\s]")
CLAIMS_FROM_SAMPLE = "amostra:"  # the origin a judgement records when its claims came from `eval --claims-from`


@dataclass
class RaterFiles:
    """One `--rater <name>:human|model:<models> <sample.csv> [<sample-claims.csv>]`; `kind` is `human` or
    `model:<models>` (None when the rater declared no kind, which two raters may not do)."""

    name: str
    sample: Path
    claims: Path | None = None
    kind: str | None = None


HUMAN = "human"
MODEL = "model"
_MODELS = re.compile(r"[A-Za-z0-9._/+,-]+")
KIND_FORMAT = "--rater <nome>:human ou --rater <nome>:model:<modelos> (por exemplo painel:model:claude-opus+gpt-5)"


def parse_rater(text: str) -> tuple[str, str | None]:
    """`lauro` (no kind: the v0.8.0 form), `lauro:human` or `painel:model:<models>` (spec v0.11.0 D4, D6(c), Q22):
    the name and the kind (`human`, `model:<models>` or None). The models of a panel are put in alphabetical order and
    joined by `+` (task 89 round 4), so `model:b+a` and `model:a,b` are the same panel and are stored the same way. A
    panel is exactly two different models (D6(c); task 89 round 5)."""
    name, sep, kind = text.strip().partition(":")
    name = name.strip()
    if not sep:
        return name, None
    kind = kind.strip()
    if kind == HUMAN:
        return name, HUMAN
    family, _, models = kind.partition(":")
    if family == MODEL and _MODELS.fullmatch(models.strip()):
        listed = [model for model in re.split(r"[+,]", models.strip()) if model]
        if not listed or len({model.casefold() for model in listed}) != len(listed):
            raise CalibrationError(
                f"--rater {text.strip()!r}: um rotulador model declara os modelos, cada um uma vez ({KIND_FORMAT})."
            )
        if len(listed) != 2:
            raise CalibrationError(
                f"--rater {text.strip()!r}: o painel model declara exatamente dois modelos, recebi {len(listed)} "
                f"({KIND_FORMAT})."
            )
        return name, f"{MODEL}:{'+'.join(sorted(listed, key=lambda model: (model.casefold(), model)))}"
    if family == MODEL:
        raise CalibrationError(
            f"--rater {text.strip()!r}: um rotulador model declara os modelos, sem espaços ({KIND_FORMAT})."
        )
    raise CalibrationError(f"--rater {text.strip()!r}: tipo {kind!r} desconhecido; use {KIND_FORMAT}.")


def stored_rater(name: str, kind: str | None) -> str:
    """What `calibrations.rater` keeps: the name of a human rater as it always was (a v0.8.0 rating has no kind and is
    a human one), `<name>:model:<models>` for a model rater, so its ratings are never read back as human ones."""
    return f"{name}:{kind}" if kind and kind != HUMAN else name


def is_model(kind: str | None) -> bool:
    return bool(kind) and kind.startswith(f"{MODEL}:")


def kind_word(kind: str | None) -> str:
    """How the report names a rater's side: `humano`, or `painel` for a model rater (one or more models, declared)."""
    return "painel" if is_model(kind) else "humano"


def kind_text(kind: str | None) -> str:
    if not is_model(kind):
        return "humano"
    models = [m for m in re.split(r"[+,]", kind.split(":", 1)[1]) if m]
    return "painel de modelos: " + " + ".join(f"`{_cell(m)}`" for m in models)


@dataclass
class Label:
    """What one rater said about one answer."""

    rater: str
    campaign: str
    rating: Rating
    claims: packets.AnswerClaims | None  # None when the rater returned no claims CSV for it
    sealed: bool


def _prefixed(name: str, messages: list[str]) -> list[str]:
    return [f"{name}: {message}" for message in messages]


def _check_marks(filled: Filled, marks: dict[str, packets.AnswerClaims], *, complete: bool = True) -> list[str]:
    """The claims CSV answers the rows of the sample CSV: every claim of a rated answer is marked (unless not
    `complete`: a panel leaves blank the claims its two members marked apart), an answer left without ratings has no
    marks, and no claim belongs to an answer the sample does not have."""
    problems = []
    rows = {row["request_id"]: row["sample_id"] for row in filled.rows}
    rated = {rating.request_id for rating in filled.ratings}
    for request_id, answer in marks.items():
        if request_id not in rows:
            problems.append(f"{answer.sample_id}: a requisição {request_id} não está no CSV de notas.")
            continue
        if rows[request_id] != answer.sample_id:
            problems.append(f"{answer.sample_id}: no CSV de notas a requisição {request_id} é {rows[request_id]}.")
        if request_id in rated and complete:
            blank = [str(claim.n) for claim in answer.claims if not claim.verdict]
            if blank:
                problems.append(f"{answer.sample_id}: falta a marca das afirmações {', '.join(blank)}.")
        elif request_id not in rated and answer.marked():
            problems.append(
                f"{answer.sample_id}: há marcas de afirmação, mas a resposta não tem notas no CSV de notas; preencha "
                "as notas ou apague as marcas."
            )
    return problems


def _entries(filled: Filled, marks: dict[str, packets.AnswerClaims]) -> list[dict]:
    """The entries of the seal, rebuilt from the files a rater returned."""
    entries = []
    for row in filled.rows:
        answer = marks.get(row["request_id"])
        claims = [{"n": c.n, "kind": c.kind, "text": c.text} for c in answer.claims] if answer else []
        entries.append({**row, "claims": claims})
    return entries


def read_rater(entry: RaterFiles, seal_path: Path | None) -> tuple[str, Filled, dict | None, bool]:
    """One rater's files: the campaign of the sample, the ratings (with the verdict computed from the marks when the
    claims CSV is given), the marks by request id and whether the sample is the sealed one, its hash checked. A model
    rater (a panel) may leave blank what its two members did not agree on (`merge_panel`, task 89 round 4); its
    verdict comes from its `unsupported_claim` column alone, blank when the members differ (None, never computed from
    the marks: the members may differ by a claim one of them added), and its marks only check it (task 89 round 5)."""
    panel = is_model(entry.kind)
    try:
        filled = read_filled(_read_text(entry.sample), verdict_optional=entry.claims is not None, partial=panel)
    except CalibrationError as exc:
        raise CalibrationError(_prefixed(entry.sample.name, exc.messages)) from None
    errors: list[str] = []
    campaign = filled.meta.get("campaign", "")
    if not campaign:
        errors.append(f"{entry.sample.name}: falta a linha 'amostra:' com a campanha; use o arquivo de --sample.")
    marks = None
    seal = filled.meta.get("seal", "")
    if entry.claims is not None:
        try:
            claims_file = packets.read_claims(_read_text(entry.claims), META_KEYS)
        except packets.ClaimsError as exc:
            raise CalibrationError(_prefixed(entry.claims.name, exc.messages)) from None
        marks = claims_file.answers
        errors += packets.verify_claims(claims_file, entry.claims.name)
        errors += _prefixed(entry.claims.name, _check_marks(filled, marks, complete=not panel))
        if claims_file.meta.get("campaign", campaign) != campaign:
            errors.append(
                f"{entry.claims.name}: a campanha {claims_file.meta['campaign']!r} não é a do CSV de notas "
                f"({campaign!r}): são amostras diferentes."
            )
        seal = seal or claims_file.meta.get("seal", "")
    if seal and seal != packets.SEAL_NAME:
        errors.append(f"{entry.sample.name}: selo desconhecido {seal!r} (o desta versão é {packets.SEAL_NAME}).")
    sealed = seal == packets.SEAL_NAME
    if sealed:
        errors += _check_seal(entry, filled, marks, seal_path)
    if errors:
        raise CalibrationError(errors)
    if marks is not None:
        ratings = []
        for rating in filled.ratings:
            answer = marks.get(rating.request_id)
            derived = _derived(answer) if panel else (answer.unsupported() if answer else False)
            typed = rating.unsupported_claim
            # a panel's typed verdict is the one its two members agreed on; only a mark both gave can contradict it
            if typed is not None and derived is not None and typed != derived and (not panel or derived):
                hint = (
                    "O veredito do painel vem da coluna: refaça a junção dos membros (--merge-panel)."
                    if panel
                    else "Deixe a coluna vazia (o veredito vem das marcas) ou corrija as marcas."
                )
                errors.append(
                    f"{entry.sample.name}, linha {rating.line} ({rating.sample_id}): unsupported_claim diz "
                    f"{_yes(typed)}, e as marcas das afirmações dão {_yes(derived)}. {hint}"
                )
            # the panel's verdict is its column (None when blank); the human's is computed from the marks
            ratings.append(replace(rating, unsupported_claim=typed if panel else derived))
        if errors:
            raise CalibrationError(errors)
        filled = replace(filled, ratings=ratings)
    return campaign, filled, marks, sealed


def _derived(answer: packets.AnswerClaims | None) -> bool | None:
    """What a panel's marks say of its verdict, only to check the verdict typed in its column (task 89 round 5): yes
    when a claim that is not `standard` has a mark against the answer, no when every such claim is marked and none is,
    None while one of them is blank."""
    if answer is None:
        return False
    if answer.unsupported():
        return True
    return None if any(not c.verdict and c.kind != "standard" for c in answer.claims) else False


def _check_seal(entry: RaterFiles, filled: Filled, marks: dict | None, seal_path: Path | None) -> list[str]:
    if marks is None:
        return [
            f"{entry.sample.name}: a amostra é a selada ({packets.SEAL_NAME}); entregue também o CSV de afirmações "
            "(--rater <nome> <sample.csv> <sample-claims.csv>), que faz parte do selo."
        ]
    try:
        expected = packets.read_seal(seal_path) if seal_path is not None else None
    except packets.ClaimsError as exc:
        return exc.messages
    if expected is None:
        return [f"{entry.sample.name}: a amostra diz ser a selada, e não há selo em {packets.SEAL_FILE.as_posix()}."]
    found = packets.seal_digest(_entries(filled, marks))
    if found != expected:
        return [
            f"{entry.sample.name}: o SHA-256 da amostra devolvida ({found[:12]}…) não é o do selo ({expected[:12]}…): "
            "alguma resposta, identidade ou afirmação mudou depois do selo. Nada foi gravado."
        ]
    return []


def read_adjudication(path: Path) -> dict[str, dict]:
    """`--adjudication <csv>`: `request_id`, `gold_verdict` (sim/nao), `gold_scores` (`criterion=value` pairs),
    `reason` and, optionally, `gold_claims` (`n=mark` pairs). Every row needs a reason and at least one gold field."""
    text = _read_text(path).lstrip("\ufeff")
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not lines:
        raise CalibrationError(f"{path.name}: arquivo de adjudicação vazio.")
    delimiter = max(DELIMITERS, key=lambda d: lines[0].count(d))
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    header: list[str] | None = None
    found: dict[str, dict] = {}
    errors: list[str] = []
    last = 0
    for cells in reader:
        start, last = last + 1, reader.line_num
        cells = [cell.strip() for cell in cells]
        if not any(cells) or cells[0].startswith("#"):
            continue
        if header is None:
            header = [_plain(cell) for cell in cells]
            missing = [column for column in ADJUDICATION_REQUIRED if column not in header]
            if missing:
                raise CalibrationError(f"{path.name}, linha {start}: faltam as colunas {', '.join(missing)}.")
            continue
        values = dict(zip(header, cells, strict=False))
        row, problems = _adjudicated_row(values)
        request_id = values.get("request_id", "")
        if request_id in found:
            problems.append(f"request_id repetido (já na linha {found[request_id]['line']})")
        if problems:
            errors.append(f"{path.name}, linha {start} ({request_id or 'sem request_id'}): {'; '.join(problems)}.")
        else:
            found[request_id] = row | {"line": start}
    if errors:
        raise CalibrationError(errors)
    return found


def _adjudicated_row(values: dict[str, str]) -> tuple[dict, list[str]]:
    problems = []
    if not values.get("request_id"):
        problems.append("request_id vazio")
    verdict = None
    raw = values.get("gold_verdict", "")
    if raw:
        if _plain(raw) in _YES | _NO:
            verdict = _plain(raw) in _YES
        else:
            problems.append(f"gold_verdict precisa ser sim ou nao, recebi {raw!r}")
    scores: dict[str, int] = {}
    for token in re.split(r"[\s,;]+", values.get("gold_scores", "")):
        if not token:
            continue
        name, _, value = token.partition("=")
        if name not in CRITERIA or value not in {str(point) for point in SCALE}:
            problems.append(f"gold_scores: {token!r} não é critério=nota (critérios {', '.join(CRITERIA)}; 1 a 5)")
        else:
            scores[name] = int(value)
    claims: dict[int, str] = {}
    for token in re.split(r"[\s,;]+", values.get("gold_claims", "")):
        if not token:
            continue
        number, _, mark = token.partition("=")
        if not number.isdigit() or packets.mark_of(mark) is None:
            problems.append(f"gold_claims: {token!r} não é n=marca (supported, partial, generic, not_found)")
        else:
            claims[int(number)] = packets.mark_of(mark)
    reason = values.get("reason", "")
    if verdict is None and not scores and not claims and not problems:
        problems.append("nenhum rótulo ouro (gold_verdict, gold_scores ou gold_claims)")
    if not reason:
        problems.append("reason vazio: a adjudicação diz por quê")
    return {"verdict": verdict, "scores": scores, "claims": claims, "reason": reason}, problems


def _gold(
    request_id: str, first: Label | None, second: Label | None, adjudicated: dict | None
) -> tuple[dict | None, list[str]]:
    """The gold label of one answer: the adjudicated value, else the value both raters gave. A divergence without an
    adjudicated value is an error; an answer only one rater rated has gold only when the adjudication gives all of it.
    Claim marks: adjudicated, else the mark both raters gave (a claim marked by one rater only has none)."""
    adjudicated = adjudicated or {"verdict": None, "scores": {}, "claims": {}}
    both = first is not None and second is not None
    scores: dict[str, int] = {}
    diverging: list[str] = []
    for criterion in CRITERIA:
        ours = first.rating.scores.get(criterion) if both else None
        theirs = second.rating.scores.get(criterion) if both else None
        if criterion in adjudicated["scores"]:
            scores[criterion] = adjudicated["scores"][criterion]
        elif both and ours is not None and ours == theirs:
            scores[criterion] = ours
        elif both:  # a value one side left blank (a panel whose members diverged) needs the adjudication too
            diverging.append(f"{criterion} {_given(ours)} × {_given(theirs)}")
    verdict = adjudicated["verdict"]
    if verdict is None and both:
        ours, theirs = first.rating.unsupported_claim, second.rating.unsupported_claim
        if ours is not None and ours == theirs:
            verdict = ours
        else:
            diverging.append(f"{VERDICT} {_given(ours)} × {_given(theirs)}")
    if diverging:
        return None, diverging
    if verdict is None or len(scores) < len(CRITERIA):
        return None, []
    marks = dict(adjudicated["claims"])
    if both and first.claims is not None and second.claims is not None:
        theirs = {claim.n: claim.verdict for claim in second.claims.claims}
        for claim in first.claims.claims:
            if claim.n not in marks and claim.verdict and theirs.get(claim.n) == claim.verdict:
                marks[claim.n] = claim.verdict
    return {"scores": scores, "unsupported_claim": verdict, "claims": marks}, []


def _given(value) -> str:
    """A rater's value in a divergence: the score, sim/não, or `sem rótulo` when it left it blank."""
    if value is None:
        return "sem rótulo"
    return _yes(value) if isinstance(value, bool) else str(value)


def _block_judgements(
    conn: sqlite3.Connection, answers: list[str], judge: str | None, runs: tuple[str, ...] | None, rubric: str | None
) -> tuple[dict[str, dict], list[str]]:
    """The first judgement (repetition 1) of each answer in the block. With several executions (`a+b`, the 24 and
    the 36 graded apart), each answer must be in exactly one of them."""
    found: dict[str, dict] = {}
    errors = []
    by = f" do juiz {judge}" if judge else ""
    by += f" sob judge.v{rubric}" if rubric else ""
    for request_id in answers:
        options = (
            [j for run in runs if (j := judgement_for(conn, request_id, judge, run, rubric))]
            if runs
            else [j for j in [judgement_for(conn, request_id, judge, None, rubric)] if j]
        )
        if not options:
            where = f" nas execuções {', '.join(runs)}" if runs else ""
            errors.append(f"não há julgamento{by}{where} da requisição {request_id} em run_evaluations deste banco.")
        elif len(options) > 1:
            errors.append(
                f"a requisição {request_id} tem julgamento{by} em mais de uma das execuções "
                f"{', '.join(j['run'] for j in options)}; escolha uma."
            )
        else:
            found[request_id] = options[0]
    return found, errors


def _resolve_blocks(
    conn: sqlite3.Connection, answers: list[str], blocks: Sequence[tuple[str | None, str | None, str | None]]
) -> list[dict]:
    """One block per `--judge` (with `--judge-run`, which may join executions with `+`, and `--rubric`); without
    `--judge`, one block with the first judgement of any judge, as in v0.8.0."""
    asked = list(blocks) or [(None, None, None)]
    if len(asked) > len(BLOCK_LABELS):
        raise CalibrationError(f"no máximo {len(BLOCK_LABELS)} blocos (--judge) por relatório.")
    resolved, errors, seen = [], [], set()
    for index, (judge, run, rubric) in enumerate(asked):
        if judge is not None and (judge.count("/") != 1 or not all(judge.split("/"))):
            raise CalibrationError(f"--judge precisa ser <provedor>/<modelo>, recebi {judge!r}.")
        version = _rubric(rubric) if judge is not None else None
        runs = tuple(part for part in run.split("+") if part) if run else None
        if judge is not None:
            if runs:
                for name in runs:
                    choose_run(conn, answers, judge, name, version)
            else:
                only = choose_run(conn, answers, judge, None, version)
                runs = (only,) if only else None
        key = (judge, runs, version)
        if key in seen:
            raise CalibrationError(f"o bloco {judge} {runs} judge.v{version} foi pedido mais de uma vez.")
        seen.add(key)
        judgements, missing = _block_judgements(conn, answers, judge, runs, version)
        errors += missing
        names = sorted({j["judge"] for j in judgements.values()})
        rubrics = sorted({j["rubric_version"] for j in judgements.values()})
        found_runs = sorted({j["run"] for j in judgements.values()})
        name = judge or ", ".join(names)
        usage = None
        if len(names) == 1 and len(rubrics) == 1:
            usage = judge_runs(conn, answers, names[0], found_runs, rubrics[0])
        resolved.append(
            {
                "label": BLOCK_LABELS[index],
                "judge": name,
                "rubric": version or ", ".join(rubrics),
                "runs": list(runs) if runs else found_runs,
                "judgements": judgements,
                "usage": usage,
            }
        )
    if errors:
        raise CalibrationError(errors)
    return resolved


def ensembles(blocks: list[dict]) -> list[dict]:
    """D6(f): every pair of blocks of two different judges under the same rubric, computed from their recorded
    judgements without a call. The verdict is yes only when both judges say yes; the scores are those of the first
    block (the ensemble changes the verdict only); the cost per judgement is the sum of both."""
    out = []
    for i, first in enumerate(blocks):
        for second in blocks[i + 1 :]:
            if first["judge"] == second["judge"] or first["rubric"] != second["rubric"]:
                continue
            judgements = {
                request_id: {
                    "scores": judged["scores"],
                    VERDICT: judged[VERDICT] and second["judgements"][request_id][VERDICT],
                    "claims": None,
                }
                for request_id, judged in first["judgements"].items()
            }
            costs = [block["usage"]["cost_per_judgement_usd"] if block["usage"] else None for block in (first, second)]
            out.append(
                {
                    "label": f"{first['label']}+{second['label']}",
                    "judge": f"{first['judge']} + {second['judge']}",
                    "rubric": first["rubric"],
                    "judgements": judgements,
                    "cost_per_judgement_usd": None if None in costs else round(sum(costs), 6),
                }
            )
    return out


def agreement(first: list[dict], second: list[dict], seed: int) -> dict:
    """Per criterion and for the verdict, as `analyze`, between any two sides (a rater, the gold label, a judge)."""
    if not first:
        return {"n": 0}
    criteria = {}
    for criterion in CRITERIA:  # a panel may have no score where its members diverged: that answer is out of this n
        kept = [
            (int(x["scores"][criterion]), int(y["scores"][criterion]))
            for x, y in zip(first, second, strict=True)
            if criterion in x["scores"] and criterion in y["scores"]
        ]
        criteria[criterion] = _measure([a for a, _ in kept], [b for _, b in kept], SCALE, seed, close=True)
    given = [(x, y) for x, y in zip(first, second, strict=True) if x[VERDICT] is not None and y[VERDICT] is not None]
    said = [int(bool(x[VERDICT])) for x, _ in given]
    other = [int(bool(y[VERDICT])) for _, y in given]
    verdict = _measure(said, other, (0, 1), seed, close=False)
    verdict["table"] = {
        "both": sum(a and b for a, b in zip(said, other, strict=True)),
        "first_only": sum(a and not b for a, b in zip(said, other, strict=True)),
        "second_only": sum(b and not a for a, b in zip(said, other, strict=True)),
        "neither": sum(not a and not b for a, b in zip(said, other, strict=True)),
    }
    return {"n": len(first), "criteria": criteria, VERDICT: verdict}


def claim_agreement(first: list[str], second: list[str], seed: int) -> dict:
    """Agreement on the claim marks (n = claims): the four marks as categories with no order (Cohen's kappa), and
    the mark that counts against the answer (generic or not_found) against the rest."""
    n = len(first)
    if not n:
        return {"n": 0}
    a, b = [MARK_CODES[m] for m in first], [MARK_CODES[m] for m in second]
    categories = tuple(range(len(CLAIM_VERDICTS)))
    kappa = cohen_kappa(a, b, categories)
    exact = sum(x == y for x, y in zip(a, b, strict=True))
    marks = {
        "n": n,
        "exact": exact / n,
        "exact_ci": wilson(exact, n),
        "kappa": kappa,
        "kappa_ci": kappa_interval(a, b, categories, seed, cohen_kappa) if kappa is not None else None,
        "kappa_note": kappa_note(a, b, kappa),
        "interval_note": None,
    }
    unsupported = _measure(
        [int(m in UNSUPPORTED_MARKS) for m in first], [int(m in UNSUPPORTED_MARKS) for m in second], (0, 1), seed,
        close=False,
    )
    return {"n": n, "marks": marks, "unsupported": unsupported}


def _claim_key(text: str) -> str:
    return " ".join(_PUNCTUATION.sub(" ", text.casefold()).split())


def judged_marks(claims: list[packets.ClaimMark], judged: dict | None) -> dict[int, str]:
    """The judge's verdict on each claim of the sample. A judgement made with the sample's own list (`eval
    --claims-from`, task 89 round 2) has the same number and text for each claim and pairs them all. A judge.v5
    judgement that listed the claims again is matched by text (case, punctuation and spacing aside), whatever its
    order: a claim it phrased otherwise has no pair and stays out."""
    if not judged:
        return {}
    verdicts = {verdict["n"]: verdict["verdict"] for verdict in judged.get("claim_verdicts", [])}
    listed = judged.get("claims", [])
    by_number = {claim["n"]: _claim_key(claim["text"]) for claim in listed}
    used: set[int] = set()
    matched: dict[int, int] = {}
    for claim in claims:  # the same number with the same text: the judge read this very claim
        if by_number.get(claim.n) == _claim_key(claim.text):
            matched[claim.n] = claim.n
            used.add(claim.n)
    pool: dict[str, list[int]] = {}
    for claim in listed:
        if claim["n"] not in used:
            pool.setdefault(_claim_key(claim["text"]), []).append(claim["n"])
    for claim in claims:
        numbers = pool.get(_claim_key(claim.text)) if claim.n not in matched else None
        if numbers:
            matched[claim.n] = numbers.pop(0)
    return {n: verdicts[number] for n, number in matched.items() if verdicts.get(number)}


def from_sample(judged: dict | None) -> bool:
    """Whether a judge.v5 judgement was made with the claims of a calibration sample (`eval --claims-from`)."""
    return bool(judged) and str(judged.get("origin", "")).startswith(CLAIMS_FROM_SAMPLE)


def _sides(names: list[str], kinds: dict[str, str]) -> dict[str, str]:
    """How the report names each rater: by its kind (`humano`, `painel`), with the name too when both are of one
    kind. A model rater is never named `humano`."""
    words = {name: kind_word(kinds.get(name)) for name in names}
    if len(set(words.values())) == len(names):
        return words
    return {name: f"{words[name]} {name}" for name in names}


def judge_side(candidate: dict) -> str:
    """A block is `juiz A`; an ensemble of two blocks is `ensemble B+C`."""
    return f"{'ensemble' if '+' in candidate['label'] else 'juiz'} {candidate['label']}"


def gold_pair(candidate: dict) -> str:
    return f"{GOLD} × {judge_side(candidate)}"


def _scope(
    ids: list[str],
    names: list[str],
    labels: dict[str, dict[str, Label]],
    gold: dict[str, dict],
    blocks: list[dict],
    combined: list[dict],
    seed: int,
    sides: dict[str, str],
) -> dict:
    """Every measure of one block of answers (the sealed ones, or all of them). Each pair is named by the kind of its
    sides (`sides`: humano or painel, with the name when both raters are of one kind)."""
    first, second = names
    a, b = labels[first], labels[second]

    def side(label: Label) -> dict:
        return {"scores": label.rating.scores, VERDICT: label.rating.unsupported_claim}

    def measure(name: str, ours: dict, theirs: dict, keep: list[str], mine) -> None:
        pairs.append((name, agreement([mine(ours[i]) for i in keep], [theirs[i] for i in keep], seed)))

    pairs: list[tuple[str, dict]] = []
    both = [i for i in ids if i in a and i in b]
    raters = f"{sides[first]} × {sides[second]}"
    pairs.append((raters, agreement([side(a[i]) for i in both], [side(b[i]) for i in both], seed)))
    golden = [i for i in ids if i in gold]
    for block in blocks:
        for name, own in ((first, a), (second, b)):
            rated = [i for i in ids if i in own]
            measure(f"{sides[name]} × {judge_side(block)}", own, block["judgements"], rated, side)
        measure(gold_pair(block), gold, block["judgements"], golden, dict)
    for ensemble in combined:
        measure(gold_pair(ensemble), gold, ensemble["judgements"], golden, dict)
    # claim by claim
    human_marks: tuple[list[str], list[str]] = ([], [])
    for i in both:
        if a[i].claims is None or b[i].claims is None:
            continue
        theirs = {claim.n: claim.verdict for claim in b[i].claims.claims}
        for claim in a[i].claims.claims:
            if claim.verdict and theirs.get(claim.n):
                human_marks[0].append(claim.verdict)
                human_marks[1].append(theirs[claim.n])
    claim_pairs = [(raters, claim_agreement(*human_marks, seed), 0)]
    claims_from: list[tuple[str, int, int]] = []
    listing = {i: next((x[i].claims for x in (a, b) if i in x and x[i].claims is not None), None) for i in ids}
    for block in blocks:
        if not any(j.get("claims") for j in block["judgements"].values()):
            continue
        golden_marks: tuple[list[str], list[str]] = ([], [])
        unpaired = 0
        for i in golden:
            claims = listing.get(i)
            if claims is None:
                continue
            judged = judged_marks(claims.claims, block["judgements"][i].get("claims"))
            for claim in claims.claims:
                mark = gold[i]["claims"].get(claim.n)
                if mark is None:
                    continue
                if claim.n in judged:
                    golden_marks[0].append(mark)
                    golden_marks[1].append(judged[claim.n])
                else:
                    unpaired += 1
        claim_pairs.append((gold_pair(block), claim_agreement(*golden_marks, seed), unpaired))
        given = sum(from_sample(block["judgements"][i].get("claims")) for i in ids if i in block["judgements"])
        if given:
            claims_from.append((block["label"], given, sum(i in block["judgements"] for i in ids)))
    golden_claims = sum(len(gold[i]["claims"]) for i in golden)
    listed_claims = sum(len(listing[i].claims) for i in ids if listing.get(i) is not None)
    return {
        "ids": ids,
        "n": len(ids),
        "both": len(both),
        "gold": len(golden),
        "pairs": pairs,
        "claim_pairs": claim_pairs,
        "claims_listed": listed_claims,
        "claims_gold": golden_claims,
        "listing": listing,
        "claims_from": claims_from,
    }


def d6_rule(scope: dict, blocks: list[dict], combined: list[dict]) -> dict | None:
    """D6(g) computed, not decided: for each candidate (each block and each ensemble), the verdict's kappa against the
    gold label on the sealed answers (at least D6_KAPPA) and, per criterion, the agreement within one point against
    that of the D6 baseline (`judge.v3` with D2_JUDGE), which no candidate may lower by more than D6_TOLERANCE. None
    when no sealed answer has a gold label."""
    if not scope["gold"]:
        return None
    measured = dict(scope["pairs"])
    base = next((b for b in blocks if b["judge"] == D2_JUDGE and b["rubric"] == "3"), None)
    base_within = (
        {c: measured[gold_pair(base)]["criteria"][c]["within_one"] for c in CRITERIA} if base else None
    )
    rows = []
    for candidate in [*blocks, *combined]:
        m = measured[gold_pair(candidate)]
        kappa = m[VERDICT]["kappa"]
        within = {c: m["criteria"][c]["within_one"] for c in CRITERIA}
        cost = (
            candidate.get("cost_per_judgement_usd")
            if "cost_per_judgement_usd" in candidate
            else (candidate["usage"] or {}).get("cost_per_judgement_usd")
        )
        holds_kappa = kappa is not None and kappa >= D6_KAPPA - _EPSILON
        holds_within = (
            None
            if base_within is None
            else all(within[c] - base_within[c] >= -D6_TOLERANCE - _EPSILON for c in CRITERIA)
        )
        rows.append(
            {
                "candidate": candidate,
                "kappa": kappa,
                "kappa_ci": m[VERDICT]["kappa_ci"],
                "within": within,
                "holds_kappa": holds_kappa,
                "holds_within": holds_within,
                "cost": cost,
                "both": holds_kappa and bool(holds_within),
            }
        )
    return {"base": base, "base_within": base_within, "rows": rows, "n": scope["gold"]}


def import_raters(
    conn: sqlite3.Connection,
    entries: Sequence[RaterFiles],
    *,
    adjudication: Path | None = None,
    blocks: Sequence[tuple[str | None, str | None, str | None]] = (),
    seal_path: Path | None = None,
    now: datetime | None = None,
) -> dict:
    """`eval-calibrate --import --rater <name> <sample.csv> [<sample-claims.csv>] ...` with two raters (spec v0.11.0
    D4): validates every file, the seal of the sealed sample and the adjudication; stores each rater's ratings in
    `calibrations` (one transaction, under the campaign of each file, linked to the first block's judgement); measures
    rater × rater, each rater × each judge and gold × each judge, per criterion, for the verdict and claim by claim, for
    the sealed answers and for all; and writes the report. Nothing is written unless everything is valid."""
    errors: list[str] = []
    read = []
    kinds: dict[str, str] = {}
    undeclared: set[str] = set()
    for entry in entries:
        name = entry.name.strip()
        if not name or name.casefold() == GOLD:
            errors.append(f"o nome do rotulador (--rater) não pode ficar vazio nem ser {GOLD!r}.")
            continue
        if ":" in name:  # `calibrations.rater` keeps `<name>:model:<models>`: a name with `:` would read as a kind
            errors.append(f"--rater {name}: o nome do rotulador não pode ter ':'; o tipo vem depois: {KIND_FORMAT}.")
            continue
        if entry.kind is None:
            if name not in undeclared:
                errors.append(f"--rater {name}: com dois rotuladores, cada um declara o tipo: {KIND_FORMAT}.")
            undeclared.add(name)
            continue
        if kinds.setdefault(name, entry.kind) != entry.kind:
            errors.append(f"--rater {name}: declarado como {kinds[name]} e como {entry.kind}; um rotulador, um tipo.")
            continue
        try:
            read.append((name, entry, *read_rater(entry, seal_path)))
        except CalibrationError as exc:
            errors += exc.messages
    if errors:
        raise CalibrationError(errors)
    names = list(dict.fromkeys(name for name, *_ in read))
    if len(names) != 2:
        raise CalibrationError(
            f"a calibração a dois precisa de exatamente dois rotuladores em --rater; recebi {len(names)}: "
            f"{', '.join(names) or '-'}."
        )
    humans = [name for name in names if not is_model(kinds[name])]
    if len(humans) != 1:  # spec v0.11.0 D6(c), Q22: one human rater, who adjudicates, and one declared panel
        raise CalibrationError(
            f"a calibração a dois precisa de exatamente um rotulador human (o ouro é adjudicado por ele) e um painel "
            f"model; recebi {len(humans)} human: "
            + ", ".join(f"{name}:{kinds[name]}" for name in names)
            + f". Use {KIND_FORMAT}. Nada foi gravado."
        )
    labels: dict[str, dict[str, Label]] = {name: {} for name in names}
    sealed_ids: set[str] = set()
    for name, entry, campaign, filled, marks, sealed in read:
        if sealed:
            sealed_ids |= {row["request_id"] for row in filled.rows}
        for rating in filled.ratings:
            if rating.request_id in labels[name]:
                errors.append(
                    f"{entry.sample.name} ({rating.sample_id}): {name} já avaliou a requisição {rating.request_id} em "
                    "outro arquivo."
                )
                continue
            answer = marks.get(rating.request_id) if marks is not None else None
            if marks is not None and answer is None:
                answer = packets.AnswerClaims(rating.sample_id, rating.request_id)
            labels[name][rating.request_id] = Label(name, campaign, rating, answer, sealed)
    first, second = names
    answers = list(dict.fromkeys([*labels[first], *labels[second]]))
    for request_id in answers:
        x, y = labels[first].get(request_id), labels[second].get(request_id)
        if x and y and x.claims is not None and y.claims is not None and x.claims.listing() != y.claims.listing():
            errors.append(
                f"{x.rating.sample_id}: {first} e {second} receberam listas de afirmações diferentes para a requisição "
                f"{request_id}; os dois marcam a mesma lista."
            )
    if not answers:
        errors.append("nenhuma resposta avaliada nos arquivos de --rater.")
    if errors:
        raise CalibrationError(errors)
    adjudicated = read_adjudication(adjudication) if adjudication is not None else {}
    unknown = sorted(set(adjudicated) - set(answers))
    if unknown:
        errors += [f"{adjudication.name}: a requisição {i} não foi avaliada por nenhum rotulador." for i in unknown]
    gold: dict[str, dict] = {}
    human, panel = humans[0], next(name for name in names if name not in humans)
    for request_id in answers:
        x, y = labels[first].get(request_id), labels[second].get(request_id)
        label, diverging = _gold(request_id, x, y, adjudicated.get(request_id))
        if diverging:
            errors.append(
                f"{(x or y).rating.sample_id} ({request_id}): {first} e {second} divergem em {'; '.join(diverging)}; "
                "a adjudicação (--adjudication, colunas request_id, gold_verdict, gold_scores, reason) é obrigatória."
            )
        elif label is not None:
            gold[request_id] = label
        elif request_id in sealed_ids and request_id in labels[human]:
            # D6(g): every sealed answer the human rated has a gold label, whatever left it without one (task 89
            # round 5): here the panel did not rate it (its members agreed on nothing, or one did not rate it)
            given = adjudicated.get(request_id) or {"verdict": None, "scores": {}}
            missing = [c for c in CRITERIA if c not in given["scores"]] + [VERDICT] * (given["verdict"] is None)
            errors.append(
                f"{labels[human][request_id].rating.sample_id} ({request_id}): resposta selada que {human} avaliou e "
                f"{panel} deixou sem rótulo; fica sem ouro em {', '.join(missing)}. Toda resposta selada avaliada pelo "
                "humano tem ouro (D6(g)): a adjudicação (--adjudication, colunas request_id, gold_verdict, "
                "gold_scores, reason) é obrigatória."
            )
    if errors:
        raise CalibrationError(errors)
    resolved = _resolve_blocks(conn, answers, blocks)
    groups: dict[tuple[str, str], tuple[list[Pair], dict[str, str]]] = {}
    for name, _, campaign, filled, _, _ in read:
        pairs, blank = groups.setdefault((campaign, stored_rater(name, kinds[name])), ([], {}))
        pairs += [Pair(r, resolved[0]["judgements"][r.request_id]) for r in filled.ratings]
        blank |= filled.blank
    for (campaign, name), (pairs, _) in groups.items():
        check_same_sample(conn, campaign, name, pairs)
    stored = store_many(conn, [(campaign, name, pairs, blank) for (campaign, name), (pairs, blank) in groups.items()])
    seeds = [filled.meta.get("seed", "") for _, _, _, filled, _, _ in read]
    seed = next((int(s) for s in seeds if str(s).lstrip("-").isdigit()), DEFAULT_SEED)
    combined = ensembles(resolved)
    sealed = [i for i in answers if i in sealed_ids]
    sides = _sides(names, kinds)
    scopes = [
        ("Seladas", _scope(sealed, names, labels, gold, resolved, combined, seed, sides)),
        ("Todas", _scope(answers, names, labels, gold, resolved, combined, seed, sides)),
    ]
    # D6(g) measures against the gold label adjudicated by the human rater: the sealed answers the human rater rated
    by_human = [i for i in sealed if i in gold and any(i in labels[name] for name in humans)]
    rule = d6_rule(_scope(by_human, names, labels, gold, resolved, combined, seed, sides), resolved, combined)
    context = {
        "names": names,
        "kinds": kinds,
        "sides": sides,
        "humans": humans,
        "labels": labels,
        "gold": gold,
        "adjudicated": adjudicated,
        "blocks": resolved,
        "ensembles": combined,
        "scopes": scopes,
        "rule": rule,
        "files": read,
        "stored": {
            f"{campaign}/{name}": result.counts() | {"removed": result.removed, "outside": result.outside}
            for ((campaign, name), _), result in zip(groups.items(), stored, strict=True)
        },
    }
    return context | {"report": render_two_raters(context, now=now)}


# --- the panel of models: the two members joined by agreement (spec v0.11.0 D6(c); task 89 round 4) ---------------


@dataclass
class _Member:
    """One member of the panel: its claims file (marks by request id and the sample line) and its sample CSV (the
    ratings, with the verdict computed from the marks)."""

    claims: Path
    meta: dict[str, str]
    marks: dict[str, packets.AnswerClaims]
    sample: Path
    filled: Filled


def _read_member(index: int, claims: Path, sample: Path, seal_path: Path | None) -> _Member:
    """A refusal names the member by its number and its files by their paths (task 89 round 5)."""
    where = f"membro {index}, {claims}"
    try:
        found = packets.read_claims(_read_text(claims), META_KEYS)
    except (packets.ClaimsError, CalibrationError) as exc:
        raise CalibrationError([f"{where}: {m}" for m in exc.messages]) from None
    problems = packets.verify_claims(found, where)
    if problems:
        raise CalibrationError(problems)
    try:  # a member labels like the human rater: every claim of a rated answer marked, the seal checked
        _, filled, marks, _ = read_rater(RaterFiles(f"membro{index}", sample, claims, HUMAN), seal_path)
    except CalibrationError as exc:
        raise CalibrationError([f"membro {index} ({sample}, {claims}): {m}" for m in exc.messages]) from None
    return _Member(claims, found.meta, marks, sample, filled)


def _rewrite(path: Path, change) -> bytes:
    """The CSV of `path` written again with the same lines, header and separator; `change(values, cells)` gives the
    new cells of a data row (or None to drop it)."""
    text = _read_text(path).lstrip("\ufeff")
    found = next((match for line in text.splitlines() if (match := _HEADER.match(line))), None)
    delimiter = found.group(1) if found else ";"
    handle = io.StringIO(newline="")
    writer = csv.writer(handle, delimiter=delimiter, lineterminator="\r\n")
    header: list[str] | None = None
    for cells in csv.reader(io.StringIO(text, newline=""), delimiter=delimiter):
        if not any(cell.strip() for cell in cells) or cells[0].strip().startswith("#"):
            writer.writerow(cells)
            continue
        if header is None:
            header = [_plain(cell) for cell in cells]
            writer.writerow(cells)
            continue
        values = dict(zip(header, [cell.strip() for cell in cells], strict=False))
        changed = change(values, list(cells), header)
        if changed is not None:
            writer.writerow(changed)
    return handle.getvalue().encode("utf-8-sig")


def merge_panel(
    claims: Sequence[Path], samples: Sequence[Path] | None, out: Path, *, seal_path: Path | None = None
) -> dict:
    """`eval-calibrate --merge-panel <member1-claims.csv> <member2-claims.csv> --sample-csv <a.csv> <b.csv> --out
    <panel.csv>`: the label of the panel is the agreement of its two members (D6(c)). Both members must be of the same
    sample (the SHA-256 of the claims and the identity of the answers); the sample CSVs are required (task 89 round 5).
    The panel's claims CSV (`<panel>-claims.csv`) has a claim's mark where both members gave it and a blank where they
    differ; the panel's sample CSV (`<panel>.csv`) has a score, or the verdict, where both gave the same and a blank
    where not, and no note. An answer on which the members agree on no score nor verdict, or that one of them did not
    rate, is left blank in both files (the panel did not rate it). Added claims are not carried over. Neither output
    file may exist already. Nothing is written unless every file is valid; nothing is called."""
    if len(claims) != 2 or samples is None or len(samples) != 2:
        raise CalibrationError(
            "--merge-panel junta os arquivos de exatamente dois membros do painel: os dois CSV de afirmações e, em "
            "--sample-csv, os dois CSV de notas, na mesma ordem. Nada foi gravado."
        )
    claims_out = packets.claims_path(out)
    targets = [claims_out, out]
    inputs = [*claims, *samples]
    same = [str(t) for t in targets for i in inputs if t.resolve() == Path(i).resolve()]
    if same:
        raise CalibrationError(f"--out gravaria sobre um arquivo de membro ({', '.join(same)}); escolha outro nome.")
    existing = [str(t) for t in targets if t.exists()]
    if existing:
        raise CalibrationError(
            f"--out: {', '.join(existing)} já existe; a junção não sobrescreve arquivos. Escolha outro nome. "
            "Nada foi gravado."
        )
    errors: list[str] = []
    members: list[_Member] = []
    for index, path in enumerate(claims, start=1):
        try:
            members.append(_read_member(index, Path(path), Path(samples[index - 1]), seal_path))
        except CalibrationError as exc:
            errors += exc.messages
    if errors:
        raise CalibrationError(errors)
    one, two = members
    if one.meta.get("claims_sha256") != two.meta.get("claims_sha256"):
        errors.append(
            f"membro 1 ({one.claims}) e membro 2 ({two.claims}) não são da mesma amostra: o SHA-256 das afirmações "
            f"difere ({one.meta.get('claims_sha256', '')[:12]}… × {two.meta.get('claims_sha256', '')[:12]}…). "
            "Nada foi gravado."
        )
    if one.filled.rows != two.filled.rows or one.filled.meta.get("campaign") != two.filled.meta.get("campaign"):
        errors.append(
            f"membro 1 ({one.sample}) e membro 2 ({two.sample}) não são da mesma amostra (campanha ou identidade das "
            "respostas diferem). Nada foi gravado."
        )
    for index, member in enumerate(members, start=1):
        if set(member.marks) != {row["request_id"] for row in member.filled.rows}:
            errors.append(
                f"membro {index}: {member.claims} não é o CSV de afirmações de {member.sample} (as requisições "
                "diferem). Nada foi gravado."
            )
    if errors:
        raise CalibrationError(errors)
    ratings = [{r.request_id: r for r in m.filled.ratings} for m in members]
    scores: dict[str, dict[str, int]] = {}
    verdicts: dict[str, bool | None] = {}
    blank: set[str] = set()
    for row in one.filled.rows:
        request_id = row["request_id"]
        x, y = ratings[0].get(request_id), ratings[1].get(request_id)
        if x is None or y is None:
            blank.add(request_id)
            continue
        scores[request_id] = {c: x.scores[c] for c in CRITERIA if x.scores[c] == y.scores[c]}
        verdicts[request_id] = x.unsupported_claim if x.unsupported_claim == y.unsupported_claim else None
        if not scores[request_id] and verdicts[request_id] is None:
            blank.add(request_id)
    same_mark: dict[str, dict[int, str]] = {}  # the marks both members gave, before any answer is left blank
    compared = 0
    for request_id, answer in one.marks.items():
        theirs = {c.n: c.verdict for c in two.marks[request_id].claims}
        compared += sum(1 for c in answer.claims if c.verdict and theirs.get(c.n))
        same_mark[request_id] = {c.n: c.verdict for c in answer.claims if c.verdict and theirs.get(c.n) == c.verdict}
    agreed = {request_id: ({} if request_id in blank else marks) for request_id, marks in same_mark.items()}
    numbered = {request_id for request_id, answer in one.marks.items() if answer.claims}
    kept_empty: set[str] = set()

    def claim_row(values: dict, cells: list[str], header: list[str]) -> list[str] | None:
        request_id, raw_n = values.get("request_id", ""), values.get("n", "")
        if not raw_n:  # the line of an answer with no claim stays, once; a claim a member added does not
            if request_id in numbered or request_id in kept_empty:
                return None
            kept_empty.add(request_id)
        mark = agreed.get(request_id, {}).get(int(raw_n)) if raw_n else None
        cells += [""] * (len(header) - len(cells))
        cells[header.index("verdict")] = mark or ""
        if "added_claim" in header:
            cells[header.index("added_claim")] = ""
        return cells

    files = {claims_out: _rewrite(one.claims, claim_row)}
    check = packets.read_claims(files[claims_out].decode("utf-8-sig"), META_KEYS)
    if packets.verify_claims(check, str(claims_out)):  # the panel keeps the members' claims, number by number
        raise CalibrationError(f"{claims_out}: o SHA-256 das afirmações do painel mudou; nada foi gravado.")

    def sample_row(values: dict, cells: list[str], header: list[str]) -> list[str]:
        request_id = values.get("request_id", "")
        given = scores.get(request_id, {}) if request_id not in blank else {}
        verdict = verdicts.get(request_id) if request_id not in blank else None
        cells += [""] * (len(header) - len(cells))
        for criterion in CRITERIA:
            cells[header.index(criterion)] = str(given[criterion]) if criterion in given else ""
        cells[header.index(VERDICT)] = "" if verdict is None else ("sim" if verdict else "nao")
        if "note" in header:
            cells[header.index("note")] = ""
        return cells

    files[out] = _rewrite(one.sample, sample_row)
    packets.write_files(files)
    in_agreement = sum(len(marks) for marks in same_mark.values())
    both_rated = [r for r in ratings[0] if r in ratings[1]]
    return {
        "claims": claims_out,
        "sample": out,
        "members": [
            {
                "claims": member.claims,
                "sample": member.sample,
                "rated": len(member.filled.ratings),
                "marked": sum(1 for answer in member.marks.values() for c in answer.claims if c.verdict),
                "in_agreement": in_agreement,
            }
            for member in members
        ],
        "claims_compared": compared,
        "claims_written": sum(len(marks) for marks in agreed.values()),
        "both_rated": len(both_rated),
        "scores_compared": len(CRITERIA) * len(both_rated),
        "scores_agreed": sum(len(v) for r, v in scores.items() if r not in blank),
        "verdicts_agreed": sum(v is not None for r, v in verdicts.items() if r not in blank),
        "blank": sorted(blank),
    }


# --- the report of the two raters -----------------------------------------------------------------------------------


def _label_names(labels: dict[str, dict[str, Label]], names: list[str]) -> dict[str, str]:
    """How each answer is named in the tables: its sample id, or `campaign:sample id` when two samples share one."""
    chosen: dict[str, Label] = {}
    for name in names:
        for request_id, label in labels[name].items():
            chosen.setdefault(request_id, label)
    counts: dict[str, int] = {}
    for label in chosen.values():
        counts[label.rating.sample_id] = counts.get(label.rating.sample_id, 0) + 1
    return {
        request_id: label.rating.sample_id
        if counts[label.rating.sample_id] == 1
        else f"{label.campaign}:{label.rating.sample_id}"
        for request_id, label in chosen.items()
    }


def _short(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= CLAIM_TEXT_CHARS else text[: CLAIM_TEXT_CHARS - 1] + "…"


def _claim_cell(measure: dict, key: str) -> str:
    m = measure[key]
    kappa = _kappa(m) if m["kappa"] is not None else "n/d"
    return f"{_share(m['exact'], m['exact_ci'])} | {kappa}"


def render_two_raters(context: dict, *, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(UTC)).isoformat(timespec="seconds")
    names, blocks, combined = context["names"], context["blocks"], context["ensembles"]
    labels, kinds = context["labels"], context["kinds"]
    shown = _label_names(labels, names)
    all_scope = context["scopes"][1][1]
    declared = " e ".join(f"`{_cell(name)}` ({kind_text(kinds[name])})" for name in names)
    lines = [
        "# Calibração a dois rotuladores (v0.11.0)",
        "",
        f"Gerado em {stamp}. Rotuladores {declared}; rótulo ouro = valor adjudicado, senão o valor em que os dois "
        "concordam (spec v0.11.0 D4).",
        "",
        "| Rotulador | Tipo | Arquivo | Campanha | Semente | Avaliadas | Afirmações | Selo |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, entry, campaign, filled, _, sealed in context["files"]:
        claims = f"`{_cell(entry.claims.name)}`" if entry.claims else "sem CSV (veredito do CSV de notas)"
        seal = f"`{packets.SEAL_NAME}` conferido" if sealed else "-"
        lines.append(
            f"| `{_cell(name)}` | {kind_text(kinds[name])} | `{_cell(entry.sample.name)}` | `{_cell(campaign)}` | "
            f"{_cell(filled.meta.get('seed', '-'))} | {len(filled.ratings)} | {claims} | {seal} |"
        )
    for name in names:
        if is_model(kinds[name]):
            lines += [
                "",
                f"> `{_cell(name)}` é um painel de modelos, declarado em `--rater`: suas notas e marcas são rótulo de "
                "modelo, não humano, e aparecem nas tabelas como `painel`.",
            ]
    lines += [
        "",
        f"Respostas avaliadas por pelo menos um rotulador: {all_scope['n']}; pelos dois: {all_scope['both']}; com "
        f"rótulo ouro: {all_scope['gold']}; adjudicadas: {len(context['adjudicated'])}. Seladas: "
        f"{context['scopes'][0][1]['n']}.",
        "",
        "| Bloco | Juiz | Rubrica | Execuções |",
        "| --- | --- | --- | --- |",
    ]
    for block in blocks:
        runs = ", ".join(f"`{_cell(name)}`" for name in block["runs"] or ["-"])
        lines.append(f"| {block['label']} | `{_cell(block['judge'])}` | `judge.v{_cell(block['rubric'])}` | {runs} |")
    for ensemble in combined:
        lines.append(
            f"| {ensemble['label']} | ensemble `{_cell(ensemble['judge'])}` (sim só quando os dois marcam) | "
            f"`judge.v{_cell(ensemble['rubric'])}` | julgamentos gravados de {ensemble['label'].replace('+', ' e ')} |"
        )
    lines += [
        "",
        f"> Ressalva de amostra pequena (D19): {all_scope['n']} respostas. Os intervalos (95%) mostram a margem; leia "
        "como indicação de quanto confiar em cada juiz, não como prova.",
    ]
    for title, scope in context["scopes"]:
        lines += _render_scope(title, scope, context, shown)
    lines += _render_rule(context["rule"], [(name, context["sides"][name]) for name in context["humans"]])
    lines += _render_adjudication(context, shown)
    named = [(f"{b['label']} `{_cell(b['judge'])}` judge.v{_cell(b['rubric'])}", b["usage"]) for b in blocks]
    named = [(name, usage) for name, usage in named if usage]
    if named:
        lines += [
            "",
            "## Consistência de cada juiz entre repetições",
            "",
            "Os julgamentos de cada bloco sobre estas respostas, das execuções da tabela de blocos. Sem pares, o juiz "
            "julgou cada resposta uma vez só.",
            "",
            *_run_tables(named),
        ]
    lines += [
        "",
        "## Como ler",
        "",
        "- Por critério: exata, ±1 (Wilson 95%) e kappa quadrático com intervalo por bootstrap, como na v0.8.0. "
        "Viés = média do segundo lado menos a do primeiro.",
        "- Veredito: com dois valores, o kappa quadrático é o kappa de Cohen. O veredito de um rotulador que entregou "
        "o CSV de afirmações é calculado das marcas: sim quando alguma afirmação que não é `standard` (ou "
        "acrescentada) é `generic` ou `not_found`, a mesma regra do `judge.v5`.",
        "- Tipo do rotulador: `human` é rotulagem humana; `model:<modelos>` é um painel de modelos declarado, nunca "
        "chamado de humano. Os pares levam o tipo de cada lado (humano, painel, juiz, ouro).",
        "- Painel: a marca, a nota e o veredito do painel são os que os seus dois membros deram iguais "
        "(`eval-calibrate --merge-panel`); o que divergiu fica sem rótulo do painel e fora do n; nota ou veredito sem "
        "rótulo do painel numa resposta que o humano avaliou passa pela adjudicação.",
        "- Por afirmação: n = afirmações. Quatro marcas: kappa de Cohen sem pesos. Sem suporte: `generic` ou "
        "`not_found` contra as demais. Ouro × juiz pareia cada afirmação da amostra com a do juiz pelo texto (caixa, "
        "pontuação e espaços à parte); uma afirmação que o juiz escreveu de outro jeito fica sem par e fora do n.",
        "- Ensemble: veredito sim só quando os dois juízes marcam, a partir dos julgamentos gravados (sem chamada); as "
        "notas são as do primeiro bloco; o custo por julgamento é a soma dos dois.",
        "- Dados: respostas do sistema sobre a conta sintética, mascaradas.",
    ]
    return "\n".join(lines) + "\n"


def _render_scope(title: str, scope: dict, context: dict, shown: dict[str, str]) -> list[str]:
    names, labels = context["names"], context["labels"]
    lines = ["", f"## {title} ({scope['n']} respostas)", ""]
    if not scope["n"]:
        lines.append(
            "Nenhuma resposta neste bloco." if title != "Seladas" else "Nenhuma amostra selada nesta importação."
        )
        return lines
    lines += [
        f"Avaliadas pelos dois: {scope['both']}; com rótulo ouro: {scope['gold']}.",
        "",
        "### Por critério",
        "",
        "| Critério | Par | n | Exata | ±1 | Kappa quadrático | Viés |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for criterion in CRITERIA:
        for pair, measured in scope["pairs"]:
            if not measured["n"]:
                lines.append(f"| {criterion} | {_cell(pair)} | 0 | - | - | - | - |")
                continue
            m = measured["criteria"][criterion]
            lines.append(
                f"| {criterion} ({CRITERIA_LABELS[criterion]}) | {_cell(pair)} | {m['n']} | "
                f"{_share(m['exact'], m['exact_ci'])} | {_share(m['within_one'], m['within_one_ci'])} | {_kappa(m)} | "
                f"{_bias(m)} |"
            )
    lines += [
        "",
        "### Veredito `unsupported_claim`",
        "",
        "| Par | n | Exata | Kappa de Cohen | Ambos sim | Só o 1º | Só o 2º | Nenhum |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for pair, measured in scope["pairs"]:
        if not measured["n"]:
            lines.append(f"| {_cell(pair)} | 0 | - | - | - | - | - | - |")
            continue
        v = measured[VERDICT]
        t = v["table"]
        lines.append(
            f"| {_cell(pair)} | {v['n']} | {_share(v['exact'], v['exact_ci'])} | {_kappa(v)} | {t['both']} | "
            f"{t['first_only']} | {t['second_only']} | {t['neither']} |"
        )
    lines += [
        "",
        "### Por afirmação",
        "",
        f"Afirmações listadas nas respostas deste bloco: {scope['claims_listed']}; com marca ouro: "
        f"{scope['claims_gold']}.",
        "",
        "| Par | Afirmações | Exata (4 marcas) | Kappa (4 marcas) | Exata (sem suporte) | Kappa (sem suporte) | "
        "Sem par |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for pair, measured, unpaired in scope["claim_pairs"]:
        if not measured["n"]:
            lines.append(f"| {_cell(pair)} | 0 | - | - | - | - | {unpaired} |")
            continue
        lines.append(
            f"| {_cell(pair)} | {measured['n']} | {_claim_cell(measured, 'marks')} | "
            f"{_claim_cell(measured, 'unsupported')} | {unpaired} |"
        )
    if len(scope["claim_pairs"]) == 1:
        lines += ["", "Nenhum bloco `judge.v5` com afirmações: ouro × juiz por afirmação não se aplica."]
    for label, given, total in scope.get("claims_from", []):
        lines += [
            "",
            f"Bloco {label}: {given} de {total} julgamentos receberam a lista de afirmações da amostra (`eval "
            "--claims-from`) e pareiam pelo número; os demais, pelo texto.",
        ]
    lines += _render_gold_claims(scope, context, shown)
    first, second = names
    added = [
        (request_id, name, text, mark)
        for request_id in scope["ids"]
        for name in names
        if (label := labels[name].get(request_id)) and label.claims
        for text, mark, _ in label.claims.added
    ]
    if added:
        lines += [
            "",
            "Afirmações acrescentadas pelos rotuladores (fora do kappa por afirmação; contam no veredito de quem "
            "acrescentou):",
            "",
            "| Amostra | Rotulador | Afirmação | Marca |",
            "| --- | --- | --- | --- |",
            *[
                f"| {_cell(shown[i])} | `{_cell(name)}` | {_cell(_short(text))} | {mark} |"
                for i, name, text, mark in added
            ],
        ]
    by_route: dict[str, int] = {}
    for request_id in scope["ids"]:
        label = labels[first].get(request_id) or labels[second][request_id]
        by_route[label.rating.route or "-"] = by_route.get(label.rating.route or "-", 0) + 1
    lines += ["", "Rotas: " + ", ".join(f"{_cell(k)} {v}" for k, v in sorted(by_route.items())) + "."]
    return lines


def _render_gold_claims(scope: dict, context: dict, shown: dict[str, str]) -> list[str]:
    """The claims the gold label marks generic or not_found (kind not standard), and what each judge did with them."""
    names, blocks, combined = context["names"], context["blocks"], context["ensembles"]
    gold, labels = context["gold"], context["labels"]
    columns = [block["label"] for block in blocks] + [ensemble["label"] for ensemble in combined]
    lines = [
        "",
        "### Afirmações marcadas pelo ouro",
        "",
        "Afirmações que não são `standard` e que o rótulo ouro marca `generic` ou `not_found`, e o que cada juiz fez: "
        "a marca do juiz na afirmação pareada (`judge.v5`), `sem par` quando o juiz não listou a mesma afirmação, ou o "
        "veredito da resposta (`resposta: sim/não`) para rubricas sem afirmações e para o ensemble.",
        "",
    ]
    rows = []
    for request_id in scope["ids"]:
        if request_id not in gold or scope["listing"].get(request_id) is None:
            continue
        claims = scope["listing"][request_id].claims
        for claim in claims:
            mark = gold[request_id]["claims"].get(claim.n)
            if mark not in UNSUPPORTED_MARKS or claim.kind == "standard":
                continue
            rater_marks = []
            for name in names:
                label = labels[name].get(request_id)
                own = label.claims.claims if label and label.claims else []
                rater_marks.append(next((c.verdict for c in own if c.n == claim.n and c.verdict), "-"))
            cells = []
            for block in blocks:
                judged = block["judgements"][request_id]
                if judged.get("claims"):
                    cells.append(judged_marks([claim], judged["claims"]).get(claim.n, "sem par"))
                else:
                    cells.append(f"resposta: {_yes(judged[VERDICT])}")
            cells += [f"resposta: {_yes(e['judgements'][request_id][VERDICT])}" for e in combined]
            rows.append(
                f"| {_cell(shown[request_id])} | {claim.n} | {claim.kind} | {_cell(_short(claim.text))} | "
                + " | ".join(rater_marks)
                + f" | {mark} | "
                + " | ".join(_cell(cell) for cell in cells)
                + " |"
            )
    if not rows:
        return [*lines, "Nenhuma."]
    head = (
        "| Amostra | nº | Tipo | Afirmação | "
        + " | ".join(f"`{_cell(name)}`" for name in names)
        + f" | {GOLD.capitalize()} | "
        + " | ".join(columns)
        + " |"
    )
    rule = "| " + " | ".join("---" for _ in range(5 + len(names) + len(columns))) + " |"
    return [*lines, head, rule, *rows]


def _render_rule(rule: dict | None, humans: list[tuple[str, str]]) -> list[str]:
    lines = [
        "",
        "## Regra D6(g) da v0.11.0 (informativa)",
        "",
        f"Calculada com os números das respostas seladas, sem decidir. Vira padrão o candidato com kappa do veredito "
        f"≥ {D6_KAPPA:.1f} contra o rótulo ouro (adjudicado pelo rotulador humano) nas seladas, sem piorar o ±1 de "
        f"nenhum critério em mais de {D6_TOLERANCE:.2f} em relação ao juiz padrão (`judge.v3` com `{D2_JUDGE}`); "
        "empate decide pelo custo. A decisão é registrada na ADR 0023.",
        "",
    ]
    if rule is None:
        return [*lines, "Não calculada: nenhuma resposta selada com rótulo ouro avaliada pelo rotulador humano."]
    who = " e ".join(f"`{_cell(name)}`" for name, _ in humans)
    lines += [f"n = {rule['n']} respostas seladas com rótulo ouro e avaliadas pelo rotulador humano ({who}).", ""]
    if rule["base"] is None:
        lines += [f"Sem bloco `judge.v3` com `{D2_JUDGE}` neste relatório: a condição do ±1 não é calculada.", ""]
    lines += [
        f"| Candidato | Kappa do veredito | ≥ {D6_KAPPA:.1f} | ±1 por critério (diferença para a base) | "
        f"Não piora > {D6_TOLERANCE:.2f} | "
        "Custo por julgamento (US$) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rule["rows"]:
        candidate = row["candidate"]
        name = f"{candidate['label']} `{_cell(candidate['judge'])}` judge.v{_cell(candidate['rubric'])}"
        kappa = "n/d" if row["kappa"] is None else f"{row['kappa']:.3f}{_interval(row['kappa_ci'])}"
        if rule["base_within"] is None:
            within = ", ".join(f"{c} {row['within'][c]:.3f}" for c in CRITERIA)
        else:
            within = ", ".join(
                f"{c} {row['within'][c]:.3f} ({row['within'][c] - rule['base_within'][c]:+.3f})" for c in CRITERIA
            )
        holds = "-" if row["holds_within"] is None else _yes(row["holds_within"])
        cost = "-" if row["cost"] is None else f"{row['cost']:.6f}"
        lines.append(f"| {name} | {kappa} | {_yes(row['holds_kappa'])} | {within} | {holds} | {cost} |")
    meeting = sorted(
        (row for row in rule["rows"] if row["both"]),
        key=lambda row: (row["cost"] is None, row["cost"] or 0.0),
    )
    lines += [
        "",
        "Atendem às duas condições: "
        + (", ".join(f"{row['candidate']['label']}" for row in meeting) + " (em ordem de custo por julgamento)."
           if meeting else "nenhum."),
    ]
    return lines


def _render_adjudication(context: dict, shown: dict[str, str]) -> list[str]:
    adjudicated = context["adjudicated"]
    lines = ["", "## Adjudicação", ""]
    if not adjudicated:
        return [*lines, "Nenhuma adjudicação: os dois rotuladores concordaram em tudo o que o ouro usa."]
    lines += ["| Amostra | Veredito | Notas | Afirmações | Motivo |", "| --- | --- | --- | --- | --- |"]
    for request_id, row in adjudicated.items():
        verdict = "-" if row["verdict"] is None else _yes(row["verdict"])
        scores = " ".join(f"{k}={v}" for k, v in row["scores"].items()) or "-"
        claims = " ".join(f"{n}={m}" for n, m in sorted(row["claims"].items())) or "-"
        lines.append(
            f"| {_cell(shown.get(request_id, request_id))} | {verdict} | {_cell(scores)} | {_cell(claims)} | "
            f"{_cell(row['reason'])} |"
        )
    return lines
