"""test_pipeline.py — 无界面验证核心处理链路（人脸检测/抠图/换底/保存）。

运行（需在已装好依赖的 venv 中）：
  python test_pipeline.py
"""
import os
import sys
import cv2
import numpy as np

import idcutter_core as core

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "test_output")
os.makedirs(OUT, exist_ok=True)


def make_test_image(path, w=600, h=800):
    """生成一张「合成身份证」测试图：蓝底 + 白色头像方块（模拟头像区域）。"""
    img = np.full((h, w, 3), 67, dtype=np.uint8)
    img[:, :, 1] = 142
    img[:, :, 2] = 219  # 蓝底
    # 在右侧画一个"头像"白块
    x0, y0, fw, fh = int(w * 0.58), int(h * 0.10), int(w * 0.34), int(h * 0.40)
    cv2.rectangle(img, (x0, y0), (x0 + fw, y0 + fh), (235, 235, 235), -1)
    cv2.imwrite(path, img)
    return path


def main():
    print("== 1. 生成测试图 ==")
    test_img = make_test_image(os.path.join(OUT, "id_test.jpg"))
    img = core.load_image(test_img)
    print(f"   载入图片 {img.shape[1]}x{img.shape[0]}")

    print("== 2. 自动定位头像区域 ==")
    rect = core.pick_head_region(img)
    print(f"   区域: {rect}")

    print("== 3. 抠背景（沙箱实测用内置 u2netp；用户默认 u2net_human_seg）==")
    crop = core.crop_region(img, rect)
    rgba = core.remove_background(crop, "u2netp")
    print(f"   抠图结果尺寸 {rgba.size}, 模式 {rgba.mode}")

    # 验证 alpha 通道：应有透明与实心两部分
    alpha = np.array(rgba)[:, :, 3]
    n_trans = int((alpha < 20).sum())
    n_opaque = int((alpha > 200).sum())
    print(f"   透明像素 {n_trans}, 不透明像素 {n_opaque}")
    assert n_trans > 0 and n_opaque > 0, "alpha 通道未正确分离前景/背景"

    print("== 4. 换白底 + 一寸尺寸合成 ==")
    fg = core.crop_to_content(rgba)
    out = core.composite_on_background(fg, "white", core.PHOTO_SIZES["1inch"])
    core.save_result(out, os.path.join(OUT, "id_1inch_white.png"), "white")
    print(f"   已保存一寸白底: {out.size}")

    print("== 5. 透明 PNG 保存 ==")
    core.save_result(rgba, os.path.join(OUT, "id_transparent.png"), "transparent")
    print("   已保存透明 PNG")

    print("\n全部通过 ✅  输出目录:", OUT)


if __name__ == "__main__":
    main()
