import 'models.dart';

double mixSample(double left, double right, Role role) {
  return switch (role) {
    Role.L => left,
    Role.R => right,
    Role.SUB || Role.MID || Role.EXTRA => 0.5 * left + 0.5 * right,
    Role.SIDE => 0.5 * left - 0.5 * right,
  };
}

int clamp16(double v) {
  final x = (v * 32767.0).round();
  if (x > 32767) return 32767;
  if (x < -32768) return -32768;
  return x;
}
