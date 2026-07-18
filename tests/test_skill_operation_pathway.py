from pathlib import Path
from types import SimpleNamespace

import pytest

from mysk.domain import LifecycleState, MyskBlock, Skill
from mysk.io.deploy import ActResult
from mysk.io.skills import InstalledSkill
from mysk.output import Output
from mysk.skill_operation_pathway import (
    SkillSelectionError,
    build_skill_choices,
    confirm,
    report_act,
    resolve_skill_selection,
)
from tests.conftest import make_target


def _installed(
    name: str, state: LifecycleState = LifecycleState.ACTIVE
) -> InstalledSkill:
    mysk = MyskBlock(state=state)
    skill = Skill(name=name, description="d", mysk=mysk)
    return InstalledSkill(skill=skill, mysk=mysk, dir=Path(f"/skills/{name}"))


def test_all_flag_returns_every_eligible_skill():
    eligible = [_installed("foo"), _installed("bar")]

    result = resolve_skill_selection(
        skill=None, bulk=None, select_all=True, eligible=eligible
    )

    assert result == eligible


def test_nothing_given_returns_none_sentinel():
    eligible = [_installed("foo"), _installed("bar")]

    result = resolve_skill_selection(
        skill=None, bulk=None, select_all=False, eligible=eligible
    )

    assert result is None


def test_skill_positional_returns_single_match():
    foo = _installed("foo")
    bar = _installed("bar")

    result = resolve_skill_selection(
        skill="bar", bulk=None, select_all=False, eligible=[foo, bar]
    )

    assert result == [bar]


def test_unknown_skill_name_raises_skill_selection_error():
    eligible = [_installed("foo")]

    with pytest.raises(SkillSelectionError, match="nonexistent"):
        resolve_skill_selection(
            skill="nonexistent", bulk=None, select_all=False, eligible=eligible
        )


def test_bulk_flag_returns_matching_subset():
    foo = _installed("foo")
    bar = _installed("bar")
    baz = _installed("baz")

    result = resolve_skill_selection(
        skill=None, bulk="foo,baz", select_all=False, eligible=[foo, bar, baz]
    )

    assert result == [foo, baz]


def test_unknown_bulk_name_raises_skill_selection_error():
    eligible = [_installed("foo")]

    with pytest.raises(SkillSelectionError, match="nonexistent"):
        resolve_skill_selection(
            skill=None, bulk="foo,nonexistent", select_all=False, eligible=eligible
        )


def test_skill_and_bulk_together_raises_mutually_exclusive_error():
    eligible = [_installed("foo"), _installed("bar")]

    with pytest.raises(SkillSelectionError, match="mutually exclusive"):
        resolve_skill_selection(
            skill="foo", bulk="foo,bar", select_all=False, eligible=eligible
        )


@pytest.mark.parametrize(
    ("skill", "bulk", "select_all"),
    [
        ("foo", None, True),
        (None, "foo,bar", True),
        ("foo", "foo,bar", True),
    ],
)
def test_other_two_of_a_kind_combinations_also_raise_mutually_exclusive_error(
    skill, bulk, select_all
):
    eligible = [_installed("foo"), _installed("bar")]

    with pytest.raises(SkillSelectionError, match="mutually exclusive"):
        resolve_skill_selection(
            skill=skill, bulk=bulk, select_all=select_all, eligible=eligible
        )


def test_confirm_yes_true_skips_prompt_and_returns_true():
    assert confirm("Really?", yes=True) is True


def test_confirm_yes_false_prompts_and_returns_users_answer(monkeypatch):
    captured = {}

    def fake_confirm(message):
        captured["message"] = message
        return SimpleNamespace(ask=lambda: False)

    monkeypatch.setattr(
        "mysk.skill_operation_pathway.questionary",
        SimpleNamespace(confirm=fake_confirm),
    )

    result = confirm("Really?", yes=False)

    assert result is False
    assert captured["message"] == "Really?"


def test_build_skill_choices_selectable_entry_has_no_disabled_reason():
    foo = _installed("foo", LifecycleState.EXPERIMENTAL)

    choices = build_skill_choices([foo], relevance=lambda r: None)

    assert len(choices) == 1
    assert choices[0].title == "foo (experimental)"
    assert choices[0].value == foo
    assert choices[0].disabled is None


def test_build_skill_choices_disabled_entry_carries_reason():
    bar = _installed("bar")

    choices = build_skill_choices([bar], relevance=lambda r: "already deployed")

    assert choices[0].disabled == "already deployed"


def test_report_act_prints_roster_header_and_outcome_line_per_skill(capsys):
    claude = make_target("claude")
    foo = _installed("foo")

    report_act([claude], [foo], act=lambda skill, target: ActResult(outcome="removed"))

    out = capsys.readouterr().out
    assert "claude:" in out
    assert "  foo: removed" in out


def test_report_act_suffixes_the_reason_in_parentheses(capsys):
    claude = make_target("claude")
    foo = _installed("foo")

    report_act(
        [claude],
        [foo],
        act=lambda skill, target: ActResult(outcome="skipped", reason="not deployed"),
    )

    assert "  foo: skipped (not deployed)" in capsys.readouterr().out


def test_report_act_separates_each_target_with_a_leading_blank_line(capsys):
    claude = make_target("claude")
    cursor = make_target("cursor")
    foo = _installed("foo")

    report_act(
        [claude, cursor],
        [foo],
        act=lambda skill, target: ActResult(outcome="removed"),
    )

    assert "\nclaude:" in capsys.readouterr().out


def test_report_act_passes_each_skill_and_target_to_the_act():
    claude = make_target("claude")
    cursor = make_target("cursor")
    foo = _installed("foo")
    bar = _installed("bar")
    seen = []

    def act(skill, target):
        seen.append((target.name, skill.skill.name))
        return ActResult(outcome="removed")

    report_act([claude, cursor], [foo, bar], act=act)

    assert seen == [
        ("claude", "foo"),
        ("claude", "bar"),
        ("cursor", "foo"),
        ("cursor", "bar"),
    ]


def test_report_act_runs_prepare_target_after_header_before_skill_lines(capsys):
    claude = make_target("claude")
    foo = _installed("foo")

    def prepare(target):
        Output("mysk.test").product("  Created ~/.claude/skills", raw=True)

    report_act(
        [claude],
        [foo],
        act=lambda skill, target: ActResult(outcome="deployed"),
        prepare_target=prepare,
    )

    out = capsys.readouterr().out
    header = out.index("claude:")
    created = out.index("Created")
    line = out.index("foo: deployed")
    assert header < created < line
