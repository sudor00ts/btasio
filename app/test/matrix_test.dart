import 'package:btasio/matrix.dart';
import 'package:btasio/models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('stereo isolate', () {
    expect(mixSample(1, 0, Role.L), 1);
    expect(mixSample(0, 1, Role.R), 1);
  });
  test('mid side', () {
    expect(mixSample(1, 1, Role.MID), 1);
    expect(mixSample(1, 1, Role.SIDE), 0);
  });
}
