"""Guards for the OOD overconfidence suite: references must be canonically correct."""

from pilot_tasks.ood_suite import BARE_SPECS, SPECS, TASK_NAMES, _selftest, validate


def test_ood_references_pass_canonical_and_own_cases():
    # _selftest hard-asserts canonical outputs and that every reference passes all
    # of its own generated hidden cases; a raise here means a bad reference.
    _selftest()
    assert all(v == 1.0 for v in validate().values())
    assert len(TASK_NAMES) == 8


def test_ood_every_task_has_both_specs():
    assert set(SPECS) == set(TASK_NAMES)
    assert set(BARE_SPECS) == set(TASK_NAMES)
