import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import '../local_hls.dart';

/// 播放页：拉起 LocalHlsServer，再把它的 m3u8 交给 AVPlayer。
class PlayerPage extends StatefulWidget {
  const PlayerPage({super.key, required this.playlist});

  final DemoPlaylist playlist;

  @override
  State<PlayerPage> createState() => _PlayerPageState();
}

class _PlayerPageState extends State<PlayerPage> {
  LocalHlsServer? _server;
  VideoPlayerController? _controller;
  String _status = '正在启动本地代理…';
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    try {
      final LocalHlsServer s = await LocalHlsServer.start(widget.playlist);
      if (!mounted) {
        await s.stop();
        return;
      }
      _server = s;
      setState(() => _status = '代理已就绪：${s.m3u8Url}');

      final VideoPlayerController c =
          VideoPlayerController.networkUrl(Uri.parse(s.m3u8Url));
      _controller = c;
      await c.initialize();
      if (!mounted) return;
      await c.play();
      setState(() => _status = '播放中');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _failed = true;
        _status = '启动失败：$e';
      });
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    _server?.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final VideoPlayerController? c = _controller;
    final bool ready = c != null && c.value.isInitialized;
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: Text('${widget.playlist.title} · ${widget.playlist.episode}'),
        backgroundColor: Colors.black,
      ),
      body: Column(
        children: <Widget>[
          AspectRatio(
            aspectRatio: ready ? c.value.aspectRatio : 16 / 9,
            child: ready
                ? GestureDetector(
                    onTap: () {
                      setState(() {
                        c.value.isPlaying ? c.pause() : c.play();
                      });
                    },
                    child: Stack(
                      alignment: Alignment.center,
                      children: <Widget>[
                        VideoPlayer(c),
                        if (!c.value.isPlaying)
                          const Icon(Icons.play_arrow,
                              size: 64, color: Colors.white70),
                      ],
                    ),
                  )
                : Center(
                    child: _failed
                        ? const Icon(Icons.error_outline,
                            size: 48, color: Colors.redAccent)
                        : const CircularProgressIndicator(),
                  ),
          ),
          if (ready)
            VideoProgressIndicator(c, allowScrubbing: true, padding:
                const EdgeInsets.symmetric(vertical: 8)),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: <Widget>[
                Text(_status,
                    style: const TextStyle(color: Colors.white70, fontSize: 13)),
                const SizedBox(height: 12),
                Text(
                  '分片数 ${widget.playlist.segmentCount} · '
                  '总时长 ${(widget.playlist.durationSeconds / 60).toStringAsFixed(1)} 分钟\n'
                  '分片直连 CDN（原路径是 .png，字节是 MPEG-TS，由本地代理改写 Content-Type）',
                  style: const TextStyle(color: Colors.white38, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
