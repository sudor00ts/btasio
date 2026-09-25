import 'package:flutter/material.dart';

const bg = Color(0xFF0E1116);
const card = Color(0xFF171C24);
const ink = Color(0xFFE8EDF4);
const muted = Color(0xFF8B97A8);
const acc = Color(0xFF6EE7B7);
const acc2 = Color(0xFF7DD3FC);

ThemeData btasioTheme() {
  final base = ThemeData.dark(useMaterial3: true);
  return base.copyWith(
    scaffoldBackgroundColor: bg,
    colorScheme: base.colorScheme.copyWith(primary: acc, surface: card, onPrimary: const Color(0xFF042014)),
    appBarTheme: const AppBarTheme(backgroundColor: bg, foregroundColor: ink, elevation: 0),
  );
}
