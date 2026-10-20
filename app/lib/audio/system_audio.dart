import 'dart:async';
import 'dart:typed_data';

import 'package:playback_capture/playback_capture.dart';

/// Captura el audio del sistema (YouTube Music, Tidal, etc.) en Android 10+.
/// Entrega frames de 20 ms a 48 kHz mono (mezcla L+R) listos para el host.
class SystemAudioSource {
  final _capture = PlaybackCapture();
  StreamController<Int16List>? _ctrl;
  bool _running = false;

  Stream<Int16List> get frames => _ctrl?.stream ?? const Stream.empty();

  Future<bool> start() async {
    if (_running) return true;
    _ctrl = StreamController<Int16List>.broadcast();
    final result = await _capture.listenAudio(
      audioDataCallback: _onData,
    );
    if (result != PlaybackCaptureResult.recording) {
      await _ctrl?.close();
      _ctrl = null;
      return false;
    }
    _running = true;
    return true;
  }

  void _onData(Uint8List data) {
    if (!_running || _ctrl == null || _ctrl!.isClosed) return;
    final samples = data.buffer.asInt16List(data.offsetInBytes, data.lengthInBytes ~/ 2);
    const frame = 960;
    var i = 0;
    while (i + frame <= samples.length) {
      _ctrl!.add(Int16List.fromList(samples.sublist(i, i + frame)));
      i += frame;
    }
  }

  Future<void> stop() async {
    _running = false;
    await _capture.stop();
    await _ctrl?.close();
    _ctrl = null;
  }
}
