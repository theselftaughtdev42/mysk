"""The autouse isolation fixture must neutralise ambient mysk env vars.

A contributor's shell may export MYSK_LOG_LEVEL; tests must be deterministic
regardless, mirroring the MYSK_HOME isolation (issue #135).
"""

import os


def test_mysk_log_level_is_cleared_by_default():
    assert "MYSK_LOG_LEVEL" not in os.environ
