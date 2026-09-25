"""BlueZ D-Bus + bluetoothctl fallback.

We only speak standard profiles:
  A2DP Sink  0000110b-0000-1000-8000-00805f9b34fb
Never vendor party-mode UUIDs.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time

from .models import Adapter, ScanResult, Sink

log = logging.getLogger("btasio.bluez")

A2DP_SINK_UUID = "0000110b-0000-1000-8000-00805f9b34fb"


class BlueZ:
    def __init__(self) -> None:
        self.ctl = shutil.which("bluetoothctl")
        self.available = self.ctl is not None

    def _ctl(self, args: list[str], timeout: float = 8.0) -> str:
        if not self.ctl:
            return ""
        r = subprocess.run(
            [self.ctl, "--timeout", str(int(timeout)), *args],
            text=True,
            capture_output=True,
        )
        return (r.stdout or "") + (r.stderr or "")

    def adapters(self) -> list[Adapter]:
        if not self.available:
            return []
        raw = self._ctl(["list"])
        out: list[Adapter] = []
        for line in raw.splitlines():
            m = re.search(r"Controller\s+([0-9A-F:]{17})\s+(.+?)(?:\s+\[default\])?$", line, re.I)
            if not m:
                continue
            addr, alias = m.group(1), m.group(2).strip()
            info = self._ctl(["show", addr])
            powered = "Powered: yes" in info
            hci = "hci0"
            hm = re.search(r"hci(\d+)", info)
            if hm:
                hci = f"hci{hm.group(1)}"
            out.append(Adapter(hci=hci, address=addr.upper(), alias=alias, powered=powered))
        for i, a in enumerate(out):
            if a.hci == "hci0" and i > 0:
                a.hci = f"hci{i}"
        return out

    def paired_sinks(self) -> list[Sink]:
        if not self.available:
            return []
        raw = self._ctl(["devices"])
        sinks: list[Sink] = []
        for line in raw.splitlines():
            m = re.search(r"Device\s+([0-9A-F:]{17})\s+(.*)$", line, re.I)
            if not m:
                continue
            mac, name = m.group(1).upper(), m.group(2).strip()
            info = self._ctl(["info", mac])
            uuids = info.lower()
            has_a2dp = A2DP_SINK_UUID in uuids or "audio sink" in uuids or "0000110b" in uuids
            sinks.append(
                Sink(
                    mac=mac,
                    name=name or mac,
                    connected="Connected: yes" in info,
                    a2dp=has_a2dp or "Connected: yes" in info,
                )
            )
        return sinks

    def scan(self, seconds: int = 8) -> list[ScanResult]:
        if not self.available:
            return []
        proc = subprocess.Popen(
            [self.ctl, "--timeout", str(seconds), "scan", "on"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            out, _ = proc.communicate(timeout=seconds + 2)
        except subprocess.TimeoutExpired:
            proc.kill()
            out = proc.communicate()[0] or ""
        found: dict[str, ScanResult] = {}
        for line in out.splitlines():
            m = re.search(r"Device\s+([0-9A-F:]{17})\s+(.*)$", line, re.I)
            if not m:
                continue
            mac, name = m.group(1).upper(), m.group(2).strip()
            found[mac] = ScanResult(mac=mac, name=name or mac, a2dp_uuid=True)
        return list(found.values())

    def pair_connect(self, mac: str, adapter: str | None = None) -> str:
        if not self.available:
            return "bluetoothctl not available"
        mac = mac.upper()
        steps = [
            ["power", "on"],
            ["pairable", "on"],
            ["agent", "NoInputNoOutput"],
            ["default-agent"],
            ["pair", mac],
            ["trust", mac],
        ]
        log_all = []
        for s in steps:
            log_all.append(self._ctl(s, timeout=20))
        dbus = shutil.which("dbus-send")
        if dbus:
            path_mac = mac.replace(":", "_")
            adapter_id = adapter or "hci0"
            r = subprocess.run(
                [
                    dbus,
                    "--system",
                    "--print-reply",
                    "--dest=org.bluez",
                    f"/org/bluez/{adapter_id}/dev_{path_mac}",
                    "org.bluez.Device1.ConnectProfile",
                    f"string:{A2DP_SINK_UUID}",
                ],
                text=True,
                capture_output=True,
            )
            log_all.append((r.stdout or "") + (r.stderr or ""))
        else:
            log_all.append(self._ctl(["connect", mac], timeout=20))
        time.sleep(0.4)
        return "\n".join(log_all)[-2000:]

    def disconnect(self, mac: str) -> None:
        self._ctl(["disconnect", mac.upper()])
