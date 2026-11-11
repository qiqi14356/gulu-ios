/// 全局配置。
/// API_BASE 通过 --dart-define 注入：
///   flutter build ios --release --dart-define=API_BASE=https://your.host
/// 未注入时回落到官网域名（官网只提供静态页 + api/site.php，业务接口在别的反代上）。
class AppConfig {
  static const String apiBase = String.fromEnvironment(
    'API_BASE',
    defaultValue: 'https://glgl.tv',
  );

  /// 从 libapp.so 静态提取到的接口路径（原样保留，便于逐个探测）。
  static const List<String> probePaths = <String>[
    '/api.php',
    '/app/runtime-policy',
    '/app/integrity/challenge',
    '/movie.do',
    '/vnd.do',
    '/mpd.json',
    '/parse/api.php',
    '/api/danmu',
    '/app/bn/room/config',
    '/app/player-protection/presentation',
  ];

  /// 官方分发的变身口令（官网 iOS 教程原文）。
  static const String iosActivationCode = 'jz10130';
  static const String officialSite = 'https://glgl.tv/';
  static const String officialBackup = 'https://link3.cc/glgl';
}
