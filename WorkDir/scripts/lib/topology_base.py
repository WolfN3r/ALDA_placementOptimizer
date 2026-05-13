"""
Abstract base classes for the decoupled placement-optimization framework.

TopologyBase — every topology must implement these methods.
SAMixin      — add to a topology to support Simulated Annealing.
GAMixin      — add to a topology to support Genetic Algorithms.

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
        """Return capability tokens, e.g. {'SA', 'GA'}."""


class SAMixin(ABC):

    @abstractmethod
    def perturb(self, temperature: float) -> Callable[[], None]:
        """
        Select and apply one SA operator in-place.
        Returns a parameterless undo closure that exactly reverses the mutation.
        May use temperature to adapt operator selection probabilities.
        """


class GAMixin(ABC):

    @abstractmethod
    def mutate(self) -> Callable[[], None]:
        """Apply one random mutation in-place. Returns undo closure."""

    @abstractmethod
    def crossover(self, other: "GAMixin") -> "GAMixin":
        """
        Combine self and other into a new valid offspring.
        Must not modify self or other.
        Offspring must be a fully valid topology state (no duplicates, no orphaned blocks).
        """

    @abstractmethod
    def random_init(self) -> None:
        """Re-randomize the topology state completely. Required for GA population seeding."""
