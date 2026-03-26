# Dashboard Create/Update/Delete Tools — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add create, update, and delete dashboard tools with dry_run confirmation flow to the AI agent's function-calling toolkit.

**Architecture:** Three new CORE tools in `ha_native.py` delegate to `DashboardManager`. All default to `dry_run=true` — AI previews changes as YAML, user confirms, AI calls again with `dry_run=false`. New `delete_dashboard` method and `_remove_from_configuration_yaml` added to `DashboardManager`.

**Tech Stack:** Python 3.12+, Home Assistant Core, PyYAML, pytest

**Spec:** `docs/superpowers/specs/2026-03-26-dashboard-tools-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `custom_components/homeclaw/managers/dashboard_manager.py` | Modify | Add `dry_run` to create/update, new `delete_dashboard`, new `_remove_from_configuration_yaml` |
| `custom_components/homeclaw/tools/ha_native.py` | Modify | 3 new tool classes at end of file |
| `custom_components/homeclaw/prompts.py` | Modify | Replace `dashboard_suggestion` with dry_run instructions |
| `custom_components/homeclaw/services.py` | Modify | Add `dry_run=False` to callsites |
| `custom_components/homeclaw/agent_compat.py` | Modify | Add `dry_run=False` to callsites |
| `custom_components/homeclaw/core/agent.py` | Modify | Add `dry_run=False` to callsite |
| `custom_components/homeclaw/core/subagent.py` | Modify | Add `delete_dashboard` to blocklist |
| `custom_components/homeclaw/proactive/heartbeat.py` | Modify | Add `delete_dashboard` to blocklist |
| `tests/test_managers/test_dashboard_manager.py` | Modify | Tests for dry_run, delete, remove_from_yaml |
| `tests/test_tools/__init__.py` | Create | Package init (empty) |
| `tests/test_tools/test_dashboard_tools.py` | Create | Tests for 3 new tool classes |

---

### Task 1: Add `dry_run` to `DashboardManager.create_dashboard`

**Files:**
- Modify: `custom_components/homeclaw/managers/dashboard_manager.py:204-289`
- Test: `tests/test_managers/test_dashboard_manager.py`

- [ ] **Step 1: Write failing tests for dry_run=True on create**

Add to `tests/test_managers/test_dashboard_manager.py` inside `TestCreateDashboard`:

```python
@pytest.mark.asyncio
async def test_create_dashboard_dry_run_returns_preview(self, dashboard_manager, hass):
    """Test that dry_run=True returns preview without writing."""
    config = {
        "title": "New Dashboard",
        "url_path": "new-dash",
        "views": [{"title": "Home", "cards": []}],
    }

    result = await dashboard_manager.create_dashboard(config, dry_run=True)

    assert result.get("dry_run") is True
    assert result.get("preview") is not None
    assert result.get("title") == "New Dashboard"
    assert "url_path" in result

@pytest.mark.asyncio
async def test_create_dashboard_dry_run_does_not_write_file(self, dashboard_manager, hass):
    """Test that dry_run=True does not create any files."""
    config = {
        "title": "New Dashboard",
        "url_path": "new-dash",
        "views": [{"title": "Home", "cards": []}],
    }

    with patch("builtins.open", mock_open()) as mock_file:
        await dashboard_manager.create_dashboard(config, dry_run=True)

    mock_file.assert_not_called()

@pytest.mark.asyncio
async def test_create_dashboard_dry_run_validates_config(self, dashboard_manager, hass):
    """Test that dry_run=True validates and returns warnings."""
    config = {
        "title": "New Dashboard",
        "url_path": "new-dash",
        "views": [{"title": "V", "cards": [{"type": "unknown-xyz"}]}],
    }

    result = await dashboard_manager.create_dashboard(config, dry_run=True)

    assert result.get("dry_run") is True
    assert "validation" in result
    assert len(result["validation"].get("warnings", [])) > 0

@pytest.mark.asyncio
async def test_create_dashboard_dry_run_false_writes(self, dashboard_manager, hass):
    """Test that dry_run=False preserves existing write behavior."""
    config = {
        "title": "New Dashboard",
        "url_path": "new-dash",
        "views": [{"title": "Home", "cards": []}],
    }

    with patch("builtins.open", mock_open()) as mock_file:
        result = await dashboard_manager.create_dashboard(config, dry_run=False)

    assert result.get("success") is True
    mock_file.assert_called()

