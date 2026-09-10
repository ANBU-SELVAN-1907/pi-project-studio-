"""
Base View Interface for OmniRoute Phone OS UI Front-End.
Allows creating modular, easily upgradable, and enhanceable application screens.
"""

from typing import Dict, Any, Tuple, Optional
import pygame


class BaseView:
    """
    Abstract Base Class for all UI front-end views.
    Any new screen or application module can inherit from BaseView and be
    registered with ViewRegistry to immediately participate in navigation,
    rendering, and touch handling without modifying UIEngine internals.
    """

    view_id: str = "BASE"
    title: str = "Base View"
    icon: str = ""

    def render(self, screen: pygame.Surface, fonts: Dict[str, Any], colors: Dict[str, Any],
               engine: Any, ox: int = 0) -> None:
        """
        Renders view elements onto the display surface.
        :param screen: The Pygame Surface (240x320).
        :param fonts: Typography dictionary (header, body, small, title, key).
        :param colors: Active theme palette dictionary.
        :param engine: Reference to the UIEngine instance.
        :param ox: Horizontal pixel offset for smooth slide transitions.
        """
        raise NotImplementedError("Subclasses must implement render()")

    def handle_touch(self, pos: Tuple[int, int], engine: Any) -> Dict[str, Any]:
        """
        Processes touch/tap events on this view.
        :param pos: (x, y) coordinates of the touch.
        :param engine: Reference to the UIEngine instance.
        :return: Action dictionary e.g. {"type": "ACTION_NAME", "value": ...} or {"type": None, "value": None}.
        """
        return {"type": None, "value": None}

    def handle_scroll(self, dy: int, engine: Any) -> None:
        """
        Processes vertical drag/scroll gesture.
        :param dy: Delta Y in pixels.
        :param engine: Reference to the UIEngine instance.
        """
        pass

    def on_enter(self, engine: Any) -> None:
        """Called when this view becomes active."""
        pass

    def on_leave(self, engine: Any) -> None:
        """Called when navigating away from this view."""
        pass
