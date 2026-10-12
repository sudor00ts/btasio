import 'dart:collection';
import 'dart:math';
import 'dart:typed_data';

import 'package:flutter_pcm_sound/flutter_pcm_sound.dart';

import '../protocol/packet.dart';

class PcmOut {
  final _q = Queue<int>();
  bool _ready = false;

  Future<void> start({int sampleRate = kSampleRate}) async {
    await FlutterPcmSound.setup(
      sampleRate: sampleRate,
      channelCount: 1,
      iosAudioCategory: IosAudioCategory.playback,
    );
    await FlutterPcmSound.setFeedThreshold(kFrameSamples);
    FlutterPcmSound.setFeedCallback(_onFeed);
    await FlutterPcmSound.start();
    _ready = true;
    // Pre-feed so AudioTrack starts and keeps requesting
    _q.addAll(List.filled(kFrameSamples * 4, 0));
    await _push(kFrameSamples * 2);
  }

  void feed(Int16List mono) {
    if (!_ready) return;
    _q.addAll(mono);
    final cap = kSampleRate ~/ 2;
    while (_q.length > cap) {
      _q.removeFirst();
    }
  }

  Future<void> playTestTone() async {
    if (!_ready) await start();
    final sr = kSampleRate;
    final n = sr; // 1 second
    final tone = Int16List(n);
    for (var i = 0; i < n; i++) {
      tone[i] = (sin(2 * pi * 440 * i / sr) * 8000).round();
    }
    feed(tone);
    await _push(n);
  }

  Future<void> _onFeed(int remaining) async {
    if (!_ready) return;
    final need = (kFrameSamples * 4 - remaining).clamp(kFrameSamples, kFrameSamples * 6);
    await _push(need);
  }

  Future<void> _push(int n) async {
    if (n <= 0) return;
    final chunk = <int>[];
    for (var i = 0; i < n; i++) {
      chunk.add(_q.isEmpty ? 0 : _q.removeFirst());
    }
    await FlutterPcmSound.feed(PcmArrayInt16.fromList(chunk));
  }

  Future<void> stop() async {
    _ready = false;
    _q.clear();
    FlutterPcmSound.setFeedCallback(null);
    try {
      await FlutterPcmSound.release();
    } catch (_) {}
  }
}
