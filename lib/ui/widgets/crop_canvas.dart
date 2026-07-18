import 'dart:typed_data';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../core/image_processor.dart';

/// 可交互选区画布：显示原图，允许拖动移动选区、拖四角缩放选区。
/// 旋转由工具栏“旋转源图”完成（与桌面版一致，选区本身保持轴对齐）。
class CropCanvas extends StatefulWidget {
  final ProcessedImage image;
  final Uint8List displayBytes; // 原图编码后的 PNG，用于显示
  final CropRect crop;
  final ValueChanged<CropRect> onChanged;

  const CropCanvas({
    super.key,
    required this.image,
    required this.displayBytes,
    required this.crop,
    required this.onChanged,
  });

  @override
  State<CropCanvas> createState() => _CropCanvasState();
}

class _CropCanvasState extends State<CropCanvas> {
  double _scale = 1;
  double _ox = 0, _oy = 0;

  // 手势状态
  _DragMode _mode = _DragMode.none;
  late CropRect _startCrop;
  Offset _startLocal = Offset.zero;
  Offset _anchor = Offset.zero; // 缩放时固定的对角点（图像坐标）

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final boxW = constraints.maxWidth;
        final boxH = constraints.maxHeight;
        final iw = widget.image.width.toDouble();
        final ih = widget.image.height.toDouble();
        _scale = math.min(boxW / iw, boxH / ih);
        final dispW = iw * _scale;
        final dispH = ih * _scale;
        _ox = (boxW - dispW) / 2;
        _oy = (boxH - dispH) / 2;

        final cropRect = Rect.fromLTWH(
          _ox + widget.crop.left * _scale,
          _oy + widget.crop.top * _scale,
          widget.crop.w * _scale,
          widget.crop.h * _scale,
        );

        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onPanStart: (d) => _onStart(d.localPosition, cropRect),
          onPanUpdate: (d) => _onUpdate(d.localPosition),
          onPanEnd: (_) => setState(() => _mode = _DragMode.none),
          child: SizedBox(
            width: boxW,
            height: boxH,
            child: Stack(
              children: [
                Positioned.fill(
                  child: Image.memory(
                    widget.displayBytes,
                    fit: BoxFit.contain,
                  ),
                ),
                CustomPaint(
                  size: Size(boxW, boxH),
                  painter: _OverlayPainter(cropRect: cropRect),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Offset _toImage(Offset local) =>
      Offset((local.dx - _ox) / _scale, (local.dy - _oy) / _scale);

  void _onStart(Offset local, Rect cropRect) {
    _startCrop = CropRect(widget.crop.cx, widget.crop.cy, widget.crop.w,
        widget.crop.h);
    _startLocal = local;

    // 命中四角？
    const hit = 26.0;
    final corners = <_Corner, Offset>{
      _Corner.tl: Offset(cropRect.left, cropRect.top),
      _Corner.tr: Offset(cropRect.right, cropRect.top),
      _Corner.bl: Offset(cropRect.left, cropRect.bottom),
      _Corner.br: Offset(cropRect.right, cropRect.bottom),
    };
    for (final e in corners.entries) {
      if ((local - e.value).distance <= hit) {
        // 固定对角点（图像坐标）
        final fixed = _oppositeCorner(e.key, _startCrop);
        _anchor = Offset(fixed.cx, fixed.cy);
        setState(() => _mode = _DragMode.resize);
        return;
      }
    }

    // 在选区内 -> 移动
    if (cropRect.contains(local)) {
      setState(() => _mode = _DragMode.move);
    } else {
      setState(() => _mode = _DragMode.none);
    }
  }

  void _onUpdate(Offset local) {
    if (_mode == _DragMode.none) return;
    if (_mode == _DragMode.move) {
      final dImg = (local - _startLocal) / _scale;
      final next = CropRect(
        (_startCrop.cx + dImg.dx)
            .clamp(10.0, (widget.image.width - 10).toDouble()),
        (_startCrop.cy + dImg.dy)
            .clamp(10.0, (widget.image.height - 10).toDouble()),
        _startCrop.w,
        _startCrop.h,
      ).clampInto(widget.image.width, widget.image.height);
      widget.onChanged(next);
    } else if (_mode == _DragMode.resize) {
      final cur = _toImage(local);
      final x1 = math.min(_anchor.dx, cur.dx);
      final x2 = math.max(_anchor.dx, cur.dx);
      final y1 = math.min(_anchor.dy, cur.dy);
      final y2 = math.max(_anchor.dy, cur.dy);
      final next = CropRect(
        (x1 + x2) / 2,
        (y1 + y2) / 2,
        math.max(x2 - x1, 20.0),
        math.max(y2 - y1, 20.0),
      ).clampInto(widget.image.width, widget.image.height);
      widget.onChanged(next);
    }
  }

  CropRect _oppositeCorner(_Corner c, CropRect r) {
    switch (c) {
      case _Corner.tl:
        return CropRect(r.right, r.bottom, 0, 0);
      case _Corner.tr:
        return CropRect(r.left, r.bottom, 0, 0);
      case _Corner.bl:
        return CropRect(r.right, r.top, 0, 0);
      case _Corner.br:
        return CropRect(r.left, r.top, 0, 0);
    }
  }
}

enum _DragMode { none, move, resize }
enum _Corner { tl, tr, bl, br }

class _OverlayPainter extends CustomPainter {
  final Rect cropRect;
  _OverlayPainter({required this.cropRect});

  @override
  void paint(Canvas canvas, Size size) {
    // 选区外变暗
    final dim = Paint()..color = Colors.black.withOpacity(0.55);
    final path = Path()
      ..addRect(Rect.fromLTWH(0, 0, size.width, size.height))
      ..addRect(cropRect)
      ..fillType = PathFillType.evenOdd;
    canvas.drawPath(path, dim);

    // 选区边框
    canvas.drawRect(
      cropRect,
      Paint()
        ..color = Colors.white
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );

    // 三分线
    final line = Paint()
      ..color = Colors.white.withOpacity(0.5)
      ..strokeWidth = 1;
    for (int i = 1; i <= 2; i++) {
      final fx = cropRect.left + cropRect.width * i / 3;
      final fy = cropRect.top + cropRect.height * i / 3;
      canvas.drawLine(Offset(fx, cropRect.top), Offset(fx, cropRect.bottom), line);
      canvas.drawLine(Offset(cropRect.left, fy), Offset(cropRect.right, fy), line);
    }

    // 四角把手
    final handle = Paint()..color = Colors.white;
    const r = 7.0;
    for (final p in [
      Offset(cropRect.left, cropRect.top),
      Offset(cropRect.right, cropRect.top),
      Offset(cropRect.left, cropRect.bottom),
      Offset(cropRect.right, cropRect.bottom),
    ]) {
      canvas.drawCircle(p, r, handle);
    }
  }

  @override
  bool shouldRepaint(covariant _OverlayPainter old) =>
      old.cropRect != cropRect;
}
