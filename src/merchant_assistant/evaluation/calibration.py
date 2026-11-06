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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from merchant_assistant.evaluation import aggregate, evidence
from merchant_assistant.evaluation.judge import (
    CAMPAIGN_PRINCIPAL,
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
# The calibration sample comes from the campaign of development only: the holdout_v080 is run once, last, by the QA
# (D17), and what the owner sees of it would be seen before that. `--split` narrows the choice, never widens it.
DEVELOPMENT_SPLITS = ("dev", "holdout")
SPLIT_CHOICES = {"development": DEVELOPMENT_SPLITS, "dev": ("dev",), "holdout": ("holdout",)}

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
        raise CalibrationError(
            f"o relatório {path.name} só tem respostas dos splits {', '.join(sorted(left_out))}, e a amostra de "
            f"calibração sai de {', '.join(splits)}. O holdout_v080 não entra na calibração (ele é visto uma vez, "
            "no fim, pelo QA)."
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


def write_csv(path: Path, rows: list[dict], meta: dict, *, delimiter: str = ";") -> None:
    """UTF-8 with a BOM (a spreadsheet then reads the accents), the instructions as `#` lines and the sample line."""
    if delimiter not in DELIMITERS:
        raise CalibrationError(f"separador inválido: {delimiter!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = (
        f"amostra: campanha={meta['campaign']}; semente={meta['seed']}; origem={meta['source']}; "
        f"sorteadas={len(rows)}; pedidas={meta['requested']}; elegiveis={meta['eligible']}; "
        f"splits={meta['splits']}; rubrica={RUBRIC}.v{RUBRIC_VERSION}"
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
    blank: dict[str, str]  # sample id -> request id of the rows with no rating at all

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
}
_YES = {"sim", "s", "true", "verdadeiro", "yes", "y", "1"}
_NO = {"nao", "n", "false", "falso", "no", "0"}


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().strip().casefold()


def read_filled(text: str) -> Filled:
    """Parses and validates the filled CSV. Every problem is collected with its line, so one pass shows them all."""
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
        _rate_row(values, start, ratings, blank, errors, seen)
    if header is None:
        raise CalibrationError("não encontrei o cabeçalho com a coluna sample_id: use o arquivo gerado por --sample.")
    if errors:
        raise CalibrationError(errors)
    return Filled(meta, ratings, blank)


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
    values: dict[str, str],
    line: int,
    ratings: list[Rating],
    blank_rows: dict[str, str],
    errors: list[str],
    seen: dict[str, dict[str, int]],
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
    }


def judgement_for(
    conn: sqlite3.Connection,
    request_id: str,
    judge: str | None = None,
    run: str | None = None,
    rubric: str | None = None,
) -> dict | None:
    """The first judgement (repetition 1) that the campaign wrote for this request, with its scores and verdict. With
    `judge` (`<provider>/<model>`, spec v0.9.0 RF-108) only that judge's judgements count; without it, any judge's.
    With `run`, only the judgements of that execution (`LEGACY_RUN` for those without a name); with `rubric` (the
    stored version, "3" or "4", spec v0.10.0 D1), only those of that rubric."""
    rows = conn.execute(
        "SELECT evaluation_id, rubric_version, evaluator, scores, unsupported_claim FROM run_evaluations "
        "WHERE request_id=? AND principal_id=? AND rubric=? AND state='completed' AND repetition=1 "
        "AND scores IS NOT NULL ORDER BY created_at, evaluation_id",
        (request_id, CAMPAIGN_PRINCIPAL, RUBRIC),
    )
    for row in rows:
        if judge is not None and _judge_name(row["evaluator"]) != judge:
            continue
        if run is not None and _run_name(row["evaluator"]) != run:
            continue
        if rubric is not None and row["rubric_version"] != rubric:
            continue
        return _judgement(row)
    return None


def judgement_by_id(conn: sqlite3.Connection, evaluation_id: str) -> dict | None:
    row = conn.execute(
        "SELECT evaluation_id, rubric_version, evaluator, scores, unsupported_claim FROM run_evaluations "
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
) -> list[Pair]:
    pairs, errors = [], []
    for rating in filled.ratings:
        judgement = judgement_for(conn, rating.request_id, judge, run, rubric)
        if judgement is None:
            by = f" do juiz {judge}" if judge else ""
            by += f" na execução {run!r} (repetição 1 completa)" if run else ""
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
    created = updated = 0
    removed: list[str] = []
    now = datetime.now(UTC).isoformat(timespec="seconds")
    conn.execute("BEGIN")
    try:
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
    in_file = {pair.rating.sample_id for pair in pairs}
    outside = [
        row["sample_id"]
        for row in conn.execute(
            "SELECT sample_id FROM calibrations WHERE campaign=? AND rater=? ORDER BY sample_id", (campaign, rater)
        )
        if row["sample_id"] not in in_file
    ]
    return Stored(created, updated, removed, outside)


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
    rubric: str = RUBRIC_VERSION,
) -> dict:
    """The judgements of `judge` under `rubric` (judge.v3 by default) on these requests, only those of the executions
    `runs` when given: consistency between its repetitions over the same answer (`aggregate`), how many failed, what
    they cost and the tokens they recorded."""
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


