##################################
# exceptions.py
#
# Custom exceptions for testgen with helpful error messages.
# jcarlin@hmc.edu Nov 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Custom exceptions for testgen with helpful error messages."""

from difflib import get_close_matches
from pathlib import Path


class MissingRegistryItemError(KeyError):
    """Base class for missing registry item errors with helpful suggestions."""

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
            item_type: Human-readable description of what type of item (e.g., "instruction formatter", "coverpoint generator")
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


class MissingInstructionFormatterError(MissingRegistryItemError):
    """Raised when no instruction formatter is registered for a given instruction type."""

    def __init__(self, instr_type: str, available_types: list[str] | None = None) -> None:
        """
        Initialize the exception with helpful context.

        Args:
            instr_type: The instruction type that was not found
            available_types: List of all registered instruction types
        """
        registry_location = Path(__file__).parent / "formatters" / "types"
        super().__init__(
            instr_type,
            available_types,
            item_type="instruction formatter",
            registry_location=registry_location,
        )
        self.instr_type = instr_type


class MissingCoverpointGeneratorError(MissingRegistryItemError):
    """Raised when no coverpoint generator is registered for a given coverpoint."""

    def __init__(self, coverpoint: str, available_patterns: list[str] | None = None) -> None:
        """
        Initialize the exception with helpful context.

        Args:
            coverpoint: The coverpoint that was not found
            available_patterns: List of all registered coverpoint patterns
        """
        registry_location = Path(__file__).parent / "coverpoints"
        super().__init__(
            coverpoint,
            available_patterns,
            item_type="coverpoint generator",
            registry_location=registry_location,
        )
        self.coverpoint = coverpoint


class MissingPrivGeneratorError(MissingRegistryItemError):
    """Raised when no priv test generator is registered."""

    def __init__(self, extension: str, available_patterns: list[str] | None = None) -> None:
        """
        Initialize the exception with helpful context.

        Args:
            extension: The extension that was not found
            available_patterns: List of all registered extension patterns
        """
        registry_location = Path(__file__).parent / "priv" / "extensions"
        super().__init__(
            extension,
            available_patterns,
            item_type="privileged test generator",
            registry_location=registry_location,
        )
        self.extension = extension
