from __future__ import annotations

import logging
from pathlib import Path

from .bluez import BlueZ
from .matrix import apply_preset
from .models import (
    AssignBody,
    CustomMatrixBody,
    DelayBody,
    HubState,
    Preset,
    Role,
    Sink,
    VolumeBody,
)
from .pw import PipeWireGraph

log = logging.getLogger("btasio.engine")
STATE_PATH = Path.home() / ".config" / "btasio" / "state.json"


class Engine:
    def __init__(self) -> None:
        self.bluez = BlueZ()
        self.pw = PipeWireGraph()
        self.state = HubState(
            dry_run=not (self.bluez.available and self.pw.available),
            message="dry-run" if not self.pw.available else "ok",
        )
        self._load()
        self.refresh()

    def _load(self) -> None:
        self._saved_sinks: dict[str, Sink] = {}
        if not STATE_PATH.exists():
            return
        try:
            saved = HubState.model_validate_json(STATE_PATH.read_text())
            self.state.preset = saved.preset
            self.state.master_volume = saved.master_volume
            self._saved_sinks = {s.mac.upper(): s for s in saved.sinks}
        except Exception as exc:
            log.warning("state load failed: %s", exc)
            self._saved_sinks = {}

    def _save(self) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(self.state.model_dump_json(indent=2))

    def refresh(self) -> HubState:
        adapters = self.bluez.adapters()
        discovered = self.bluez.paired_sinks()
        saved = getattr(self, "_saved_sinks", {})
        pw_nodes = {n.get("mac"): n for n in self.pw.list_sink_nodes() if n.get("mac")}

        merged: dict[str, Sink] = {}
        for s in discovered:
            prev = saved.get(s.mac.upper())
            if prev:
                s.role = prev.role
                s.volume = prev.volume
                s.delay_ms = prev.delay_ms
                s.mute = prev.mute
                s.gain_l, s.gain_r, s.invert = prev.gain_l, prev.gain_r, prev.invert
            node = pw_nodes.get(s.mac.lower())
            if node:
                s.pw_node = node["name"]
                s.a2dp = True
            merged[s.mac.upper()] = s

        for mac, prev in saved.items():
            if mac not in merged:
                prev.connected = False
                prev.a2dp = False
                merged[mac] = prev

        self.state.adapters = adapters
        self.state.sinks = list(merged.values())
        apply_preset(self.state.sinks, self.state.preset)
        self.state.graph_ready = self.pw.ensure_master()
        self._saved_sinks = {s.mac.upper(): s for s in self.state.sinks}
        self._save()
        return self.state

    def apply_graph(self) -> HubState:
        self.refresh()
        apply_preset(self.state.sinks, self.state.preset)
        for s in self.state.sinks:
            self.pw.apply_sink(s)
        self.state.message = "graph applied"
        self._save()
        return self.state

    def set_preset(self, preset: Preset) -> HubState:
        self.state.preset = preset
        apply_preset(self.state.sinks, preset)
        return self.apply_graph()

    def assign(self, body: AssignBody) -> HubState:
        for s in self.state.sinks:
            if s.mac.upper() == body.mac.upper():
                s.role = body.role
        self.state.preset = Preset.CUSTOM if body.role == Role.UNASSIGNED else self.state.preset
        return self.apply_graph()

    def set_delay(self, body: DelayBody) -> HubState:
        for s in self.state.sinks:
            if s.mac.upper() == body.mac.upper():
                s.delay_ms = body.delay_ms
        return self.apply_graph()

    def set_volume(self, body: VolumeBody) -> HubState:
        if body.master:
            self.state.master_volume = body.volume
        else:
            for s in self.state.sinks:
                if s.mac.upper() == (body.mac or "").upper():
                    s.volume = body.volume
                    if body.mute is not None:
                        s.mute = body.mute
        return self.apply_graph()

    def set_matrix(self, body: CustomMatrixBody) -> HubState:
        self.state.preset = Preset.CUSTOM
        for s in self.state.sinks:
            if s.mac.upper() == body.mac.upper():
                s.gain_l, s.gain_r, s.invert = body.gain_l, body.gain_r, body.invert
        return self.apply_graph()

    def connect(self, mac: str, adapter: str | None) -> HubState:
        msg = self.bluez.pair_connect(mac, adapter)
        self.state.message = msg[-400:]
        return self.apply_graph()

    def disconnect(self, mac: str) -> HubState:
        self.bluez.disconnect(mac)
        return self.refresh()

    def scan(self, seconds: int = 8):
        self.state.scanning = True
        try:
            return self.bluez.scan(seconds)
        finally:
            self.state.scanning = False
