"""Runtime settings for the equipment request runner."""

import os
from dataclasses import dataclass
from pathlib import Path

from enums import (
    FlagPrompt,
    GenerationModel,
    MaxStepsPrompt,
    ModelProvider,
    PlanPrompt,
    ReactPrompt,
    ReflectPrompt,
    StoreProvider,
)

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Settings:
    """Paths and model hosts read from the environment, with lab defaults."""

    generation_provider: ModelProvider
    generation_model: GenerationModel
    store_provider: StoreProvider
    ollama_host: str
    data_dir: Path
    runs_dir: Path
    prompts_dir: Path
    golden_path: Path
    max_turns: int
    plan_prompt: PlanPrompt
    react_prompt: ReactPrompt
    reflect_prompt: ReflectPrompt
    flag_prompt: FlagPrompt
    max_steps_prompt: MaxStepsPrompt

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from env vars, falling back to local lab defaults."""
        return cls(
            generation_provider=ModelProvider(
                os.environ.get(
                    "GENERATION_PROVIDER",
                    ModelProvider.OLLAMA,
                )
            ),
            generation_model=GenerationModel(
                os.environ.get(
                    "GENERATION_MODEL",
                    GenerationModel.QWEN3_8B,
                )
            ),
            store_provider=StoreProvider(
                os.environ.get("STORE_PROVIDER", StoreProvider.JSON)
            ),
            ollama_host=os.environ.get(
                "OLLAMA_HOST",
                "http://host.docker.internal:11434",
            ),
            data_dir=Path(os.environ.get("DATA_DIR", str(ROOT / "data"))),
            runs_dir=Path(os.environ.get("RUNS_DIR", str(ROOT / "runs"))),
            prompts_dir=Path(
                os.environ.get("PROMPTS_DIR", str(ROOT / "src" / "prompts"))
            ),
            golden_path=Path(
                os.environ.get(
                    "GOLDEN_PATH",
                    str(ROOT / "data" / "golden" / "golden.json"),
                )
            ),
            max_turns=int(os.environ.get("MAX_TURNS", "8")),
            plan_prompt=PlanPrompt(
                os.environ.get("PLAN_PROMPT", PlanPrompt.V1)
            ),
            react_prompt=ReactPrompt(
                os.environ.get("REACT_PROMPT", ReactPrompt.V2)
            ),
            reflect_prompt=ReflectPrompt(
                os.environ.get("REFLECT_PROMPT", ReflectPrompt.V1)
            ),
            flag_prompt=FlagPrompt(
                os.environ.get("FLAG_PROMPT", FlagPrompt.V1)
            ),
            max_steps_prompt=MaxStepsPrompt(
                os.environ.get("MAX_STEPS_PROMPT", MaxStepsPrompt.V1)
            ),
        )