@pytest.mark.asyncio
async def test_create_dashboard_duplicate_url_path(self, dashboard_manager, hass):
    """Test that creating with existing url_path returns error."""
    config = {
        "title": "Duplicate",
        "url_path": "existing-dash",
        "views": [],
    }

    with patch("os.path.exists", return_value=True):
        result = await dashboard_manager.create_dashboard(config, dry_run=True)

    assert "error" in result
    assert "already exists" in result["error"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_managers/test_dashboard_manager.py::TestCreateDashboard -v`
Expected: FAIL — `create_dashboard()` does not accept `dry_run` parameter.

- [ ] **Step 3: Implement dry_run in create_dashboard**

In `custom_components/homeclaw/managers/dashboard_manager.py`, modify `create_dashboard` (line 204):

```python
async def create_dashboard(
    self, config: dict[str, Any], dashboard_id: str | None = None, *, dry_run: bool = True
) -> dict[str, Any]:
    """Create a new dashboard.

    Args:
        config: Dashboard configuration with title, url_path, views, etc.
        dashboard_id: Optional explicit dashboard ID (uses url_path from config if not provided).
        dry_run: If True, validate and return preview without writing files.

    Returns:
        Result dictionary with preview (dry_run) or success status.
    """
    try:
        _LOGGER.debug("Creating dashboard with config: %s (dry_run=%s)", config, dry_run)

        if not config.get("title"):
            return {"error": "Dashboard title is required"}

        url_path = dashboard_id or config.get("url_path")
        if not url_path:
            return {"error": "Dashboard URL path is required"}

        url_path = url_path.lower().replace(" ", "-").replace("_", "-")

        # Check for duplicate
        lovelace_config_file = self.hass.config.path(f"ui-lovelace-{url_path}.yaml")
        file_exists = await self.hass.async_add_executor_job(
            lambda: os.path.exists(lovelace_config_file)
        )
        if file_exists:
            return {"error": f"Dashboard '{url_path}' already exists"}

        dashboard_data = {
            "title": config["title"],
            "icon": config.get("icon", "mdi:view-dashboard"),
            "show_in_sidebar": config.get("show_in_sidebar", True),
            "require_admin": config.get("require_admin", False),
            "views": config.get("views", []),
        }

        if dry_run:
            validation = self.validate_dashboard_config(dashboard_data)
            preview_yaml = yaml.dump(
                dashboard_data, default_flow_style=False, allow_unicode=True
            )
            return {
                "dry_run": True,
                "title": config["title"],
                "url_path": url_path,
                "preview": preview_yaml,
                "validation": validation,
            }

        # --- Existing write logic (unchanged) ---
        def write_dashboard_file():
            with open(lovelace_config_file, "w") as f:
                yaml.dump(
                    dashboard_data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                )

        await self.hass.async_add_executor_job(write_dashboard_file)

        _LOGGER.info("Successfully created dashboard file: %s", lovelace_config_file)

        try:
            config_updated = await self._update_configuration_yaml(url_path, config)

            if config_updated:
                return {
                    "success": True,
                    "message": f"Dashboard '{config['title']}' created successfully. Restart required.",
                    "url_path": url_path,
                    "restart_required": True,
                }
            else:
                return {
                    "success": True,
                    "message": "Dashboard file created. Manual configuration.yaml update may be needed.",
                    "url_path": url_path,
                    "restart_required": True,
                }

        except Exception as config_error:
            _LOGGER.warning("Could not update configuration.yaml: %s", str(config_error))
            return {
                "success": True,
                "message": "Dashboard file created but configuration.yaml update failed.",
                "url_path": url_path,
                "restart_required": True,
            }

    except Exception as e:
        _LOGGER.exception("Error creating dashboard: %s", str(e))
        return {"error": f"Error creating dashboard: {str(e)}"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_managers/test_dashboard_manager.py::TestCreateDashboard -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/managers/dashboard_manager.py tests/test_managers/test_dashboard_manager.py
git commit -m "add dry_run to create_dashboard in DashboardManager"
```

---

### Task 2: Add `dry_run` to `DashboardManager.update_dashboard`

**Files:**
- Modify: `custom_components/homeclaw/managers/dashboard_manager.py:414-479`
- Test: `tests/test_managers/test_dashboard_manager.py`

- [ ] **Step 1: Write failing tests for dry_run=True on update**

Add to `tests/test_managers/test_dashboard_manager.py` inside `TestUpdateDashboard`:

```python
@pytest.mark.asyncio
async def test_update_dashboard_dry_run_returns_preview(self, dashboard_manager, hass):
    """Test that dry_run=True returns old and new config preview."""
    config = {
        "title": "Updated Dashboard",
        "views": [{"title": "Updated View", "cards": []}],
    }
    existing_yaml = yaml.dump({
        "title": "Old Dashboard",
        "icon": "mdi:view-dashboard",
        "show_in_sidebar": True,
        "require_admin": False,
        "views": [{"title": "Old View", "cards": []}],
    })

    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=existing_yaml)):
            result = await dashboard_manager.update_dashboard(
                "test-dash", config, dry_run=True
            )

    assert result.get("dry_run") is True
    assert "current_config" in result
    assert "new_config" in result

@pytest.mark.asyncio
async def test_update_dashboard_dry_run_does_not_write(self, dashboard_manager, hass):
    """Test that dry_run=True does not overwrite the file."""
    config = {"title": "Updated", "views": []}
    existing_yaml = yaml.dump({"title": "Old", "views": [], "icon": "mdi:test",
                                "show_in_sidebar": True, "require_admin": False})

    mock_file = mock_open(read_data=existing_yaml)
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_file):
            await dashboard_manager.update_dashboard("test-dash", config, dry_run=True)

    # open should be called for reading, but not for writing
    for call in mock_file.call_args_list:
        if len(call[0]) > 1:
            assert call[0][1] != "w", "File should not be opened for writing in dry_run"

@pytest.mark.asyncio
async def test_update_dashboard_dry_run_not_found(self, dashboard_manager, hass):
    """Test dry_run on non-existent dashboard returns error."""
    config = {"title": "Updated", "views": []}

    with patch("os.path.exists", return_value=False):
        result = await dashboard_manager.update_dashboard(
            "nonexistent", config, dry_run=True
        )

    assert "error" in result

@pytest.mark.asyncio
async def test_update_dashboard_rejects_empty_url(self, dashboard_manager, hass):
    """Test that empty dashboard_id is rejected."""
    result = await dashboard_manager.update_dashboard("", {"title": "X"})

    assert "error" in result
    assert "default" in result["error"].lower() or "empty" in result["error"].lower()

