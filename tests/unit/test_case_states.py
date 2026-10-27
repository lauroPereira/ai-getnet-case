import pytest

from merchant_assistant.cases import InvalidTransition, Turn, next_state, transition


def test_answer_waits_for_the_customer():
    assert next_state("in_progress", None, Turn("answered", "none")) == ("awaiting_customer", None)


def test_customer_confirmation_resolves_with_evidence():
    assert next_state("awaiting_customer", None, Turn("answered", "resolved")) == ("resolved", "customer_confirmed")


def test_tool_verification_resolves():
    assert next_state("awaiting_customer", None, Turn("answered", "none", tool_verified=True)) == (
        "resolved",
        "tool_verified",
    )


def test_thanks_alone_does_not_resolve():
    assert next_state("awaiting_customer", None, Turn("answered", "thanks_only")) == ("awaiting_customer", None)


def test_handoff_is_sticky():
    assert next_state("in_progress", None, Turn("handoff", "none"))[0] == "handoff"
    assert next_state("handoff", None, Turn("answered", "resolved"))[0] == "handoff"


def test_new_issue_reopens_a_resolved_case():
    assert next_state("resolved", "customer_confirmed", Turn("answered", "none")) == ("awaiting_customer", None)


def test_invalid_transition_is_refused():
    with pytest.raises(InvalidTransition):
        transition("handoff", "resolved")
