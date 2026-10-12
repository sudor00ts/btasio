#!/usr/bin/env python3
"""Receiver web para iPhone/Safari.

La Mac escucha el mismo UDP :8746 que usa lan_host.py y lo reenvía
por Server-Sent Events a cualquier navegador. Safari en el iPhone
reproduce el PCM y el sistema lo manda al parlante Bluetooth emparejado.

Uso:
  python3 tools/web_rx_server.py
  # en el iPhone: http://IP_DE_LA_MAC:8080
  # en otra terminal:
  python3 tools/lan_host.py --to IP_SAMSUNG:L --to 127.0.0.1:R
"""

from __future__ import annotations

import json
import queue
import socket
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAGIC = 0x42544153
HEADER = struct.Struct("<I B B H I q i I H H I")  # 36 bytes
UDP_PORT = 8746
HTTP_PORT = 8080

# clients: list of queues
clients: list[queue.Queue] = []
clients_lock = threading.Lock()


def udp_loop() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", UDP_PORT))
    print(f"UDP escuchando en :{UDP_PORT}", flush=True)
    while True:
        data, _ = sock.recvfrom(65535)
        if len(data) < 36:
            continue
        try:
            magic, _, ch, flags, seq, pts, ndelay, sr, nch, n, nbytes = HEADER.unpack(data[:36])
        except struct.error:
            continue
        if magic != MAGIC or nbytes != len(data) - 36:
            continue
        pcm = data[36:]
        msg = json.dumps({
            "ch": ch,
            "seq": seq,
            "sr": sr,
            "pcm": pcm.hex(),
        })
        with clients_lock:
            dead = []
            for q in clients:
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                clients.remove(q)


HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>btasio web rx</title>
<style>
  body { font-family: system-ui, sans-serif; background:#0b0f14; color:#e8eef6; margin:0; padding:16px; }
  h1 { font-size:22px; margin:0 0 4px; }
  .sub { color:#8aa0b8; font-size:13px; margin-bottom:16px; }
  button, select { font-size:16px; padding:10px 14px; border-radius:10px; border:0; }
  button { background:#3dffb0; color:#042014; font-weight:700; }
  .row { display:flex; gap:8px; align-items:center; margin:12px 0; flex-wrap:wrap; }
  #status { color:#8aa0b8; font-size:13px; }
</style>
</head>
<body>
  <h1>btasio · web rx</h1>
  <div class="sub">Emparejá el parlante en Ajustes del iPhone antes. Safari manda el audio ahí.</div>
  <div class="row">
    <label>Rol
      <select id="role">
        <option value="0">L</option>
        <option value="1">R</option>
        <option value="2">SUB</option>
        <option value="3">MID</option>
        <option value="4">SIDE</option>
        <option value="5">EXTRA</option>
      </select>
    </label>
    <button id="btn">Escuchar</button>
  </div>
  <div id="status">idle</div>
<script>
const roleSel = document.getElementById('role');
const btn = document.getElementById('btn');
const statusEl = document.getElementById('status');
let es = null;
let ctx = null;
let nextTime = 0;
let running = false;
let packets = 0;

function setStatus(s) { statusEl.textContent = s; }

function playPcm(hex, sr) {
  if (!ctx) return;
  const bytes = new Uint8Array(hex.match(/.{1,2}/g).map(b => parseInt(b, 16)));
  const view = new DataView(bytes.buffer);
  const n = bytes.length / 2;
  const buf = ctx.createBuffer(1, n, sr || 48000);
  const ch = buf.getChannelData(0);
  for (let i = 0; i < n; i++) {
    const s = view.getInt16(i * 2, true);
    ch[i] = s / 32768;
  }
  const src = ctx.createBufferSource();
  src.buffer = buf;
  src.connect(ctx.destination);
  const now = ctx.currentTime;
  if (nextTime < now) nextTime = now + 0.05;
  src.start(nextTime);
  nextTime += buf.duration;
}

btn.onclick = async () => {
  if (running) {
    running = false;
    if (es) es.close();
    es = null;
    if (ctx) ctx.close();
    ctx = null;
    btn.textContent = 'Escuchar';
    setStatus('detenido');
    return;
  }
  ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 48000 });
  await ctx.resume();
  nextTime = 0;
  packets = 0;
  running = true;
  btn.textContent = 'Dejar de escuchar';
  setStatus('conectando…');
  es = new EventSource('/stream');
  es.onmessage = (ev) => {
    if (!running) return;
    const msg = JSON.parse(ev.data);
    if (msg.ch !== parseInt(roleSel.value, 10)) return;
    packets++;
    if (packets % 25 === 0) setStatus(`rx seq=${msg.seq} ch=${msg.ch} pkts=${packets}`);
    playPcm(msg.pcm, msg.sr);
  };
  es.onerror = () => setStatus('error de conexión');
};
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            q: queue.Queue = queue.Queue(maxsize=64)
            with clients_lock:
                clients.append(q)
            try:
                while True:
                    try:
                        msg = q.get(timeout=15)
                        self.wfile.write(f"data: {msg}\n\n".encode())
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b":: ping\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with clients_lock:
                    if q in clients:
                        clients.remove(q)
            return
        self.send_response(404)
        self.end_headers()


def main() -> None:
    t = threading.Thread(target=udp_loop, daemon=True)
    t.start()
    httpd = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    print(f"web rx en http://0.0.0.0:{HTTP_PORT}", flush=True)
    print("En el iPhone abrí http://IP_DE_ESTA_MAC:8080", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
