"""Policy gate tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from clearmetric.core.errors import PolicyDeniedError
from clearmetric.core.models import Node
from clearmetric.policy import gate, require_allow
from clearmetric.policy.models import PolicyRule, PolicyRulesFile, PolicySelector


def _node(**kwargs: object) -> Node:
    payload = {"id": "column:orders.email", "kind": "column", "name": "email", **kwargs}
    return Node.model_validate(payload)


def test_empty_rules_denies_via_gate():
    node = _node()
    assert gate(node=node, identity="analyst", rules=PolicyRulesFile()) == "deny"


def test_require_allow_raises_for_deny():
    node = _node()
    rules = PolicyRulesFile(rules=[])
    with pytest.raises(PolicyDeniedError):
        require_allow(node=node, identity="analyst", rules=rules)


def test_require_allow_raises_for_mask():
    node = _node()
    rules = PolicyRulesFile(
        rules=[
            PolicyRule(
                id="mask-email",
                kind="masking",
                identity="analyst",
                effect="mask",
                selector=PolicySelector(kind="column"),
            )
        ]
    )
    with pytest.raises(PolicyDeniedError):
        require_allow(node=node, identity="analyst", rules=rules)


def test_require_allow_raises_for_filter():
    node = _node()
    rules = PolicyRulesFile(
        rules=[
            PolicyRule(
                id="filter-email",
                kind="rls",
                identity="analyst",
                effect="deny",
                selector=PolicySelector(kind="column"),
            )
        ]
    )
    with pytest.raises(PolicyDeniedError):
        require_allow(node=node, identity="analyst", rules=rules)


def test_security_floor_violation_returns_deny_from_gate():
    node = Node(
        id="column:orders.email",
        kind="column",
        name="email",
        aspects={"classification": "pii"},
    )
    rules = PolicyRulesFile(
        rules=[
            PolicyRule(
                id="allow-columns",
                kind="rbac",
                identity="analyst",
                effect="allow",
                selector=PolicySelector(kind="column"),
            )
        ]
    )
    assert gate(node=node, identity="analyst", rules=rules) == "deny"


def test_evaluator_exception_returns_deny_from_gate():
    node = _node()
    rules = PolicyRulesFile(rules=[])
    with patch(
        "clearmetric.policy.gate.evaluate_node",
        side_effect=RuntimeError("boom"),
    ):
        assert gate(node=node, identity="analyst", rules=rules) == "deny"


def test_require_allow_succeeds_for_allow():
    node = _node()
    rules = PolicyRulesFile(
        rules=[
            PolicyRule(
                id="allow-columns",
                kind="rbac",
                identity="analyst",
                effect="allow",
                selector=PolicySelector(kind="column"),
            )
        ]
    )
    require_allow(node=node, identity="analyst", rules=rules)