@pytest.mark.asyncio
async def test_update_dashboard_dry_run_false_writes(self, dashboard_manager, hass):
    """Test that dry_run=False preserves existing write behavior."""
    config = {"title": "Updated", "views": [{"title": "V", "cards": []}]}

    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open()) as mock_file:
            result = await dashboard_manager.update_dashboard(
                "test-dash", config, dry_run=False
            )

    assert result.get("success") is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_managers/test_dashboard_manager.py::TestUpdateDashboard -v`
Expected: FAIL — `update_dashboard()` does not accept `dry_run` parameter.

- [ ] **Step 3: Implement dry_run in update_dashboard**

In `custom_components/homeclaw/managers/dashboard_manager.py`, modify `update_dashboard` (line 414):

```python
async def update_dashboard(
    self, dashboard_id: str, config: dict[str, Any], *, dry_run: bool = True
) -> dict[str, Any]:
    """Update an existing dashboard.

    Args:
        dashboard_id: The dashboard URL path to update.
        config: New dashboard configuration.
        dry_run: If True, return preview without writing.

    Returns:
        Result dictionary with preview (dry_run) or success status.
    """
    try:
        if not dashboard_id:
            return {"error": "Cannot modify the default dashboard through this tool"}

        _LOGGER.debug("Updating dashboard %s (dry_run=%s)", dashboard_id, dry_run)

        # Locate dashboard file
        dashboard_file = self.hass.config.path(f"ui-lovelace-{dashboard_id}.yaml")
        file_exists = await self.hass.async_add_executor_job(
            lambda: os.path.exists(dashboard_file)
        )

        if not file_exists:
            alt_dashboard_file = self.hass.config.path(f"dashboards/{dashboard_id}.yaml")
            alt_exists = await self.hass.async_add_executor_job(
                lambda: os.path.exists(alt_dashboard_file)
            )
            if alt_exists:
                dashboard_file = alt_dashboard_file
                file_exists = True

        if not file_exists:
            return {"error": f"Dashboard file for '{dashboard_id}' not found"}

        dashboard_data = {
            "title": config.get("title", "Updated Dashboard"),
            "icon": config.get("icon", "mdi:view-dashboard"),
            "show_in_sidebar": config.get("show_in_sidebar", True),
            "require_admin": config.get("require_admin", False),
            "views": config.get("views", []),
        }

        if dry_run:
            # Read current config for diff
            def read_current():
                with open(dashboard_file, "r") as f:
                    return yaml.safe_load(f) or {}

            current_config = await self.hass.async_add_executor_job(read_current)
            validation = self.validate_dashboard_config(dashboard_data)

            return {
                "dry_run": True,
                "dashboard_url": dashboard_id,
                "current_config": yaml.dump(
                    current_config, default_flow_style=False, allow_unicode=True
                ),
                "new_config": yaml.dump(
                    dashboard_data, default_flow_style=False, allow_unicode=True
                ),
                "validation": validation,
            }

        # --- Existing write logic ---
        def update_dashboard_file():
            with open(dashboard_file, "w") as f:
                yaml.dump(
                    dashboard_data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                )

        await self.hass.async_add_executor_job(update_dashboard_file)

        _LOGGER.info("Successfully updated dashboard file: %s", dashboard_file)
        return {
            "success": True,
            "message": f"Dashboard '{dashboard_id}' updated successfully!",
        }

    except Exception as e:
        _LOGGER.exception("Error updating dashboard: %s", str(e))
        return {"error": f"Error updating dashboard: {str(e)}"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_managers/test_dashboard_manager.py::TestUpdateDashboard -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/managers/dashboard_manager.py tests/test_managers/test_dashboard_manager.py
git commit -m "add dry_run to update_dashboard in DashboardManager"
```

---

### Task 3: Add `delete_dashboard` and `_remove_from_configuration_yaml` to DashboardManager

**Files:**
- Modify: `custom_components/homeclaw/managers/dashboard_manager.py`
- Test: `tests/test_managers/test_dashboard_manager.py`

- [ ] **Step 1: Write failing tests for _remove_from_configuration_yaml**

Add new test class to `tests/test_managers/test_dashboard_manager.py`:

```python
class TestRemoveFromConfigurationYaml:
    """Tests for _remove_from_configuration_yaml."""

    @pytest.mark.asyncio
    async def test_removes_dashboard_entry(self, dashboard_manager, hass):
        """Test removing a dashboard entry from configuration.yaml."""
        content = (
            "homeassistant:\n"
            "  name: My Home\n"
            "\n"
            "lovelace:\n"
            "  dashboards:\n"
            "    energy:\n"
            "      mode: yaml\n"
            "      title: Energy\n"
            "      icon: mdi:flash\n"
            "      filename: ui-lovelace-energy.yaml\n"
            "    climate:\n"
            "      mode: yaml\n"
            "      title: Climate\n"
            "      filename: ui-lovelace-climate.yaml\n"
        )

        with patch("builtins.open", mock_open(read_data=content)):
            with patch(
                "custom_components.homeclaw.managers.dashboard_manager.atomic_write_file"
            ) as mock_write:
                with patch(
                    "custom_components.homeclaw.managers.dashboard_manager.backup_file"
                ):
                    result = await dashboard_manager._remove_from_configuration_yaml("energy")

        assert result is True
        written = mock_write.call_args[0][1]
        assert "energy:" not in written
        assert "climate:" in written

    @pytest.mark.asyncio
    async def test_removes_only_dashboard_entry(self, dashboard_manager, hass):
        """Test removing the only dashboard leaves dashboards: key."""
        content = (
            "lovelace:\n"
            "  dashboards:\n"
            "    energy:\n"
            "      mode: yaml\n"
            "      title: Energy\n"
            "      filename: ui-lovelace-energy.yaml\n"
        )

        with patch("builtins.open", mock_open(read_data=content)):
            with patch(
                "custom_components.homeclaw.managers.dashboard_manager.atomic_write_file"
            ) as mock_write:
                with patch(
                    "custom_components.homeclaw.managers.dashboard_manager.backup_file"
                ):
                    result = await dashboard_manager._remove_from_configuration_yaml("energy")

        assert result is True
        written = mock_write.call_args[0][1]
        assert "energy:" not in written
        assert "lovelace:" in written

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self, dashboard_manager, hass):
        """Test returns False when dashboard entry not found."""
        content = (
            "lovelace:\n"
            "  dashboards:\n"
            "    climate:\n"
            "      mode: yaml\n"
            "      title: Climate\n"
        )

        with patch("builtins.open", mock_open(read_data=content)):
            with patch(
                "custom_components.homeclaw.managers.dashboard_manager.backup_file"
            ):
                result = await dashboard_manager._remove_from_configuration_yaml("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_no_lovelace(self, dashboard_manager, hass):
        """Test returns False when no lovelace section exists."""
        content = "homeassistant:\n  name: My Home\n"

        with patch("builtins.open", mock_open(read_data=content)):
            with patch(
                "custom_components.homeclaw.managers.dashboard_manager.backup_file"
            ):
                result = await dashboard_manager._remove_from_configuration_yaml("energy")

        assert result is False
```

- [ ] **Step 2: Write failing tests for delete_dashboard**

Add new test class to `tests/test_managers/test_dashboard_manager.py`:

```python
class TestDeleteDashboard:
    """Tests for delete_dashboard method."""

    @pytest.mark.asyncio
    async def test_delete_dry_run_returns_info(self, dashboard_manager, hass):
        """Test dry_run=True returns info about what will be deleted."""
        existing_yaml = yaml.dump({"title": "Energy", "views": []})

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=existing_yaml)):
                result = await dashboard_manager.delete_dashboard("energy", dry_run=True)

        assert result.get("dry_run") is True
        assert result.get("exists") is True
        assert "file" in result
        assert "title" in result

    @pytest.mark.asyncio
    async def test_delete_dry_run_not_found(self, dashboard_manager, hass):
        """Test dry_run on non-existent dashboard."""
        with patch("os.path.exists", return_value=False):
            result = await dashboard_manager.delete_dashboard("nonexistent", dry_run=True)

        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_delete_dry_run_false_removes_file(self, dashboard_manager, hass):
        """Test dry_run=False actually deletes the file."""
        existing_yaml = yaml.dump({"title": "Energy", "views": []})

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=existing_yaml)):
                with patch("os.remove") as mock_remove:
                    with patch.object(
                        dashboard_manager, "_remove_from_configuration_yaml",
                        new_callable=AsyncMock, return_value=True
                    ):
                        result = await dashboard_manager.delete_dashboard(
                            "energy", dry_run=False
                        )

        assert result.get("success") is True
        assert result.get("restart_required") is True
        mock_remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_rejects_empty_url(self, dashboard_manager, hass):
        """Test that empty dashboard_id is rejected."""
        result = await dashboard_manager.delete_dashboard("")

        assert "error" in result
        assert "default" in result["error"].lower() or "cannot" in result["error"].lower()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_managers/test_dashboard_manager.py::TestDeleteDashboard tests/test_managers/test_dashboard_manager.py::TestRemoveFromConfigurationYaml -v`
Expected: FAIL — methods don't exist yet.

- [ ] **Step 4: Implement _remove_from_configuration_yaml**

Add to `custom_components/homeclaw/managers/dashboard_manager.py` after `_do_update_configuration_yaml`:

```python
async def _remove_from_configuration_yaml(self, url_path: str) -> bool:
    """Remove a dashboard entry from configuration.yaml.

    Args:
        url_path: The dashboard URL path to remove.

    Returns:
        True if entry was found and removed, False otherwise.
    """
    config_file = self.hass.config.path("configuration.yaml")

    async with CONFIG_WRITE_LOCK:
        return await self.hass.async_add_executor_job(
            self._do_remove_from_configuration_yaml, config_file, url_path
        )

