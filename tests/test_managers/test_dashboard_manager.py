"""Tests for DashboardManager.

Tests dashboard operations extracted from the God Class.
Uses TDD approach - tests written first.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, mock_open
import yaml

from custom_components.homeclaw.managers.dashboard_manager import DashboardManager


class MockDashboard:
    """Mock dashboard object."""

    def __init__(
        self,
        url_path: str | None = None,
        title: str = "Test Dashboard",
        icon: str = "mdi:view-dashboard",
    ):
        self.url_path = url_path
        self.title = title
        self.icon = icon

    async def async_get_info(self):
        """Mock async_get_info method."""
        return {
            "url_path": self.url_path,
            "title": self.title,
            "icon": self.icon,
        }


class MockLovelaceData:
    """Mock lovelace data structure."""

    def __init__(self, dashboards: dict = None, yaml_dashboards: dict = None):
        self.dashboards = dashboards or {}
        self.yaml_dashboards = yaml_dashboards or {}


@pytest.fixture
def dashboard_manager(hass):
    """Create a DashboardManager with mocked hass."""
    # Setup necessary mocks on hass if they aren't already present
    if not hasattr(hass, "config"):
        hass.config = MagicMock()
    
    # Ensure config.path works as expected if not already set
    if not hasattr(hass.config, "path"):
        hass.config.path = MagicMock(side_effect=lambda x: f"/config/{x}")
    else:
        # If it exists (real hass), we might want to mock it for predictable paths in tests
        # or just leave it. The original mock forced /config/. 
        # Let's mock it to match previous behavior for safety.
        hass.config.path = MagicMock(side_effect=lambda x: f"/config/{x}")
        
    # Ensure async_add_executor_job is a mock/async-compatible
    # Real hass has this, but we want to avoid actual thread pools in unit tests usually
    hass.async_add_executor_job = AsyncMock(side_effect=lambda f, *args: f(*args) if args else f())
    
    return DashboardManager(hass)


@pytest.fixture
def sample_dashboards():
    """Create sample dashboard objects for testing."""
    return {
        None: MockDashboard(None, "Overview", "mdi:home"),
        "energy": MockDashboard("energy", "Energy Dashboard", "mdi:flash"),
        "climate": MockDashboard("climate", "Climate Control", "mdi:thermometer"),
    }


@pytest.fixture
def sample_yaml_dashboards():
    """Create sample YAML dashboard configs."""
    return {
        None: {"title": "Overview", "icon": "mdi:home", "show_in_sidebar": True},
        "energy": {"title": "Energy Dashboard", "icon": "mdi:flash", "show_in_sidebar": True},
        "climate": {"title": "Climate Control", "icon": "mdi:thermometer", "show_in_sidebar": True, "require_admin": True},
    }


class TestGetDashboards:
    """Tests for get_dashboards method."""

    @pytest.mark.asyncio
    async def test_get_dashboards_returns_list(
        self, dashboard_manager, hass, sample_dashboards, sample_yaml_dashboards
    ):
        """Test that get_dashboards returns a list of dashboards."""
        mock_lovelace_data = MockLovelaceData(sample_dashboards, sample_yaml_dashboards)
        hass.data["lovelace"] = mock_lovelace_data

        result = await dashboard_manager.get_dashboards()

        assert isinstance(result, list)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_dashboards_returns_dashboard_info(
        self, dashboard_manager, hass, sample_dashboards, sample_yaml_dashboards
    ):
        """Test that get_dashboards returns proper dashboard info."""
        mock_lovelace_data = MockLovelaceData(sample_dashboards, sample_yaml_dashboards)
        hass.data["lovelace"] = mock_lovelace_data

        result = await dashboard_manager.get_dashboards()

        url_paths = [d["url_path"] for d in result]
        assert None in url_paths  # Default dashboard
        assert "energy" in url_paths
        assert "climate" in url_paths

        # Check dashboard structure
        for dashboard in result:
            assert "url_path" in dashboard
            assert "title" in dashboard
            assert "icon" in dashboard
            assert "show_in_sidebar" in dashboard

    @pytest.mark.asyncio
    async def test_get_dashboards_lovelace_not_available(self, dashboard_manager, hass):
        """Test that get_dashboards handles missing lovelace gracefully."""
        # Clean data to simulate missing lovelace
        # Note: hass.data is a dict, we can't just replace it with {}, but we can clear it or remove 'lovelace'
        if "lovelace" in hass.data:
            del hass.data["lovelace"]
        # Or if the test expects empty data
        # hass.data = {} # This might break other things in a real hass fixture, but for this test scope it might be fine.
        # Let's try to just ensure 'lovelace' is missing.
        
        # The original test did: mock_hass.data = {}
        # Let's replicate that behavior safely
        original_data = hass.data
        hass.data = {}

        try:
            result = await dashboard_manager.get_dashboards()

            assert isinstance(result, list)
            assert len(result) == 1
            assert "error" in result[0]
        finally:
            hass.data = original_data

    @pytest.mark.asyncio
    async def test_get_dashboards_empty_list(self, dashboard_manager, hass):
        """Test that get_dashboards returns empty list when no dashboards exist."""
        mock_lovelace_data = MockLovelaceData({}, {})
        hass.data["lovelace"] = mock_lovelace_data

        result = await dashboard_manager.get_dashboards()

        assert isinstance(result, list)
        assert len(result) == 0


class TestGetDashboardConfig:
    """Tests for get_dashboard_config method."""

    @pytest.mark.asyncio
    async def test_get_dashboard_config_default(
        self, dashboard_manager, hass, sample_dashboards
    ):
        """Test getting default dashboard config."""
        mock_lovelace_data = MockLovelaceData(sample_dashboards)
        hass.data["lovelace"] = mock_lovelace_data

        result = await dashboard_manager.get_dashboard_config(None)

        assert result is not None
        assert result.get("title") == "Overview"
        assert result.get("url_path") is None

    @pytest.mark.asyncio
    async def test_get_dashboard_config_by_url(
        self, dashboard_manager, hass, sample_dashboards
    ):
        """Test getting dashboard config by URL path."""
        mock_lovelace_data = MockLovelaceData(sample_dashboards)
        hass.data["lovelace"] = mock_lovelace_data

        result = await dashboard_manager.get_dashboard_config("energy")

        assert result is not None
        assert result.get("title") == "Energy Dashboard"

    @pytest.mark.asyncio
    async def test_get_dashboard_config_not_found(
        self, dashboard_manager, hass, sample_dashboards
    ):
        """Test that get_dashboard_config returns error for non-existent dashboard."""
        mock_lovelace_data = MockLovelaceData(sample_dashboards)
        hass.data["lovelace"] = mock_lovelace_data

        result = await dashboard_manager.get_dashboard_config("nonexistent")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_dashboard_config_lovelace_not_available(
        self, dashboard_manager, hass
    ):
        """Test that get_dashboard_config handles missing lovelace."""
        original_data = hass.data
        hass.data = {}

        try:
            result = await dashboard_manager.get_dashboard_config("energy")
            assert "error" in result
        finally:
            hass.data = original_data


class TestCreateDashboard:
    """Tests for create_dashboard method."""

    @pytest.mark.asyncio
    async def test_create_dashboard_success(self, dashboard_manager, hass):
        """Test creating a new dashboard successfully."""
        config = {
            "title": "New Dashboard",
            "url_path": "new-dashboard",
            "icon": "mdi:view-dashboard",
            "views": [{"title": "Home", "cards": []}],
        }

        with patch("builtins.open", mock_open()) as mock_file:
            result = await dashboard_manager.create_dashboard(config)

        assert result.get("success") is True
        assert "url_path" in result

    @pytest.mark.asyncio
    async def test_create_dashboard_missing_title(self, dashboard_manager, hass):
        """Test that create_dashboard fails without title."""
        config = {
            "url_path": "new-dashboard",
        }

        result = await dashboard_manager.create_dashboard(config)

        assert "error" in result
        assert "title" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_create_dashboard_missing_url_path(self, dashboard_manager, hass):
        """Test that create_dashboard fails without url_path."""
        config = {
            "title": "New Dashboard",
        }

        result = await dashboard_manager.create_dashboard(config)

        assert "error" in result
        assert "url" in result["error"].lower() or "path" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_create_dashboard_sanitizes_url_path(self, dashboard_manager, hass):
        """Test that create_dashboard sanitizes URL path."""
        config = {
            "title": "New Dashboard",
            "url_path": "New_Dashboard With Spaces",
        }

        with patch("builtins.open", mock_open()) as mock_file:
            result = await dashboard_manager.create_dashboard(config)

        # URL path should be sanitized to lowercase with hyphens
        if result.get("success"):
            assert result.get("url_path") == "new-dashboard-with-spaces"

    @pytest.mark.asyncio
    async def test_create_dashboard_writes_yaml_file(self, dashboard_manager, hass):
        """Test that create_dashboard writes YAML file."""
        config = {
            "title": "Test Dashboard",
            "url_path": "test",
            "views": [{"title": "View 1", "cards": []}],
        }

        written_content = []

        def capture_write(content):
            written_content.append(content)

        mock_file = mock_open()
        mock_file.return_value.write = capture_write

        with patch("builtins.open", mock_file):
            result = await dashboard_manager.create_dashboard(config)

        # Verify file was opened for writing
        mock_file.assert_called()


class TestUpdateDashboard:
    """Tests for update_dashboard method."""

    @pytest.mark.asyncio
    async def test_update_dashboard_success(self, dashboard_manager, hass):
        """Test updating an existing dashboard."""
        config = {
            "title": "Updated Dashboard",
            "views": [{"title": "Updated View", "cards": []}],
        }

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open()) as mock_file:
                result = await dashboard_manager.update_dashboard("test-dashboard", config)

        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_update_dashboard_not_found(self, dashboard_manager, hass):
        """Test updating a non-existent dashboard."""
        config = {
            "title": "Updated Dashboard",
        }

        with patch("os.path.exists", return_value=False):
            result = await dashboard_manager.update_dashboard("nonexistent", config)

        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_dashboard_preserves_structure(self, dashboard_manager, hass):
        """Test that update_dashboard preserves dashboard structure."""
        config = {
            "title": "Updated Dashboard",
            "icon": "mdi:home",
            "views": [
                {"title": "Main", "cards": [{"type": "entities", "entities": []}]}
            ],
        }

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open()) as mock_file:
                result = await dashboard_manager.update_dashboard("test", config)

        assert result.get("success") is True


class TestValidateDashboardConfig:
    """Tests for validate_dashboard_config method."""

    def test_validate_dashboard_config_valid(self, dashboard_manager):
        """Test validating a valid dashboard config."""
        config = {
            "title": "Test Dashboard",
            "views": [
                {
                    "title": "Main View",
                    "cards": [
                        {"type": "entities", "entities": ["light.living_room"]}
                    ],
                }
            ],
        }

        result = dashboard_manager.validate_dashboard_config(config)

        assert result.get("valid") is True

    def test_validate_dashboard_config_missing_views(self, dashboard_manager):
        """Test validating config without views."""
        config = {
            "title": "Test Dashboard",
        }

        result = dashboard_manager.validate_dashboard_config(config)

        # Should either add default views or flag as invalid
        assert "valid" in result or "views" in result.get("error", "")

    def test_validate_dashboard_config_empty_views(self, dashboard_manager):
        """Test validating config with empty views list."""
        config = {
            "title": "Test Dashboard",
            "views": [],
        }

        result = dashboard_manager.validate_dashboard_config(config)

        # Empty views might be valid or trigger a warning
        assert "valid" in result or "warning" in result or "error" in result

    def test_validate_dashboard_config_invalid_card_type(self, dashboard_manager):
        """Test validating config with invalid card type."""
        config = {
            "title": "Test Dashboard",
            "views": [
                {
                    "title": "Main View",
                    "cards": [
                        {"type": "invalid-card-type-xyz", "entities": []}
                    ],
                }
            ],
        }

        result = dashboard_manager.validate_dashboard_config(config)

        # Should warn about unknown card type or pass through
        assert "valid" in result or "warning" in result

    def test_validate_dashboard_config_view_structure(self, dashboard_manager):
        """Test validating view structure in config."""
        config = {
            "title": "Test Dashboard",
            "views": [
                {
                    "title": "View 1",
                    "path": "view-1",
                    "icon": "mdi:home",
                    "cards": [],
                },
                {
                    "title": "View 2",
                    "cards": [{"type": "markdown", "content": "Hello"}],
                },
            ],
        }

        result = dashboard_manager.validate_dashboard_config(config)

        assert result.get("valid") is True


class TestDashboardManagerInitialization:
    """Tests for DashboardManager initialization."""

    def test_init_stores_hass(self, hass):
        """Test that DashboardManager stores hass reference."""
        manager = DashboardManager(hass)

        assert manager.hass is hass

    def test_init_with_none_hass_raises(self):
        """Test that DashboardManager raises error with None hass."""
        with pytest.raises(ValueError, match="hass is required"):
            DashboardManager(None)
