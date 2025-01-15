"""Managers for Homeclaw.

This module contains manager classes extracted from the God Class
for better separation of concerns.
"""

from .automation_manager import AutomationManager
from .control_manager import ControlManager
from .dashboard_manager import DashboardManager
from .entity_manager import EntityManager
from .registry_manager import RegistryManager

__all__ = [
    "AutomationManager",
    "ControlManager",
    "DashboardManager",
    "EntityManager",
    "RegistryManager",
]
