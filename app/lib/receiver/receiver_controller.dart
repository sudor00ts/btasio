import 'dart:async';
import 'package:flutter/foundation.dart';
import '../audio/pcm_out.dart';
import '../models.dart';
import '../net/media_socket.dart';
import '../protocol/packet.dart';

class ReceiverController extends ChangeNotifier {
  ReceiverController();
  final _net = MediaSocket();
  final _out = PcmOut();
  Role role = Role.L;
  int delayMs = 160;
  bool running = false;
  String status = 'idle';
  int packets = 0;
  StreamSubscription? _sub;

  void setRole(Role r) { role = r; notifyListeners(); }
  void setDelay(int ms) { delayMs = ms.clamp(0, 500); notifyListeners(); }

  Future<void> start() async {
    if (running) return;
    try {
      await _net.bind(port: kMediaPort);
      await _out.start();
    } catch (e) {
      status = 'bind/audio: $e';
      notifyListeners();
      return;
    }
    running = true;
    packets = 0;
    status = 'escuchando UDP $kMediaPort rol ${role.name}';
    notifyListeners();
    _sub = _net.packets.listen(_onPkt);
  }

  void _onPkt(MediaPacket pkt) {
    if (!running || pkt.channel != role.channel) return;
    packets++;
    if (packets % 25 == 0) {
      status = 'rx seq=${pkt.seq} ch=${pkt.channel.name}';
      notifyListeners();
    }
    _out.feed(pkt.pcm);
  }

  Future<void> stop() async {
    running = false;
    await _sub?.cancel();
    _sub = null;
    await _net.close();
    await _out.stop();
    status = 'detenido';
    notifyListeners();
  }

  @override
  void dispose() { stop(); super.dispose(); }
}
