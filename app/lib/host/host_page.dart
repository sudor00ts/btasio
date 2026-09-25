import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../app_theme.dart';
import '../models.dart';
import 'host_controller.dart';

class HostPage extends StatefulWidget {
  const HostPage({super.key, required this.ctrl});
  final HostController ctrl;
  @override
  State<HostPage> createState() => _HostPageState();
}

class _HostPageState extends State<HostPage> {
  final _ip = TextEditingController();
  Role _newRole = Role.L;
  @override
  void dispose() { _ip.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    final c = widget.ctrl;
    return ListenableBuilder(
      listenable: c,
      builder: (_, __) => ListView(
        padding: const EdgeInsets.fromLTRB(18, 8, 18, 32),
        children: [
          Text(c.status, style: const TextStyle(color: muted, fontSize: 13)),
          const SizedBox(height: 14),
          Wrap(spacing: 8, children: [
            _chip(c, Preset.stereoSub, 'Stereo + Sub'),
            _chip(c, Preset.midSide, 'Mid / Side'),
            _chip(c, Preset.all, 'Todos'),
          ]),
          const SizedBox(height: 18),
          Row(children: [
            Expanded(child: OutlinedButton(
              onPressed: () async {
                final r = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: const ['wav']);
                final path = r?.files.single.path;
                if (path != null) await c.loadWav(path);
              },
              child: Text(c.wavName ?? 'Elegir WAV 16-bit'),
            )),
            const SizedBox(width: 8),
            OutlinedButton(onPressed: c.clearWav, child: const Text('Tono')),
          ]),
          const SizedBox(height: 18),
          const Text('Receivers', style: TextStyle(fontWeight: FontWeight.w700)),
          Row(children: [
            Expanded(child: TextField(controller: _ip, decoration: const InputDecoration(hintText: 'IP del receiver', isDense: true))),
            DropdownButton<Role>(value: _newRole, items: Role.values.map((r) => DropdownMenuItem(value: r, child: Text(r.name))).toList(), onChanged: (v) => setState(() => _newRole = v ?? Role.L)),
            IconButton(onPressed: () { c.addTarget(_ip.text, _newRole); _ip.clear(); }, icon: const Icon(Icons.add)),
          ]),
          ...c.targets.map((t) => Card(color: card, child: ListTile(
            title: Text(t.host),
            trailing: Row(mainAxisSize: MainAxisSize.min, children: [
              DropdownButton<Role>(value: t.role, items: Role.values.map((r) => DropdownMenuItem(value: r, child: Text(r.name))).toList(), onChanged: (v) { if (v != null) c.setTargetRole(t.id, v); }),
              IconButton(onPressed: () => c.removeTarget(t.id), icon: const Icon(Icons.close)),
            ]),
          ))),
          const SizedBox(height: 20),
          FilledButton(onPressed: c.running ? c.stop : c.start, child: Text(c.running ? 'Detener' : 'Transmitir')),
        ],
      ),
    );
  }

  Widget _chip(HostController c, Preset p, String label) {
    final on = c.preset == p;
    return ChoiceChip(label: Text(label), selected: on, selectedColor: acc, onSelected: (_) => c.setPreset(p));
  }
}
