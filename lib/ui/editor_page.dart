import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;
import 'package:image_gallery_saver/image_gallery_saver.dart';
import '../core/segmenter.dart';
import '../core/image_processor.dart';
import 'widgets/crop_canvas.dart';

class EditorPage extends StatefulWidget {
  final Uint8List originalBytes;
  const EditorPage({super.key, required this.originalBytes});

  @override
  State<EditorPage> createState() => _EditorPageState();
}

class _EditorPageState extends State<EditorPage> {
  final Segmenter _segmenter = Segmenter();
  ProcessedImage? _p;
  CropRect _crop = CropRect(0, 0, 1, 1);
  bool _whiteBg = true;
  Uint8List? _displayBytes;
  Uint8List? _previewBytes;
  bool _loading = true;
  bool _busy = false;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      final decoded = img.decodeImage(widget.originalBytes);
      if (decoded == null) throw Exception('无法解码图片');

      final alpha = Float32List(decoded.width * decoded.height);
      alpha.fillRange(0, alpha.length, 1.0);
      _p = ProcessedImage(decoded, alpha);
      _p = orientLandscape(_p!);
      await _segmenter.load();
      await _redetectInternal();
      _refreshDisplay();
      if (mounted) setState(() => _loading = false);
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = '初始化失败：$e';
        });
      }
    }
  }

  /// 重新推理蒙版并计算人像选区（不旋转源图）。
  Future<void> _redetectInternal() async {
    final mask = await _segmenter.predictMask(_p!.original);
    final up = resizeMaskBilinear(mask, 320, 320, _p!.width, _p!.height);
    // 用新蒙版覆盖 alpha
    _p = ProcessedImage(_p!.original, up);
    _crop = computePersonBBox(mask, _p!.width, _p!.height);
    _computePreview();
  }

  Future<void> _redetect() async {
    if (_busy || _p == null) return;
    setState(() => _busy = true);
    try {
      await _redetectInternal();
      _refreshDisplay();
    } catch (e) {
      _showMsg('重新检测失败：$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _refreshDisplay() {
    if (_p == null) return;
    _displayBytes = img.encodePng(_p!.original);
    _computePreview();
    if (mounted) setState(() {});
  }

  void _computePreview() {
    if (_p == null) return;
    final out = exportIdPhoto(_p!, _crop, whiteBg: _whiteBg, outW: 250, outH: 335);
    _previewBytes = img.encodePng(out);
  }

  void _onCropChanged(CropRect next) {
    _crop = next;
    _computePreview();
    if (mounted) setState(() {});
  }

  void _rotateSource(bool ccw) {
    if (_busy || _p == null) return;
    final old = _p!;
    final ow = old.width;
    final oh = old.height;
    _p = ccw ? rotateCCW(old) : rotateCW(old);
    // 选区随源图一起旋转（90°：中心映射 + 宽高互换）
    _crop = ccw
        ? rotateCropCCW(_crop, ow, oh)
        : rotateCropCW(_crop, ow, oh);
    _refreshDisplay();
  }

  Future<void> _save() async {
    if (_busy || _p == null) return;
    setState(() => _busy = true);
    try {
      final out = exportIdPhoto(_p!, _crop, whiteBg: _whiteBg);
      final png = img.encodePng(out);
      final ts = DateTime.now();
      final name =
          '头像_${ts.year}${_pad(ts.month)}${_pad(ts.day)}_${_pad(ts.hour)}${_pad(ts.minute)}${_pad(ts.second)}';
      final res = await ImageGallerySaver.saveImage(
        Uint8List.fromList(png),
        quality: 100,
        name: name,
      );
      final ok = res is Map && (res['isSuccess'] == true || res['errorMessage'] == null);
      _showMsg(ok ? '已保存到相册：$name' : '保存失败：$res');
    } catch (e) {
      _showMsg('保存失败：$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _showMsg(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  String _pad(int n) => n.toString().padLeft(2, '0');

  @override
  void dispose() {
    _segmenter.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('编辑头像'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: '重新检测人像',
            onPressed: _busy ? null : _redetect,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error.isNotEmpty
              ? Center(child: Text(_error, style: const TextStyle(color: Colors.red)))
              : Column(
                  children: [
                    Expanded(
                      child: _p == null || _displayBytes == null
                          ? const SizedBox.shrink()
                          : CropCanvas(
                              image: _p!,
                              displayBytes: _displayBytes!,
                              crop: _crop,
                              onChanged: _onCropChanged,
                            ),
                    ),
                    _buildToolbar(),
                  ],
                ),
    );
  }

  Widget _buildToolbar() {
    return Container(
      color: Theme.of(context).colorScheme.surface,
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
      child: Column(
        children: [
          Row(
            children: [
              // 预览
              Container(
                width: 50,
                height: 67,
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey),
                  color: _whiteBg ? Colors.white : Colors.grey.shade300,
                ),
                child: _previewBytes != null
                    ? Image.memory(_previewBytes!, fit: BoxFit.contain)
                    : null,
              ),
              const SizedBox(width: 12),
              const Text('500 × 670', style: TextStyle(fontWeight: FontWeight.bold)),
              const Spacer(),
              // 底色切换
              SegmentedButton<bool>(
                segments: const [
                  ButtonSegment(value: true, label: Text('白底')),
                  ButtonSegment(value: false, label: Text('透明')),
                ],
                selected: {_whiteBg},
                onSelectionChanged: (s) {
                  _whiteBg = s.first;
                  _computePreview();
                  setState(() {});
                },
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              IconButton.filledTonal(
                icon: const Icon(Icons.rotate_left),
                tooltip: '向左旋转 90°',
                onPressed: _busy ? null : () => _rotateSource(true),
              ),
              IconButton.filledTonal(
                icon: const Icon(Icons.rotate_right),
                tooltip: '向右旋转 90°',
                onPressed: _busy ? null : () => _rotateSource(false),
              ),
              IconButton.filledTonal(
                icon: const Icon(Icons.zoom_out),
                tooltip: '缩小选区',
                onPressed: _busy ? null : () => _zoomCrop(0.9),
              ),
              IconButton.filledTonal(
                icon: const Icon(Icons.zoom_in),
                tooltip: '放大选区',
                onPressed: _busy ? null : () => _zoomCrop(1.1),
              ),
              FilledButton.icon(
                icon: _busy
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.save),
                label: const Text('保存'),
                onPressed: _busy ? null : _save,
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _zoomCrop(double factor) {
    if (_p == null) return;
    final next = CropRect(
      _crop.cx,
      _crop.cy,
      (_crop.w * factor).clamp(20.0, _p!.width.toDouble()),
      (_crop.h * factor).clamp(20.0, _p!.height.toDouble()),
    ).clampInto(_p!.width, _p!.height);
    _onCropChanged(next);
  }
}
