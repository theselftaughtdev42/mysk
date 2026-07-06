"""Tests for configure_logging() — the narrow structural unit.

These guarantees are not observable at the CLI boundary, so this is the one
place the suite asserts on handler objects and logger levels directly. Each
test restores the global ``mysk`` / ``httpx`` logger state so ordering can't
leak configuration between tests.
"""

import logging

import pytest
from rich.logging import RichHandler

from mysk.logging_config import configure_logging


@pytest.fixture(autouse=True)
def restore_logger_state():
    """Snapshot and restore the loggers configure_logging() mutates."""
    mysk = logging.getLogger("mysk")
    httpx = logging.getLogger("httpx")
    saved = [(lg, lg.handlers[:], lg.level, lg.propagate) for lg in (mysk, httpx)]
    yield
    for lg, handlers, level, propagate in saved:
        lg.handlers[:] = handlers
        lg.setLevel(level)
        lg.propagate = propagate


def test_off_attaches_nullhandler_and_no_richhandler(monkeypatch):
    monkeypatch.delenv("MYSK_LOG_LEVEL", raising=False)
    configure_logging()
    handlers = logging.getLogger("mysk").handlers
    assert any(isinstance(h, logging.NullHandler) for h in handlers)
    assert not any(isinstance(h, RichHandler) for h in handlers)


def test_on_attaches_richhandler_and_sets_level(monkeypatch):
    monkeypatch.setenv("MYSK_LOG_LEVEL", "DEBUG")
    configure_logging()
    logger = logging.getLogger("mysk")
    assert any(isinstance(h, RichHandler) for h in logger.handlers)
    assert not any(isinstance(h, logging.NullHandler) for h in logger.handlers)
    assert logger.level == logging.DEBUG


def test_repeated_calls_do_not_accumulate_handlers(monkeypatch):
    monkeypatch.setenv("MYSK_LOG_LEVEL", "DEBUG")
    configure_logging()
    configure_logging()
    configure_logging()
    handlers = logging.getLogger("mysk").handlers
    assert sum(isinstance(h, RichHandler) for h in handlers) == 1


def test_debug_cascades_httpx_to_info(monkeypatch):
    monkeypatch.setenv("MYSK_LOG_LEVEL", "DEBUG")
    logging.getLogger("httpx").setLevel(logging.NOTSET)
    configure_logging()
    assert logging.getLogger("httpx").level == logging.INFO


def test_non_debug_level_leaves_httpx_untouched(monkeypatch):
    monkeypatch.setenv("MYSK_LOG_LEVEL", "WARNING")
    logging.getLogger("httpx").setLevel(logging.NOTSET)
    configure_logging()
    assert logging.getLogger("httpx").level == logging.NOTSET
