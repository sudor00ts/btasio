import 'dart:io';
import 'dart:typed_data';
import '../protocol/packet.dart';

class WavPcm {
  WavPcm({required this.sampleRate, required this.channels, required this.samples});
  final int sampleRate;
  final int channels;
  final Int16List samples;
  int cursor = 0;
  int get frames => samples.length ~/ channels;

  Float64List nextStereo(int n) {
    final out = Float64List(n * 2);
    for (var i = 0; i < n; i++) {
      if (cursor >= frames) cursor = 0;
      if (channels == 1) {
        final v = samples[cursor] / 32768.0;
        out[i * 2] = v;
        out[i * 2 + 1] = v;
      } else {
        final base = cursor * channels;
        out[i * 2] = samples[base] / 32768.0;
        out[i * 2 + 1] = samples[base + 1] / 32768.0;
      }
      cursor++;
    }
    return out;
  }

  static Future<WavPcm> load(String path) async => parse(await File(path).readAsBytes());

  static WavPcm parse(Uint8List bytes) {
    if (bytes.length < 44) throw const FormatException('WAV corto');
    final d = ByteData.sublistView(bytes);
    if (String.fromCharCodes(bytes.sublist(0, 4)) != 'RIFF') {
      throw const FormatException('No es WAV');
    }
    var off = 12;
    var sr = kSampleRate;
    var ch = 2;
    Uint8List? data;
    while (off + 8 <= bytes.length) {
      final id = String.fromCharCodes(bytes.sublist(off, off + 4));
      final size = d.getUint32(off + 4, Endian.little);
      final start = off + 8;
      if (id == 'fmt ') {
        final format = d.getUint16(start, Endian.little);
        ch = d.getUint16(start + 2, Endian.little);
        sr = d.getUint32(start + 4, Endian.little);
        final bits = d.getUint16(start + 14, Endian.little);
        if (format != 1 || bits != 16) {
          throw FormatException('Solo PCM 16-bit');
        }
      } else if (id == 'data') {
        data = bytes.sublist(start, (start + size).clamp(0, bytes.length));
      }
      off = start + size + (size.isOdd ? 1 : 0);
    }
    if (data == null) throw const FormatException('sin data');
    final samples = Int16List.view(data.buffer, data.offsetInBytes, data.lengthInBytes ~/ 2);
    return WavPcm(sampleRate: sr, channels: ch, samples: Int16List.fromList(samples));
  }
}
