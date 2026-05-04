from __future__ import annotations

import os
from dataclasses import dataclass

from src.domain.training.models import ExecutorDefinition, ModelAdapterDefinition
from src.domain.training.registries import ExecutorRegistry, ModelRegistry


@dataclass(frozen=True)
class TrainingCatalogOption:
    key: str
    label: str
    description: str | None = None


@dataclass(frozen=True)
class TrainingCapabilitiesSnapshot:
    available: bool
    models: list[ModelAdapterDefinition]
    executors: list[ExecutorDefinition]
    dataset_profiles: list[TrainingCatalogOption]
    feature_profiles: list[TrainingCatalogOption]
    league_options: list[TrainingCatalogOption]
    days_back_options: list[int]
    reasons: list[dict[str, str]]


class ModelRegistryService(ModelRegistry):
    def __init__(self, models: list[ModelAdapterDefinition]) -> None:
        self._models = {model.key: model for model in models}

    @classmethod
    def build_default(cls) -> "ModelRegistryService":
        league_ids = _resolve_league_ids()
        supported_days_back = [30, 90, 180, 365, 550]
        models = [
            ModelAdapterDefinition(
                key="baseline-model",
                label="Baseline Model",
                description="Modelo base alineado con el pipeline historico actual.",
                supported_feature_profiles=["default", "aggressive"],
                supported_dataset_profiles=["default", "extended"],
                supported_executor_targets=["default", "local-worker"],
                supported_league_ids=league_ids,
                supported_days_back=supported_days_back,
                default_executor_target="default",
                artifact_format="pickle",
            ),
            ModelAdapterDefinition(
                key="xgboost-model",
                label="XGBoost Model",
                description="Adaptador alternativo para corridas comparativas y recipes nuevas.",
                supported_feature_profiles=["default"],
                supported_dataset_profiles=["default", "experimental"],
                supported_executor_targets=["default", "local-worker"],
                supported_league_ids=league_ids,
                supported_days_back=supported_days_back,
                default_executor_target="default",
                artifact_format="json",
            ),
        ]
        return cls(models)

    def list_models(self) -> list[ModelAdapterDefinition]:
        return list(self._models.values())

    def get_model(self, model_key: str) -> ModelAdapterDefinition | None:
        return self._models.get(model_key)


class TrainingExecutorRegistry(ExecutorRegistry):
    def __init__(self, executors: list[ExecutorDefinition], default_key: str) -> None:
        self._executors = {executor.key: executor for executor in executors}
        self._default_key = default_key

    @classmethod
    def build_default(cls) -> "TrainingExecutorRegistry":
        api_only_mode = os.getenv("API_ONLY_MODE", "false").strip().lower() == "true"
        executors = [
            ExecutorDefinition(
                key="default",
                label="Control Plane Queue",
                description="Acepta el job en el control plane y delega la ejecucion fuera del request web.",
                is_available=True,
                supports_cancel=False,
                supports_logs=True,
            ),
            ExecutorDefinition(
                key="local-worker",
                label="Local Worker",
                description="Ejecutor local para entornos donde el worker comparte runtime con el backend.",
                is_available=not api_only_mode,
                unavailable_reasons=(
                    ["API_ONLY_MODE activo: el worker local no esta expuesto desde el API web."]
                    if api_only_mode
                    else []
                ),
                supports_cancel=False,
                supports_logs=True,
            ),
        ]
        return cls(executors, default_key="default")

    def list_executors(self) -> list[ExecutorDefinition]:
        return list(self._executors.values())

    def get_executor(self, executor_key: str) -> ExecutorDefinition | None:
        return self._executors.get(executor_key)

    def get_default_executor(self) -> ExecutorDefinition | None:
        return self._executors.get(self._default_key)


class TrainingCapabilityService:
    def __init__(
        self,
        *,
        model_registry: ModelRegistry,
        executor_registry: ExecutorRegistry,
    ) -> None:
        self.model_registry = model_registry
        self.executor_registry = executor_registry

    def snapshot(self) -> TrainingCapabilitiesSnapshot:
        models = self.model_registry.list_models()
        executors = self.executor_registry.list_executors()
        reasons: list[dict[str, str]] = []
        available_executors = [executor for executor in executors if executor.is_available]
        if not models:
            reasons.append(
                {
                    "code": "model_catalog_empty",
                    "message": "No hay modelos registrados para entrenamiento manual.",
                }
            )
        if not available_executors:
            reasons.append(
                {
                    "code": "executor_unavailable",
                    "message": "No hay ejecutores disponibles en este momento.",
                }
            )

        dataset_profiles = _dedupe_options(
            profile
            for model in models
            for profile in (model.supported_dataset_profiles or ["default"])
        )
        feature_profiles = _dedupe_options(
            profile
            for model in models
            for profile in (model.supported_feature_profiles or ["default"])
        )
        league_options = _dedupe_options(
            league_id
            for model in models
            for league_id in (model.supported_league_ids or _resolve_league_ids())
        )
        days_back_options = sorted(
            {
                day
                for model in models
                for day in (model.supported_days_back or [30, 90, 180, 365, 550])
            }
        )

        return TrainingCapabilitiesSnapshot(
            available=bool(models) and bool(available_executors),
            models=models,
            executors=executors,
            dataset_profiles=dataset_profiles,
            feature_profiles=feature_profiles,
            league_options=league_options,
            days_back_options=days_back_options,
            reasons=reasons,
        )


def _resolve_league_ids() -> list[str]:
    raw_leagues = os.getenv("PREDICT_LEAGUES", "E0")
    resolved = [league.strip() for league in raw_leagues.split(",") if league.strip()]
    return resolved or ["E0"]


def _dedupe_options(values) -> list[TrainingCatalogOption]:
    seen: set[str] = set()
    options: list[TrainingCatalogOption] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        options.append(TrainingCatalogOption(key=normalized, label=normalized))
    return options