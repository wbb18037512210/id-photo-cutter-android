import 'dart:typed_data';
import 'package:flutter_onnxruntime/flutter_onnxruntime.dart';
import 'package:image/image.dart' as img;

/// 本地离线加载 rembg 的 u2net 系列模型，输出 320x320 的人像 alpha 蒙版。
///
/// 与桌面版 rembg 默认行为对齐：
///  - 输入归一化：img/255，再按 ImageNet 均值/标准差归一化
///  - 输入尺寸固定 320x320（拉伸）
///  - 模型输出已含 sigmoid，直接当作 alpha（0..1）
class Segmenter {
  /// 模型资源路径（与 pubspec.yaml 中 assets 保持一致）。
  /// 想换更小更快的 u2netp.onnx 时改这里。
  static const String modelAsset = 'assets/models/u2net_human_seg.onnx';

  static const int modelSize = 320;

  OrtSession? _session;
  String _inputName = 'input.1';
  String _outputName = 'output.1';

  bool get isLoaded => _session != null;

  /// 从 Flutter assets 加载模型。只调用一次即可复用。
  Future<void> load() async {
    if (_session != null) return;
    final ort = OnnxRuntime();
    _session = await ort.createSessionFromAsset(modelAsset);
    if (_session!.inputNames.isNotEmpty) _inputName = _session!.inputNames[0];
    if (_session!.outputNames.isNotEmpty) _outputName = _session!.outputNames[0];
  }

  /// 对一张图推理，返回 320x320 的 float alpha 蒙版（值 0..1）。
  Future<Float32List> predictMask(img.Image image) async {
    if (_session == null) await load();

    // 1) 拉伸到 320x320
    final resized = img.copyResize(
      image,
      width: modelSize,
      height: modelSize,
      interpolation: img.Interpolation.linear,
    );

    // 2) 归一化到 NCHW float32
    final input = Float32List(1 * 3 * modelSize * modelSize);
    int i = 0;
    const mean = [0.485, 0.456, 0.406];
    const std = [0.229, 0.224, 0.225];
    for (int y = 0; y < modelSize; y++) {
      for (int x = 0; x < modelSize; x++) {
        final p = resized.getPixel(x, y);
        input[i++] = (p.r / 255.0 - mean[0]) / std[0];
        input[i++] = (p.g / 255.0 - mean[1]) / std[1];
        input[i++] = (p.b / 255.0 - mean[2]) / std[2];
      }
    }

    final inputTensor =
        await OrtValue.fromList(input, [1, 3, modelSize, modelSize]);
    final outputs = await _session!.run({_inputName: inputTensor});
    await inputTensor.dispose();

    final outTensor = outputs[_outputName]!;
    final flat = await outTensor.asFlattenedList();
    for (final t in outputs.values) {
      await t.dispose();
    }

    // 输出形状 [1,1,320,320]，扁平化后索引 = y*320 + x
    final mask = Float32List(modelSize * modelSize);
    for (int k = 0; k < mask.length; k++) {
      mask[k] = (flat[k] as num).toDouble().clamp(0.0, 1.0);
    }
    return mask;
  }

  void dispose() {
    _session?.close();
    _session = null;
  }
}
