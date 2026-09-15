##################################
# exceptions.py
#
# Base exceptions for testgen.
# jcarlin@hmc.edu Nov 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Base exceptions for testgen."""

from difflib import get_close_matches
from pathlib import Path


class MissingRegistryItemError(KeyError):
    """Base class for missing registry item errors with helpful suggestions.

    Subclasses should be defined in their respective registry modules
    (e.g., MissingInstructionFormatterError in formatters/registry.py).
    """

    def __init__(
        self,
        item_name: str,
        available_items: list[str] | None = None,
        *,
        item_type: str = "item",
        registry_location: Path | None = None,
    ) -> None:
        """
        Initialize the exception with helpful context.

        Args:
            item_name: The item that was not found
            available_items: List of all registered items
            item_type: Human-readable description of what type of item
                       (e.g., "instruction formatter", "coverpoint generator")
            registry_location: Path where new items can be added
        """
        if available_items:
            # Find similar items using difflib
            similar_items = get_close_matches(item_name, available_items, n=5, cutoff=0.4)

            msg = f"No {item_type} registered for '{item_name}'. "
            if similar_items:
                msg += f"Similar items: {', '.join(similar_items)}. "
            else:
                msg += "No similar items found. "
            if registry_location:
                msg += f"To add support, create a new file in '{registry_location}'."
            super().__init__(msg)
        else:
            # Minimal message for unpickling
            super().__init__(item_name)
        self.item_name = item_name
