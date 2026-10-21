import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

import '../audio/system_audio.dart';
import '../audio/tone.dart';
import '../audio/wav_pcm.dart';
import '../matrix.dart';
import '../models.dart';
import '../net/media_socket.dart';
import '../protocol/packet.dart';

class HostController extends ChangeNotifier {
  HostController();

  final _uuid = const Uuid();
  final _system = SystemAudioSource();
  final _tone = ToneSource();
  bool useSystemAudio = false;
  StreamSubscription? _sysSub;
  Int16List? _lastSystemFrame;
  final _net = MediaSocket();

  Preset preset = Preset.stereoSub;
  bool running = false;
  String? wavName;
  String status = 'idle';
  String? localIp;
  final targets = <ReceiverTarget>[];

  WavPcm? _wav;
  Timer? _tick;
  int _seq = 0;
  DateTime? _origin;

  Future<void> init() async {
    try {
      await _net.bind(port: 0);
    } catch (e) {
      status = 'bind falló: $e';
      notifyListeners();
      return;
    }
    status = 'host listo — agregá IPs de receivers en la misma Wi‑Fi';
    notifyListeners();
  }

  void setPreset(Preset p) {
    preset = p;
    notifyListeners();
  }

  void addTarget(String host, Role role) {
    final ip = host.trim();
    if (ip.isEmpty) return;
    targets.add(ReceiverTarget(id: _uuid.v4(), host: ip, role: role));
    notifyListeners();
  }

  void removeTarget(String id) {
    targets.removeWhere((t) => t.id == id);
    notifyListeners();
  }

  void setTargetRole(String id, Role role) {
    final t = targets.where((e) => e.id == id);
    if (t.isEmpty) return;
    t.first.role = role;
    notifyListeners();
  }

  Future<void> loadWav(String path) async {
    _wav = await WavPcm.load(path);
    wavName = path.split(Platform.pathSeparator).last;
    _tone.reset();
    status = 'WAV ${wavName!} ${_wav!.sampleRate} Hz ${_wav!.channels} ch';
    notifyListeners();
  }

  void clearWav() {
    _wav = null;
    wavName = null;
    _tone.reset();
    status = 'tono de prueba 440 / 660 Hz';
    notifyListeners();
  }

  Future<void> setSystemAudio(bool on) async {
    useSystemAudio = on;
    if (on) {
      final ok = await _system.start();
      if (!ok) {
        useSystemAudio = false;
        status = 'no pude capturar audio del sistema (permiso o Android < 10)';
        notifyListeners();
        return;
      }
      _sysSub?.cancel();
      _sysSub = _system.frames.listen((f) => _lastSystemFrame = f);
      status = 'capturando audio del sistema';
    } else {
      await _system.stop();
      _sysSub?.cancel();
      _lastSystemFrame = null;
      status = 'tono de prueba';
    }
    notifyListeners();
  }

  Future<void> start() async {
    if (running) return;
    if (targets.isEmpty) {
      status = 'agregá al menos un receiver (IP)';
      notifyListeners();
      return;
    }
    running = true;
    _seq = 0;
    _origin = DateTime.now();
    status = useSystemAudio ? 'streaming audio del sistema' : (_wav == null ? 'streaming tono' : 'streaming $wavName');
    notifyListeners();
    _tick?.cancel();
    _tick = Timer.periodic(const Duration(milliseconds: kFrameMs), (_) => _emit());
  }

  void stop() {
    running = false;
    _tick?.cancel();
    _tick = null;
    status = 'detenido';
    notifyListeners();
  }

  void _emit() {
    if (!running) return;
    Float64List stereo;
    if (useSystemAudio && _lastSystemFrame != null) {
      stereo = _expandMonoFloat(_lastSystemFrame!);
    } else {
      stereo = _wav?.nextStereo(kFrameSamples) ?? _tone.nextStereo(kFrameSamples);
    }
    final pts = DateTime.now().difference(_origin!).inMicroseconds;
    final roles = targets.map((t) => t.role).toSet();
    final frames = <Role, Int16List>{};
    for (final role in roles) {
      final mono = Int16List(kFrameSamples);
      for (var i = 0; i < kFrameSamples; i++) {
        mono[i] = clamp16(mixSample(stereo[i * 2], stereo[i * 2 + 1], role));
      }
      frames[role] = mono;
    }
    for (final t in targets) {
      final pcm = frames[t.role];
      if (pcm == null) continue;
      final pkt = MediaPacket(
        channel: t.role.channel,
        seq: _seq,
        ptsUs: pts,
        pcm: pcm,
      );
      try {
        _net.send(pkt.encode(), InternetAddress(t.host), t.port);
      } catch (e) {
        status = 'send ${t.host}: $e';
      }
    }
    _seq++;
  }

  Float64List _expandMonoFloat(Int16List mono) {
    final out = Float64List(mono.length * 2);
    for (var i = 0; i < mono.length; i++) {
      final v = mono[i] / 32768.0;
      out[i * 2] = v;
      out[i * 2 + 1] = v;
    }
    return out;
  }

  @override
  void dispose() {
    stop();
    _system.stop();
    _net.close();
    super.dispose();
  }
}
