"""Task 88 (spec v0.11.0 D3, CA-61): `judge_claims.v1` and `judge.v5`, the judge claim by claim. The first call lists
the claims of the reply without the evidence, the second gives a verdict per claim and the four criteria, and
`unsupported_claim` is computed in code from the verdicts. Offline: the scripted model answers both calls."""

from __future__ import annotations

import hashlib
import json
import re

import pytest
from openai.lib._pydantic import to_strict_json_schema
from pydantic import SecretStr, ValidationError

from merchant_assistant.config import PROJECT_ROOT, Settings
from merchant_assistant.data.db import connect
from merchant_assistant.evaluation import judge as judge_module
from merchant_assistant.evaluation.judge import (
    CLAIM_KINDS,
    CLAIM_VERDICTS,
    CRITERIA,
    RUBRIC_VERSION,
    ClaimList,
    JudgeScoreV3,
    JudgeScoreV5,
    claim_counts,
    resolve_judge,
    save_evaluation,
    unsupported_from_claims,
    validate_judge,
)
from merchant_assistant.evaluation.scripted_judge import claims_handler, handler, scripted_judge, verdicts_handler
from merchant_assistant.llm.anthropic_llm import output_format
from merchant_assistant.llm.base import LLMError, NullMeter, Usage
from merchant_assistant.llm.prompts import load_prompt, prompt_versions
from merchant_assistant.llm.scripted import ScriptedLLM

PROMPTS = PROJECT_ROOT / "prompts"
AGENT = ("openai", "gpt-6-luna")
# judge.v3.md and judge.v4.md as v0.10.0 shipped them (LF line endings): v5 is a new file, the old ones do not move.
SHIPPED = {
    "judge.v3.md": "45d59f0cfebacd6b19cbf7c20532e8d8d409404f77d423e0a2e25216f75152bd",
    "judge.v4.md": "7c416d5d6b3845f7c3ffac9d1cc085a301d7e46ca88ecb7e9a56dea7e5e32e3c",
}
TOOL = {"kind": "tool_result", "label": "get_receivables_schedule", "text": '{"net_amount": "R$ 120,00"}'}


def data(reply: str, evidence=(TOOL,), notes=()) -> dict:
    return {
        "merchant_message": "Quanto vou receber ontem de recebíveis?",
        "status": "answered",
        "route": "support",
        "sources": ["Receivables (your account)"],
        "evidence": list(evidence),
        "evidence_truncation": {"truncated": False},
        "evidence_notes": list(notes),
        "reply": reply,
    }


def flat(text: str) -> str:
    return " ".join(text.split())


class CountingMeter:
    """Every settled call costs US$ 0.001: the judgement's cost is the sum of its calls."""

    def __init__(self) -> None:
        self.cost_usd, self.reserved = 0.0, []

    def reserve(self, **kwargs):
        self.reserved.append(kwargs)

    def settle(self, reservation, usage):
        self.cost_usd += 0.001


def v5(llm=None, meter=None):
    return scripted_judge(PROMPTS, meter or NullMeter(), llm, rubric="v5")


# --- the prompts ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(SHIPPED))
def test_judge_v3_and_v4_are_byte_for_byte_the_shipped_files(name):
    raw = (PROMPTS / name).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == SHIPPED[name]


def test_the_two_new_prompts_load_and_say_what_d3_asks():
    claims, v5_prompt = load_prompt(PROMPTS, "judge_claims", "1"), load_prompt(PROMPTS, "judge", "5")
    assert (claims.ref, v5_prompt.ref) == ("judge_claims@1", "judge@5")
    listing = flat(claims.template)
    assert all(f"- {kind}:" in claims.template for kind in CLAIM_KINDS)
    assert "do not see any evidence" in listing and "Split a sentence that says two things" in listing
    text = flat(v5_prompt.template)
    assert all(f"- {verdict}:" in v5_prompt.template for verdict in CLAIM_VERDICTS)
    assert "A web_page is evidence in full" in text and "A web_summary is not a page and does not prove a fact" in text
    assert "guidance or a generalization stated as fact with no passage that sustains it" in text
    assert "at most 200 characters" in text and "Give exactly one verdict for each claim number" in text
    assert "unsupported_claim" not in text  # the verdict is computed in code, never asked of the model
    assert all(criterion in text for criterion in CRITERIA)


def test_judge_v5_says_the_verdict_of_each_web_case():
    # review P3-2: a claim backed only by the web_summary, one it contradicts, and guidance in a web reply
    text = flat(load_prompt(PROMPTS, "judge", "5").template)
    assert "a claim found only in a web_summary is never supported" in text
    assert "Also partial: a claim consistent with the web_summary and with the listed sources when no web_page" in text
    assert "A claim that the web_summary or the listed sources contradict is not_found" in text
    assert "This holds in a reply that came from a web search too" in text
    assert "does not make such a claim partial" in text
    assert "mark such claims partial" not in text  # the v0.11.0 draft let web guidance pass as partial


