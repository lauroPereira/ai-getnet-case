"""Calibration claim by claim (spec v0.11.0 D4, D5; task 89): what the raters get beside the sample CSV.

`eval-calibrate --sample --packets` writes, for every answer of the sample, a Markdown packet (`<id>.md`: question,
route, reply, the evidence the judge read, item by item with its cuts, and the claims numbered with boxes to mark) and
one `sample-claims.csv` (answer, number, kind, claim, the mark left blank and a column for a claim the rater adds).
The claims come from a recorded `judge.v5` judgement of the answer (its list only, never its verdicts) or, when the
answer has none, from one call to `judge_claims.v1` made while the sample is written; the packet says which.

Every claims CSV carries in its sample line the SHA-256 of its claims (`sha256_afirmacoes=`: each answer's sample and
request ids and its numbered claims); `--import` and `eval --claims-from` recompute it and refuse a file whose claims
were deleted, edited or retyped. `--seal` writes into `tests/scenarios/calibration_v0110.sha256` the SHA-256 of the
sample (each answer's identity and its numbered claims), the SHA-256 of the identity alone (checked before any claim
is listed) and the SHA-256 of every file written (the sample CSV, the claims CSV and each packet); `--import`
recomputes the first from the files the raters return and refuses a sample marked sealed whose hash differs. Nothing
here holds a judge's score or verdict."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from merchant_assistant.evaluation import evidence
from merchant_assistant.evaluation.judge import (
    CLAIM_KINDS,
    CLAIM_VERDICTS,
    CLAIMS_INPUT,
    UNSUPPORTED_VERDICTS,
    ClaimList,
    judge_spec_v3,
)
from merchant_assistant.guardrails.input import mask_sensitive

SEAL_NAME = "calibration_v0110"
SEAL_FILE = Path("tests") / "scenarios" / f"{SEAL_NAME}.sha256"
CLAIMS_COLUMNS = ("sample_id", "request_id", "n", "kind", "claim", "verdict", "added_claim")
CLAIMS_REQUIRED = ("sample_id", "request_id", "n", "kind", "claim", "verdict")
IDENTITY = ("sample_id", "request_id", "case_id", "route", "split")
IDENTITY_LINE = f"{SEAL_NAME}.amostra"  # the seal line of the identity alone (task 89 round 2, P3-3)
RECORDED = "gravadas"  # the claims of a recorded judge.v5 judgement
LISTED = "judge_claims.v1"  # the claims listed by a call made while the sample was written
MARK_LABELS = {
    "supported": "apoiada",
    "partial": "parcial",
    "generic": "genérica",
    "not_found": "não encontrada",
}
# The marks a rater may type: the four verdicts of judge.v5, in English or in the Portuguese of the packet.
MARK_ALIASES = {
    **{verdict: verdict for verdict in CLAIM_VERDICTS},
    "apoiada": "supported",
    "parcial": "partial",
    "generica": "generic",
    "nao_encontrada": "not_found",
}


class ClaimsError(ValueError):
    """A claims CSV or an exclusion file that cannot be read. `messages` are one problem per line."""

    def __init__(self, messages: list[str] | str) -> None:
        self.messages = [messages] if isinstance(messages, str) else list(messages)
        super().__init__("\n".join(self.messages))


# The labelling instruction the raters receive with the files (`docs/templates/instrucao-rotulagem-calibracao.md`).
# The `#` lines of the claims CSV and the note of each packet point to it and repeat none of its rules (review P2-1 of
# judge.v5 iteration 3): where a summary and the instruction could differ, the instruction holds.
LABELLING_INSTRUCTION = "instrucao-rotulagem-calibracao.md"
CLAIMS_INSTRUCTIONS = (
    "Calibração por afirmação (v0.11.0). Cada linha é uma afirmação da resposta, na ordem do pacote <sample_id>.md; "
    "marque a coluna verdict (supported, partial, generic ou not_found) pela instrução de rotulagem que acompanha "
    f"estes arquivos ({LABELLING_INSTRUCTION}); onde estas linhas diferirem dela, vale a instrução.",
    "Não altere n, kind nem claim e não apague linhas: o SHA-256 da linha 'amostra:' é conferido na importação. "
    "Afirmação que faltou: uma linha com o mesmo sample_id e request_id, n vazio e o texto em added_claim. Resposta "
    "sem afirmações aparece numa linha com n vazio. Salve como CSV UTF-8, com o mesmo separador.",
)


# --- the claims of each answer --------------------------------------------------------------------------------------


def recorded_claims(row: dict) -> list[dict] | None:
    """The claims of the recorded judge.v5 judgement of a report row (repetition 1), without their verdicts; None when
    the answer has no completed judgement with claims."""
    judged = row.get("judge") or {}
    listed = (judged.get("claims") or {}).get("claims") if judged.get("state") == "completed" else None
    if not listed:
        return None if listed is None else []
    return [{"n": int(c["n"]), "kind": c["kind"], "text": c["text"]} for c in sorted(listed, key=lambda c: c["n"])]


def list_claims(judge, given: dict) -> list[dict]:
    """One call to the claims prompt of a judge.v5 judge (`judge_claims.v1`), with the input that prompt reads (no
    evidence). Raises what the call raises: the sample is not written with an answer whose claims are missing."""
    if getattr(judge, "claims_prompt", None) is None:
        raise ValueError("the judge has no claims prompt: build it under --rubric v5")
    listing = {key: given.get(key) for key in CLAIMS_INPUT}
    spec = judge_spec_v3(judge.claims_prompt, listing, judge.claims_max_output_tokens)
    result = judge.llm.parse(spec, ClaimList, judge.meter)
    return [{"n": c.n, "kind": c.kind, "text": c.text} for c in sorted(result.value.claims, key=lambda c: c.n)]


def _safe(text: str) -> str:
    masked = mask_sensitive(text)[0]
    return " " + masked if masked[:1] in "=+-@\t\r" else masked


def _norm(text: str) -> str:
    return " ".join(str(text).split())


# --- the seal -------------------------------------------------------------------------------------------------------


def seal_digest(entries: Sequence[dict]) -> str:
    """SHA-256 of a sample: each answer's identity (sample, request, case, route, split) and its numbered claims
    (number, kind, text), whitespace normalized, in the order of the sample ids. The ratings and the marks are not in
    it: the blank sample and the files the raters return have the same hash."""
    canonical = [
        {
            **{key: _norm(entry.get(key, "")) for key in IDENTITY},
            "claims": [[int(c["n"]), _norm(c["kind"]), _norm(c["text"])] for c in sorted(entry["claims"], key=_n)],
        }
        for entry in sorted(entries, key=lambda entry: _norm(entry["sample_id"]))
    ]
    data = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _n(claim: dict) -> int:
    return int(claim["n"])


def claims_digest(answers: Sequence[dict]) -> str:
    """SHA-256 of a claims CSV (task 89 round 2, P2-2): each answer's sample and request ids and its numbered claims
    (number, kind, text), whitespace normalized, in the order of the sample ids. Marks and added claims are not in it,
    so the blank file and the file a rater returns have the same digest; a deleted line, or a kind or text changed, do
    not."""
    canonical = [
        [
            _norm(answer["sample_id"]),
            _norm(answer["request_id"]),
            [[int(c["n"]), _norm(c["kind"]), _norm(c["text"])] for c in sorted(answer["claims"], key=_n)],
        ]
        for answer in sorted(answers, key=lambda answer: (_norm(answer["sample_id"]), _norm(answer["request_id"])))
    ]
    data = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def rows_digest(claim_rows: Sequence[dict]) -> str:
    """`claims_digest` of the rows written into a claims CSV (a line with no `n` is an answer with no claim)."""
    answers: dict[str, dict] = {}
    for row in claim_rows:
        answer = answers.setdefault(row["request_id"], {**row, "claims": []})
        if row["n"]:
            answer["claims"].append({"n": row["n"], "kind": row["kind"], "text": row["claim"]})
    return claims_digest(list(answers.values()))


def verify_claims(found: ClaimsFile, name: str) -> list[str]:
    """The digest of the sample line, recomputed from the claims read; an empty list when it matches."""
    expected = found.meta.get("claims_sha256", "")
    if not expected:
        return [
            f"{name}: falta sha256_afirmacoes na linha 'amostra:'; use o CSV de afirmações gerado por --packets "
            "(sem ele não dá para saber se alguma linha foi apagada ou alterada). Nada foi gravado."
        ]
    answers = [
        {"sample_id": a.sample_id, "request_id": a.request_id, "claims": [vars(c) for c in a.claims]}
        for a in found.answers.values()
    ]
    actual = claims_digest(answers)
    if actual != expected:
        return [
            f"{name}: o SHA-256 das afirmações ({actual[:12]}…) não é o da linha 'amostra:' ({expected[:12]}…): alguma "
            "linha foi apagada ou alguma coluna n, kind ou claim mudou. Nada foi gravado."
        ]
    return []


def identity_digest(rows: Sequence[dict]) -> str:
    """SHA-256 of the identity of the answers of a sample alone (no claim): known as soon as the sample is drawn, so
    `--seal` compares it with an existing seal before any claim is listed (task 89 round 2, P3-3)."""
    canonical = sorted([_norm(row.get(key, "")) for key in IDENTITY] for row in rows)
    data = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def file_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


_DIGEST = re.compile(r"^([0-9a-f]{64})\b")
_SEAL_LINE = re.compile(r"^([0-9a-f]{64})\s+\*?(\S.*)$")


def read_seal(path: Path) -> str | None:
    """The hash written by `--seal`, or None when there is no seal file."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    for line in text.splitlines():
        found = _DIGEST.match(line.strip())
        if found:
            return found.group(1)
    raise ClaimsError(f"{path.name} não tem um SHA-256 na primeira linha de dados")


