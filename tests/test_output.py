"""Tests for the Output facade — the unified presentation + diagnostics surface."""

import logging

from rich.table import Table

from mysk.output import Output


def test_product_lands_on_stdout(capsys):
    Output("mysk.test").product("hello")
    captured = capsys.readouterr()
    assert "hello" in captured.out
    assert "hello" not in captured.err


def test_warn_lands_on_stderr_with_prefix(capsys):
    Output("mysk.test").warn("careful")
    captured = capsys.readouterr()
    assert "Warning:" in captured.err
    assert "careful" in captured.err
    assert "careful" not in captured.out


def test_success_lands_on_stdout(capsys):
    Output("mysk.test").success("Deleted 'foo'.")
    captured = capsys.readouterr()
    assert "Deleted 'foo'." in captured.out
    assert "Deleted 'foo'." not in captured.err


def test_note_lands_on_stdout(capsys):
    Output("mysk.test").note("Nothing selected.")
    captured = capsys.readouterr()
    assert "Nothing selected." in captured.out
    assert "Nothing selected." not in captured.err


def test_error_lands_on_stderr_with_prefix(capsys):
    Output("mysk.test").error("No skills found")
    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "No skills found" in captured.err
    assert "No skills found" not in captured.out


def test_product_renders_rich_renderables(capsys):
    # list builds a Rich Table and hands the renderable to product; the facade
    # must render it, not reject a non-str argument.
    table = Table()
    table.add_column("Name")
    table.add_row("my-skill")
    Output("mysk.test").product(table)
    assert "my-skill" in capsys.readouterr().out


def test_product_raw_emits_bracketed_data_verbatim(capsys):
    # Pure-data product lines (paths, per-target reports) bypass markup parsing
    # so a value containing brackets is emitted exactly as given.
    path = "/home/user/sk[ill]s"
    Output("mysk.test").product(path, raw=True)
    captured = capsys.readouterr()
    assert path in captured.out


def test_styled_verbs_escape_bracketed_values(capsys):
    # A dynamic value containing Rich-markup brackets must appear verbatim,
    # not be consumed as a style tag — the facade escapes it internally.
    bracketed = "skill [red]evil[/red]"
    verbs_per_stream = 2  # success + note on stdout; warn + error on stderr
    out = Output("mysk.test")
    out.success(bracketed)
    out.note(bracketed)
    out.warn(bracketed)
    out.error(bracketed)
    captured = capsys.readouterr()
    assert captured.out.count(bracketed) == verbs_per_stream
    assert captured.err.count(bracketed) == verbs_per_stream


def test_debug_emits_record_on_module_logger(caplog):
    with caplog.at_level(logging.DEBUG, logger="mysk"):
        Output("mysk.io.github").debug("fetching tarball")
    record = next(r for r in caplog.records if r.message == "fetching tarball")
    assert record.levelno == logging.DEBUG
    assert record.name == "mysk.io.github"


def test_info_emits_info_level_record(caplog):
    with caplog.at_level(logging.INFO, logger="mysk"):
        Output("mysk.commands.import_skill").info("importing 'foo'")
    record = next(r for r in caplog.records if r.message == "importing 'foo'")
    assert record.levelno == logging.INFO
    assert record.name == "mysk.commands.import_skill"


def test_exception_captures_traceback(caplog):
    with caplog.at_level(logging.DEBUG, logger="mysk"):
        try:
            int("boom")  # raises ValueError with an active traceback to capture
        except ValueError:
            Output("mysk.io.github").exception("download failed")
    record = next(r for r in caplog.records if r.message == "download failed")
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None
    assert record.exc_info[0] is ValueError


def test_diagnostic_records_attribute_to_caller_not_facade(caplog):
    # stacklevel=2 makes show_path / lineno / funcName point at the real caller
    # rather than at output.py's wrapper method.
    def emitting_helper():
        Output("mysk.test").debug("traced")

    with caplog.at_level(logging.DEBUG, logger="mysk"):
        emitting_helper()
    record = next(r for r in caplog.records if r.message == "traced")
    assert record.funcName == "emitting_helper"
    assert record.pathname.endswith("test_output.py")
