#!/usr/bin/env python3
"""btasio beta hub.

Un solo proceso:
- Genera el audio (tono o WAV)
- Empuja UDP a los receivers Android
- Sirve la página web para el iPhone (http://IP_DEL_PC:8080)

Uso en Windows:
  python beta_hub.py
  o doble clic en start_beta.bat

Config: editá config.json (IP del Samsung y roles).
"""

from __future__ import annotations

import json
import math
import socket
import struct
import sys
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAGIC = 0x42544153
FLAG_PCM = 1 << 2
SR = 48000
FRAME_MS = 20
N = SR * FRAME_MS // 1000
HEADER = struct.Struct("<I B B H I q i I H H I")
CH = {"L": 0, "R": 1, "SUB": 2, "MID": 3, "SIDE": 4, "EXTRA": 5}

UDP_PORT = 8746
HTTP_PORT = 8080
MAX_KEEP = 80

frames: dict[int, list[dict]] = {}
frames_lock = threading.Lock()
running = True


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
    return HEADER.pack(MAGIC, 0, channel, FLAG_PCM, seq, pts, 0, SR, 1, N, len(pcm)) + pcm


def tone_frame(cursor: int):
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
    frames_n = len(samples) // ch
    i = 0
    while True:
        stereo = []
        for _ in range(N):
            if ch == 1:
                v = samples[i % frames_n] / 32768.0
                stereo.append((v, v))
            else:
                base = (i % frames_n) * ch
                stereo.append((samples[base] / 32768.0, samples[base + 1] / 32768.0))
            i += 1
        yield stereo


def load_config(path: Path) -> dict:
    if not path.exists():
        default = {
            "targets": [
                {"ip": "192.168.1.50", "role": "L", "name": "Samsung Flip 6"},
                {"ip": "127.0.0.1", "role": "R", "name": "iPhone web (local)"},
            ],
            "wav": None,
        }
        path.write_text(json.dumps(default, indent=2))
        print(f"Creado {path}. Editá la IP del Samsung y volvé a correr.", flush=True)
        return default
    return json.loads(path.read_text())


