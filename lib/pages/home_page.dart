import 'package:flutter/material.dart';
import '../config.dart';

/// 首页：先放「官方入口 + 变身口令说明 + 片库占位」，
/// 真业务数据等接口探测确认后再接。
class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(20),
      children: <Widget>[
        Row(
          children: <Widget>[
            const Icon(Icons.play_circle_fill, size: 40, color: Color(0xFF7C4DFF)),
            const SizedBox(width: 12),
            Text('咕噜咕噜', style: theme.textTheme.headlineSmall),
          ],
        ),
        const SizedBox(height: 8),
        Text('iOS 重建客户端 v2.2.5', style: theme.textTheme.bodySmall),
        const SizedBox(height: 24),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('官方 iOS 通道', style: theme.textTheme.titleMedium),
                const SizedBox(height: 8),
                const Text('官方 iOS 版是 App Store 上的马甲应用，装好后在搜索框输入口令即可变身。'),
                const SizedBox(height: 12),
                SelectableText('口令：${AppConfig.iosActivationCode}',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 12),
                Text('官网：${AppConfig.officialSite}', style: theme.textTheme.bodySmall),
                Text('备用：${AppConfig.officialBackup}', style: theme.textTheme.bodySmall),
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
                Text('片库', style: theme.textTheme.titleMedium),
                const SizedBox(height: 8),
                const Text('等待接口探测结果接入（/movie.do、/vnd.do、/api.php）。'),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
