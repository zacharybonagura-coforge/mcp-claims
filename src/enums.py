"""Fixed names for adapters and prompt templates."""

from enum import StrEnum


class ModelProvider(StrEnum):
    OLLAMA = "ollama"


class GenerationModel(StrEnum):
    QWEN3_8B = "qwen3:8b"
    

class StoreProvider(StrEnum):
    JSON = "json"


class PlanPrompt(StrEnum):
    V1 = "plan.v1.md"


class ReactPrompt(StrEnum):
    V2 = "react.v2.md"


class ReflectPrompt(StrEnum):
    V1 = "reflect.v1.md"


class FlagPrompt(StrEnum):
    V1 = "flag.v1.md"


class MaxStepsPrompt(StrEnum):
    V1 = "max_steps.v1.md"