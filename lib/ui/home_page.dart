import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'editor_page.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  Future<void> _pick(ImageSource source, BuildContext context) async {
    final picker = ImagePicker();
    final xfile = await picker.pickImage(
      source: source,
      imageQuality: 100,
    );
    if (xfile == null) return;
    final bytes = await xfile.readAsBytes();
    if (!context.mounted) return;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => EditorPage(originalBytes: bytes),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('身份证头像抠图')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.account_box_rounded,
                  size: 96, color: Colors.indigo),
              const SizedBox(height: 16),
              const Text('本地离线 · 不上传服务器',
                  style: TextStyle(fontSize: 16, color: Colors.grey)),
              const SizedBox(height: 32),
              FilledButton.icon(
                icon: const Icon(Icons.photo_library),
                label: const Text('从相册选择'),
                onPressed: () => _pick(ImageSource.gallery, context),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                icon: const Icon(Icons.camera_alt),
                label: const Text('拍照'),
                onPressed: () => _pick(ImageSource.camera, context),
              ),
              const SizedBox(height: 24),
              const Text(
                '打开图片后自动抠图、自动校正方向，\n可拖动/缩放选区，结果保存为 500×670 白底。',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
