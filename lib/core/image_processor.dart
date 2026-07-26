import 'dart:typed_data';
import 'package:image/image.dart' as img;

/// 选区矩形（原图像素坐标系，轴对齐，无旋转——旋转由“旋转源图”实现，与桌面版一致）。
class CropRect {
  double cx;
  double cy;
  double w;
  double h;

  CropRect(this.cx, this.cy, this.w, this.h);

  double get left => cx - w / 2;
  double get top => cy - h / 2;
  double get right => cx + w / 2;
  double get bottom => cy + h / 2;

  CropRect clampInto(int width, int height) {
    final w = this.w.clamp(20.0, width.toDouble());
    final h = this.h.clamp(20.0, height.toDouble());
    final cx = this.cx.clamp(w / 2, width - w / 2);
    final cy = this.cy.clamp(h / 2, height - h / 2);
    return CropRect(cx, cy, w, h);
  }
}

/// 处理好的图像：原始 RGBA + 与原始同尺寸的 alpha 蒙版（0..1）。
class ProcessedImage {
  final img.Image original; // RGBA
  final Float32List alpha; // length = width*height，值 0..1
  final int width;
  final int height;

  ProcessedImage(this.original, this.alpha)
      : width = original.width,
        height = original.height;
}

/// 证件照底色模式（白 / 蓝 / 红 / 透明）。
enum BgMode { white, blue, red, transparent }

/// 各底色对应的 RGB（透明用 null 表示）。
const Map<BgMode, (int, int, int)> bgRgb = {
  BgMode.white: (255, 255, 255),
  BgMode.blue: (47, 111, 224),
  BgMode.red: (224, 73, 77),
};

/// 标准证件照尺寸预设（像素，300dpi 常见规格）。
class SizePreset {
  final String name;
  final int w;
  final int h;
  const SizePreset(this.name, this.w, this.h);
}

const List<SizePreset> kSizePresets = [
  SizePreset('一寸', 295, 413),
  SizePreset('二寸', 413, 626),
  SizePreset('标准', 500, 670),
  SizePreset('大一寸', 390, 567),
];

/// 把 320x320 的蒙版双线性上采样到原图尺寸。
Float32List resizeMaskBilinear(Float32List src, int sw, int sh, int dw, int dh) {
  final out = Float32List(dw * dh);
  for (int y = 0; y < dh; y++) {
    final sy = (y + 0.5) * sh / dh - 0.5;
    int y0 = sy.floor();
    int y1 = y0 + 1;
    final ty = sy - y0;
    y0 = y0.clamp(0, sh - 1);
    y1 = y1.clamp(0, sh - 1);
    for (int x = 0; x < dw; x++) {
      final sx = (x + 0.5) * sw / dw - 0.5;
      int x0 = sx.floor();
      int x1 = x0 + 1;
      final tx = sx - x0;
      x0 = x0.clamp(0, sw - 1);
      x1 = x1.clamp(0, sw - 1);
      final v00 = src[y0 * sw + x0];
      final v01 = src[y0 * sw + x1];
      final v10 = src[y1 * sw + x0];
      final v11 = src[y1 * sw + x1];
      final top = v00 + (v01 - v00) * tx;
      final bot = v10 + (v11 - v10) * tx;
      out[y * dw + x] = top + (bot - top) * ty;
    }
  }
  return out;
}