@staticmethod
def _do_remove_from_configuration_yaml(config_file: str, url_path: str) -> bool:
    """Synchronous configuration.yaml entry removal (runs in executor).

    Algorithm: line-based scan. Find the url_path: line under dashboards:,
    delete it and all following lines at deeper indentation.

    Args:
        config_file: Path to configuration.yaml.
        url_path: Dashboard URL path to remove.

    Returns:
        True if entry was removed, False if not found.
    """
    try:
        backup_file(config_file)
    except Exception:
        _LOGGER.warning("Failed to backup configuration.yaml before dashboard removal")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return False

    lines = content.split("\n")

    # Find the dashboard entry
    in_lovelace = False
    in_dashboards = False
    entry_start = -1
    entry_indent = -1

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue

        if re.match(r"^lovelace:", line):
            in_lovelace = True
            continue

        if in_lovelace and re.match(r"^\s+dashboards:", line):
            in_dashboards = True
            continue

        if in_lovelace and not line.startswith(" "):
            # Left lovelace section
            in_lovelace = False
            in_dashboards = False
            continue

        if in_dashboards:
            # Match the specific dashboard entry (4-space indent)
            match = re.match(rf"^(\s+){re.escape(url_path)}:", line)
            if match:
                entry_start = idx
                entry_indent = len(match.group(1))
                break

    if entry_start == -1:
        return False

    # Find end of entry block — all lines indented deeper than entry_indent
    entry_end = entry_start + 1
    while entry_end < len(lines):
        line = lines[entry_end]
        if not line.strip():  # blank line
            entry_end += 1
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent <= entry_indent:
            break
        entry_end += 1

    # Remove the entry lines
    new_lines = lines[:entry_start] + lines[entry_end:]
    new_content = "\n".join(new_lines)

    try:
        atomic_write_file(config_file, new_content)
        return True
    except Exception as exc:
        _LOGGER.error("Failed to write configuration.yaml: %s", exc)
        return False
