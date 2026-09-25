# btasio

Agregador open source de parlantes Bluetooth. Sin lock-in de marca ni
Party Connect / Connect+ / SimpleSync.

Un **hub Linux** (PC o Raspberry Pi en el estudio) es la fuente A2DP.
El **teléfono** solo controla el matrix por Wi‑Fi.

```
DAW / reproductor  →  btasio_in  →  matrix (L/R/Sub o M/S/extra)  →  3 sinks A2DP
                                           ↑
                                    PWA en el teléfono
```

Licencia: GPL-3.0-or-later.

## Lo que esto no es

No es una app de teléfono que “abre 3 A2DP a la vez” contra el radio
del celular. A2DP clásico es unicast. Auracast manda **el mismo**
audio a muchos LE Audio sinks, no un L distinto de un R.

Si tu requisito es JBL + Edifier + un sub genérico en Mid/Side, el
radio tiene que estar en el hub, un HCI por sink.

## Hardware (3 parlantes)

- Linux con PipeWire + BlueZ 5.66+
- Bluetooth onboard + **2 dongles USB 5.0+** (regla v0: 1 A2DP por radio)
- Los parlantes solo necesitan A2DP Sink. SBC alcanza. AAC/aptX si ambos lados lo tienen.

## Audio — no hagas el doble hop

Mal: teléfono —BT→ hub —BT→ parlantes (~300 ms y drift).

Bien:

1. El PC/Pi reproduce (DAW, browser, `pw-play`).
2. Salida por defecto = `btasio Master`.
3. El teléfono abre `http://<ip-del-hub>:8745`.

## Presets

| Preset | A | B | C |
| --- | --- | --- | --- |
| `stereo_sub` | L | R | (L+R)/2 |
| `mid_side` | M = (L+R)/2 | S = (L−R)/2 | M extra |
| `all` | mono mix | mono mix | mono mix |

Delay por sink para alinear SBC vs SBC. Calibrá con oído: tono de prueba
en v0.2.

## Hub

```bash
cd hub
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
btasio-hub
```

PWA: `http://0.0.0.0:8745`

En otra máquina Linux del estudio:

```bash
pactl list short sinks          # tiene que aparecer btasio_in al aplicar graph
bluetoothctl list               # 3 adapters
```

Servicio de usuario: `systemd/btasio.service`.

## API

- `GET  /api/state`
- `POST /api/preset`     `{ "preset": "stereo_sub"|"mid_side"|"all"|"custom" }`
- `POST /api/assign`     `{ "mac": "AA:BB:…", "role": "L"|"R"|"SUB"|"MID"|"SIDE"|"EXTRA" }`
- `POST /api/delay`      `{ "mac": "…", "delay_ms": 160 }`
- `POST /api/volume`
- `POST /api/scan`
- `POST /api/connect`    `{ "mac": "…" }`
- `POST /api/apply`

## Estado del código

v0.1: control plane + PWA + BlueZ pair/connect A2DP + skeleton PipeWire.

El matrix Mid/Side exacto (coeficientes con inversión de fase) queda
cerrado en v0.2 con `filter-chain` de PipeWire. v0.1 ya rutea L / R /
mono-sum, que es el 90 % del caso stereo+sub.

## Roadmap

- [x] arquitectura híbrida
- [x] API + PWA
- [x] pair/connect perfil A2DP estándar
- [ ] filter-chain MS con inversión real
- [ ] LPF en el rol SUB
- [ ] mDNS `_btasio._tcp`
- [ ] tono de calibración de delay
- [ ] wrapper Flutter (misma API)
- [ ] LE Audio CIS cuando el parlante lo anuncie