def test_judge_v5_iteration_2_says_the_verdict_of_gaps_next_steps_handoffs_and_caveats():
    # D6(a) iteration 2: the seven false positives of iteration 1 on the 24 tuning answers, by cause, and the
    # rules that keep the generic phrases the human marked (contract dependence) and add a contradicted "nothing more"
    text = flat(load_prompt(PROMPTS, "judge", "5").template)
    assert "a claim that only restates an item or draws its direct consequence" in text  # S02
    assert "states a gap, not a fact: supported" in text  # S20
    assert "It is not_found only when an item shows the thing was found or read" in text
    assert "Guidance that sends the merchant to a Getnet channel" in text and "partial otherwise" in text  # S04, S20
    assert "Guidance that implies a fact the evidence does not hold" in text and "is still generic" in text
    assert "An offer of what the assistant can still do" in text  # S20
    assert "When the status is handoff, a statement that the case was handed to a person" in text  # S15, S22
    assert "A promise beyond that (a deadline, an outcome, a cancellation) still needs an item" in text
    assert "A caveat that only qualifies a figure the reply gives as approximate" in text  # S18, S19
    assert "A statement about what applies to the merchant or to a Getnet product, rate or contract is not" in text
    # review P3-2 of iteration 2: the verdict of each of these rules, and the heading of the block, are fixed too
    assert "(answer general questions, hand the case over) is courtesy: partial." in text
    assert "who will reply or get in touch restates that status: supported, with the status" in text
    assert "(a quote that moves during the day, a forecast that may change), adds no fact: partial." in text
    assert (  # the adjustment for iteration 3 adds the date of the reply to the heading
        "Gaps, next steps, courtesy, handoffs, caveats and the date of the reply get the verdicts below, not generic "
        "or not_found, except where a rule below says otherwise:" in text
    )
    assert "Gaps, next steps and caveats are not claims without support" not in text  # review P3-1: wider than them
    # kept and sharpened: the generic phrases of S01, S16 and S21, and the contradiction of S13
    assert "depend on the contract, the profile or an analysis is generic when no item states that dependence" in text
    assert "Partial is not for a claim that only shares a topic with an item" in text
    assert "A claim that there is nothing more (no other step, option or channel) when an item lists one" in text


def test_judge_v5_adjustment_for_iteration_3_says_the_verdict_of_an_absent_figure_and_of_the_date_of_the_reply():
    # D6(a) iteration 2 left two false positives: "Getnet gives no single rate for <a product no item names>" read as
    # a fact (S04, claim 1) and "today, 4 November 2026" read as a date to find in the evidence (S18, claim 1)
    text = flat(load_prompt(PROMPTS, "judge", "5").template)
    assert "A statement that the sources do not state what the merchant asked" in text
    assert "also when worded as Getnet not stating it." in text
    assert "A statement that Getnet or a product does not offer, accept, charge, allow or have something" in text
    assert "It is not_found only when an item shows the thing was found or read, or states it" in text
    assert "A statement of the date of the reply's day, or of the day before or after it," in text
    assert "only places the reply in time and adds no fact: partial." in text
    assert "The date of an event (a payment, a deadline, a request) is not such a statement." in text
    # what marks the generic phrases stays: a "nothing more" is not a gap (S13), the contract dependence (S01, S16,
    # S21), and the account data no tool_result shows
    assert "as does a claim that there is nothing more (no other step, option or channel)." in text
    assert "depend on the contract, the profile or an analysis is generic when no item states that dependence" in text
    assert "A specific of the merchant's own account (an amount, a date, a status) that no tool_result shows" in text


def test_judge_v5_iteration_3_keeps_the_contract_and_the_proposal_out_of_the_channels():
    # review P2-2 of iteration 2: "see your contract for the conditions" was a channel (partial) and a contract
    # dependence (generic) at once; now it is generic, in the rule of the dependence and in the rule of the channel
    text = flat(load_prompt(PROMPTS, "judge", "5").template)
    assert "a Getnet channel (the app, the portal, support, a person) to see what the reply could not give" in text
    assert "their proposal or contract, support" not in text
    assert (
        "Guidance that sends the merchant to their contract or proposal to see the conditions that apply, with no "
        "item that says so, is generic for the same reason: the contract and the proposal are not channels" in text
    )
    assert (
        "The contract and the proposal are not channels: guidance that sends the merchant to their contract or "
        "proposal to see the conditions that apply, with no item that says so, is generic" in text
    )