def read_seal_lines(path: Path) -> dict[str, str] | None:
    """Every `<sha256>  <name>` line of the seal file by name, or None when there is no seal file."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    return seal_lines(text)


def seal_lines(text: str) -> dict[str, str]:
    return {found.group(2).strip(): found.group(1) for line in text.splitlines() if (found := _SEAL_LINE.match(line))}


def seal_text(digest: str, identity: str, files: Sequence[tuple[str, str]], meta: dict) -> str:
    """The seal file: the hash of the sample, the hash of its identity and one line per file written, with the path
    relative to the folder of the sample CSV (`sha256sum -c --ignore-missing` checks those from that folder)."""
    return "".join(
        [
            f"# Selo da amostra de calibração da v0.11.0 (spec D5): campanha {meta['campaign']}, semente "
            f"{meta['seed']}, {meta['drawn']} respostas de {meta['source']}.\n",
            "# 1ª linha: SHA-256 da identidade de cada resposta e das suas afirmações numeradas (eval-calibrate "
            "--seal); eval-calibrate --import recusa a amostra se o hash dos arquivos devolvidos for outro.\n",
            f"# 2ª linha ({IDENTITY_LINE}): SHA-256 só da identidade das respostas (sample_id, request_id, case_id, "
            "rota, split), conferido por --seal antes de listar qualquer afirmação.\n",
            "# Demais linhas: SHA-256 de cada arquivo gravado (amostra, afirmações e pacotes com a resposta e a "
            "evidência), caminho relativo à pasta do sample.csv; confira com `sha256sum -c --ignore-missing "
            f"{SEAL_FILE.name}` a partir dessa pasta.\n",
            f"{digest}  {SEAL_NAME}\n",
            f"{identity}  {IDENTITY_LINE}\n",
            *[f"{sha}  {name}\n" for name, sha in files],
        ]
    )


def check_files(seal_path: Path, folder: Path) -> list[str]:
    """The files of the seal (every line but the two of the sample) whose SHA-256 is not the sealed one, relative to
    `folder` (the folder of the sample CSV): an empty list when all of them are intact."""
    lines = read_seal_lines(seal_path) or {}
    problems = []
    for name, sha in lines.items():
        if name in (SEAL_NAME, IDENTITY_LINE):
            continue
        try:
            found = file_digest((folder / name).read_bytes())
        except FileNotFoundError:
            problems.append(f"{name}: arquivo ausente")
            continue
        if found != sha:
            problems.append(f"{name}: SHA-256 {found[:12]}… não é o do selo ({sha[:12]}…)")
    return problems


# --- writing the files of a sample ----------------------------------------------------------------------------------


def claims_rows(rows: list[dict], claims: dict[str, list[dict]]) -> list[dict]:
    """The rows of `sample-claims.csv`, one per claim, in the order of the sample; the mark is left blank."""
    out = []
    for row in rows:
        if not claims[row["request_id"]]:  # an answer with no claim keeps a line: the file lists every answer
            out.append(dict.fromkeys(CLAIMS_COLUMNS, "") | {key: row[key] for key in ("sample_id", "request_id")})
        for claim in claims[row["request_id"]]:
            out.append(
                {
                    "sample_id": row["sample_id"],
                    "request_id": row["request_id"],
                    "n": str(claim["n"]),
                    "kind": claim["kind"],
                    "claim": _safe(claim["text"]),
                    "verdict": "",
                    "added_claim": "",
                }
            )
    return out


def seal_entries(rows: list[dict], claim_rows: list[dict]) -> list[dict]:
    """The entries the hash is taken over, built from the values written (the importer rebuilds them from the files)."""
    by_request: dict[str, list[dict]] = {row["request_id"]: [] for row in rows}
    for claim in (claim for claim in claim_rows if claim["n"]):
        by_request[claim["request_id"]].append({"n": claim["n"], "kind": claim["kind"], "text": claim["claim"]})
    return [{**{key: row[key] for key in IDENTITY}, "claims": by_request[row["request_id"]]} for row in rows]


def claims_csv_bytes(claim_rows: list[dict], stamp: str, *, delimiter: str = ";") -> bytes:
    """The claims CSV as written: UTF-8 with a BOM, the instructions as `#` lines and the sample line."""
    handle = io.StringIO(newline="")
    writer = csv.writer(handle, delimiter=delimiter, lineterminator="\r\n")
    for line in (*CLAIMS_INSTRUCTIONS, stamp):
        writer.writerow([f"# {line}"])
    writer.writerow(CLAIMS_COLUMNS)
    for row in claim_rows:
        writer.writerow([row[column] for column in CLAIMS_COLUMNS])
    return handle.getvalue().encode("utf-8-sig")


def write_claims_csv(path: Path, claim_rows: list[dict], stamp: str, *, delimiter: str = ";") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(claims_csv_bytes(claim_rows, stamp, delimiter=delimiter))


def _fence(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def _block(text: str) -> list[str]:
    fence = _fence(text)
    return [fence + "text", text, fence]


def packet(row: dict, given: dict, claims: list[dict], origin: str, meta: dict) -> str:
    """The Markdown a rater reads for one answer. Everything comes from the judge's input (masked again) and from the
    claims list; nothing of a judge's scores or verdicts."""
    sample_id = row["sample_id"]
    lines = [
        f"# {sample_id} — pacote de calibração",
        "",
        f"Campanha `{meta['campaign']}`, rota `{row['route']}`, split `{row['split']}`, status `{row['status']}`, "
        f"caso `{row['case_id']}`, requisição `{row['request_id']}`.",
        "",
        "## Mensagem do lojista",
        "",
        *_block(_safe(given["merchant_message"])),
        "",
        "## Resposta",
        "",
        *_block(_safe(given["reply"])),
        "",
        "## Fontes citadas",
        "",
        *([f"- {_safe(source)}" for source in given.get("sources", [])] or ["Nenhuma."]),
        "",
        "## Evidência (o que o juiz recebeu, item por item)",
    ]
    items = given.get("evidence", [])
    if not items:
        lines += ["", "Nenhum item: nenhuma ferramenta nem trecho foi usado."]
    for number, item in enumerate(items, start=1):
        head = f"### Item {number} — `{item['kind']}`: {_safe(item.get('label', ''))}"
        lines += ["", head, ""]
        if item.get("url"):
            lines += [f"URL: {_safe(item['url'])}", ""]
        if item.get("cut"):
            lines += [
                f"Cortado para caber no limite de {evidence.EVIDENCE_LIMIT_CHARS} caracteres da evidência; "
                f"`{evidence.CUT_MARK.strip()}` marca o corte. O juiz recebeu este mesmo texto.",
                "",
            ]
        lines += _block(_safe(item.get("text", "")))
    notes = given.get("evidence_notes", [])
    if notes:
        from merchant_assistant.evaluation.calibration import NOTES_PT

        lines += ["", "Notas da evidência:", "", *[f"- {NOTES_PT.get(note, note)}" for note in notes]]
    cut = given.get("evidence_truncation") or {}
    if cut.get("truncated"):
        lines += [
            "",
            f"A evidência gravada tinha {cut.get('original_chars')} caracteres; o juiz recebeu {cut.get('kept_chars')} "
            f"(limite {cut.get('limit_chars')}), com {cut.get('items_cut')} de {cut.get('items')} itens cortados.",
        ]
    source = (
        "listadas pela chamada `judge_claims.v1` feita na geração da amostra"
        if origin == LISTED
        else "da lista gravada no julgamento `judge.v5` desta resposta (só a lista; nenhum veredito do juiz)"
    )
    lines += [
        "",
        "## Afirmações",
        "",
        f"Afirmações {source}. Marque cada uma no `sample-claims.csv` (coluna `verdict`) pela instrução de rotulagem "
        f"que acompanha estes arquivos (`{LABELLING_INSTRUCTION}`); onde esta nota diferir dela, vale a instrução.",
        "",
    ]
    if not claims:
        lines.append("A lista está vazia: a resposta não afirma nada.")
    boxes = " ".join(f"☐ {verdict}" for verdict in CLAIM_VERDICTS)
    for claim in claims:
        lines += [f"{claim['n']}. **[{claim['kind']}]** {_safe(claim['text'])}  ", f"   {boxes}"]
    return "\n".join(lines) + "\n"


