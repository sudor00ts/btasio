enum Role { L, R, SUB, MID, SIDE, EXTRA }

enum Preset { stereoSub, midSide, all }

enum ChannelId {
  L(0),
  R(1),
  SUB(2),
  MID(3),
  SIDE(4),
  EXTRA(5),
  MIX(6);

  const ChannelId(this.wire);
  final int wire;

  static ChannelId fromWire(int v) =>
      ChannelId.values.firstWhere((e) => e.wire == v, orElse: () => ChannelId.MIX);
}

extension RoleX on Role {
  ChannelId get channel => switch (this) {
        Role.L => ChannelId.L,
        Role.R => ChannelId.R,
        Role.SUB => ChannelId.SUB,
        Role.MID => ChannelId.MID,
        Role.SIDE => ChannelId.SIDE,
        Role.EXTRA => ChannelId.EXTRA,
      };
}

class ReceiverTarget {
  ReceiverTarget({
    required this.id,
    required this.host,
    this.port = 8746,
    required this.role,
    this.delayMs = 160,
  });

  final String id;
  String host;
  int port;
  Role role;
  int delayMs;
}
