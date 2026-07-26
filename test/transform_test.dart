import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:id_photo_cutter/core/image_processor.dart';

/// 构造一张测试图：背景全黑 alpha=0（透明），putBlock 时在左上角放一个 20x20 红块（alpha=1）。
ProcessedImage makeImage(int w, int h, {bool putBlock = false}) {
  final im = img.Image(width: w, height: h);
  final alpha = Float32List(w * h);
  for (int y = 0; y < h; y++) {
    for (int x = 0; x < w; x++) {
      im.setPixel(x, y, img.ColorRgba8(0, 0, 0, 255));
      alpha[y * w + x] = 0.0; // 背景透明
    }
  }
  if (putBlock) {
    for (int y = 10; y < 30; y++) {
      for (int x = 10; x < 30; x++) {
        im.setPixel(x, y, img.ColorRgba8(255, 0, 0, 255));
        alpha[y * w + x] = 1.0;
      }
    }
  }
  return ProcessedImage(im, alpha);
}

int countRed(img.Image out) {
  int c = 0;
  for (int y = 0; y < out.height; y++) {
    for (int x = 0; x < out.width; x++) {
      final p = out.getPixel(x, y);
      if (p.r > 200 && p.g < 60 && p.b < 60) c++;
    }
  }
  return c;
}

void main() {
  test('正向映射：整图选区保持红块面积比例', () {
    final p = makeImage(200, 100, putBlock: true);
    final crop = CropRect(100, 50, 200, 100); // 整图
    final out = exportIdPhoto(p, crop, bg: BgMode.transparent);
    final red = countRed(out);
    // 源红块 400 / 20000，拉伸后应保持相同面积比例
    final expected = 400.0 / 20000.0 * out.width * out.height;
    expect((red - expected).abs() / expected, lessThan(0.05));
  });

  test('正向映射：红块出现在预期输出坐标', () {
    final p = makeImage(200, 100, putBlock: true);
    final crop = CropRect(100, 50, 200, 100);
    final out = exportIdPhoto(p, crop, bg: BgMode.transparent);
    // 源 (20,20) -> 输出约 (50,134)
    final c = out.getPixel(50, 134);
    expect(c.r, greaterThan(200));
    expect(c.g, lessThan(60));
  });

  test('rotateCCW 坐标映射：旋转后红块位置正确', () {
    final p0 = makeImage(200, 100, putBlock: true);
    final p = rotateCCW(p0); // 新图 100x200
    // 红块旧中心 (20,20) -> 新中心 (20, 179)
    final crop = CropRect(50, 100, 100, 200);
    final out = exportIdPhoto(p, crop, bg: BgMode.transparent);
    // 新 (20,179) -> 输出约 (100,600)
    final c = out.getPixel(100, 600);
    expect(c.r, greaterThan(200));
    expect(c.g, lessThan(60));
  });

  test('白底合成：非红区域应为白色而非黑色', () {
    final p = makeImage(200, 100, putBlock: true);
    final crop = CropRect(100, 50, 200, 100);
    final out = exportIdPhoto(p, crop, bg: BgMode.white);
    // 背景区域应为白
    final bg = out.getPixel(490, 660);
    expect(bg.r, greaterThan(240));
    expect(bg.g, greaterThan(240));
    expect(bg.b, greaterThan(240));
  });

  test('rotateCropCCW 中心映射公式', () {
    final c = CropRect(40, 30, 20, 20); // 小选区，避免被 clamp
    final r = rotateCropCCW(c, 200, 100);
    expect(r.cx, closeTo(30, 0.001)); // = c.cy
    expect(r.cy, closeTo(159, 0.001)); // = ow-1-c.cx = 199-40
    expect(r.w, closeTo(20, 0.001)); // = c.h
    expect(r.h, closeTo(20, 0.001)); // = c.w
  });

  test('rotateCropCW 中心映射公式', () {
    final c = CropRect(40, 30, 20, 20);
    final r = rotateCropCW(c, 200, 100);
    expect(r.cx, closeTo(69, 0.001)); // = oh-1-c.cy = 99-30
    expect(r.cy, closeTo(40, 0.001)); // = c.cx
    expect(r.w, closeTo(20, 0.001));
    expect(r.h, closeTo(20, 0.001));
  });

  test('集成：图片与选区一起顺时针旋转，红块落点正确', () {
    final p0 = makeImage(200, 100, putBlock: true);
    final pCW = rotateCW(p0); // 100x200
    final crop = rotateCropCW(CropRect(100, 50, 200, 100), 200, 100); // 整图
    final out = exportIdPhoto(pCW, crop, bg: BgMode.transparent);
    // 旧红块中心 (20,20) -> 顺时针后新中心 (79,20) -> 输出约 (395,67)
    final c = out.getPixel(395, 67);
    expect(c.r, greaterThan(200));
    expect(c.g, lessThan(60));
  });

  test('集成：图片与选区一起逆时针旋转，红块落点正确', () {
    final p0 = makeImage(200, 100, putBlock: true);
    final pCCW = rotateCCW(p0); // 100x200
    final crop = rotateCropCCW(CropRect(100, 50, 200, 100), 200, 100); // 整图
    final out = exportIdPhoto(pCCW, crop, bg: BgMode.transparent);
    // 旧红块中心 (20,20) -> 逆时针后新中心 (20,179) -> 输出约 (100,600)
    final c = out.getPixel(100, 600);
    expect(c.r, greaterThan(200));
    expect(c.g, lessThan(60));
  });
}
