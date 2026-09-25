# btasio

Agregador open source de parlantes Bluetooth. Sin lock-in de marca ni
Party Connect / Connect+ / SimpleSync.

Hay dos skins, **el mismo matrix**:

1. **App Flutter (Android + iOS)** — el teléfono es el reproductor. No abre 3 A2DP. Parte L/R/M/S por Wi‑Fi a *nodos* (otro celu, Pi, o ESP32→AUX). Cada nodo hace **un** A2DP a **un** parlante. Ver `docs/MOBILE.md`.
2. **Hub Linux** — DAW / PipeWire / 3 dongles en el estudio. La PWA o la app solo controlan.

Licencia: GPL-3.0-or-later.

## Lo que esto no es

No es una app de teléfono que “abre 3 A2DP a la vez” contra el radio
del celular. A2DP clásico es unicast. Auracast manda **el mismo**
audio a muchos LE Audio sinks, no un L distinto de un R.

## App móvil (workaround)

No se puede publicar “3 A2DP clásicos con contenido distinto desde un iPhone”.
iOS no da A2DP SRC a terceros. Android reserva el multi-sink a system APIs / Auracast.

Workaround publicable: `docs/MOBILE.md` + `docs/protocol.md`.

```
app host  --Wi-Fi, 3 flujos timestamped-->  nodo L / nodo R / nodo Sub
                                            cada nodo = 1 radio = 1 parlante
```

Nodo barato: un teléfono viejo en modo receiver, o Pi Zero 2 W.
Nodo más limpio: ESP32-S3 + DAC al AUX del parlante.
ESP32 clásico no hace Wi‑Fi y A2DP Classic a la vez.

## Hub Linux

```bash
cd hub
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
btasio-hub
```

PWA: `http://0.0.0.0:8745`

## Roadmap

- [x] arquitectura híbrida + PWA
- [x] diseño app Android/iOS + protocolo UDP
- [ ] Flutter host + receiver (WAV stereo L/R)
- [ ] Android MediaProjection capture
- [ ] filter-chain MS
- [ ] firmware nodo AUX
