import 'dart:collection';
import 'dart:typed_data';
import 'package:flutter_pcm_sound/flutter_pcm_sound.dart';
import '../protocol/packet.dart';

class PcmOut {
  final _q = Queue<int>();
  bool _ready = false;

  Future<void> start({int sampleRate = kSampleRate}) async {
    await FlutterPcmSound.setup(sampleRate: sampleRate, channelCount: 1, iosAudioCategory: IosAudioCategory.playback);
    await FlutterPcmSound.setFeedThreshold(kFrameSamples * 2);
    FlutterPcmSound.setFeedCallback(_onFeed);
    await FlutterPcmSound.start();
    _ready = true;
  }

  void feed(Int16List mono) {
    if (!_ready) return;
    _q.addAll(mono);
    final cap = kSampleRate ~/ 2;
    while (_q.length > cap) {
      _q.removeFirst();
    }
  }

  Future<void> _onFeed(int remaining) async {
    if (!_ready) return;
    final need = (kFrameSamples * 3 - remaining).clamp(0, kFrameSamples * 4);
    if (need <= 0) return;
    final chunk = <int>[];
    for (var i = 0; i < need; i++) {
      chunk.add(_q.isEmpty ? 0 : _q.removeFirst());
    }
    await FlutterPcmSound.feed(PcmArrayInt16.fromList(chunk));
  }

  Future<void> stop() async {
    _ready = false;
    _q.clear();
    FlutterPcmSound.setFeedCallback(null);
    try { await FlutterPcmSound.release(); } catch (_) {}
  }
}
