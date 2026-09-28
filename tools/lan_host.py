#!/usr/bin/env python3
"""Host UDP btasio. Corre en Monterey con Python 3.10+ de Apple. Sin Flutter."""
from __future__ import annotations
import argparse, math, socket, struct, sys, time, wave
from pathlib import Path

MAGIC = 0x42544153
FLAG_PCM = 1 << 2
SR = 48000
FRAME_MS = 20
N = SR * FRAME_MS // 1000
HEADER = struct.Struct("<I B B H I q i I H H I")
CH = {"L": 0, "R": 1, "SUB": 2, "MID": 3, "SIDE": 4, "EXTRA": 5}

def mix(l, r, role):
    if role == "L": return l
    if role == "R": return r
    if role == "SIDE": return 0.5 * l - 0.5 * r
    return 0.5 * l + 0.5 * r

def s16(x):
    return max(-32768, min(32767, int(x * 32767)))

def pack(channel, seq, pts, pcm):
    return HEADER.pack(MAGIC, 0, channel, FLAG_PCM, seq, pts, 0, SR, 1, N, len(pcm)) + pcm

def tone_frame(cursor):
    out = []
    for i in range(N):
        t = (cursor + i) / SR
        out.append((0.25 * math.sin(2 * math.pi * 440 * t), 0.25 * math.sin(2 * math.pi * 660 * t)))
    return out

def wav_frames(path):
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            sys.exit("WAV PCM 16-bit")
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

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--to", action="append", default=[], help="ip:ROL")
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
        cache = {}
        for ip, role in targets:
            if role not in cache:
                cache[role] = b"".join(struct.pack("<h", s16(mix(l, r, role))) for l, r in stereo)
            sock.sendto(pack(CH[role], seq, pts, cache[role]), (ip, args.port))
        seq += 1
        delay = t0 + seq * FRAME_MS / 1000 - time.monotonic()
        if delay > 0:
            time.sleep(delay)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstop")
