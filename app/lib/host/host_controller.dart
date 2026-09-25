import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';
import '../audio/tone.dart';
import '../audio/wav_pcm.dart';
import '../matrix.dart';
import '../models.dart';
import '../net/media_socket.dart';
import '../protocol/packet.dart';

class HostController extends ChangeNotifier {
  HostController();
  final _uuid = const Uuid();
  final _tone = ToneSource();
  final _net = MediaSocket();
  Preset preset = Preset.stereoSub;
  bool running = false;
  String? wavName;
  String status = 'idle';
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
    status = 'host listo — agregá IPs de receivers en la misma Wi-Fi';
    notifyListeners();
  }

  void setPreset(Preset p) { preset = p; notifyListeners(); }
  void addTarget(String host, Role role) {
    final ip = host.trim();
    if (ip.isEmpty) return;
    targets.add(ReceiverTarget(id: _uuid.v4(), host: ip, role: role));
    notifyListeners();
  }
  void removeTarget(String id) { targets.removeWhere((t) => t.id == id); notifyListeners(); }
  void setTargetRole(String id, Role role) {
    for (final t in targets) { if (t.id == id) t.role = role; }
    notifyListeners();
  }
  Future<void> loadWav(String path) async {
    _wav = await WavPcm.load(path);
    wavName = path.split(Platform.pathSeparator).last;
    status = 'WAV $wavName';
    notifyListeners();
  }
  void clearWav() { _wav = null; wavName = null; _tone.reset(); status = 'tono 440/660'; notifyListeners(); }

  Future<void> start() async {
    if (running) return;
    if (targets.isEmpty) { status = 'agregá un receiver'; notifyListeners(); return; }
    running = true; _seq = 0; _origin = DateTime.now();
    status = _wav == null ? 'streaming tono' : 'streaming $wavName';
    notifyListeners();
    _tick?.cancel();
    _tick = Timer.periodic(const Duration(milliseconds: kFrameMs), (_) => _emit());
  }

  void stop() { running = false; _tick?.cancel(); _tick = null; status = 'detenido'; notifyListeners(); }

  void _emit() {
    if (!running) return;
    final stereo = _wav?.nextStereo(kFrameSamples) ?? _tone.nextStereo(kFrameSamples);
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
      final pkt = MediaPacket(channel: t.role.channel, seq: _seq, ptsUs: pts, pcm: pcm);
      try { _net.send(pkt.encode(), InternetAddress(t.host), t.port); } catch (e) { status = 'send ${t.host}: $e'; }
    }
    _seq++;
  }

  @override
  void dispose() { stop(); _net.close(); super.dispose(); }
}
