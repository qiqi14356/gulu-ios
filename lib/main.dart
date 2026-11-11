import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';

import 'pages/home_page.dart';
import 'pages/probe_page.dart';

void main() => runApp(const GuluApp());

class GuluApp extends StatelessWidget {
  const GuluApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '咕噜咕噜',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF7C4DFF),
          brightness: Brightness.dark,
        ),
        scaffoldBackgroundColor: const Color(0xFF0E0E12),
      ),
      home: const RootShell(),
    );
  }
}

/// 发布构建只有主页；`接口探测`是开发期用来核对 libapp.so 里静态提取的路径的，
/// 真机上没必要出现，而且它会打 `AppConfig.apiBase` 这个还不知道的地址。
class RootShell extends StatefulWidget {
  const RootShell({super.key});

  @override
  State<RootShell> createState() => _RootShellState();
}

class _RootShellState extends State<RootShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    if (!kDebugMode) {
      return const Scaffold(body: SafeArea(child: HomePage()));
    }
    return Scaffold(
      body: SafeArea(
        child: IndexedStack(
          index: _index,
          children: const <Widget>[HomePage(), ProbePage()],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (int i) => setState(() => _index = i),
        destinations: const <NavigationDestination>[
          NavigationDestination(icon: Icon(Icons.movie_outlined), label: '片库'),
          NavigationDestination(icon: Icon(Icons.wifi_tethering), label: '接口探测'),
        ],
      ),
    );
  }
}