# review P2-1 of iteration 2: the human and the two members of the panel label by the same rules the judge reads.
# Each pair is the same rule, with its verdict, in the prompt and in the labelling instruction.
INSTRUCTION = PROJECT_ROOT / "docs" / "templates" / "instrucao-rotulagem-calibracao.md"
SAME_RULES = {
    "consequência direta": (
        "Also supported: a claim that only restates an item or draws its direct consequence",
        "Também `supported`: afirmação que só repete um item ou tira dele uma consequência direta",
    ),
    "partial não é para quem só divide o tema": (
        "Partial is not for a claim that only shares a topic with an item: a rule the item does not state stays "
        "generic or not_found.",
        "`partial` não é para afirmação que só divide o tema com um item: regra que o item não diz fica `generic` ou "
        "`not_found`.",
    ),
    "dependência de contrato, perfil ou análise": (
        "depend on the contract, the profile or an analysis is generic when no item states that dependence, even if "
        "an item is about the same rate or product.",
        "dependem do contrato, do perfil ou de uma análise é `generic` quando nenhum item diz essa dependência, mesmo "
        "que um item trate da mesma taxa ou do mesmo produto.",
    ),
    # review P3-2 of iteration 3: "terms" is "termos", not "prazos"
    "condições, taxas ou termos": (
        "the merchant's conditions, rates or terms depend on the contract",
        "as condições, taxas ou termos do lojista dependem do contrato",
    ),
    "contrato ou proposta sem item": (
        "their contract or proposal to see the conditions that apply, with no item that says so, is generic for the "
        "same reason: the contract and the proposal are not channels",
        'ao contrato ou à proposta "para ver as condições que se aplicam", sem item que diga isso, é `generic` pelo '
        "mesmo motivo: contrato e proposta não são canais",
    ),
    # review P3-1 of iteration 3: each "also not_found" rule carries its own verdict in both files
    "não há outras etapas": (
        "A claim that there is nothing more (no other step, option or channel) when an item lists one is not_found.",
        "Afirmação de que não há mais nada (não há outras etapas, opções ou canais) quando um item lista outra é "
        "`not_found`.",
    ),
    "contradição pelo resumo ou pelas fontes": (
        "A claim that the web_summary or the listed sources contradict is not_found.",
        "Afirmação que o resumo da busca ou as fontes contradizem é `not_found`.",
    ),
    "dado da conta sem tool_result": (
        "A specific of the merchant's own account (an amount, a date, a status) that no tool_result shows is "
        "not_found.",
        "Dado da conta do lojista (valor, data, status) que nenhum `tool_result` mostra é `not_found`.",
    ),
    "web_summary nunca é supported": (
        "a claim found only in a web_summary is never supported.",
        "Afirmação encontrada só no resumo da busca nunca é `supported`.",
    ),
    "web_summary coerente": (
        "Also partial: a claim consistent with the web_summary and with the listed sources when no web_page holds it.",
        "Também `partial`: afirmação coerente com o resumo da busca (`web_summary`) e com as fontes listadas quando "
        "nenhuma página citada (`web_page`) a contém.",
    ),
    "standard não conta contra a resposta": (
        "A claim of kind standard (handing over, a protocol, a request for clarification, courtesy) gets a verdict "
        "too, but a standard phrase is not held against the reply.",
        "Afirmação do tipo `standard` (encaminhamento, protocolo, pedido de esclarecimento, cortesia) também recebe "
        "marca, mas não conta contra a resposta.",
    ),
    "cabeçalho": (
        "Gaps, next steps, courtesy, handoffs, caveats and the date of the reply get the verdicts below, not generic "
        "or not_found, except where a rule below says otherwise:",
        "Lacunas, próximos passos, cortesia, encaminhamento, ressalvas e a data da resposta recebem as marcas abaixo, "
        "e não `generic` nem `not_found`, salvo onde a regra diz outra coisa:",
    ),
    "lacuna": (
        "states a gap, not a fact: supported",
        "é lacuna, não fato: `supported`",
    ),
    # adjustment for iteration 3 of D6(a): a source that does not give what was asked is a gap; "nothing more" is not
    "fonte que não informa": (
        "A statement that the sources do not state what the merchant asked (no rate is stated for that product) is "
        "such a gap too, also when worded as Getnet not stating it.",
        "Dizer que as fontes não informam o que o lojista perguntou (nenhuma taxa é informada para aquele produto) "
        'também é lacuna, mesmo quando dito como "a Getnet não informa".',
    ),
    # review P2-1 of 7877a60: a fact about what Getnet or a product does not offer is not a gap
    "o que a Getnet não oferece é fato": (
        "A statement that Getnet or a product does not offer, accept, charge, allow or have something is a fact, not "
        "such a gap: it follows the not_found rule above,",
        "Dizer que a Getnet ou um produto não oferece, não aceita, não cobra, não permite ou não tem algo é fato, não "
        "essa lacuna: segue a regra do `not_found` acima,",
    ),
    "lacuna encontrada": (
        "It is not_found only when an item shows the thing was found or read, or states it.",
        "Só é `not_found` quando um item mostra que a coisa foi encontrada ou lida, ou a informa.",
    ),
    "não há mais nada não é lacuna": (
        "it follows the not_found rule above, as does a claim that there is nothing more (no other step, option or "
        "channel).",
        "segue a regra do `not_found` acima, como a afirmação de que não há mais nada (não há outras etapas, opções ou "
        "canais).",
    ),
    "canal Getnet": (
        "a Getnet channel (the app, the portal, support, a person) to see what the reply could not give, or to go on "
        "after a gap the reply states, is a next step: supported when an item names that channel, partial otherwise.",
        "a um canal da Getnet (o app, o portal, o atendimento, uma pessoa) para ver o que a resposta não deu, ou para "
        "seguir depois de uma lacuna que a resposta diz, é próximo passo: `supported` quando um item cita esse canal, "
        "`partial` quando nenhum cita.",
    ),
    "contrato e proposta não são canais": (
        "The contract and the proposal are not channels: guidance that sends the merchant to their contract or "
        "proposal to see the conditions that apply, with no item that says so, is generic",
        'Contrato e proposta não são canais: mandar o lojista ao contrato ou à proposta "para ver as condições que se '
        'aplicam", sem item que diga isso, é `generic`',
    ),
    # review P3-2 of iteration 3: a sentence with a channel and the contract is generic, the contract part prevails
    "canal e contrato na mesma frase": (
        "A sentence that sends the merchant to a Getnet channel and also to their contract or proposal to see the "
        "conditions is generic: the part about the contract prevails.",
        "Frase que manda o lojista a um canal da Getnet e também ao contrato ou à proposta para ver as condições é "
        "`generic`: a parte do contrato prevalece.",
    ),
    "orientação que supõe fato": (
        "(that a bank or another third party must solve it, that waiting will solve it) is still generic.",
        "(que um banco ou outro terceiro precisa resolver, que esperar resolve) continua `generic`.",
    ),
    "cortesia": (
        "(answer general questions, hand the case over) is courtesy: partial.",
        "(responder dúvidas gerais, encaminhar o caso) é cortesia: `partial`.",
    ),
    "handoff": (
        "When the status is handoff, a statement that the case was handed to a person who will reply or get in touch "
        "restates that status: supported",
        "Com status `handoff`, dizer que o caso foi passado a uma pessoa que vai responder ou entrar em contato repete "
        "o status: `supported`.",
    ),
    "promessa além do handoff": (  # review P3-2 of iteration 3: with no item, the promise is not_found
        "A promise beyond that (a deadline, an outcome, a cancellation) still needs an item that says it: with no such "
        "item, it is not_found.",
        "Promessa além disso (um prazo, um resultado, um cancelamento) continua precisando de um item que a diga: sem "
        "esse item, é `not_found`.",
    ),
    "ressalva sobre número da própria resposta": (
        "A caveat that only qualifies a figure the reply gives as approximate, or as changing over time or between "
        "providers (a quote that moves during the day, a forecast that may change), adds no fact: partial.",
        "Ressalva que só qualifica um número que a própria resposta dá, como aproximado ou como algo que muda com o "
        "tempo ou entre fornecedores (uma cotação que muda durante o dia, uma previsão que pode mudar), não acrescenta "
        "fato: `partial`.",
    ),
    "o que vale para o lojista não é ressalva": (
        "A statement about what applies to the merchant or to a Getnet product, rate or contract is not such a caveat.",
        "Dizer o que vale para o lojista ou para um produto, taxa ou contrato da Getnet não é essa ressalva.",
    ),
    # adjustment for iteration 3 of D6(a): the date of the reply places it in time; another date for that day is not
    "data da resposta": (
        "A statement of the date of the reply's day, or of the day before or after it, only places the reply in time "
        "and adds no fact: partial. It is not_found when an item or the merchant message shows another date for that "
        "day.",
        "Dizer a data do dia da resposta, ou a do dia anterior ou seguinte, só situa a resposta no tempo e não "
        "acrescenta fato: `partial`. É `not_found` quando um item ou a mensagem do lojista mostra outra data para esse "
        "dia.",
    ),
    "data de um acontecimento": (
        "The date of an event (a payment, a deadline, a request) is not such a statement.",
        "A data de um acontecimento (um pagamento, um prazo, um pedido) não é essa afirmação.",
    ),
}


