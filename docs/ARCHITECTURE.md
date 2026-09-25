# btasio architecture

btasio is the ASIO4ALL idea applied to Bluetooth sinks: one virtual input,
a routing matrix, and N independent A2DP (or LE Audio) outputs. No JBL
Connect, no Sony Party Connect, no vendor UUID.

## Why a hub

Classic A2DP is a unicast point-to-point profile. One radio can usually
keep **one** high-quality SRC→SNK stream stable. Some controllers do two;
three concurrent streams of different content from a phone radio is not a
portable API.

Auracast / LE Audio BIS solves "same audio to many devices", not
"different channels to different devices". Stereo L/R and Mid/Side need
**separate unicast streams**.

So the source of truth is a Linux box in the studio:

```
DAW / browser / phone-over-WiFi
        |
        v
 +--------------+
 |  btasio_in   |  PipeWire null sink (stereo master)
 +------+-------+
        |
        v
 +--------------+
 |    matrix    |  stereo | mid-side | all | custom
 +------+-------+
        |
   +----+----+
   v    v    v
  A2DP A2DP A2DP     one HCI adapter per sink when possible
  L    R    Sub
```

The phone is a controller on the LAN. It does **not** carry the music
over a second Bluetooth hop. Phone → hub A2DP → speakers A2DP adds
~250–400 ms and jitter. Don't do that.

## Protocols in play

| Layer | Role |
| --- | --- |
| GAP / BR-EDR | discovery, pairing, ACL |
| SDP | find A2DP Sink UUID `0000110b-0000-1000-8000-00805f9b34fb` |
| AVDTP | stream endpoint negotiation |
| A2DP SRC | hub is the source; speaker is SNK |
| SBC (mandatory) | fallback codec, ~100–200 ms typical |
| AAC / aptX / LDAC | used if **both** ends advertise them; never required |
| AVRCP | optional transport controls |
| LE Audio BAP / CIS | future path for lower latency when the speaker supports it |
| BlueZ D-Bus | `org.bluez.Adapter1`, `Device1`, `Media1`, `ConnectProfile` |
| PipeWire | graph, channel remix, per-sink delay |

Vendor "party" modes stay unused on purpose. They are closed meshes.

## Three-device roles

Presets map a stereo master to three sinks.

### `stereo_sub`

- Device A ← FL
- Device B ← FR
- Device C ← (FL+FR)/2  (sub / mono fill; LPF comes later)

### `mid_side`

```
M = (L + R) / 2
S = (L − R) / 2
```

- Device A ← M
- Device B ← S
- Device C ← M   (or unused; useful as a centre / extra mid)

Playing raw S alone sounds thin. That is correct Mid/Side, not a bug.
Use `mid_side` when you want MS processing or an MS pair plus a centre.

### `all`

Every assigned sink gets a mono downmix `(L+R)/2`. Party / fill mode.

### `custom`

Each sink has an independent 2×1 gain vector `[gL, gR]` plus invert
flag. Stereo, MS and all are presets of this matrix.

## Sync

Each A2DP encoder + speaker DAC has its own latency. btasio does not
guess a magic number. It:

1. Assumes the slowest sink is the time reference.
2. Inserts `target_delay_ms − measured_ms` on the faster sinks
   (`pw-loopback` / `target.delay`).
3. Ships a test-tone button so you align by ear (click + 1 kHz).

Typical starting offsets: wired 0 ms, SBC 140–180 ms, AAC 120–200 ms.
Measure, don't copy.

## Radios

Reliable rule for v0: **one A2DP sink per HCI adapter**.

For three speakers use onboard Bluetooth plus two USB 5.0+ dongles
(CSR8510-class or better; avoid the cheapest dual-mode sticks that drop
the second SCO/A2DP). Bind each MAC to an adapter with BlueZ
`Address` + `Adapter1.SetDiscoveryFilter` / connect on that adapter.

## Control plane

- HTTP + WebSocket on `0.0.0.0:8745`
- mDNS `_btasio._tcp`
- PWA in `hub/static` (phone UI, no store)
- Native Flutter wrapper is a later skin over the same API

Audio never leaves the hub over that HTTP port.