def packets_dir(csv_path: Path) -> Path:
    return csv_path.with_name(f"{csv_path.stem}-pacotes")


def claims_path(csv_path: Path) -> Path:
    return csv_path.with_name(f"{csv_path.stem}-claims{csv_path.suffix}")


def packet_files(
    csv_path: Path,
    rows: list[dict],
    drawn: list[dict],
    claims: dict[str, list[dict]],
    origins: dict[str, str],
    meta: dict,
    stamp: str,
    *,
    delimiter: str = ";",
) -> dict[Path, bytes]:
    """The bytes of the claims CSV (beside the sample CSV) and of one packet per answer (in `<stem>-pacotes/`), by
    path, in that order. Nothing is written here, so a seal can be checked against them first."""
    by_request = {row["request_id"]: row for row in drawn}
    files = {claims_path(csv_path): claims_csv_bytes(claims_rows(rows, claims), stamp, delimiter=delimiter)}
    folder = packets_dir(csv_path)
    for row in rows:
        given = by_request[row["request_id"]]["judge_input"]
        text = packet(row, given, claims[row["request_id"]], origins[row["request_id"]], meta)
        files[folder / f"{row['sample_id']}.md"] = text.encode("utf-8")
    return files


def write_files(files: dict[Path, bytes]) -> None:
    for path, data in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


