import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'app_theme.dart';
import 'host/host_controller.dart';
import 'host/host_page.dart';
import 'receiver/receiver_controller.dart';
import 'receiver/receiver_page.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const BtasioApp());
}

class BtasioApp extends StatelessWidget {
  const BtasioApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'btasio',
      debugShowCheckedModeBanner: false,
      theme: btasioTheme(),
      home: const Shell(),
    );
  }
}

class Shell extends StatefulWidget {
  const Shell({super.key});
  @override
  State<Shell> createState() => _ShellState();
}

class _ShellState extends State<Shell> {
  final host = HostController();
  final rx = ReceiverController();
  int tab = 0;

  @override
  void initState() {
    super.initState();
    host.init();
    [Permission.nearbyWifiDevices, Permission.storage].request();
  }

  @override
  void dispose() {
    host.dispose();
    rx.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('btasio', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
            Text('host + receiver · Wi-Fi · un A2DP por teléfono', style: TextStyle(fontSize: 12, color: muted)),
          ],
        ),
      ),
      body: tab == 0 ? HostPage(ctrl: host) : ReceiverPage(ctrl: rx),
      bottomNavigationBar: NavigationBar(
        selectedIndex: tab,
        onDestinationSelected: (i) => setState(() => tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.podcasts), label: 'Host'),
          NavigationDestination(icon: Icon(Icons.speaker), label: 'Receiver'),
        ],
      ),
    );
  }
}
