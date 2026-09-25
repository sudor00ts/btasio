import 'dart:typed_data';

import '../models.dart';

const int kMagic = 0x42544153;
const int kFlagPcmS16le = 1 << 2;
const int kHeaderSize = 36;
const int kSampleRate = 48000;
const int kFrameMs = 20;
const int kFrameSamples = kSampleRate * kFrameMs ~/ 1000;

class MediaPacket {
  MediaPacket({
    required this.channel,
    required this.seq,
    required this.ptsUs,
    required this.pcm,
    this.ndelayUs = 0,
    this.sampleRate = kSampleRate,
  });

  final ChannelId channel;
  final int seq;
  final int ptsUs;
  final int ndelayUs;
  final int sampleRate;
  final Int16List pcm;

  Uint8List encode() {
    final nbytes = pcm.length * 2;
    final out = ByteData(kHeaderSize + nbytes);
    var o = 0;
    out.setUint32(o, kMagic, Endian.little); o += 4;
    out.setUint8(o, 0); o += 1;
    out.setUint8(o, channel.wire); o += 1;
    out.setUint16(o, kFlagPcmS16le, Endian.little); o += 2;
    out.setUint32(o, seq, Endian.little); o += 4;
    out.setInt64(o, ptsUs, Endian.little); o += 8;
    out.setInt32(o, ndelayUs, Endian.little); o += 4;
    out.setUint32(o, sampleRate, Endian.little); o += 4;
    out.setUint16(o, 1, Endian.little); o += 2;
    out.setUint16(o, pcm.length, Endian.little); o += 2;
    out.setUint32(o, nbytes, Endian.little); o += 4;
    final bytes = out.buffer.asUint8List();
    bytes.setRange(kHeaderSize, kHeaderSize + nbytes, Uint8List.view(pcm.buffer));
    return bytes;
  }

  static MediaPacket? decode(Uint8List raw) {
    if (raw.length < kHeaderSize) return null;
    final b = ByteData.sublistView(raw);
    if (b.getUint32(0, Endian.little) != kMagic) return null;
    if (b.getUint8(4) != 0) return null;
    final ch = ChannelId.fromWire(b.getUint8(5));
    final flags = b.getUint16(6, Endian.little);
    if (flags & kFlagPcmS16le == 0) return null;
    final seq = b.getUint32(8, Endian.little);
    final pts = b.getInt64(12, Endian.little);
    final ndelay = b.getInt32(20, Endian.little);
    final sr = b.getUint32(24, Endian.little);
    final nsamp = b.getUint16(30, Endian.little);
    final nbytes = b.getUint32(32, Endian.little);
    if (raw.length < kHeaderSize + nbytes) return null;
    final pcmBytes = raw.sublist(kHeaderSize, kHeaderSize + nbytes);
    final pcm = Int16List.view(pcmBytes.buffer, pcmBytes.offsetInBytes, nsamp.clamp(0, pcmBytes.length ~/ 2));
    return MediaPacket(channel: ch, seq: seq, ptsUs: pts, ndelayUs: ndelay, sampleRate: sr, pcm: Int16List.fromList(pcm));
  }
}