@pytest.mark.parametrize("rule", sorted(SAME_RULES))
def test_the_labelling_instruction_has_each_rule_of_judge_v5_with_the_same_verdict(rule):
    prompt_phrase, instruction_phrase = SAME_RULES[rule]
    assert prompt_phrase in flat(load_prompt(PROMPTS, "judge", "5").template), rule
    assert instruction_phrase in flat(INSTRUCTION.read_text(encoding="utf-8")), rule


VERDICT_WORD = re.compile(r"\b(supported|partial|generic|not_found)\b", re.IGNORECASE)


def rule_bullets(block: str) -> list[str]:
    return [flat(part) for part in re.split(r"\n(?=- )|\n\n", block) if part.lstrip().startswith("- ")]


def rule_marks(block: str) -> list[list[str]]:
    """The verdicts each rule bullet of a block names, in order: one list per bullet."""
    return [[word.lower() for word in VERDICT_WORD.findall(bullet)] for bullet in rule_bullets(block)]


def rule_sentences(bullet: str) -> int:
    """How many sentences a rule bullet has (a sentence ends with a full stop before a capital letter or a quote)."""
    return len(re.split(r"(?<=\.)\s+(?=[A-ZÀ-Ý\"'`])", bullet))


def test_each_rule_of_judge_v5_names_the_same_verdicts_in_the_same_order_in_the_labelling_instruction():
    # review P3-4 of the adjustment for iteration 3: a sentence with a verdict added to one side only (a new case, an
    # exception) changes that bullet's marks there and not on the other side, even when every pair above still matches
    prompt = load_prompt(PROMPTS, "judge", "5").template
    prompt = prompt.split("give one verdict:", 1)[1].split("Then score each criterion", 1)[0]
    instruction = INSTRUCTION.read_text(encoding="utf-8")
    instruction = instruction.split("## Marca de cada afirmação", 1)[1].split("## Notas de cada resposta", 1)[0]
    marks = rule_marks(prompt)
    assert len(marks) == 10 and marks[0] == ["supported", "supported"]  # four verdicts and six other rules
    assert marks[-1] == ["partial", "not_found"]  # the date of the reply
    assert rule_marks(instruction) == marks
    assert marks[4] == ["supported", "not_found", "not_found"]  # the gap, its exception and what is not a gap
    # review P2-1 of 7877a60: a sentence without a verdict added to one side (say, "a statement that Getnet does not
    # offer something is such a gap too") changes the number of sentences of that rule; the six rules after the
    # heading have as many sentences in the prompt as in the instruction
    heading = re.compile(r"^- \*\*[^*]+\*\* ")
    rules = [rule_sentences(heading.sub("- ", b)) for b in rule_bullets(instruction)[4:]]
    assert [rule_sentences(b) for b in rule_bullets(prompt)[4:]] == rules


