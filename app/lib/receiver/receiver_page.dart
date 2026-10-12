import 'package:flutter/material.dart';

import '../app_theme.dart';
import '../models.dart';
import 'receiver_controller.dart';

class ReceiverPage extends StatelessWidget {
  const ReceiverPage({super.key, required this.ctrl});
  final ReceiverController ctrl;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: ctrl,
      builder: (_, __) {
        return ListView(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 32),
          children: [
            Text(ctrl.status, style: const TextStyle(color: muted, fontSize: 13)),
            const SizedBox(height: 6),
            Text('paquetes ${ctrl.packets}', style: const TextStyle(color: muted, fontSize: 12)),
            const SizedBox(height: 16),
            const Text('Rol de este teléfono', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: Role.values.map((r) {
                final on = ctrl.role == r;
                return ChoiceChip(
                  label: Text(r.name),
                  selected: on,
                  selectedColor: acc2,
                  onSelected: (_) => ctrl.setRole(r),
                );
              }).toList(),
            ),
            const SizedBox(height: 20),
            Text('delay ${ctrl.delayMs} ms (SBC típico 160)'),
            Slider(
              min: 0,
              max: 400,
              value: ctrl.delayMs.toDouble(),
              onChanged: (v) => ctrl.setDelay(v.round()),
            ),
            const SizedBox(height: 8),
            const Text(
              'Conectá el parlante Bluetooth en Ajustes del sistema ANTES. '
              'Este modo solo reproduce el canal que el host le manda.',
              style: TextStyle(color: muted, fontSize: 12),
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: () => ctrl.running ? ctrl.stop() : ctrl.start(),
              child: Text(ctrl.running ? 'Dejar de escuchar' : 'Escuchar :8746'),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: ctrl.testTone,
              child: const Text('Test tono local'),
            ),
          ],
        );
      },
    );
  }
}