```

- [ ] **Step 5: Implement delete_dashboard**

Add to `custom_components/homeclaw/managers/dashboard_manager.py` after `update_dashboard`:

```python
async def delete_dashboard(
    self, dashboard_id: str, *, dry_run: bool = True
) -> dict[str, Any]:
    """Delete an existing dashboard.

    Args:
        dashboard_id: The dashboard URL path to delete.
        dry_run: If True, return info without deleting.

    Returns:
        Result dictionary with info (dry_run) or success status.
    """
    try:
        if not dashboard_id:
            return {"error": "Cannot delete the default dashboard"}

        _LOGGER.debug("Deleting dashboard %s (dry_run=%s)", dashboard_id, dry_run)

        # Locate dashboard file
        dashboard_file = self.hass.config.path(f"ui-lovelace-{dashboard_id}.yaml")
        file_exists = await self.hass.async_add_executor_job(
            lambda: os.path.exists(dashboard_file)
        )

        if not file_exists:
            alt_dashboard_file = self.hass.config.path(f"dashboards/{dashboard_id}.yaml")
            alt_exists = await self.hass.async_add_executor_job(
                lambda: os.path.exists(alt_dashboard_file)
            )
            if alt_exists:
                dashboard_file = alt_dashboard_file
                file_exists = True

        if not file_exists:
            return {"error": f"Dashboard '{dashboard_id}' not found"}

        # Read current config for info
        def read_current():
            with open(dashboard_file, "r") as f:
                return yaml.safe_load(f) or {}

        current_config = await self.hass.async_add_executor_job(read_current)

        if dry_run:
            return {
                "dry_run": True,
                "exists": True,
                "dashboard_url": dashboard_id,
                "file": dashboard_file,
                "title": current_config.get("title", dashboard_id),
                "preview": yaml.dump(
                    current_config, default_flow_style=False, allow_unicode=True
                ),
            }

        # Delete the file
        await self.hass.async_add_executor_job(os.remove, dashboard_file)
        _LOGGER.info("Deleted dashboard file: %s", dashboard_file)

        # Remove from configuration.yaml
        config_removed = await self._remove_from_configuration_yaml(dashboard_id)
        if not config_removed:
            _LOGGER.warning(
                "Dashboard file deleted but entry not found in configuration.yaml"
            )

        return {
            "success": True,
            "message": f"Dashboard '{dashboard_id}' deleted. Restart required.",
            "restart_required": True,
        }

    except Exception as e:
        _LOGGER.exception("Error deleting dashboard: %s", str(e))
        return {"error": f"Error deleting dashboard: {str(e)}"}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_managers/test_dashboard_manager.py::TestDeleteDashboard tests/test_managers/test_dashboard_manager.py::TestRemoveFromConfigurationYaml -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add custom_components/homeclaw/managers/dashboard_manager.py tests/test_managers/test_dashboard_manager.py
git commit -m "add delete_dashboard and _remove_from_configuration_yaml"
```

---

### Task 4: Register 3 new tools in ha_native.py

**Files:**
- Modify: `custom_components/homeclaw/tools/ha_native.py` (append after line 1358)
- Create: `tests/test_tools/__init__.py` (empty)
- Create: `tests/test_tools/test_dashboard_tools.py`

- [ ] **Step 1: Create test directory and write failing tests**

Create `tests/test_tools/__init__.py` (empty file) and `tests/test_tools/test_dashboard_tools.py`:

```python
"""Tests for dashboard management tools."""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.homeclaw.tools.base import ToolRegistry, ToolResult, ToolTier


@pytest.fixture
def mock_hass():
    """Minimal hass mock for tool tests (named to avoid conftest hass conflict)."""
    h = MagicMock()
    h.config.path = MagicMock(side_effect=lambda x: f"/config/{x}")
    h.async_add_executor_job = AsyncMock(side_effect=lambda f, *a: f(*a) if a else f())
    h.data = {}
    return h


@pytest.fixture
def mock_config():
    """Minimal config dict."""
    return {}


