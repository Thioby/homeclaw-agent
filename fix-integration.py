import re

with open("tests/test_homeclaw/test_integration.py", "r") as f:
    content = f.read()

# Fix integration setup
content = content.replace('import pytest\nfrom homeassistant.core import HomeAssistant', 'import pytest\nfrom unittest.mock import patch, MagicMock, AsyncMock\nfrom homeassistant.core import HomeAssistant')

with open("tests/test_homeclaw/test_integration.py", "w") as f:
    f.write(content)

with open("tests/test_homeclaw/conftest.py", "w") as f:
    f.write("""import pytest
from unittest.mock import AsyncMock

@pytest.fixture(autouse=True)
def mock_dependencies():
    with patch("homeassistant.setup.async_setup_component", return_value=True):
        yield
""")
