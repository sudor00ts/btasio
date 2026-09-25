"""Channel matrix presets.

Master is always stereo FL/FR.
Each sink is a 2→1 mix plus optional polarity invert.

    out = gL * L + gR * R
    if invert: out = -out

Mid/Side:
    M = 0.5 * L + 0.5 * R
    S = 0.5 * L - 0.5 * R
"""

from __future__ import annotations

from .models import Preset, Role, Sink

PRESET_GAINS: dict[Preset, dict[Role, tuple[float, float, bool]]] = {
    Preset.STEREO_SUB: {
        Role.L: (1.0, 0.0, False),
        Role.R: (0.0, 1.0, False),
        Role.SUB: (0.5, 0.5, False),
        Role.EXTRA: (0.5, 0.5, False),
        Role.MID: (0.5, 0.5, False),
        Role.SIDE: (0.5, -0.5, False),
    },
    Preset.MID_SIDE: {
        Role.MID: (0.5, 0.5, False),
        Role.SIDE: (0.5, -0.5, False),
        Role.L: (0.5, 0.5, False),
        Role.R: (0.5, -0.5, False),
        Role.SUB: (0.5, 0.5, False),
        Role.EXTRA: (0.5, 0.5, False),
    },
    Preset.ALL: {
        Role.L: (0.5, 0.5, False),
        Role.R: (0.5, 0.5, False),
        Role.SUB: (0.5, 0.5, False),
        Role.MID: (0.5, 0.5, False),
        Role.SIDE: (0.5, 0.5, False),
        Role.EXTRA: (0.5, 0.5, False),
    },
}

DEFAULT_ROLES = {
    Preset.STEREO_SUB: [Role.L, Role.R, Role.SUB],
    Preset.MID_SIDE: [Role.MID, Role.SIDE, Role.EXTRA],
    Preset.ALL: [Role.EXTRA, Role.EXTRA, Role.EXTRA],
}


def apply_preset(sinks: list[Sink], preset: Preset) -> list[Sink]:
    if preset == Preset.CUSTOM:
        return sinks
    table = PRESET_GAINS[preset]
    for sink in sinks:
        if sink.role == Role.UNASSIGNED:
            sink.gain_l, sink.gain_r, sink.invert = 0.0, 0.0, False
            continue
        g = table.get(sink.role, (0.5, 0.5, False))
        sink.gain_l, sink.gain_r, sink.invert = g
    return sinks


def suggested_roles(preset: Preset, count: int) -> list[Role]:
    base = DEFAULT_ROLES.get(preset, [Role.EXTRA] * count)
    if len(base) >= count:
        return base[:count]
    return base + [Role.EXTRA] * (count - len(base))
