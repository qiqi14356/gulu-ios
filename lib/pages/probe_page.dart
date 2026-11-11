import 'package:flutter/material.dart';
import '../api.dart';
import '../config.dart';

/// 接口探测页：一键把 libapp.so 里静态提取到的路径全部打一遍，
/// 把状态码 + 返回体记下来，作为后续业务建模的依据。
class ProbePage extends StatefulWidget {
  const ProbePage({super.key});

  @override
  State<ProbePage> createState() => _ProbePageState();
}

class _ProbePageState extends State<ProbePage> {
  final ApiClient _api = ApiClient();
  final List<ProbeResult> _results = <ProbeResult>[];
  bool _running = false;

  Future<void> _runAll() async {
    setState(() {
      _running = true;
      _results.clear();
    });
    for (final String path in AppConfig.probePaths) {
      final ProbeResult r = await _api.probe(path);
      if (!mounted) return;
      setState(() => _results.add(r));
    }
    if (mounted) setState(() => _running = false);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
          child: Row(
            children: <Widget>[
              Expanded(
                child: Text('Base: ${AppConfig.apiBase}',
                    style: theme.textTheme.bodySmall, overflow: TextOverflow.ellipsis),
              ),
              FilledButton.icon(
                onPressed: _running ? null : _runAll,
                icon: const Icon(Icons.play_arrow, size: 18),
                label: Text(_running ? '探测中' : '全部探测'),
              ),
            ],
          ),
        ),
        const Divider(height: 1),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: _results.length,
            itemBuilder: (BuildContext ctx, int i) {
              final ProbeResult r = _results[i];
              final bool ok = r.status >= 200 && r.status < 400;
              return Card(
                margin: const EdgeInsets.only(bottom: 10),
                child: ExpansionTile(
                  leading: Icon(
                    ok ? Icons.check_circle : Icons.error_outline,
                    color: ok ? Colors.greenAccent : Colors.redAccent,
                  ),
                  title: Text('${r.status}  ${r.path}',
                      style: const TextStyle(fontFamily: 'Menlo', fontSize: 13)),
                  subtitle: Text('${r.elapsedMs}ms  ${r.contentType}',
                      style: theme.textTheme.bodySmall),
                  children: <Widget>[
                    Padding(
                      padding: const EdgeInsets.all(12),
                      child: SelectableText(
                        r.body.isEmpty ? '(空)' : r.body,
                        style: const TextStyle(fontFamily: 'Menlo', fontSize: 11),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