# --- reading the claims a rater marked ------------------------------------------------------------------------------


@dataclass
class ClaimMark:
    n: int
    kind: str
    text: str
    verdict: str | None
    line: int


@dataclass
class AnswerClaims:
    sample_id: str
    request_id: str
    claims: list[ClaimMark] = field(default_factory=list)
    added: list[tuple[str, str, int]] = field(default_factory=list)  # (text, verdict, line)

    def marked(self) -> bool:
        return any(c.verdict for c in self.claims) or bool(self.added)

    def unsupported(self) -> bool:
        """D3 applied to the marks: a claim that is not `standard` (or one the rater added) marked generic or
        not_found."""
        listed = any(c.verdict in UNSUPPORTED_VERDICTS and c.kind != "standard" for c in self.claims)
        return listed or any(verdict in UNSUPPORTED_VERDICTS for _, verdict, _ in self.added)

    def listing(self) -> list[tuple[int, str, str]]:
        return [(c.n, c.kind, _norm(c.text)) for c in sorted(self.claims, key=lambda c: c.n)]


@dataclass
class ClaimsFile:
    meta: dict[str, str]
    answers: dict[str, AnswerClaims]  # request id -> claims


_HEADER = re.compile(r'^"?sample_id"?([;,\t])')
_META = re.compile(r"(\w+)=([^;]*)")


