# Probar btasio en una Mac Monterey

Monterey (12.x): Xcode máximo 14.2. Flutter actual y App Store piden Xcode 16.
La Mac igual sirve como host UDP con el Python de fábrica.

```bash
python3 tools/lan_host.py --to 192.168.0.12:R --to 192.168.0.13:L
python3 tools/lan_rx.py --role R
```

Loopback: host a 127.0.0.1 y rx en otra terminal. L=440 Hz, R=660 Hz.
