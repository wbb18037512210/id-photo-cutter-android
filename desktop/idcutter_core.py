"""
idcutter_core.py — 身份证头像抠图核心逻辑（完全本地处理，照片不上传任何服务器）

依赖：rembg / onnxruntime / opencv-python-headless / pillow / numpy
"""
import os
import cv2
import numpy as np
from PIL import Image
# 懒加载 rembg，避免未安装/未使用时硬依赖

# rembg 2.x：U2NET_HOME 即模型目录本身（默认 ~/.u2net）。
_MODEL_DIR = os.path.expanduser(
    os.getenv("U2NET_HOME", os.path.join(os.getenv("XDG_DATA_HOME", "~"), ".u2net"))
)
os.makedirs(_MODEL_DIR, exist_ok=True)

# 常用证件照底色 (R, G, B)
BG_COLORS = {
    "white": (255, 255, 255),
    "blue": (67, 142, 219),   # 标准证件照蓝底
    "red": (255, 0, 0),       # 标准证件照红底
}

# 常用证件照尺寸 (宽, 高) 单位:像素
PHOTO_SIZES = {
    "origin": None,
    "500x670": (500, 670),    # 标准输出尺寸
}


def load_image(path):
    """读取图片为 BGR numpy 数组（OpenCV 默认格式）。支持中文路径。"""
    # cv2.imread 在 Windows 上不支持中文/非 ANSI 路径，改用文件字节 + imdecode
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"无法读取图片: {path}")
    return img


def detect_faces(image_bgr):
    """用 Haar 级联检测人脸（需 OpenCV <= 4.x）。返回 [(x, y, w, h), ...]。"""
    try:
        if not (hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data")
                and hasattr(cv2.data, "haarcascades")):
            return []
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        if not os.path.exists(cascade_path):
            return []
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            return []
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        return [tuple(int(v) for v in f) for f in faces]
    except Exception:
        return []


def default_id_region(image_bgr):
    """中国二代身份证默认照片区域（照片位于右上区域）。

    横版（标准扫描 w>=h）：取右侧约 60%~96% 宽、顶部 6%~40% 高。
    竖版（可能已是头像照）：取居中大部分。
    """
    h, w = image_bgr.shape[:2]
    if w >= h:
        x0, x1 = int(w * 0.57), int(w * 0.98)
        y0, y1 = int(h * 0.04), int(h * 0.44)
    else:
        x0, x1 = int(w * 0.06), int(w * 0.94)
        y0, y1 = int(h * 0.03), int(h * 0.95)
    return (x0, y0, x1 - x0, y1 - y0)


def pick_head_region(image_bgr):
    """自动定位头像区域：优先人脸检测，失败则使用标准身份证区域。返回 (x, y, w, h)。"""
    faces = detect_faces(image_bgr)
    h, w = image_bgr.shape[:2]
    if len(faces) == 0:
        return default_id_region(image_bgr)
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])  # 取最大人脸
    # 外扩：左右各 25%，上方多留头部空间
    pad_x = int(fw * 0.25)
    pad_y_top = int(fh * 0.35)
    pad_y_bot = int(fh * 0.20)
    nx = max(0, x - pad_x)
    ny = max(0, y - pad_y_top)
    nw = min(w - nx, fw + 2 * pad_x)
    nh = min(h - ny, fh + pad_y_top + pad_y_bot)
    return (nx, ny, nw, nh)