def _plain(text: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().strip().casefold()


def mark_of(raw: str) -> str | None:
    """The verdict a rater typed (`not found`, `Não encontrada` and `not-found` are `not_found`), or None."""
    return MARK_ALIASES.get("_".join(_plain(raw).replace("-", " ").split()))


def read_claims(text: str, meta_keys: dict[str, str]) -> ClaimsFile:
    """Parses and validates a `sample-claims.csv`. Every problem is collected with its line."""
    text = text.lstrip("\ufeff")
    found = next((match for line in text.splitlines() if (match := _HEADER.match(line))), None)
    if found is None:
        raise ClaimsError(["não encontrei o cabeçalho com a coluna sample_id: use o arquivo gerado por --packets."])
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=found.group(1))
    meta: dict[str, str] = {}
    header: list[str] | None = None
    errors: list[str] = []
    answers: dict[str, AnswerClaims] = {}
    owner: dict[str, str] = {}
    last = 0
    for cells in reader:
        start, last = last + 1, reader.line_num
        cells = [cell.strip() for cell in cells]
        if not any(cells):
            continue
        if cells[0].startswith("#"):
            if cells[0].lstrip("# ").startswith("amostra:"):
                meta |= {meta_keys[k]: v.strip() for k, v in _META.findall(cells[0]) if k in meta_keys}
            continue
        if header is None:
            header = [_plain(cell) for cell in cells]
            missing = [column for column in CLAIMS_REQUIRED if column not in header]
            if missing:
                raise ClaimsError(
                    [f"linha {start}: faltam as colunas {', '.join(missing)} no cabeçalho (é o CSV de afirmações?)."]
                )
            continue
        if any(cells[len(header) :]):
            errors.append(f"linha {start}: {len(cells)} colunas para um cabeçalho de {len(header)}.")
            continue
        values = dict(zip(header, cells, strict=False))
        _claim_row(values, start, answers, owner, errors)
    if header is None:
        raise ClaimsError(["não encontrei o cabeçalho com a coluna sample_id."])
    if errors:
        raise ClaimsError(errors)
    return ClaimsFile(meta, answers)


