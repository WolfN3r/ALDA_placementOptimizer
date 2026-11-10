"""
Abstract base classes for the decoupled placement-optimization framework.

TopologyBase — every topology must implement these methods.
SAMixin      — add to a topology to support Simulated Annealing.

Optimizers import only these ABCs, never concrete topology classes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class TopologyBase(ABC):

    @abstractmethod
    def seed(self, blocks: dict, mode: str = "random") -> None:
        """
        Initialize topology state from block definitions.
        mode="random" → random valid topology.
        mode="ordered" → deterministic left-to-right packing priority.
        Must leave the topology ready for an immediate decode() call.
        """

    @abstractmethod
    def decode(self) -> dict[str, tuple[float, float]]:
        """
        Run this topology's placer and return {block_id: (x, y)}.
        Only path from topology state to concrete block coordinates.
        """

    @abstractmethod
    def copy_state(self) -> Any:
        """Return a deep copy of current topology state. Called on every new best."""

    @abstractmethod
    def restore_state(self, saved: Any) -> None:
        """Restore the topology to a previously saved state."""

    @abstractmethod
    def capabilities(self) -> set[str]:
        """Return capability tokens, e.g. {'SA'}."""

    def get_variant_map(self) -> dict[str, int]:
        """Return {block_id: active_variant_idx} for the current topology state.
        Override in topologies that support variant selection."""
        return {}


class SAMixin(ABC):

    @abstractmethod
    def perturb(self, temperature: float) -> Callable[[], None]:
        """
        Select and apply one SA operator in-place.
        Returns a parameterless undo closure that exactly reverses the mutation.
        May use temperature to adapt operator selection probabilities.
        """