def test_the_labelling_instruction_lists_no_contract_or_proposal_among_the_channels():
    text = flat(INSTRUCTION.read_text(encoding="utf-8"))
    listed = text.split("canal da Getnet (", 1)[1].split(")", 1)[0]
    assert listed == "o app, o portal, o atendimento, uma pessoa"


def test_prompt_versions_names_judge_claims_only_when_the_default_rubric_uses_it(monkeypatch):
    # review P3-3: /ready and the run snapshots name the prompts in use; judge_claims is used by judge.v5 only
    versions = prompt_versions(PROMPTS)
    assert RUBRIC_VERSION == "5" and versions["judge"] == "5" and versions["judge_claims"] == "1"
    monkeypatch.setattr(judge_module, "RUBRIC_VERSION", "3")
    assert {k: v for k, v in prompt_versions(PROMPTS).items() if k.startswith("judge")} == {"judge": "3"}
    monkeypatch.setattr(judge_module, "RUBRIC_VERSION", "5")
    assert {k: v for k, v in prompt_versions(PROMPTS).items() if k.startswith("judge")} == {
        "judge": "5",
        "judge_claims": "1",
    }


# --- the schemas ----------------------------------------------------------------------------------------------------


def test_the_claim_list_schema_accepts_the_seven_kinds_and_distinct_numbers_only():
    listed = ClaimList.model_validate({"claims": [{"n": 1, "text": "R$ 120,00", "kind": kind} for kind in ["value"]]})
    assert listed.claims[0].kind == "value"
    for kind in CLAIM_KINDS:
        ClaimList.model_validate({"claims": [{"n": 1, "text": "x", "kind": kind}]})
    for bad in (
        [{"n": 1, "text": "x", "kind": "opinion"}],
        [{"n": 1, "text": "x", "kind": "fact"}, {"n": 1, "text": "y", "kind": "fact"}],
        [{"n": 0, "text": "x", "kind": "fact"}],
        [{"text": "x", "kind": "fact"}],
    ):
        with pytest.raises(ValidationError):
            ClaimList.model_validate({"claims": bad})
    assert ClaimList.model_validate({"claims": []}).claims == []