def _claim_row(
    values: dict[str, str], line: int, answers: dict[str, AnswerClaims], owner: dict[str, str], errors: list[str]
) -> None:
    sample_id, request_id = values.get("sample_id", ""), values.get("request_id", "")
    where = f"linha {line} ({sample_id or 'sem sample_id'}"
    problems = []
    if not sample_id or not request_id:
        problems.append("sample_id e request_id não podem ficar vazios")
    elif owner.setdefault(sample_id, request_id) != request_id:
        problems.append(f"sample_id {sample_id} já aparece com a requisição {owner[sample_id]}")
    raw_n, raw_mark = values.get("n", ""), values.get("verdict", "")
    added = values.get("added_claim", "")
    mark = mark_of(raw_mark) if raw_mark else None
    if raw_mark and mark is None:
        problems.append(f"verdict precisa ser supported, partial, generic ou not_found, recebi {raw_mark!r}")
    answer = answers.setdefault(request_id, AnswerClaims(sample_id, request_id))
    if raw_n:
        if not raw_n.isdigit() or int(raw_n) < 1:
            problems.append(f"n precisa ser um inteiro a partir de 1, recebi {raw_n!r}")
        elif any(claim.n == int(raw_n) for claim in answer.claims):
            problems.append(f"a afirmação {raw_n} já aparece para esta resposta")
        kind = values.get("kind", "")
        if kind not in CLAIM_KINDS:
            problems.append(f"kind {kind!r} desconhecido (não altere as colunas n, kind e claim)")
        if added:
            problems.append("added_claim só vale numa linha nova, com n vazio")
        if not problems:
            answer.claims.append(ClaimMark(int(raw_n), kind, values.get("claim", ""), mark, line))
    elif added:
        if not raw_mark:
            problems.append("a afirmação acrescentada precisa de verdict")
        if not problems:
            answer.added.append((added, mark, line))
    elif raw_mark or values.get("claim", ""):
        problems.append("linha sem n e sem added_claim: para acrescentar uma afirmação, escreva-a em added_claim")
    if problems:
        errors.append(f"{where}): {'; '.join(problems)}.")


# --- the calibrated answers left out of a new sample ----------------------------------------------------------------


def excluded_ids(paths: Sequence[Path], read_text) -> set[str]:
    """The request ids of earlier calibration CSVs (`--exclude`): those answers stay out of the new sample (spec
    v0.11.0 D5). New answers to the same cases are not excluded (decision of the Supervisor in the review of task 89:
    the calibration measures the judge, and an answer never calibrated is new to it)."""
    requests: set[str] = set()
    for path in paths:
        text = read_text(path).lstrip("\ufeff")
        found = next((match for line in text.splitlines() if (match := _HEADER.match(line))), None)
        if found is None:
            raise ClaimsError(f"{path.name}: não encontrei o cabeçalho com a coluna sample_id.")
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=found.group(1))
        header: list[str] | None = None
        for cells in reader:
            cells = [cell.strip() for cell in cells]
            if not any(cells) or cells[0].startswith("#"):
                continue
            if header is None:
                header = [_plain(cell) for cell in cells]
                if "request_id" not in header:
                    raise ClaimsError(f"{path.name}: falta a coluna request_id no cabeçalho.")
                continue
            values = dict(zip(header, cells, strict=False))
            if values.get("request_id"):
                requests.add(values["request_id"])
        if header is None:
            raise ClaimsError(f"{path.name}: nenhuma linha de dados.")
    return requests
