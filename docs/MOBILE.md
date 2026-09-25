# App Android + iOS: el workaround real

La UI puede ser Flutter y vivir en Play Store / App Store.
El radio Bluetooth del teléfono **no** puede ser ASIO4ALL.

## Lo que el SO deja hacer

### Android

- `AudioTrack.setPreferredDevice` rutea un track a un sink.
- Tres AudioTrack hacia tres A2DP clásicos no es portable.
- `setPreferredDevicesForStrategy` es system API, no Play Store.
- Dual Audio / Auracast: 2 sinks o el mismo stream a muchos LE Audio.
- Útil: MediaProjection para capturar Spotify/YouTube y mandarlo por Wi-Fi.

### iOS

- Core Bluetooth no abre A2DP SRC.
- AirPlay 2 = speakers AirPlay, no BT baratos.
- Audio Sharing = 2x AirPods, mismo contenido.
- Capturar Spotify desde otra app = rechazo en review.
- La app iOS tiene que ser el reproductor.

## Workaround publicable

```
app Flutter (host) --Wi-Fi--> nodo L / nodo R / nodo Sub
                              cada nodo = 1 A2DP = 1 parlante
```

Nodos: teléfono viejo en modo receiver, Pi Zero 2 W, o ESP32-S3+DAC al AUX.
ESP32 clásico no coexiste Wi-Fi + A2DP Classic.

Ver protocol.md para el datagrama UDP y el reloj.
