"""PipeWire graph controller."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass

from .models import Sink

log = logging.getLogger("btasio.pw")
MASTER = "btasio_in"
MASTER_DESC = "btasio Master"


@dataclass
class Loopback:
    mac: str
    pid: int | None
    capture: str
    playback: str


class PipeWireGraph:
    def __init__(self) -> None:
        self.available = shutil.which("pw-cli") is not None
        self.loopbacks: dict[str, Loopback] = {}
        self.pactl = shutil.which("pactl")
        self.pw_loopback = shutil.which("pw-loopback")
        self.pw_link = shutil.which("pw-link")

    def run(self, args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, text=True, capture_output=True, check=check)

    def ensure_master(self) -> bool:
        if not self.available or not self.pactl:
            log.warning("PipeWire tools not found — dry-run graph")
            return False
        existing = self.run(["pactl", "list", "short", "sinks"])
        if MASTER in existing.stdout:
            return True
        r = self.run([
            "pactl", "load-module", "module-null-sink",
            f"sink_name={MASTER}",
            f"sink_properties=device.description='{MASTER_DESC}'",
            "media.class=Audio/Sink", "audio.channels=2",
            "channel_map=front-left,front-right",
        ])
        if r.returncode != 0:
            log.error("null sink failed: %s", r.stderr)
            return False
        return True

    def list_sink_nodes(self) -> list[dict]:
        if not self.pactl:
            return []
        r = self.run(["pactl", "--format=json", "list", "sinks"])
        if r.returncode != 0:
            return []
        try:
            data = json.loads(r.stdout or "[]")
        except json.JSONDecodeError:
            return []
        out = []
        for s in data:
            name = s.get("name") or ""
            props = s.get("properties") or {}
            out.append({
                "name": name,
                "description": s.get("description") or props.get("device.description") or name,
                "bluez": name.startswith("bluez_output."),
                "mac": _mac_from_bluez_name(name),
            })
        return out

    def apply_sink(self, sink: Sink) -> None:
        if not self.available or not self.pw_loopback:
            return
        self.remove_sink(sink.mac)
        if sink.role.value == "UNASSIGNED" or sink.mute or not sink.pw_node:
            return
        target = sink.pw_node
        delay = max(sink.delay_ms, 0)
        playback_props = [
            f"node.name=btasio_to_{_safe(sink.mac)}",
            f"node.description=btasio {sink.name}",
            f"target.object={target}",
            "audio.channels=2",
        ]
        if delay:
            playback_props.append(f"target.delay.sec={delay / 1000.0:.4f}")
        capture_props = [
            f"node.name=btasio_cap_{_safe(sink.mac)}",
            "media.class=Stream/Input/Audio",
            f"target.object={MASTER}",
            "channelmix.upmix=false",
            "channelmix.normalize=false",
        ]
        cmd = [
            self.pw_loopback,
            "--capture-props", " ".join(capture_props),
            "--playback-props", " ".join(playback_props),
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self.loopbacks[sink.mac] = Loopback(
            mac=sink.mac, pid=proc.pid,
            capture=f"btasio_cap_{_safe(sink.mac)}",
            playback=f"btasio_to_{_safe(sink.mac)}",
        )
        self._link_matrix(sink)

    def _link_matrix(self, sink: Sink) -> None:
        if not self.pw_link or not sink.pw_node:
            return
        src_l = f"{MASTER}:monitor_FL"
        src_r = f"{MASTER}:monitor_FR"
        dst_l = f"{sink.pw_node}:playback_FL"
        dst_r = f"{sink.pw_node}:playback_FR"
        if sink.gain_l == 1.0 and sink.gain_r == 0.0:
            links = [(src_l, dst_l), (src_l, dst_r)]
        elif sink.gain_l == 0.0 and sink.gain_r == 1.0:
            links = [(src_r, dst_l), (src_r, dst_r)]
        else:
            links = [(src_l, dst_l), (src_l, dst_r), (src_r, dst_l), (src_r, dst_r)]
        for a, b in links:
            self.run([self.pw_link, a, b])

    def remove_sink(self, mac: str) -> None:
        lb = self.loopbacks.pop(mac, None)
        if lb and lb.pid:
            subprocess.run(["kill", str(lb.pid)], capture_output=True)

    def teardown(self) -> None:
        for mac in list(self.loopbacks):
            self.remove_sink(mac)


def _mac_from_bluez_name(name: str) -> str | None:
    if not name.startswith("bluez_output."):
        return None
    parts = name.split(".")
    if len(parts) < 2:
        return None
    return parts[1].replace("_", ":").lower()


def _safe(mac: str) -> str:
    return mac.replace(":", "_").lower()
