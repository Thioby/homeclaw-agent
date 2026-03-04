import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture(autouse=True)
def mock_dependencies():
    with patch("homeassistant.setup.async_setup_component", return_value=True):
        yield
