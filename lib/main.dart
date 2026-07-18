import 'package:flutter/material.dart';
import 'ui/home_page.dart';

void main() {
  runApp(const IdPhotoApp());
}

class IdPhotoApp extends StatelessWidget {
  const IdPhotoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '身份证头像抠图',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.indigo,
        scaffoldBackgroundColor: Colors.grey.shade100,
      ),
      home: const HomePage(),
    );
  }
}
