import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;

import '../config.dart';
import '../local_hls.dart';
import 'player_page.dart';

/// 首页：能直接播的剧集列表（离线分片清单）+ 官方通道说明。
///
/// 片库接口（`/app/bn/v2`）用的是会话密钥加密的 protobuf，静态无法复现；
/// 但播放链路和片库是解耦的 —— 只要拿到分片清单，就能脱离 App 直接播。
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  static const List<Map<String, String>> _sources = <Map<String, String>>[
    <String, String>{'asset': 'assets/demo/ep02.json', 'label': '嫁金钗 · 第02集'},
    <String, String>{'asset': 'assets/demo/ep05.json', 'label': '嫁金钗 · 第05集'},
    <String, String>{'asset': 'assets/demo/ep06.json', 'label': '嫁金钗 · 第06集'},
  ];

  String? _loading;

  Future<void> _open(Map<String, String> src) async {
    setState(() => _loading = src['asset']);
    try {
      final String raw = await rootBundle.loadString(src['asset']!);
      final DemoPlaylist pl = DemoPlaylist.decode(raw);
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => PlayerPage(playlist: pl),
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('加载失败：$e')));
      }
    } finally {
      if (mounted) setState(() => _loading = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(20),
      children: <Widget>[
        Row(
          children: <Widget>[
            const Icon(Icons.play_circle_fill,
                size: 40, color: Color(0xFF7C4DFF)),
            const SizedBox(width: 12),
            Text('咕噜咕噜', style: theme.textTheme.headlineSmall),
          ],
        ),
        const SizedBox(height: 8),
        Text('iOS 客户端 v2.2.5 · 离线可播构建',
            style: theme.textTheme.bodySmall),
        const SizedBox(height: 20),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('可播放剧集', style: theme.textTheme.titleMedium),
                const SizedBox(height: 4),
                Text('分片直连 CDN，无需登录或破解片库接口。',
                    style: theme.textTheme.bodySmall),
                const SizedBox(height: 12),
                for (final Map<String, String> s in _sources)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.movie_outlined),
                    title: Text(s['label']!),
                    trailing: _loading == s['asset']
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.play_arrow),
                    onTap: _loading == null ? () => _open(s) : null,
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('官方 iOS 通道', style: theme.textTheme.titleMedium),
                const SizedBox(height: 8),
                const Text('官方 iOS 版是 App Store 上的马甲应用，装好后在搜索框输入口令变身。'),
                const SizedBox(height: 12),
                const SelectableText(
                  '口令：${AppConfig.iosActivationCode}',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
                const SizedBox(height: 12),
                Text('官网：${AppConfig.officialSite}',
                    style: theme.textTheme.bodySmall),
                Text('备用：${AppConfig.officialBackup}',
                    style: theme.textTheme.bodySmall),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
