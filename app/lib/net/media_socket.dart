import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import '../protocol/packet.dart';

const int kMediaPort = 8746;

class MediaSocket {
  RawDatagramSocket? _sock;

  Future<void> bind({int port = kMediaPort}) async {
    await close();
    _sock = await RawDatagramSocket.bind(InternetAddress.anyIPv4, port);
    _sock!.broadcastEnabled = true;
  }

  Stream<MediaPacket> get packets async* {
    final sock = _sock;
    if (sock == null) return;
    await for (final event in sock) {
      if (event != RawSocketEvent.read) continue;
      final dg = sock.receive();
      if (dg == null) continue;
      final pkt = MediaPacket.decode(dg.data);
      if (pkt != null) yield pkt;
    }
  }

  void send(Uint8List bytes, InternetAddress ip, int port) {
    _sock?.send(bytes, ip, port);
  }

  Future<void> close() async {
    _sock?.close();
    _sock = null;
  }
}
