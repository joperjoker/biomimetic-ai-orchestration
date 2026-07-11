"""Guards for the held-out expert tier: references must be canonically correct."""

from pilot_tasks.held_out_suite import BARE_SPECS, SPECS, TASK_NAMES, _selftest, validate


def test_held_out_references_pass_canonical_and_own_cases():
    _selftest()
    assert all(v == 1.0 for v in validate().values())
    assert len(TASK_NAMES) == 8


def test_held_out_disjoint_from_expert_and_ood():
    from pilot_tasks.expert_suite import TASK_NAMES as expert_names
    from pilot_tasks.ood_suite import TASK_NAMES as ood_names

    assert not (set(TASK_NAMES) & set(expert_names))
    assert not (set(TASK_NAMES) & set(ood_names))


def test_held_out_every_task_has_both_specs():
    assert set(SPECS) == set(TASK_NAMES)
    assert set(BARE_SPECS) == set(TASK_NAMES)
