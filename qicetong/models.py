from __future__ import annotations

import math
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Fact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str | int | float | bool | None = None
    unit: str = ""
    period: str = ""
    evidence: list[str] = Field(default_factory=list, max_length=20)
    status: Literal["confirmed", "unverified", "conflict"] = "unverified"

    @field_validator("value")
    @classmethod
    def finite_number(cls, value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("数值必须有限")
        return value


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    title: str = Field(min_length=1, max_length=200)
    locator: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=30000)
    asset_id: str | None = None


class Company(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    name: str = Field(min_length=1, max_length=200)
    district: str = Field(default="海淀区", max_length=80)
    industry: str = Field(default="软件和信息技术服务业", max_length=100)
    is_demo: bool = True
    note: str = Field(default="", max_length=2000)
    facts: dict[str, Fact] = Field(default_factory=dict, max_length=200)
    evidence: list[Evidence] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def evidence_integrity(self):
        evidence_ids = [e.id for e in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("材料证据 ID 不能重复")
        known = set(evidence_ids)
        for key, fact in self.facts.items():
            if not key.replace("_", "").isalnum() or len(key) > 80:
                raise ValueError("无效字段名")
            if set(fact.evidence) - known:
                raise ValueError(f"{key} 引用了不存在的材料证据")
            if fact.status == "confirmed" and not fact.evidence:
                raise ValueError(f"{key} 确认前必须关联材料证据")
        return self


class ReviewRequest(BaseModel):
    company_id: str
    policy_id: str
    as_of: date = Field(default_factory=date.today)


class FactUpdate(BaseModel):
    value: str | float | bool | None
    unit: str = ""
    period: str = ""
    confirmed: bool = False
    note: str = Field(min_length=1, max_length=1000)
