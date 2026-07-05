"""Guards for the expert-tier suite: references must be canonically correct."""

from pilot_tasks.expert_suite import TASK_NAMES, _selftest, validate


def test_expert_references_pass_canonical_and_own_cases():
    # _selftest hard-asserts canonical outputs and that every reference passes
    # all of its own generated hidden cases; a raise here means a bad reference.
    _selftest()
    assert all(v == 1.0 for v in validate().values())
    assert len(TASK_NAMES) == 8
