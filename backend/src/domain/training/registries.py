from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.training.models import ExecutorDefinition, ModelAdapterDefinition


class ModelRegistry(ABC):
    @abstractmethod
    def list_models(self) -> list[ModelAdapterDefinition]:
        """Return all registered model adapters."""

    @abstractmethod
    def get_model(self, model_key: str) -> ModelAdapterDefinition | None:
        """Resolve a model adapter by key."""


class ExecutorRegistry(ABC):
    @abstractmethod
    def list_executors(self) -> list[ExecutorDefinition]:
        """Return all registered training executors."""

    @abstractmethod
    def get_executor(self, executor_key: str) -> ExecutorDefinition | None:
        """Resolve a training executor by key."""

    @abstractmethod
    def get_default_executor(self) -> ExecutorDefinition | None:
        """Return the default executor for manual training requests."""