def host_loop(targets: list[tuple[str, str]], wav_path: Path | None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    src = wav_frames(wav_path) if wav_path and wav_path.exists() else None
    print("host →", ", ".join(f"{ip}:{role}" for ip, role in targets), flush=True)
    seq = 0
    t0 = time.monotonic()
    cursor = 0
    while running:
        stereo = next(src) if src else tone_frame(cursor)
        cursor += N
        pts = int((time.monotonic() - t0) * 1_000_000)
        cache: dict[str, bytes] = {}
        for ip, role in targets:
            if role not in cache:
                pcm = b"".join(struct.pack("<h", s16(mix(l, r, role))) for l, r in stereo)
                cache[role] = pcm
            pkt = pack(CH[role], seq, pts, cache[role])
            try:
                sock.sendto(pkt, (ip, UDP_PORT))
            except OSError:
                pass
            if ip in ("127.0.0.1", "localhost"):
                item = {"ch": CH[role], "seq": seq, "sr": SR, "pcm": cache[role].hex()}
                with frames_lock:
                    lst = frames.setdefault(CH[role], [])
                    lst.append(item)
                    if len(lst) > MAX_KEEP:
                        del lst[: len(lst) - MAX_KEEP]
        seq += 1
        target = t0 + seq * FRAME_MS / 1000
        delay = target - time.monotonic()
        if delay > 0:
            time.sleep(delay)


HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>btasio</title>
<style>body{font-family:system-ui;background:#0b0f14;color:#e8eef6;margin:0;padding:16px}button,select{font-size:16px;padding:10px 14px;border-radius:10px;border:0}button{background:#3dffb0;color:#042014;font-weight:700}.row{display:flex;gap:8px;margin:12px 0;flex-wrap:wrap}#status{color:#8aa0b8;font-size:13px}</style></head>
<body><h1>btasio · web rx</h1>
<div class="sub">Emparejá el parlante en Ajustes del iPhone. Esta página reproduce el canal que elijas.</div>
<div class="row"><select id="role"><option value="0">L</option><option value="1">R</option><option value="2">SUB</option><option value="3">MID</option><option value="4">SIDE</option><option value="5">EXTRA</option></select>
<button id="btn">Escuchar</button><button id="test" style="background:#8aa0b8">Test tono</button></div>
<div id="status">idle</div>
<script>
const roleSel=document.getElementById("role"),btn=document.getElementById("btn"),st=document.getElementById("status");
let ctx=null,nextTime=0,running=false,packets=0,lastSeq=-1;
function play(hex,sr){
  if(!ctx)return;
  const b=new Uint8Array(hex.match(/.{1,2}/g).map(x=>parseInt(x,16)));
  const v=new DataView(b.buffer),n=b.length/2;
  const buf=ctx.createBuffer(1,n,sr||48000),ch=buf.getChannelData(0);
  for(let i=0;i<n;i++)ch[i]=v.getInt16(i*2,true)/32768;
  const s=ctx.createBufferSource();s.buffer=buf;s.connect(ctx.destination);
  const now=ctx.currentTime;
  if(nextTime<now+0.15)nextTime=now+0.30;
  s.start(nextTime);nextTime+=buf.duration;
}
async function poll(){
  if(!running)return;
  try{
    const r=await fetch("/poll?ch="+roleSel.value+"&after="+lastSeq);
    const arr=await r.json();
    for(const m of arr){if(m.seq<=lastSeq)continue;lastSeq=m.seq;packets++;play(m.pcm,m.sr)}
    if(packets&&packets%10===0)st.textContent="rx seq="+lastSeq+" pkts="+packets;
    else if(!packets)st.textContent="conectado, esperando…";
  }catch(e){st.textContent="error: "+e}
  if(running)setTimeout(poll,50);
}
btn.onclick=async()=>{
  if(running){running=false;if(ctx)ctx.close();ctx=null;btn.textContent="Escuchar";st.textContent="detenido";return}
  ctx=new (window.AudioContext||window.webkitAudioContext)({sampleRate:48000});
  await ctx.resume();
  const u=ctx.createBufferSource();u.buffer=ctx.createBuffer(1,1,48000);u.connect(ctx.destination);u.start(0);
  nextTime=0;packets=0;lastSeq=-1;running=true;btn.textContent="Dejar de escuchar";st.textContent="conectando…";poll();
};
document.getElementById("test").onclick=async()=>{
  const c=new (window.AudioContext||window.webkitAudioContext)();await c.resume();
  const o=c.createOscillator(),g=c.createGain();o.frequency.value=440;g.gain.value=0.3;o.connect(g);g.connect(c.destination);o.start();
  setTimeout(()=>{o.stop();c.close()},800);st.textContent="test tono";
};
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        return

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/poll":
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            try:
                ch = int(qs.get("ch", ["0"])[0])
                after = int(qs.get("after", ["-1"])[0])
            except ValueError:
                ch, after = 0, -1
            with frames_lock:
                out = [x for x in frames.get(ch, []) if x["seq"] > after]
                if len(out) > 8:
                    out = out[-8:]
            body = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


def main():
    cfg_path = Path("config.json")
    cfg = load_config(cfg_path)
    targets = []
    for t in cfg.get("targets", []):
        ip = t.get("ip", "").strip()
        role = t.get("role", "L").upper()
        if ip and role in CH:
            targets.append((ip, role))
    if not targets:
        print("No hay targets válidos en config.json", flush=True)
        return
    wav = Path(cfg["wav"]) if cfg.get("wav") else None

    threading.Thread(target=host_loop, args=(targets, wav), daemon=True).start()

    httpd = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    print(f"web rx en http://0.0.0.0:{HTTP_PORT}", flush=True)
    print("En el iPhone abrí http://IP_DE_ESTE_PC:8080", flush=True)
    print("En el Samsung: app btasio → Receiver → rol L → Escuchar :8746", flush=True)
    print("Ctrl+C para parar", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        global running
        running = False
        print("\nstop")


if __name__ == "__main__":
    main()
