import 'dart:async';
import 'dart:convert';
import 'dart:io';

/// 离线 HLS 本地代理。
///
/// 为什么要这一层：片源 CDN 把每个分片伪装成 `.png`（`Content-Type: image/png`，
/// 实际字节是 MPEG-TS，首字节 0x47）。AVPlayer 和 ffmpeg 都不接受非标准扩展名的
/// 分片，直接喂原始 m3u8 会报错。这一层做两件事：
///   1. 生成一份分片地址为 `http://127.0.0.1:<port>/seg/<i>.ts` 的 m3u8；
///   2. 把 `/seg/<i>.ts` 反向代理到 CDN 原始 `.png`，并把 Content-Type 改写成
///      `video/mp2t`。
///
/// 分片 URL 本身长期有效（只有 m3u8 的 token 会过期），所以只要手里有
/// 分片清单，这一层就能离线复现播放。
class LocalHlsServer {
  LocalHlsServer._(this._server, this._playlist);

  final HttpServer _server;
  final DemoPlaylist _playlist;

  int get port => _server.port;
  String get m3u8Url => 'http://127.0.0.1:$port/index.m3u8';

  static Future<LocalHlsServer> start(DemoPlaylist playlist) async {
    final HttpServer server = await HttpServer.bind(
      InternetAddress.loopbackIPv4,
      0,
    );
    final LocalHlsServer hls = LocalHlsServer._(server, playlist);
    server.listen(hls._handle, onError: (Object _) {});
    return hls;
  }

  Future<void> _handle(HttpRequest req) async {
    final HttpResponse res = req.response;
    final String path = req.uri.path;
    try {
      if (path == '/index.m3u8') {
        res.headers.contentType =
            ContentType('application', 'vnd.apple.mpegurl');
        res.write(_playlist.buildM3u8(port));
        await res.close();
        return;
      }
      final RegExpMatch? m = RegExp(r'^/seg/(\d+)\.ts$').firstMatch(path);
      if (m != null) {
        final int i = int.parse(m.group(1)!);
        final String? url = _playlist.segmentUrl(i);
        if (url == null) {
          res.statusCode = HttpStatus.notFound;
          await res.close();
          return;
        }
        await _proxy(url, res);
        return;
      }
      res.statusCode = HttpStatus.notFound;
      await res.close();
    } catch (_) {
      try {
        res.statusCode = HttpStatus.internalServerError;
        await res.close();
      } catch (_) {}
    }
  }

  Future<void> _proxy(String url, HttpResponse res) async {
    final HttpClient client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 15);
    try {
      final HttpClientRequest upReq =
          await client.getUrl(Uri.parse(url)).timeout(
                const Duration(seconds: 15),
              );
      // CDN 对 UA 不挑，但保持和 App 一致更稳。
      upReq.headers.set(HttpHeaders.userAgentHeader, 'Dart/3.10 (dart:io)');
      final HttpClientResponse upRes =
          await upReq.close().timeout(const Duration(seconds: 15));
      res.statusCode = upRes.statusCode;
      // 关键改写：CDN 返回 image/png，实际是 MPEG-TS。
      res.headers.set(HttpHeaders.contentTypeHeader, 'video/mp2t');
      res.headers.set(HttpHeaders.acceptRangesHeader, 'bytes');
      await res.addStream(upRes);
      await res.close();
    } finally {
      client.close(force: true);
    }
  }

  Future<void> stop() async => _server.close(force: true);
}

/// 一份离线分片清单。
///
/// 存储形态是「公共前缀 + 每段尾巴」：888 段的完整 URL 有 80 KB，拆开后
/// 只有 65 KB，且能一眼看出 CDN 的目录结构（`/xfy/<日期>/<时间戳>_<随机>.<n>/<hash>.png`）。
class DemoPlaylist {
  DemoPlaylist({
    required this.title,
    required this.episode,
    required this.prefix,
    required this.durs,
    required this.tails,
  });

  final String title;
  final String episode;
  final String prefix;
  final List<double> durs;
  final List<String> tails;

  /// `durs` 存的是毫秒（和 App 内部 `segmentDurationMs` 一致），
  /// 对外一律换算成秒，不要在这里直接当秒用 —— 否则 EXTINF 会写成 8050.0。
  int get segmentCount => tails.length;
  double get durationSeconds =>
      durs.fold<double>(0, (double a, double b) => a + b) / 1000.0;

  String? segmentUrl(int i) {
    if (i < 0 || i >= tails.length) return null;
    return '$prefix${tails[i]}';
  }

  /// 生成给 AVPlayer 用的 m3u8：分片全部指向本地代理的 `.ts` 路径。
  String buildM3u8(int port) {
    // TARGETDURATION 必须是「最大分片时长的向上取整」，写死 10 会在某些分片
    // 超过 10 秒时让 AVPlayer 判断异常。
    final double maxSec = durs.isEmpty
        ? 1
        : durs.reduce((double a, double b) => a > b ? a : b) / 1000.0;
    final int target = maxSec.ceil().clamp(1, 60);
    final StringBuffer sb = StringBuffer()
      ..writeln('#EXTM3U')
      ..writeln('#EXT-X-VERSION:3')
      ..writeln('#EXT-X-MEDIA-SEQUENCE:0')
      ..writeln('#EXT-X-ALLOW-CACHE:YES')
      ..writeln('#EXT-X-TARGETDURATION:$target');
    for (int i = 0; i < tails.length; i++) {
      final double d = durs[i] / 1000.0;
      sb.writeln('#EXTINF:${d.toStringAsFixed(6)},');
      sb.writeln('http://127.0.0.1:$port/seg/$i.ts');
    }
    sb.writeln('#EXT-X-ENDLIST');
    return sb.toString();
  }

  static DemoPlaylist fromJson(Map<String, dynamic> j) {
    return DemoPlaylist(
      title: j['title'] as String,
      episode: j['episode'] as String,
      prefix: j['prefix'] as String,
      durs: (j['durs'] as List<dynamic>)
          .map((dynamic e) => (e as num).toDouble())
          .toList(),
      tails: (j['tails'] as List<dynamic>).map((dynamic e) => e as String).toList(),
    );
  }

  static DemoPlaylist decode(String raw) =>
      fromJson(jsonDecode(raw) as Map<String, dynamic>);
}
