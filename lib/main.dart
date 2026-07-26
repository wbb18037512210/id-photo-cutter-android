import 'package:flutter/material.dart';
import 'theme/app_theme.dart';
import 'ui/home_page.dart';

void main() {
  runApp(const IdPhotoApp());
}

class IdPhotoApp extends StatelessWidget {
  const IdPhotoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '证件照工作室',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.system,
      home: const HomePage(),
    );
  }
}
