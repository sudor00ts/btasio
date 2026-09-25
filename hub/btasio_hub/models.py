from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Role(str, Enum):
    L = "L"
    R = "R"
    SUB = "SUB"
    MID = "MID"
    SIDE = "SIDE"
    EXTRA = "EXTRA"
    UNASSIGNED = "UNASSIGNED"


class Preset(str, Enum):
    STEREO_SUB = "stereo_sub"
    MID_SIDE = "mid_side"
    ALL = "all"
    CUSTOM = "custom"


class Adapter(BaseModel):
    hci: str
    address: str
    alias: str = ""
    powered: bool = True


class Sink(BaseModel):
    mac: str
    name: str
    adapter: str | None = None
    connected: bool = False
    a2dp: bool = False
    codec: str | None = None
    role: Role = Role.UNASSIGNED
    volume: float = Field(default=1.0, ge=0.0, le=1.5)
    delay_ms: int = Field(default=0, ge=0, le=500)
    mute: bool = False
    gain_l: float = 1.0
    gain_r: float = 1.0
    invert: bool = False
    pw_node: str | None = None


class HubState(BaseModel):
    preset: Preset = Preset.STEREO_SUB
    master_volume: float = Field(default=1.0, ge=0.0, le=1.5)
    sinks: list[Sink] = Field(default_factory=list)
    adapters: list[Adapter] = Field(default_factory=list)
    scanning: bool = False
    graph_ready: bool = False
    dry_run: bool = False
    message: str = ""


class ScanResult(BaseModel):
    mac: str
    name: str
    rssi: int | None = None
    a2dp_uuid: bool = False


class AssignBody(BaseModel):
    mac: str
    role: Role


class DelayBody(BaseModel):
    mac: str
    delay_ms: int = Field(ge=0, le=500)


class VolumeBody(BaseModel):
    mac: str | None = None
    volume: float = Field(ge=0.0, le=1.5)
    mute: bool | None = None
    master: bool = False


class ConnectBody(BaseModel):
    mac: str
    adapter: str | None = None


class PresetBody(BaseModel):
    preset: Preset


class CustomMatrixBody(BaseModel):
    mac: str
    gain_l: float
    gain_r: float
    invert: bool = False


RoleLiteral = Literal["L", "R", "SUB", "MID", "SIDE", "EXTRA", "UNASSIGNED"]
