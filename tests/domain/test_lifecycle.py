import pytest

from mysk.domain import LifecycleState


@pytest.mark.parametrize(
    "state, deployable",
    [
        (LifecycleState.ACTIVE, True),
        (LifecycleState.EXPERIMENTAL, True),
        (LifecycleState.INIT, False),
        (LifecycleState.DEPRECATED, False),
    ],
)
def test_only_active_and_experimental_deploy(state, deployable):
    assert state.is_deployable is deployable