class TestCreateDashboardTool:
    """Tests for CreateDashboard tool."""

    @pytest.mark.asyncio
    async def test_tool_registered(self):
        """Test that create_dashboard is registered in ToolRegistry."""
        tool_cls = ToolRegistry.get_tool_class("create_dashboard")
        assert tool_cls is not None

    @pytest.mark.asyncio
    async def test_tool_is_core_tier(self):
        """Test that create_dashboard is CORE tier."""
        tool_cls = ToolRegistry.get_tool_class("create_dashboard")
        assert tool_cls.tier == ToolTier.CORE

    @pytest.mark.asyncio
    async def test_dry_run_true_returns_preview(self, mock_hass, mock_config):
        """Test dry_run=true returns YAML preview."""
        mock_result = {
            "dry_run": True,
            "title": "Security",
            "url_path": "security",
            "preview": "title: Security\n",
            "validation": {"valid": True, "warnings": [], "errors": []},
        }

        with patch(
            "custom_components.homeclaw.managers.dashboard_manager.DashboardManager.create_dashboard",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            tool = ToolRegistry.get_tool("create_dashboard", hass=mock_hass, config=mock_config)
            result = await tool.execute(
                title="Security",
                url_path="security",
                views=[{"title": "Cameras", "cards": []}],
                dry_run=True,
            )

        assert result.success
        output = json.loads(result.output)
        assert output["dry_run"] is True

    @pytest.mark.asyncio
    async def test_dry_run_false_creates(self, mock_hass, mock_config):
        """Test dry_run=false creates dashboard."""
        mock_result = {
            "success": True,
            "message": "Dashboard created.",
            "url_path": "security",
            "restart_required": True,
        }

        with patch(
            "custom_components.homeclaw.managers.dashboard_manager.DashboardManager.create_dashboard",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            tool = ToolRegistry.get_tool("create_dashboard", hass=mock_hass, config=mock_config)
            result = await tool.execute(
                title="Security",
                url_path="security",
                views=[{"title": "Cameras", "cards": []}],
                dry_run=False,
            )

        assert result.success
        output = json.loads(result.output)
        assert output["success"] is True


class TestUpdateDashboardTool:
    """Tests for UpdateDashboard tool."""

    @pytest.mark.asyncio
    async def test_tool_registered(self):
        """Test that update_dashboard is registered."""
        tool_cls = ToolRegistry.get_tool_class("update_dashboard")
        assert tool_cls is not None

    @pytest.mark.asyncio
    async def test_dry_run_returns_diff(self, mock_hass, mock_config):
        """Test dry_run returns current vs new config."""
        mock_result = {
            "dry_run": True,
            "dashboard_url": "energy",
            "current_config": "title: Old\n",
            "new_config": "title: New\n",
            "validation": {"valid": True, "warnings": [], "errors": []},
        }

        with patch(
            "custom_components.homeclaw.managers.dashboard_manager.DashboardManager.update_dashboard",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            tool = ToolRegistry.get_tool("update_dashboard", hass=mock_hass, config=mock_config)
            result = await tool.execute(
                dashboard_url="energy",
                title="New Energy",
                views=[],
                dry_run=True,
            )

        assert result.success
        output = json.loads(result.output)
        assert output["dry_run"] is True


class TestDeleteDashboardTool:
    """Tests for DeleteDashboard tool."""

    @pytest.mark.asyncio
    async def test_tool_registered(self):
        """Test that delete_dashboard is registered."""
        tool_cls = ToolRegistry.get_tool_class("delete_dashboard")
        assert tool_cls is not None

    @pytest.mark.asyncio
    async def test_dry_run_returns_info(self, mock_hass, mock_config):
        """Test dry_run returns info about what will be deleted."""
        mock_result = {
            "dry_run": True,
            "exists": True,
            "dashboard_url": "energy",
            "file": "/config/ui-lovelace-energy.yaml",
            "title": "Energy",
            "preview": "title: Energy\n",
        }

        with patch(
            "custom_components.homeclaw.managers.dashboard_manager.DashboardManager.delete_dashboard",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            tool = ToolRegistry.get_tool("delete_dashboard", hass=mock_hass, config=mock_config)
            result = await tool.execute(dashboard_url="energy", dry_run=True)

        assert result.success
        output = json.loads(result.output)
        assert output["exists"] is True

    @pytest.mark.asyncio
    async def test_dry_run_false_deletes(self, mock_hass, mock_config):
        """Test dry_run=false deletes dashboard."""
        mock_result = {
            "success": True,
            "message": "Dashboard deleted.",
            "restart_required": True,
        }

        with patch(
            "custom_components.homeclaw.managers.dashboard_manager.DashboardManager.delete_dashboard",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            tool = ToolRegistry.get_tool("delete_dashboard", hass=mock_hass, config=mock_config)
            result = await tool.execute(dashboard_url="energy", dry_run=False)

        assert result.success
        output = json.loads(result.output)
        assert output["success"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tools/test_dashboard_tools.py -v`
Expected: FAIL — tool classes don't exist yet.

- [ ] **Step 3: Implement 3 tool classes**

Append to end of `custom_components/homeclaw/tools/ha_native.py` (after line 1358):

```python


@ToolRegistry.register
class CreateDashboard(Tool):
    id = "create_dashboard"
    description = (
        "Create a new Lovelace dashboard. Use dry_run=true first to preview, "
        "then dry_run=false after user confirms."
    )
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(name="title", type="string", description="Dashboard title", required=True),
        ToolParameter(name="url_path", type="string", description="URL path (e.g. 'security')", required=True),
        ToolParameter(name="icon", type="string", description="MDI icon (default: mdi:view-dashboard)", required=False),
        ToolParameter(
            name="show_in_sidebar", type="boolean", description="Show in HA sidebar (default: true)", required=False
        ),
        ToolParameter(name="views", type="list", description="List of views with cards", required=True),
        ToolParameter(
            name="dry_run",
            type="boolean",
            description="Preview without saving (default: true). Set false to create.",
            required=False,
        ),
    ]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            from ..managers.dashboard_manager import DashboardManager

            manager = DashboardManager(self.hass)
            config = {
                "title": kwargs["title"],
                "url_path": kwargs["url_path"],
                "icon": kwargs.get("icon", "mdi:view-dashboard"),
                "show_in_sidebar": kwargs.get("show_in_sidebar", True),
                "views": kwargs.get("views", []),
            }
            dry_run = kwargs.get("dry_run", True)

            result = await manager.create_dashboard(config, dry_run=dry_run)

            if "error" in result:
                return ToolResult(output=json.dumps(result), error=result["error"], success=False)

            return ToolResult(output=json.dumps(result, default=str), metadata=result)
        except Exception as e:
            _LOGGER.error("Error in create_dashboard tool: %s", e)
            return ToolResult(output=f"Error: {e}", error=str(e), success=False)


@ToolRegistry.register
class UpdateDashboard(Tool):
    id = "update_dashboard"
    description = (
        "Update an existing Lovelace dashboard. Use dry_run=true first to preview changes, "
        "then dry_run=false after user confirms."
    )
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="dashboard_url", type="string", description="URL path of existing dashboard", required=True
        ),
        ToolParameter(name="title", type="string", description="New dashboard title", required=False),
        ToolParameter(name="icon", type="string", description="New MDI icon", required=False),
        ToolParameter(name="show_in_sidebar", type="boolean", description="Show in HA sidebar", required=False),
        ToolParameter(name="views", type="list", description="New list of views with cards", required=False),
        ToolParameter(
            name="dry_run",
            type="boolean",
            description="Preview without saving (default: true). Set false to apply.",
            required=False,
        ),
    ]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            from ..managers.dashboard_manager import DashboardManager

            manager = DashboardManager(self.hass)
            dashboard_url = kwargs["dashboard_url"]
            config = {}
            for key in ("title", "icon", "show_in_sidebar", "views"):
                if key in kwargs:
                    config[key] = kwargs[key]
            dry_run = kwargs.get("dry_run", True)

            result = await manager.update_dashboard(dashboard_url, config, dry_run=dry_run)

            if "error" in result:
                return ToolResult(output=json.dumps(result), error=result["error"], success=False)

            return ToolResult(output=json.dumps(result, default=str), metadata=result)
        except Exception as e:
            _LOGGER.error("Error in update_dashboard tool: %s", e)
            return ToolResult(output=f"Error: {e}", error=str(e), success=False)


@ToolRegistry.register
class DeleteDashboard(Tool):
    id = "delete_dashboard"
    description = (
        "Delete a Lovelace dashboard. Use dry_run=true first to see what will be deleted, "
        "then dry_run=false after user confirms."
    )
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="dashboard_url", type="string", description="URL path of dashboard to delete", required=True
        ),
        ToolParameter(
            name="dry_run",
            type="boolean",
            description="Preview without deleting (default: true). Set false to delete.",
            required=False,
        ),
    ]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            from ..managers.dashboard_manager import DashboardManager

            manager = DashboardManager(self.hass)
            dashboard_url = kwargs["dashboard_url"]
            dry_run = kwargs.get("dry_run", True)

            result = await manager.delete_dashboard(dashboard_url, dry_run=dry_run)

            if "error" in result:
                return ToolResult(output=json.dumps(result), error=result["error"], success=False)

            return ToolResult(output=json.dumps(result, default=str), metadata=result)
        except Exception as e:
            _LOGGER.error("Error in delete_dashboard tool: %s", e)
            return ToolResult(output=f"Error: {e}", error=str(e), success=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tools/test_dashboard_tools.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/tools/ha_native.py tests/test_tools/__init__.py tests/test_tools/test_dashboard_tools.py
git commit -m "register create, update, delete dashboard tools"
```

---

### Task 5: Update method signatures, callsites, and blocklists

**Files:**
- Modify: `custom_components/homeclaw/agent_compat.py:524-536`
- Modify: `custom_components/homeclaw/core/agent.py:292-306`
- Modify: `custom_components/homeclaw/services.py:167,188`
- Modify: `custom_components/homeclaw/core/subagent.py:52-53`
- Modify: `custom_components/homeclaw/proactive/heartbeat.py:63-64`

**Important:** Both the method signatures AND the callsites must be updated. Adding
`dry_run=False` to a call without updating the receiving method's signature will cause
TypeError at runtime.

- [ ] **Step 1: Update agent_compat.py — signatures AND calls**

Update `create_dashboard` (line ~524) — add `dry_run` param and forward it:

```python
async def create_dashboard(self, dashboard_config: dict, *, dry_run: bool = True) -> dict[str, Any]:
    """Create a new dashboard."""
    return await self._agent.create_dashboard(dashboard_config, dry_run=dry_run)
```

Update `update_dashboard` (line ~528) — add `dry_run` param and forward it:

```python
async def update_dashboard(
    self,
    dashboard_url: str,
    dashboard_config: dict,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Update an existing dashboard."""
    return await self._agent._get_dashboard_manager().update_dashboard(
        dashboard_url, dashboard_config, dry_run=dry_run
    )
```

- [ ] **Step 2: Update core/agent.py — signature AND call**

Update `create_dashboard` (line ~292) — add `dry_run` param and forward it:

```python
async def create_dashboard(
    self, config: dict[str, Any], dashboard_id: str | None = None, *, dry_run: bool = True
) -> dict[str, Any]:
    """Create a new dashboard."""
    return await self._get_dashboard_manager().create_dashboard(
        config, dashboard_id, dry_run=dry_run
    )
```

- [ ] **Step 3: Update services.py callsites**

In `services.py`, add `dry_run=False` to both service handler calls:

Line 167: `return await agent.create_dashboard(dashboard_config)`
→ `return await agent.create_dashboard(dashboard_config, dry_run=False)`

Line 188: `return await agent.update_dashboard(dashboard_url, dashboard_config)`
→ `return await agent.update_dashboard(dashboard_url, dashboard_config, dry_run=False)`

- [ ] **Step 4: Update existing tests that call create/update without dry_run**

Since `dry_run` now defaults to `True`, existing tests that expect write behavior must
pass `dry_run=False` explicitly. Update in `tests/test_managers/test_dashboard_manager.py`:

- `TestCreateDashboard.test_create_dashboard_success`: add `dry_run=False`
- `TestCreateDashboard.test_create_dashboard_sanitizes_url_path`: add `dry_run=False`
- `TestCreateDashboard.test_create_dashboard_writes_yaml_file`: add `dry_run=False`
- `TestUpdateDashboard.test_update_dashboard_success`: add `dry_run=False`
- `TestUpdateDashboard.test_update_dashboard_preserves_structure`: add `dry_run=False`

Example fix:
```python
# Before:
result = await dashboard_manager.create_dashboard(config)
# After:
result = await dashboard_manager.create_dashboard(config, dry_run=False)
```

- [ ] **Step 5: Add delete_dashboard to blocklists**

In `core/subagent.py`, add `"delete_dashboard"` to `DENIED_TOOLS` frozenset (line ~53).

In `proactive/heartbeat.py`, add `"delete_dashboard"` to `HEARTBEAT_DENIED_TOOLS` frozenset (line ~64).

- [ ] **Step 6: Run existing tests to verify nothing is broken**

Run: `pytest tests/test_managers/test_dashboard_manager.py tests/test_core/test_agent.py tests/test_agent_compat.py tests/test_proactive/test_heartbeat.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add custom_components/homeclaw/services.py custom_components/homeclaw/agent_compat.py custom_components/homeclaw/core/agent.py custom_components/homeclaw/core/subagent.py custom_components/homeclaw/proactive/heartbeat.py tests/test_managers/test_dashboard_manager.py
git commit -m "update signatures and callsites with dry_run, add delete to blocklists"
```

---

### Task 6: Update prompts

**Files:**
- Modify: `custom_components/homeclaw/prompts.py:159-164,226`

- [ ] **Step 1: Replace dashboard_suggestion in BASE_SYSTEM_PROMPT**

In `prompts.py`, replace lines 159-164:

```python
"DASHBOARD CREATION (only when user explicitly asks!):\n"
"- First gather entities with get_* tools\n"
"- Then respond with EXACTLY this JSON format (UI needs it for install button):\n"
'{"request_type": "dashboard_suggestion", "message": "Here is your dashboard", '
'"dashboard": {"title": "...", "url_path": "...", "icon": "mdi:...", '
'"show_in_sidebar": true, "views": [...]}}\n\n'
```

With:

```python
"DASHBOARD MANAGEMENT (only when user explicitly asks!):\n"
"- First gather entities with get_* tools\n"
"- ALWAYS call create/update/delete_dashboard with dry_run=true first\n"
"- Show the YAML preview to user and wait for confirmation\n"
"- Only call with dry_run=false after user confirms\n"
"- Available tools: create_dashboard, update_dashboard, delete_dashboard\n\n"
```

- [ ] **Step 2: Replace dashboard_suggestion in SYSTEM_PROMPT_LOCAL**

In `prompts.py`, replace the `dashboard_suggestion` reference (line ~226):

```python
"3. DASHBOARD → Use 'dashboard_suggestion' (ONLY if explicitly asked!)\n"
```

With:

```python
"3. DASHBOARD → Use dashboard tools with dry_run=true first (ONLY if explicitly asked!)\n"
```

- [ ] **Step 3: Run full test suite to verify nothing broken**

Run: `pytest tests/ -v --timeout=60`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add custom_components/homeclaw/prompts.py
git commit -m "replace dashboard_suggestion prompt with dry_run tool flow"
```

---

### Task 7: Final integration test

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v --timeout=60`
Expected: ALL PASS, no regressions.

- [ ] **Step 2: Run linting**

Run: `black --check custom_components/homeclaw/managers/dashboard_manager.py custom_components/homeclaw/tools/ha_native.py custom_components/homeclaw/prompts.py custom_components/homeclaw/services.py custom_components/homeclaw/agent_compat.py custom_components/homeclaw/core/agent.py && isort --check custom_components/homeclaw/managers/dashboard_manager.py custom_components/homeclaw/tools/ha_native.py`

Fix any issues, commit separately if needed.

- [ ] **Step 3: Verify tool registration**

Quick sanity check — run in Python:

```bash
python -c "
from custom_components.homeclaw.tools.ha_native import *
from custom_components.homeclaw.tools.base import ToolRegistry
tools = [t.id for t in ToolRegistry.get_all_tools()]
assert 'create_dashboard' in tools
assert 'update_dashboard' in tools
assert 'delete_dashboard' in tools
print('All 3 dashboard tools registered.')
"
```
