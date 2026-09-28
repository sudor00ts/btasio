#!/usr/bin/env python3
from __future__ import annotations
import argparse, socket, struct, wave
from pathlib import Path

MAGIC = 0x42544153
HEADER = struct.Struct("<I B B H I q i I H H I")
CH = {0: "L", 1: "R", 2: "SUB", 3: "MID", 4: "SIDE", 5: "EXTRA", 6: "MIX"}

def try_player(sr):
    try:
        import sounddevice as sd
    except ImportError:
        return None
    class Dev:
        def __init__(self):
            self.stream = sd.RawOutputStream(samplerate=sr, channels=1, dtype="int16", blocksize=960)
            self.stream.start()
        def write(self, pcm):
            self.stream.write(pcm)
    return Dev()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--role", default="L")
    p.add_argument("--port", type=int, default=8746)
    p.add_argument("--wav-out", type=Path)
    args = p.parse_args()
    want = args.role.upper()
    want_id = {v: k for k, v in CH.items()}[want]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", args.port))
    print(f"rx rol={want} udp/{args.port}", flush=True)
    player = try_player(48000)
    if player is None:
        print("sin sounddevice: pip3 install sounddevice  (o --wav-out)", flush=True)
    wav = None
    n = 0
    while True:
        data, addr = sock.recvfrom(4096)
        if len(data) < HEADER.size:
            continue
        magic, ver, ch, flags, seq, pts, *_ = HEADER.unpack(data[: HEADER.size])
        if magic != MAGIC or ch != want_id:
            continue
        pcm = data[HEADER.size :]
        n += 1
        if player:
            player.write(pcm)
        if args.wav_out:
            if wav is None:
                wav = wave.open(str(args.wav_out), "wb")
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(48000)
            wav.writeframes(pcm)
        if n % 50 == 0:
            print(f"rx {n} seq={seq} from={addr[0]} bytes={len(pcm)}", flush=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstop")