def test_the_v5_judgement_has_verdicts_and_four_criteria_and_no_unsupported_claim():
    assert "unsupported_claim" not in JudgeScoreV5.model_fields and "unsupported_claim" in JudgeScoreV3.model_fields
    assert set(JudgeScoreV5.model_fields) == {"claim_verdicts", *CRITERIA, *(f"{c}_reason" for c in CRITERIA)}
    base = {c: 4 for c in CRITERIA} | {f"{c}_reason": "ok" for c in CRITERIA}
    long_quote = [{"n": 1, "verdict": "partial", "support": "s" * 300}]
    score = JudgeScoreV5.model_validate(base | {"claim_verdicts": long_quote})
    assert len(score.claim_verdicts[0].support) == 200  # the quote is cut, the judgement stays
    with pytest.raises(ValidationError):
        JudgeScoreV5.model_validate(base | {"claim_verdicts": [{"n": 1, "verdict": "maybe", "support": ""}]})
    with pytest.raises(ValidationError, match="between 1 and 5"):
        JudgeScoreV5.model_validate(base | {"relevance": 6, "claim_verdicts": []})


@pytest.mark.parametrize("schema", [ClaimList, JudgeScoreV5])
def test_both_schemas_are_strict_structured_outputs_for_openai_deepseek_and_anthropic(schema):
    for strict in (to_strict_json_schema(schema), output_format(schema)["schema"]):
        assert strict["additionalProperties"] is False and sorted(strict["required"]) == sorted(schema.model_fields)
        (nested,) = strict["$defs"].values()
        assert nested["additionalProperties"] is False and len(nested["required"]) == 3


# --- the verdict in code --------------------------------------------------------------------------------------------


def claims_of(*kinds):
    return [{"n": n, "text": f"claim {n}", "kind": kind} for n, kind in enumerate(kinds, start=1)]


def verdicts_of(*verdicts):
    return [{"n": n, "verdict": verdict, "support": ""} for n, verdict in enumerate(verdicts, start=1)]


@pytest.mark.parametrize(
    ("kinds", "verdicts", "expected"),
    [
        (("value", "fact"), ("supported", "supported"), False),
        (("value", "fact"), ("supported", "partial"), False),  # partial does not mark
        (("value", "guidance"), ("supported", "generic"), True),
        (("value", "fact"), ("not_found", "supported"), True),
        (("standard", "fact"), ("not_found", "supported"), False),  # a standard phrase is never held against it
        (("standard", "standard"), ("generic", "not_found"), False),
        (("promise", "standard"), ("not_found", "generic"), True),
        ((), (), False),  # a reply with no claim
    ],
)
def test_unsupported_claim_is_computed_from_the_verdicts(kinds, verdicts, expected):
    assert unsupported_from_claims(claims_of(*kinds), verdicts_of(*verdicts)) is expected


def test_claim_counts_count_each_verdict_and_the_standard_phrases():
    claims = {
        "claims": claims_of("value", "standard", "guidance"),
        "claim_verdicts": verdicts_of("supported", "generic", "generic"),
    }
    expected = {"claims": 3, "supported": 1, "partial": 0, "generic": 2, "not_found": 0, "standard": 1}
    assert claim_counts(claims) == expected


# --- the two calls --------------------------------------------------------------------------------------------------


def test_a_v5_judgement_runs_two_calls_and_computes_the_verdict_from_the_claims():
    llm, meter = ScriptedLLM(handler, model="scripted-judge-v3"), CountingMeter()
    judge = v5(llm, meter)
    record = judge.evaluate(data("O valor líquido é R$ 90,00. Posso ajudar em algo mais? Acompanhe pelo app."))
    first, second = llm.calls
    assert first.schema is ClaimList and second.schema is JudgeScoreV5
    assert first.spec.instructions == load_prompt(PROMPTS, "judge_claims", "1").render()
    assert second.spec.instructions == load_prompt(PROMPTS, "judge", "5").render()
    listing = json.loads(first.spec.input)
    assert set(listing) == {"merchant_message", "route", "status", "reply"}  # the first call sees no evidence
    judged = json.loads(second.spec.input)
    assert judged["evidence"] == [TOOL] and [c["n"] for c in judged["claims"]] == [1, 2, 3]
    assert [c["kind"] for c in judged["claims"]] == ["value", "standard", "fact"]
    assert (first.spec.max_output_tokens, second.spec.max_output_tokens) == (1200, 2000)

    assert record["state"] == "completed" and record["rubric_version"] == "5" and record["unsupported_claim"] is True
    assert [v["verdict"] for v in record["claims"]["claim_verdicts"]] == ["not_found", "supported", "supported"]
    assert record["claims"]["claims"] == judged["claims"]
    assert set(record["scores"]) == set(CRITERIA) and set(record["reasons"]) == set(CRITERIA)
    assert record["cost_usd"] == pytest.approx(0.002) and len(meter.reserved) == 2  # both calls metered
    assert record["usage"]["output_tokens"] == 120  # 60 + 60: the tokens of both calls
    assert record["usage"]["input_tokens"] == sum(
        (len(call.spec.instructions) + len(call.spec.input)) // 4 for call in llm.calls
    )
    config = judge.config()
    assert (config["prompt"], config["claims_prompt"], config["rubric_version"]) == ("judge@5", "judge_claims@1", "5")
    assert config["parameters"] == {"max_output_tokens": 2000, "effort": "none", "claims_max_output_tokens": 1200}


