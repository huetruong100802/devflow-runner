from __future__ import annotations

import pytest

from devflow_runner.errors import ResolverError
from devflow_runner.resolver import VariableResolver


def test_resolver_supports_inputs_profile_and_steps():
    resolver = VariableResolver()
    scope = {
        "inputs": {"work_item": 6219, "workspace": "dxfactory"},
        "profile": {"organization": "Industrial-nois", "defaults": {"base_branch": "dxfac/development"}},
        "steps": {"s1": {"output": {"title": "Fix dropdown"}}},
    }

    value = resolver.resolve({
        "id": "{{ inputs.work_item }}",
        "org": "{{ profile.organization }}",
        "branch": "{{ profile.defaults.base_branch }}",
        "title": "WI {{ inputs.work_item }} - {{ steps.s1.output.title }}",
    }, scope)

    assert value["id"] == 6219
    assert value["org"] == "Industrial-nois"
    assert value["branch"] == "dxfac/development"
    assert value["title"] == "WI 6219 - Fix dropdown"


def test_resolver_rejects_unknown_root():
    resolver = VariableResolver()

    with pytest.raises(ResolverError):
        resolver.resolve("{{ env.PATH }}", {"inputs": {}, "profile": {}, "steps": {}})


def test_resolver_rejects_missing_value():
    resolver = VariableResolver()

    with pytest.raises(ResolverError):
        resolver.resolve("{{ inputs.missing }}", {"inputs": {}, "profile": {}, "steps": {}})