def kappa_interval(
    human: list[int], judge: list[int], categories: tuple[int, ...], seed: int
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
        value = quadratic_kappa([human[i] for i in picks], [judge[i] for i in picks], categories)
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
        "original, conferidas linha a linha; não houve avaliação humana nova. A entra com o julgamento da "
        f"repetição 1 de cada resposta na execução {a_runs}; B, com o julgamento ao qual cada nota foi ligada na "
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
    each condition holds; the choice of the default rubric is recorded in task 86."""
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
    return next((b for b in blocks if b["judge"] == block["judge"] and b["rubric"] == RUBRIC_VERSION), None)


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
        "campanha original; cada outro bloco entra com o julgamento da repetição 1 de cada resposta na execução e "
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
        "## Regra D2 da v0.10.0 (informativa)",
        "",
        "Calculada com os números acima, sem decidir. Pela D2, a `judge.v4` vira padrão se, com o juiz padrão "
        f"(`{D2_JUDGE}`), (a) a concordância do veredito com o humano não cair, (b) pelo menos "
        f"{D2_MIN_GENERIC} das {len(GENERIC_SAMPLES)} frases genéricas forem marcadas e (c) a concordância ±1 de "
        f"nenhum critério piorar mais de {D2_TOLERANCE:.2f}; os outros juízes são reportados e não decidem. Cada "
        "bloco `judge.v4` é comparado com o bloco `judge.v3` do mesmo juiz. A decisão é registrada na tarefa 86.",
        "",
    ]
    candidates = [block for block in blocks if block["rubric"] != RUBRIC_VERSION]
    if not candidates:
        lines.append("Nenhum bloco sob outra rubrica que não a `judge.v3`.")
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
    """The stored version of a rubric ("3" or "4"; `v3` and `v4` are accepted); `None` is the configured default.
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
        blocks.append((name, run, version, link(conn, filled, name, run, version)))
    return blocks


def _token(text: str) -> str:
    """A name safe to put in the sample line (no `;`, `=` or spaces) and in a table cell."""
    return re.sub(r"[^\w.\-]+", "-", text).strip("-") or "campanha"


def make_sample(
    report: Path, size: int, seed: int, campaign: str | None = None, split: str = "development"
) -> tuple[list[dict], dict]:
    """`eval-calibrate --sample`: the CSV rows and the sample line for `size` answers of the report, drawn from the
    development splits (`split` can narrow that to `dev` or `holdout`; the holdout_v080 is never sampled)."""
    if split not in SPLIT_CHOICES:
        raise CalibrationError(f"split inválido para a amostra: {split!r} (use {', '.join(SPLIT_CHOICES)}).")
    splits = SPLIT_CHOICES[split]
    rows, stem, left_out = load_source(report, splits)
    meta = {
        "campaign": _token(campaign or stem),
        "seed": seed,
        "source": _token(report.name),
        "requested": size,
        "eligible": len(rows),
        "splits": "+".join(splits),
        "left_out": left_out,
    }
    return sample_rows(draw_sample(rows, size, seed)), meta


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
) -> dict:
    """`eval-calibrate --import`: validates the file, stores the ratings and measures the agreement. Nothing is
    written unless every line is valid and has its judgement in `run_evaluations`.

    With `judge` (`<provider>/<model>`, spec v0.9.0 RF-108) the ratings are compared with that judge's judgements and
    stored under `campaign`, which must differ from the campaign of the file (the original one keeps its link to its
    own judge). The ratings must equal those the original campaign stored; the report then shows that campaign's judge
    beside the requested one, against the same ratings. `judge_run` names the execution of the requested judge to
    read (required when it has more than one on these answers); the original judge is read in the executions of the
    judgements its ratings are linked to.

    `rubric` (the stored version, "3" by default, spec v0.10.0 D1) is the rubric of the requested judge's judgements;
    `more` adds other blocks, each a `(judge, execution, rubric)` (the execution may be `None` when the judge has one
    under that rubric). With a rubric other than judge.v3 or with `more`, the report has one block per judge,
    execution and rubric beside the original judge, the table of the four general claims with no source and the D2
    line (spec v0.10.0 D2); otherwise it is the v0.9.0 report, unchanged. The ratings are linked to the first block."""
    filled = read_filled(_read_text(path))
    meta = dict(filled.meta)
    original = meta.get("campaign")
    if judge_run is not None and judge is None:
        raise CalibrationError("--judge-run só vale com --judge: escolhe a execução do juiz comparado.")
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
    pairs = link(conn, filled, judge, run, version if judge is not None else None)
    others = _other_blocks(conn, filled, request_ids, (judge, run, version), extra)
    check_same_sample(conn, meta["campaign"], rater, pairs)
    stored = store(conn, meta["campaign"], rater, pairs, filled.blank)
    seed = int(meta["seed"]) if str(meta.get("seed", "")).lstrip("-").isdigit() else DEFAULT_SEED
    analysis = analyze(pairs, seed)
    comparison = None
    if before is not None:
        original_judge = ", ".join(sorted({p.judgement["judge"] for p in before}))
        original_runs = sorted({p.judgement["run"] for p in before})
        comparison = {
            "judge": judge,
            "judge_run": run,
            "campaign": meta["campaign"],
            "original_judge": original_judge,
            "original_runs": original_runs,
            "original_campaign": original,
            "pairs": before,
            "analysis": analyze(before, seed),
            "runs": {
                "A": judge_runs(conn, request_ids, judge, [run], version),
                "B": judge_runs(conn, request_ids, original_judge, original_runs),
            },
        }
        if extra or version != RUBRIC_VERSION:
            original_rubric = ", ".join(sorted({p.judgement["rubric_version"] for p in before}))
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
