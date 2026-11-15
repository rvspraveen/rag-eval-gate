"""Gate configuration (gate.yaml)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .errors import ConfigError
from .metrics import validate_names


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_drop: float | None = Field(default=None, ge=0)
    max_drop_rel: float | None = Field(default=None, ge=0, le=1)
    min: float | None = None
    severity: Literal["error", "warn"] = "error"

    @model_validator(mode="after")
    def _one_margin(self) -> Rule:
        if self.max_drop is not None and self.max_drop_rel is not None:
            raise ValueError("use either max_drop or max_drop_rel, not both")
        if self.max_drop is None and self.max_drop_rel is None and self.min is None:
            raise ValueError("a rule needs max_drop, max_drop_rel or min")
        return self

    def margin(self, baseline_mean: float) -> float | None:
        if self.max_drop is not None:
            return self.max_drop
        if self.max_drop_rel is not None:
            return self.max_drop_rel * baseline_mean
        return None


class Bootstrap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    samples: int = Field(default=2000, ge=100, le=100_000)
    confidence: float = Field(default=0.95, gt=0.5, lt=1)
    seed: int = 7


class Gate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: dict[str, Rule] = Field(min_length=1)
    bootstrap: Bootstrap = Field(default_factory=Bootstrap)
    min_items: int = Field(default=20, ge=1)
    item_drop: float = Field(default=0.1, gt=0)
    max_items_listed: int = Field(default=10, ge=0)


def load_gate(path: str | Path) -> Gate:
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"gate file not found: {p}")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ConfigError(f"{p}: invalid YAML ({e})") from e
    if not isinstance(raw, dict):
        raise ConfigError(f"{p}: expected a mapping at the top level")
    try:
        gate = Gate.model_validate(raw)
    except ValidationError as e:
        first = e.errors()[0]
        loc = ".".join(str(x) for x in first["loc"])
        raise ConfigError(f"{p}: {loc}: {first['msg']}") from e
    validate_names(list(gate.metrics))
    return gate
