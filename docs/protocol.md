# btasio wire protocol v0

LAN only. No cloud. UDP + mDNS.

## Discovery

mDNS `_btasio._udp.local` port 8746 (media) + 8745 (HTTP control).

TXT: role=host|receiver id=<uuid> ch=L|R|SUB|MID|SIDE|EXTRA|none ver=0

## Media datagram (UDP 8746)

Little-endian: magic 0x42544153, ver, channel, flags, seq, pts_us,
ndelay_us, sr, nch, nsamp, nbytes, payload.

channel: 0=L 1=R 2=SUB 3=MID 4=SIDE 5=EXTRA 6=MIX
flags: bit1=opus bit2=pcm_s16le

## Clock

POST /api/ping { t0_us } -> { t1_us, t2_us }
offset = ((t1-t0)+(t2-t3))/2
play = pts_us - offset_us + delay_ms*1000

## Matrix

L=xL R=xR SUB=MID=(xL+xR)/2 SIDE=(xL-xR)/2
