把抠图模型放到这个目录
======================

本 App 需要在本地离线运行 rembg 的 u2net 模型，因此必须把模型文件放在这里：

    u2net_human_seg.onnx   （约 176 MB，已内置在你的桌面版里）

获取方式（任选其一）：
1) 复制桌面版里的模型：
   桌面版工程目录 / id-photo-cutter / models / u2net_human_seg.onnx
   → 复制本文件到本目录，改名/保持为 u2net_human_seg.onnx

2) 从本地已经下载过的 rembg 缓存复制（如本地有）：
   Windows: %USERPROFILE%\.u2net\u2net_human_seg.onnx

放置后目录结构应为：
   assets/models/u2net_human_seg.onnx

⚠️ 之后才能执行 `flutter pub get` 与 `flutter build apk`。
   若想用更小的模型（u2netp.onnx 约 4.7MB，速度更快、精度略低），
   请把 u2netp.onnx 放进来，并修改 lib/core/segmenter.dart 中
   MODEL_ASSET 常量为 'assets/models/u2netp.onnx'。
