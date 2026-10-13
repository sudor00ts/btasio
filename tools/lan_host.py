#!/usr/bin/env python3
"""Host UDP btasio. Corre en Monterey con Python 3.10+ de Apple. Sin Flutter."""

from __future__ import annotations

import argparse
import math
import socket
import struct
import sys
import time
import wave
from pathlib import Path

MAGIC = 0x42544153
FLAG_PCM = 1 << 2
SR = 48000
FRAME_MS = 20
N = SR * FRAME_MS // 1000
HEADER = struct.Struct("<I B B H I q i I H H I")  # 36 bytes

CH = {"L": 0, "R": 1, "SUB": 2, "MID": 3, "SIDE": 4, "EXTRA": 5}


def mix(l: float, r: float, role: str) -> float:
    if role == "L":
        return l
    if role == "R":
        return r
    if role == "SIDE":
        return 0.5 * l - 0.5 * r
    return 0.5 * l + 0.5 * r


def s16(x: float) -> int:
    v = int(x * 32767)
    return max(-32768, min(32767, v))


def pack(channel: int, seq: int, pts: int, pcm: bytes) -> bytes:
    hdr = HEADER.pack(MAGIC, 0, channel, FLAG_PCM, seq, pts, 0, SR, 1, N, len(pcm))
    return hdr + pcm


def tone_frame(cursor: int) -> list[tuple[float, float]]:
    out = []
    for i in range(N):
        t = (cursor + i) / SR
        out.append((0.5 * math.sin(2 * math.pi * 440 * t), 0.5 * math.sin(2 * math.pi * 660 * t)))
    return out


def wav_frames(path: Path):
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            sys.exit("WAV tiene que ser PCM 16-bit")
        ch = w.getnchannels()
        raw = w.readframes(w.getnframes())
    samples = memoryview(raw).cast("h")
    frames = len(samples) // ch
    i = 0
    while True:
        stereo = []
        for _ in range(N):
            if ch == 1:
                v = samples[i % frames] / 32768.0
                stereo.append((v, v))
            else:
                base = (i % frames) * ch
                stereo.append((samples[base] / 32768.0, samples[base + 1] / 32768.0))
            i += 1
        yield stereo


def main() -> None:
    p = argparse.ArgumentParser(description="btasio host UDP para Mac vieja")
    p.add_argument("--to", action="append", default=[], help="ip:ROL  ej. 192.168.0.12:R")
    p.add_argument("--wav", type=Path)
    p.add_argument("--port", type=int, default=8746)
    args = p.parse_args()
    if not args.to:
        sys.exit("pasá al menos un --to IP:ROL  (L R SUB MID SIDE EXTRA)")

    targets = []
    for spec in args.to:
        ip, _, role = spec.partition(":")
        role = role.upper() or "L"
        if role not in CH:
            sys.exit(f"rol desconocido: {role}")
        targets.append((ip, role))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    src = wav_frames(args.wav) if args.wav else None
    print("host →", ", ".join(f"{ip}:{role}" for ip, role in targets), flush=True)
    seq = 0
    t0 = time.monotonic()
    cursor = 0
    while True:
        stereo = next(src) if src else tone_frame(cursor)
        cursor += N
        pts = int((time.monotonic() - t0) * 1_000_000)
        cache: dict[str, bytes] = {}
        for ip, role in targets:
            if role not in cache:
                pcm = b"".join(
                    struct.pack("<h", s16(mix(l, r, role))) for l, r in stereo
                )
                cache[role] = pcm
            sock.sendto(pack(CH[role], seq, pts, cache[role]), (ip, args.port))
        seq += 1
        # pace 20 ms
        target = t0 + seq * FRAME_MS / 1000
        delay = target - time.monotonic()
        if delay > 0:
            time.sleep(delay)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstop")
