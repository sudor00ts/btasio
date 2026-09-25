import 'dart:math';
import 'dart:typed_data';
import '../protocol/packet.dart';

class ToneSource {
  ToneSource({this.sampleRate = kSampleRate});
  final int sampleRate;
  int _cursor = 0;

  Float64List nextStereo(int frames) {
    final out = Float64List(frames * 2);
    for (var i = 0; i < frames; i++) {
      final t = (_cursor + i) / sampleRate;
      out[i * 2] = 0.25 * sin(2 * pi * 440 * t);
      out[i * 2 + 1] = 0.25 * sin(2 * pi * 660 * t);
    }
    _cursor += frames;
    return out;
  }

  void reset() => _cursor = 0;
}
