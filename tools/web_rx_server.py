#!/usr/bin/env python3
"""Receiver web. HTTP por defecto. Buffer ~300 ms."""
from __future__ import annotations
import json, socket, ssl, struct, subprocess, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAGIC = 0x42544153
HEADER = struct.Struct("<I B B H I q i I H H I")
UDP_PORT = 8746
HTTP_PORT = 8080
frames: dict[int, list[dict]] = {}
frames_lock = threading.Lock()
MAX_KEEP = 200

def udp_loop() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", UDP_PORT))
    print(f"UDP escuchando en :{UDP_PORT}", flush=True)
    while True:
        data, _ = sock.recvfrom(65535)
        if len(data) < 36: continue
        try:
            magic, _, ch, flags, seq, pts, ndelay, sr, nch, n, nbytes = HEADER.unpack(data[:36])
        except struct.error:
            continue
        if magic != MAGIC or nbytes != len(data) - 36: continue
        pcm = data[36:]
        item = {"ch": ch, "seq": seq, "sr": sr, "pcm": pcm.hex()}
        with frames_lock:
            lst = frames.setdefault(ch, [])
            lst.append(item)
            if len(lst) > MAX_KEEP:
                del lst[: len(lst) - MAX_KEEP]

HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>btasio web rx</title>
<style>body{font-family:system-ui,sans-serif;background:#0b0f14;color:#e8eef6;margin:0;padding:16px}h1{font-size:22px;margin:0 0 4px}.sub{color:#8aa0b8;font-size:13px;margin-bottom:16px}button,select{font-size:16px;padding:10px 14px;border-radius:10px;border:0}button{background:#3dffb0;color:#042014;font-weight:700}.row{display:flex;gap:8px;align-items:center;margin:12px 0;flex-wrap:wrap}#status{color:#8aa0b8;font-size:13px}</style></head>
<body><h1>btasio · web rx</h1><div class="sub">Emparejá el parlante en Ajustes del iPhone antes.</div>
<div class="row"><label>Rol <select id="role"><option value="0">L</option><option value="1">R</option><option value="2">SUB</option><option value="3">MID</option><option value="4">SIDE</option><option value="5">EXTRA</option></select></label>
<button id="btn">Escuchar</button><button id="test" style="background:#8aa0b8;color:#0b0f14">Test tono</button></div>
<div id="status">idle</div>
<script>
const roleSel=document.getElementById('role'),btn=document.getElementById('btn'),statusEl=document.getElementById('status');
let ctx=null,nextTime=0,running=false,packets=0,lastSeq=-1;
function setStatus(s){statusEl.textContent=s}
function playPcm(hex,sr){
  if(!ctx)return;
  const bytes=new Uint8Array(hex.match(/.{1,2}/g).map(b=>parseInt(b,16)));
  const view=new DataView(bytes.buffer),n=bytes.length/2;
  const buf=ctx.createBuffer(1,n,sr||48000),ch=buf.getChannelData(0);
  for(let i=0;i<n;i++)ch[i]=view.getInt16(i*2,true)/32768;
  const src=ctx.createBufferSource();src.buffer=buf;src.connect(ctx.destination);
  const now=ctx.currentTime;
  if(nextTime<now+0.15)nextTime=now+0.30;
  src.start(nextTime);nextTime+=buf.duration;
}
async function poll(){
  if(!running)return;
  const ch=roleSel.value;
  try{
    const r=await fetch('/poll?ch='+ch+'&after='+lastSeq);
    if(!r.ok)throw new Error('http '+r.status);
    const arr=await r.json();
    for(const msg of arr){if(msg.seq<=lastSeq)continue;lastSeq=msg.seq;packets++;playPcm(msg.pcm,msg.sr)}
    if(packets>0&&packets%10===0)setStatus('rx seq='+lastSeq+' pkts='+packets);
    else if(packets===0)setStatus('conectado, esperando paquetes…');
  }catch(e){setStatus('error: '+e)}
  if(running)setTimeout(poll,40);
}
btn.onclick=async()=>{
  if(running){running=false;if(ctx)ctx.close();ctx=null;btn.textContent='Escuchar';setStatus('detenido');return}
  ctx=new (window.AudioContext||window.webkitAudioContext)({sampleRate:48000});
  await ctx.resume();
  const u=ctx.createBufferSource();u.buffer=ctx.createBuffer(1,1,48000);u.connect(ctx.destination);u.start(0);
  nextTime=0;packets=0;lastSeq=-1;running=true;btn.textContent='Dejar de escuchar';setStatus('conectando…');poll();
};
document.getElementById('test').onclick=async()=>{
  const c=new (window.AudioContext||window.webkitAudioContext)();await c.resume();
  const o=c.createOscillator(),g=c.createGain();o.frequency.value=440;g.gain.value=0.3;o.connect(g);g.connect(c.destination);o.start();
  setTimeout(()=>{o.stop();c.close()},800);setStatus('test tono local');
};
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[http] {self.address_string()} {fmt % args}", flush=True)
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
                if ch < 0:
                    out = []
                    for lst in frames.values():
                        out.extend(x for x in lst if x["seq"] > after)
                    out.sort(key=lambda x: x["seq"])
                    out = out[-20:]
                else:
                    out = [x for x in frames.get(ch, []) if x["seq"] > after]
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

def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--https", action="store_true")
    p.add_argument("--ip", default="")
    args = p.parse_args()
    t = threading.Thread(target=udp_loop, daemon=True)
    t.start()
    httpd = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    if args.https:
        cert_dir = Path(tempfile.gettempdir()) / "btasio"
        cert_dir.mkdir(exist_ok=True)
        cert_path = cert_dir / "cert.pem"
        key_path = cert_dir / "key.pem"
        ip = args.ip or "127.0.0.1"
        cnf = cert_dir / "openssl.cnf"
        cnf.write_text(f"[req]\ndistinguished_name=dn\nx509_extensions=v3\nprompt=no\n[dn]\nCN=btasio\n[v3]\nsubjectAltName=IP:{ip}\n")
        subprocess.check_call(["openssl","req","-x509","-newkey","rsa:2048","-keyout",str(key_path),"-out",str(cert_path),"-days","365","-nodes","-config",str(cnf),"-extensions","v3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert_path, key_path)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        print(f"web rx en https://{ip}:{HTTP_PORT}", flush=True)
    else:
        print(f"web rx en http://0.0.0.0:{HTTP_PORT}", flush=True)
        print("En el iPhone: http://IP_DE_ESTA_MAC:8080", flush=True)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
