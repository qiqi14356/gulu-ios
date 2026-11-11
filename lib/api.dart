import 'package:dio/dio.dart';
import 'config.dart';

/// 极简 API 客户端：只做「探测 + 原样回显」。
/// 用途是拿真机去逐个打接口，把返回体记录下来再补业务模型，
/// 而不是凭空猜参数。
class ApiClient {
  ApiClient()
      : _dio = Dio(
          BaseOptions(
            baseUrl: AppConfig.apiBase,
            connectTimeout: const Duration(seconds: 12),
            receiveTimeout: const Duration(seconds: 20),
            headers: <String, dynamic>{
              'User-Agent': 'GuluGulu/2.2.5 (iOS; Flutter)',
              'Accept': 'application/json, text/plain, */*',
            },
            validateStatus: (_) => true,
          ),
        );

  final Dio _dio;

  Future<ProbeResult> probe(String path) async {
    final DateTime started = DateTime.now();
    try {
      final Response<dynamic> resp = await _dio.get<dynamic>(path);
      final String body = resp.data?.toString() ?? '';
      return ProbeResult(
        path: path,
        status: resp.statusCode ?? -1,
        contentType: resp.headers.value('content-type') ?? '',
        elapsedMs: DateTime.now().difference(started).inMilliseconds,
        body: body.length > 4000 ? '${body.substring(0, 4000)}\n…(截断)' : body,
      );
    } on DioException catch (e) {
      return ProbeResult(
        path: path,
        status: -1,
        contentType: '',
        elapsedMs: DateTime.now().difference(started).inMilliseconds,
        body: 'ERR ${e.type}: ${e.message}',
      );
    }
  }

  /// 保留一个语义明确的别名，避免把 `get` 当成方法名（Dart 里它是保留标记）。
  Future<ProbeResult> fetch(String path) => probe(path);
}

class ProbeResult {
  ProbeResult({
    required this.path,
    required this.status,
    required this.contentType,
    required this.elapsedMs,
    required this.body,
  });

  final String path;
  final int status;
  final String contentType;
  final int elapsedMs;
  final String body;
}