def test_the_scripted_v5_verdict_is_the_scripted_v3_verdict():
    for reply in (
        "O valor líquido é R$ 120,00, com pagamento em 2 dias.",
        "O valor líquido é R$ 90,00. Obrigado pelo contato.",
        "Seu caso foi encaminhado com o protocolo HO-20261106-ABC123.",
    ):
        given = data(reply)
        under_v3 = scripted_judge(PROMPTS, NullMeter(), rubric="v3").evaluate(given)
        under_v5 = v5().evaluate(given)
        assert under_v5["unsupported_claim"] == under_v3["unsupported_claim"], reply
        assert under_v5["scores"] == under_v3["scores"]


def test_the_scripted_steps_list_one_claim_per_sentence_and_quote_the_evidence():
    listed = claims_handler(data("Seu caso foi encaminhado. O valor é R$ 120,00!\nVence em 12/05. Pode confirmar?"))
    kinds = [(c["n"], c["kind"]) for c in listed["claims"]]
    assert kinds == [(1, "standard"), (2, "value"), (3, "date"), (4, "standard")]
    claim = {"n": 1, "text": "O valor é R$ 120,00.", "kind": "value"}
    judged = verdicts_handler(data(claim["text"]) | {"claims": [claim]})
    assert judged["claim_verdicts"] == [{"n": 1, "verdict": "supported", "support": TOOL["text"]}]
    assert "unsupported_claim" not in judged


@pytest.mark.parametrize(
    ("verdicts", "message"),
    [
        ([{"n": 1, "verdict": "supported", "support": ""}, {"n": 9, "verdict": "supported", "support": ""}],
         "unknown claim number(s) 9; missing claim number(s) 2"),
        ([{"n": 1, "verdict": "supported", "support": ""}], "missing claim number(s) 2"),
        ([{"n": 1, "verdict": "supported", "support": ""}, {"n": 2, "verdict": "generic", "support": ""},
          {"n": 2, "verdict": "generic", "support": ""}], "repeated claim number(s) 2"),
    ],
)
def test_verdicts_that_do_not_answer_the_claims_make_a_failed_judgement_never_completed(verdicts, message):
    def answers(call):
        if call.schema is ClaimList:
            return {"claims": claims_of("fact", "guidance")}
        return verdicts_handler(json.loads(call.spec.input)) | {"claim_verdicts": verdicts}

    llm = ScriptedLLM(answers, model="scripted-judge-v3")
    record = v5(llm).evaluate(data("Uma frase. Outra frase."))
    assert record["state"] == "failed" and record["unsupported_claim"] is None and record["scores"] == {}
    assert record["claims"] is None and message in record["error"] and "ClaimMismatch" in record["error"]
    assert record["usage"]["output_tokens"] == 120 and len(llm.calls) == 2  # both calls were billed


def test_a_verdict_without_its_number_is_a_failed_judgement():
    def answers(call):
        if call.schema is ClaimList:
            return {"claims": claims_of("fact")}
        no_number = [{"verdict": "supported", "support": ""}]
        return verdicts_handler(json.loads(call.spec.input)) | {"claim_verdicts": no_number}

    record = v5(ScriptedLLM(answers)).evaluate(data("Uma frase."))
    assert record["state"] == "failed" and "ValidationError" in record["error"]


def test_a_failure_of_either_call_is_recorded_with_the_tokens_billed():
    billed = LLMError("cut answer")
    billed.usage = Usage(input_tokens=500, output_tokens=1200)

    def first_fails(call):
        return billed

    llm = ScriptedLLM(first_fails)
    record = v5(llm).evaluate(data("Uma frase."))
    assert record["state"] == "failed" and len(llm.calls) == 1 and record["error"] == "LLMError: cut answer"
    assert record["usage"] == {
        "input_tokens": 500,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "output_tokens": 1200,
    }

    def second_fails(call):
        return claims_handler(json.loads(call.spec.input)) if call.schema is ClaimList else billed

    llm = ScriptedLLM(second_fails)
    record = v5(llm).evaluate(data("Uma frase."))
    assert record["state"] == "failed" and len(llm.calls) == 2
    first_input = (len(llm.calls[0].spec.instructions) + len(llm.calls[0].spec.input)) // 4
    assert record["usage"]["output_tokens"] == 60 + 1200 and record["usage"]["input_tokens"] == first_input + 500