def orient_landscape(image_bgr, rect):
    """若图片为竖向（高>宽），逆时针旋转 90° 变为横向长方形，并同步映射 rect。
    返回 (new_image, new_rect)；若已是横向则原样返回。

    映射关系：cv2.rotate(ROTATE_90_COUNTERCLOCKWISE) 把原图点 (px, py)
    映射到新图 (py, w - 1 - px)。按矩形左上角/尺寸表示，新矩形为：
        (y, w - x - rw, rh, rw)
    """
    h, w = image_bgr.shape[:2]
    if h <= w:
        return image_bgr, rect
    rot = cv2.rotate(image_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if rect is None:
        return rot, None
    x, y, rw, rh = rect
    nx = y
    ny = w - x - rw
    new_w = rh
    new_h = rw
    # 限制在新图范围内，防止切片越界得到空图
    H, W = rot.shape[:2]
    nx = max(0, min(nx, W - 1))
    ny = max(0, min(ny, H - 1))
    new_w = max(1, min(new_w, W - nx))
    new_h = max(1, min(new_h, H - ny))
    return rot, (nx, ny, new_w, new_h)


def rotate_image_and_rect(image_bgr, rect, clockwise):
    """将图片旋转 90°（clockwise=True 顺时针 / False 逆时针），并同步映射 rect。
    无论原图横竖都会旋转。返回 (new_image, new_rect)。"""
    h, w = image_bgr.shape[:2]
    if clockwise:
        rot = cv2.rotate(image_bgr, cv2.ROTATE_90_CLOCKWISE)
        # 原图点 (px, py) -> 新图 (h-1-py, px)
        def mp(px, py):
            return (h - 1 - py, px)
    else:
        rot = cv2.rotate(image_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
        # 原图点 (px, py) -> 新图 (py, w-1-px)
        def mp(px, py):
            return (py, w - 1 - px)
    if rect is None:
        return rot, None
    x, y, rw, rh = rect
    x1, y1 = x + rw, y + rh
    pts = [mp(x, y), mp(x1, y), mp(x, y1), mp(x1, y1)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    nx0, ny0 = min(xs), min(ys)
    nw, nh = max(xs) - nx0, max(ys) - ny0
    # 限制在新图范围内，防越界切片得到空图
    Hn, Wn = rot.shape[:2]
    nx0 = max(0, min(nx0, Wn - 1))
    ny0 = max(0, min(ny0, Hn - 1))
    nw = max(1, min(nw, Wn - nx0))
    nh = max(1, min(nh, Hn - ny0))
    return rot, (nx0, ny0, nw, nh)


def detect_person_bbox(image_bgr, model_name="u2netp", padding_ratio=0.18, max_size=1024):
    """对身份证照片进行 rembg 分割，定位人像边界框（含 padding）的 (x, y, w, h)。

    策略：先在身份证右上角的大范围搜索区域（横版图右侧、竖版图居中）内分割，
    这样不容易把整张身份证误当成前景。若未检测到人像，再回退到全图分割。
    """
    def _bbox_from_image(sub_bgr, origin_x=0, origin_y=0, scale=1.0):
        h, w = sub_bgr.shape[:2]
        if max(w, h) > max_size:
            s = max_size / max(w, h)
            new_w = max(1, int(w * s))
            new_h = max(1, int(h * s))
            small = cv2.resize(sub_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            s = 1.0
            small = sub_bgr
        rgba = remove_background(small, model_name)
        bbox = content_bbox(rgba, threshold=30)
        if bbox is None:
            return None
        x0, y0, x1, y1 = bbox
        if s != 1.0:
            x0, y0, x1, y1 = int(x0 / s), int(y0 / s), int(x1 / s), int(y1 / s)
        x0 = origin_x + x0
        y0 = origin_y + y0
        x1 = origin_x + x1
        y1 = origin_y + y1
        ph = max(1, y1 - y0)
        pw = max(1, x1 - x0)
        pad_x = int(pw * padding_ratio)
        pad_y_top = int(ph * padding_ratio * 1.3)
        pad_y_bot = int(ph * padding_ratio)
        x0 = max(0, x0 - pad_x)
        y0 = max(0, y0 - pad_y_top)
        x1 = min(image_bgr.shape[1], x1 + pad_x)
        y1 = min(image_bgr.shape[0], y1 + pad_y_bot)
        return (x0, y0, x1 - x0, y1 - y0)

    H, W = image_bgr.shape[:2]
    # 1. 先搜索身份证右上角的大致人像区域
    if W >= H:
        x0, y0, sw, sh = int(W * 0.45), int(H * 0.03), int(W * 0.53), int(H * 0.82)
    else:
        x0, y0, sw, sh = int(W * 0.06), int(H * 0.03), int(W * 0.88), int(H * 0.95)
    x1, y1 = min(W, x0 + sw), min(H, y0 + sh)
    x0, y0 = max(0, x0), max(0, y0)
    search_img = image_bgr[y0:y1, x0:x1]
    if search_img.size > 0:
        bbox = _bbox_from_image(search_img, x0, y0)
        if bbox is not None:
            bx, by, bw, bh = bbox
            if bh > bw * 0.5 and bh > 20 and bw > 20:
                return bbox
    # 2. 兜底：全图分割
    bbox = _bbox_from_image(image_bgr)
    if bbox is not None:
        bx, by, bw, bh = bbox
        if bh > bw * 0.5 and bh > 20 and bw > 20:
            return bbox
    return None


def crop_region(image_bgr, rect):
    x, y, w, h = [int(v) for v in rect]
    H, W = image_bgr.shape[:2]
    # 限制在图内，防止越界切片得到空图
    x = max(0, min(x, W - 1)) if W > 0 else 0
    y = max(0, min(y, H - 1)) if H > 0 else 0
    w = max(1, min(w, W - x)) if W > 0 else 1
    h = max(1, min(h, H - y)) if H > 0 else 1
    return image_bgr[y:y + h, x:x + w]

def remove_background(image_bgr, model_name="u2netp"):
    """抠背景，返回带 alpha 通道的 PIL RGBA 图像。

    默认 u2netp：轻量（约 4.7MB），随程序内置，完全离线、秒级出图，
    对身份证这类纯色背景的人像效果足够。若追求更高精度可选 u2net_human_seg
    （效果更好，约 167MB，首次运行联网下载一次，之后离线可用）。
    """
    if image_bgr is None or image_bgr.size == 0 or image_bgr.ndim < 3:
        raise ValueError("传入的图像为空或格式异常，无法抠图。")
    from rembg import remove, new_session
    img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(img_rgb)
    session = new_session(model_name)
    return remove(pil, session=session)


def crop_to_content(rgba):
    """裁剪到不透明内容边界，去掉透明边。"""
    arr = np.array(rgba)
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > 10)
    if len(xs) == 0:
        return rgba
    x0, x1 = xs.min(), xs.max() + 1
    y0, y1 = ys.min(), ys.max() + 1
    return rgba.crop((x0, y0, x1, y1))


def content_bbox(rgba, threshold=10):
    """返回不透明内容（人像）的边界框 (x0, y0, x1, y1)；若全透明返回 None。

    用于在自动检测后用前景蒙版反推精确的头像区域。
    """
    arr = np.array(rgba)
    if arr.ndim != 3 or arr.shape[2] < 4:
        return None
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > threshold)
    if len(xs) == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def composite_on_background(fg_rgba, bg_name="white", size=None, margin=0.06):
    """把前景放到指定底色 + 尺寸的画布上，居中并保留边距。"""
    bg_color = BG_COLORS.get(bg_name, (255, 255, 255))
    if size is None:
        size = fg_rgba.size
    canvas = Image.new("RGBA", size, (bg_color[0], bg_color[1], bg_color[2], 255))
    fw, fh = fg_rgba.size
    cw, ch = size
    # 可用区域（留边距）
    avail_w = cw * (1 - 2 * margin)
    avail_h = ch * (1 - 2 * margin)
    scale = min(avail_w / fw, avail_h / fh)
    new_w, new_h = max(1, int(fw * scale)), max(1, int(fh * scale))
    fg_resized = fg_rgba.resize((new_w, new_h), Image.LANCZOS)
    offset = ((cw - new_w) // 2, (ch - new_h) // 2)
    canvas.paste(fg_resized, offset, fg_resized)
    return canvas


def arrange_idphoto(fg_rgba, size, bg_name="white", head_ratio=0.68, top_margin=0.10):
    """标准证件照排版：把头像按头部比例缩放并居中偏上放置，自动校正大小与位置。

    head_ratio：头像（去透明边后）高度占整张证件照高度的比例（约 2/3）。
    top_margin ：头像顶部留白比例（证件照规范：头顶上方约留 10% 空白）。
    """
    cw, ch = size
    if bg_name == "transparent":
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    else:
        bg_color = BG_COLORS.get(bg_name, (255, 255, 255))
        canvas = Image.new("RGBA", size, (bg_color[0], bg_color[1], bg_color[2], 255))
    fw, fh = fg_rgba.size
    if fw == 0 or fh == 0:
        return canvas
    # 先按头部比例算高度缩放
    target_h = max(1, int(ch * head_ratio))
    scale = target_h / fh
    new_w, new_h = max(1, int(fw * scale)), target_h
    # 防止头像过宽超出画布
    if new_w > cw:
        scale = cw / fw
        new_w, new_h = cw, max(1, int(fh * scale))
    fg_resized = fg_rgba.resize((new_w, new_h), Image.LANCZOS)
    offset_x = (cw - new_w) // 2
    offset_y = int(ch * top_margin)
    canvas.paste(fg_resized, (offset_x, offset_y), fg_resized)
    return canvas


def stretch_to_size(fg_rgba, size, bg_name="transparent"):
    """将前景直接拉伸（忽略原始比例）到指定 size=(w,h)。

    用于「已选框区域不论多大，结果都拉扯到固定尺寸」的场景。
    """
    from PIL import Image
    w, h = size
    stretched = fg_rgba.resize((w, h), Image.LANCZOS)
    if bg_name == "transparent":
        return stretched
    bg_color = BG_COLORS.get(bg_name, (255, 255, 255))
    canvas = Image.new("RGBA", (w, h), (bg_color[0], bg_color[1], bg_color[2], 255))
    canvas.alpha_composite(stretched)
    return canvas


def to_rgb_with_bg(rgba, bg_name="white"):
    """把 RGBA 合并到底色上，返回 RGB 图像（用于保存 JPG）。"""
    bg_color = BG_COLORS.get(bg_name, (255, 255, 255))
    rgb = Image.new("RGB", rgba.size, bg_color)
    rgb.paste(rgba, mask=rgba.split()[3])
    return rgb


def save_result(image_rgba, path, bg_name="white"):
    """保存结果。PNG 保留透明（若底色为透明）；JPG 合并底色。"""
    lower = path.lower()
    if bg_name == "transparent" or lower.endswith(".png"):
        # 透明底色：导出原始 RGBA
        image_rgba.save(path)
    else:
        to_rgb_with_bg(image_rgba, bg_name).save(path)
