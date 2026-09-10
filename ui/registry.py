"""
View Registry for OmniRoute Phone OS UI Front-End.
Provides dynamic registration and decoupled dispatch for modular views.
"""

from typing import Dict, List, Optional
from ui.base_view import BaseView


class ViewRegistry:
    """
    Central catalog of UI views.
    Enables new applications and views to be plugged into the UI front-end
    dynamically without touching the core display or render engine.
    """

    _views: Dict[str, BaseView] = {}
    _order: List[str] = []

    @classmethod
    def register(cls, view: BaseView) -> None:
        """Registers a view instance."""
        vid = view.view_id
        cls._views[vid] = view
        if vid not in cls._order:
            cls._order.append(vid)

    @classmethod
    def get(cls, view_id: str) -> Optional[BaseView]:
        """Retrieves a registered view by ID."""
        return cls._views.get(view_id)

    @classmethod
    def has(cls, view_id: str) -> bool:
        """Checks if a view ID is registered."""
        return view_id in cls._views

    @classmethod
    def get_all(cls) -> List[BaseView]:
        """Returns all registered view instances in registration order."""
        return [cls._views[vid] for vid in cls._order if vid in cls._views]

    @classmethod
    def get_all_ids(cls) -> List[str]:
        """Returns list of all registered view IDs."""
        return list(cls._order)

    @classmethod
    def set_order(cls, order: List[str]) -> None:
        """Customizes navigation slide transition order."""
        cls._order = [vid for vid in order if vid in cls._views]
        for vid in cls._views:
            if vid not in cls._order:
                cls._order.append(vid)