def test_v3_and_v4_judgements_keep_one_call_and_their_record():
    for rubric in ("v3", "v4"):
        llm = ScriptedLLM(handler, model="scripted-judge-v3")
        judge = scripted_judge(PROMPTS, NullMeter(), llm, rubric=rubric)
        record = judge.evaluate(data("O valor líquido é R$ 120,00."))
        assert len(llm.calls) == 1 and llm.calls[0].schema is JudgeScoreV3 and "claims" not in record
        assert "claims_prompt" not in judge.config() and judge.config()["parameters"]["max_output_tokens"] == 400


# --- selection and sizes --------------------------------------------------------------------------------------------


def test_the_paid_judge_under_v5_loads_both_prompts_and_sizes_both_calls_without_any_call():
    settings = Settings(
        _env_file=None,
        openai_api_key=None,
        deepseek_api_key=SecretStr("synthetic-deepseek-key"),
        anthropic_api_key=SecretStr("synthetic-anthropic-key"),
    )
    setup = validate_judge(settings, agent=AGENT, rubric="v5")
    assert (setup.prompt.ref, setup.claims_prompt.ref) == ("judge@5", "judge_claims@1")
    default = validate_judge(settings, agent=AGENT)
    assert default.claims_prompt.ref == "judge_claims@1" and RUBRIC_VERSION == "5"
    assert validate_judge(settings, agent=AGENT, rubric="v3").claims_prompt is None
    llm = ScriptedLLM(handler, model="deepseek-flash")
    judge = resolve_judge(settings, agent=AGENT, factory=lambda provider, model: llm, rubric="5")
    assert (judge.claims_max_output_tokens, judge.max_output_tokens) == (1200, 2000) and llm.calls == []
    assert judge.config()["claims_prompt"] == "judge_claims@1"
    claude = settings.model_copy(update={"judge_provider": "anthropic", "judge_model": "claude-opus-5-5"})
    opus = resolve_judge(claude, agent=AGENT, factory=lambda provider, model: llm, rubric="v5")
    assert (opus.claims_max_output_tokens, opus.max_output_tokens) == (2800, 3600)  # the same thinking margin
    # v3 and v4 do not change
    assert (
        judge_module.max_output_tokens_for("deepseek", "3"),
        judge_module.max_output_tokens_for("anthropic", "4"),
    ) == (
        400,
        2000,
    )


# --- persistence ----------------------------------------------------------------------------------------------------


def test_the_claims_are_stored_in_their_column_and_in_result_and_v3_leaves_the_column_empty(tmp_path):
    conn = connect(tmp_path / "judgements.sqlite3")
    under_v5, under_v3 = v5(), scripted_judge(PROMPTS, NullMeter(), rubric="v3")
    given = data("O valor líquido é R$ 90,00. Posso ajudar em algo mais?")
    for judge, request_id in ((under_v5, "req_v5"), (under_v3, "req_v3")):
        save_evaluation(conn, request_id=request_id, judge=judge, record=judge.evaluate(given), data=given, run="t88")
    rows = {r["request_id"]: r for r in conn.execute("SELECT * FROM run_evaluations")}
    stored = json.loads(rows["req_v5"]["claims"])
    assert [c["kind"] for c in stored["claims"]] == ["value", "standard"]
    assert [v["verdict"] for v in stored["claim_verdicts"]] == ["not_found", "supported"]
    assert json.loads(rows["req_v5"]["result"])["claims"] == stored and rows["req_v5"]["unsupported_claim"] == 1
    assert rows["req_v5"]["rubric_version"] == "5"
    evaluator = json.loads(rows["req_v5"]["evaluator"])
    assert (evaluator["prompt"], evaluator["claims_prompt"], evaluator["run"]) == ("judge@5", "judge_claims@1", "t88")
    assert rows["req_v3"]["claims"] is None and "claims" not in json.loads(rows["req_v3"]["result"])
    assert "claims_prompt" not in json.loads(rows["req_v3"]["evaluator"])

    failed = v5(ScriptedLLM(lambda call: RuntimeError("provider down"))).evaluate(given)
    save_evaluation(conn, request_id="req_failed", judge=under_v5, record=failed, data=given)
    row = conn.execute("SELECT claims, state FROM run_evaluations WHERE request_id='req_failed'").fetchone()
    assert tuple(row) == (None, "failed")
    conn.close()