/// 根据 320 蒙版估出人像外接框（原图像素坐标），带 padding。
CropRect computePersonBBox(Float32List mask320, int origW, int origH,
    {double pad = 0.18}) {
  const int s = 320;
  int minX = s, minY = s, maxX = -1, maxY = -1;
  for (int y = 0; y < s; y++) {
    for (int x = 0; x < s; x++) {
      if (mask320[y * s + x] > 0.5) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }
  if (maxX < 0) {
    // 兜底：整图中心 80%
    return CropRect(origW / 2, origH / 2, origW * 0.8, origH * 0.8);
  }
  final cx = (minX + maxX) / 2 / s * origW;
  final cy = (minY + maxY) / 2 / s * origH;
  final w = (maxX - minX) / s * origW * (1 + 2 * pad);
  final h = (maxY - minY) / s * origH * (1 + 2 * pad);
  return CropRect(cx, cy, w, h).clampInto(origW, origH);
}

/// 若原图为竖向（高>宽）则逆时针旋转 90° 变成横向长方形，与桌面版一致。
ProcessedImage orientLandscape(ProcessedImage p) {
  if (p.height <= p.width) return p;
  return rotateCCW(p);
}

/// 逆时针旋转 90°（原 (px,py) -> 新 (py, W-1-px)）。
ProcessedImage rotateCCW(ProcessedImage p) {
  final ow = p.width, oh = p.height;
  final nw = oh, nh = ow;
  final out = img.Image(width: nw, height: nh);
  final aOut = Float32List(nw * nh);
  for (int y = 0; y < nh; y++) {
    for (int x = 0; x < nw; x++) {
      final px = ow - 1 - y;
      final py = x;
      final c = p.original.getPixelSafe(px, py);
      out.setPixel(x, y, img.ColorRgba8(c.r.toInt(), c.g.toInt(), c.b.toInt(), c.a.toInt()));
      aOut[y * nw + x] = p.alpha[py * ow + px];
    }
  }
  return ProcessedImage(out, aOut);
}

/// 顺时针旋转 90°（原 (px,py) -> 新 (H-1-py, px)）。
ProcessedImage rotateCW(ProcessedImage p) {
  final ow = p.width, oh = p.height;
  final nw = oh, nh = ow;
  final out = img.Image(width: nw, height: nh);
  final aOut = Float32List(nw * nh);
  for (int y = 0; y < nh; y++) {
    for (int x = 0; x < nw; x++) {
      final px = y;
      final py = oh - 1 - x;
      final c = p.original.getPixelSafe(px, py);
      out.setPixel(x, y, img.ColorRgba8(c.r.toInt(), c.g.toInt(), c.b.toInt(), c.a.toInt()));
      aOut[y * nw + x] = p.alpha[py * ow + px];
    }
  }
  return ProcessedImage(out, aOut);
}

/// 选区随源图逆时针旋转 90°（与 rotateCCW 的像素映射一致）。
/// 旋转后新图尺寸为 (oldH, oldW)。
CropRect rotateCropCCW(CropRect c, int oldW, int oldH) {
  return CropRect(c.cy, oldW - 1 - c.cx, c.h, c.w).clampInto(oldH, oldW);
}

/// 选区随源图顺时针旋转 90°（与 rotateCW 的像素映射一致）。
/// 旋转后新图尺寸为 (oldH, oldW)。
CropRect rotateCropCW(CropRect c, int oldW, int oldH) {
  return CropRect(oldH - 1 - c.cy, c.cx, c.h, c.w).clampInto(oldH, oldW);
}

/// 双线性采样原图的 RGBA + alpha（越界返回透明）。
img.Color sampleRgba(ProcessedImage p, double fx, double fy) {
  final W = p.width, H = p.height;
  if (fx < 0 || fy < 0 || fx > W - 1 || fy > H - 1) {
    return img.ColorRgba8(0, 0, 0, 0);
  }
  final x0 = fx.floor();
  final y0 = fy.floor();
  final x1 = (x0 + 1).clamp(0, W - 1);
  final y1 = (y0 + 1).clamp(0, H - 1);
  final tx = fx - x0;
  final ty = fy - y0;

  final c00 = p.original.getPixelSafe(x0, y0);
  final c01 = p.original.getPixelSafe(x1, y0);
  final c10 = p.original.getPixelSafe(x0, y1);
  final c11 = p.original.getPixelSafe(x1, y1);
  final a00 = p.alpha[y0 * W + x0];
  final a01 = p.alpha[y0 * W + x1];
  final a10 = p.alpha[y1 * W + x0];
  final a11 = p.alpha[y1 * W + x1];

  int lerp(num a, num b, double t) => (a + (b - a) * t).round().clamp(0, 255);
  double lerpa(double a, double b, double t) => a + (b - a) * t;

  final r = lerp(lerp(c00.r, c01.r, tx), lerp(c10.r, c11.r, tx), ty);
  final g = lerp(lerp(c00.g, c01.g, tx), lerp(c10.g, c11.g, tx), ty);
  final b = lerp(lerp(c00.b, c01.b, tx), lerp(c10.b, c11.b, tx), ty);
  final a = lerpa(lerpa(a00, a01, tx), lerpa(a10, a11, tx), ty);
  return img.ColorRgba8(r, g, b, (a * 255).round().clamp(0, 255));
}

/// 导出标准证件照：把选区拉伸到 outW×outH，合成到底色（白/蓝/红/透明）。
/// 与桌面版 stretch_to_size 行为一致——无论选区多大都强制拉伸到目标尺寸。
img.Image exportIdPhoto(
  ProcessedImage p,
  CropRect crop, {
  BgMode bg = BgMode.white,
  int outW = 500,
  int outH = 670,
}) {
  final out = img.Image(width: outW, height: outH);
  final solid = bg != BgMode.transparent ? bgRgb[bg]! : null;
  for (int v = 0; v < outH; v++) {
    for (int u = 0; u < outW; u++) {
      // 输出像素 -> 选区归一化中心坐标 (-0.5..0.5)
      final nx = (u / outW - 0.5) * crop.w;
      final ny = (v / outH - 0.5) * crop.h;
      // 映射到原图坐标
      final sx = crop.cx + nx;
      final sy = crop.cy + ny;
      final c = sampleRgba(p, sx, sy);
      final a = (c.a / 255.0).clamp(0.0, 1.0); // 蒙版 alpha
      int r, g, b, outA;
      if (solid != null) {
        r = (c.r * a + solid.$1 * (1 - a)).round().clamp(0, 255);
        g = (c.g * a + solid.$2 * (1 - a)).round().clamp(0, 255);
        b = (c.b * a + solid.$3 * (1 - a)).round().clamp(0, 255);
        outA = 255;
      } else {
        r = c.r.toInt();
        g = c.g.toInt();
        b = c.b.toInt();
        outA = (a * 255).round().clamp(0, 255);
      }
      out.setPixel(u, v, img.ColorRgba8(r, g, b, outA));
    }
  }
  return out;
}
