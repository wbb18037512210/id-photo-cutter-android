"""
main.py — 证件照工作室桌面软件（PyQt6，完全本地处理）

运行：python main.py
打包：pyinstaller 头像抠图.spec  （见 头像抠图.spec）
"""
import sys
import os
import shutil
import datetime

# 让 rembg 使用指定的模型目录（U2NET_HOME 即模型目录本身）
if getattr(sys, "frozen", False):
    # 打包后：模型解包到只读的 _MEIPASS，复制到用户可写目录，便于首次下载/更新
    _BASE = sys._MEIPASS
    _U2NET_HOME = os.path.join(os.path.expanduser("~"), ".u2net_idcutter")
    os.makedirs(_U2NET_HOME, exist_ok=True)
    _bundled = os.path.join(_BASE, "models")
    if os.path.isdir(_bundled):
        for f in os.listdir(_bundled):
            if f.endswith(".onnx"):
                dst = os.path.join(_U2NET_HOME, f)
                if not os.path.exists(dst):
                    try:
                        shutil.copy(os.path.join(_bundled, f), dst)
                    except Exception:
                        pass
else:
    # 开发时：直接使用项目内 models 目录
    _BASE = os.path.dirname(os.path.abspath(__file__))
    _U2NET_HOME = os.path.join(_BASE, "models")
    os.makedirs(_U2NET_HOME, exist_ok=True)
os.environ["U2NET_HOME"] = _U2NET_HOME

import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QFileDialog, QMessageBox, QCheckBox, QSizePolicy, QGroupBox,
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QDragEnterEvent, QDropEvent
from PyQt6.QtCore import Qt, QRect, QPoint, QThread, pyqtSignal, QStandardPaths

import idcutter_core as core


# ------------------------- 全局异常钩子（避免静默闪退） -------------------------
def _global_excepthook(etype, value, tb):
    import traceback
    msg = "".join(traceback.format_exception(etype, value, tb))
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance()
        if app is not None:
            QMessageBox.critical(None, "程序出错", msg[-2000:])
        else:
            print(msg)
    except Exception:
        print(msg)
    try:
        with open(os.path.join(os.path.expanduser("~"), "idcutter_error.log"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def _safe_notify(app, receiver, event):
    try:
        return app.notify(receiver, event)
    except Exception:
        _global_excepthook(*sys.exc_info())
        return False


# ------------------------- 命令行自测（--selftest） -------------------------
def selftest():
    import numpy as np
    from PIL import Image, ImageDraw
    w, h = 320, 320
    img = Image.new("RGB", (w, h), (210, 210, 210))
    d = ImageDraw.Draw(img)
    d.ellipse([90, 90, 230, 230], fill=(235, 215, 195))
    d.ellipse([120, 130, 150, 160], fill=(40, 40, 40))
    d.ellipse([170, 130, 200, 160], fill=(40, 40, 40))
    arr = np.array(img)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    print("SELFTEST: loading model u2netp ...", flush=True)
    try:
        rgba = core.remove_background(bgr, "u2netp")
        print("SELFTEST OK, result size:", rgba.size, "mode:", rgba.mode, flush=True)
    except Exception as ex:
        import traceback
        print("SELFTEST ERROR:", repr(ex), flush=True)
        traceback.print_exc()
        sys.exit(2)
    sys.exit(0)


# ------------------------- 捕获 Qt 事件循环中的未捕获异常（避免静默闪退） -------------------------
class App(QApplication):
    def notify(self, receiver, event):
        try:
            return super().notify(receiver, event)
        except Exception:
            _global_excepthook(*sys.exc_info())
            return False


# ------------------------- 工具函数 -------------------------
def bgr_to_pixmap(bgr):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    qimg = QImage(rgb.tobytes(), w, h, w * ch, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg)


def pil_to_pixmap(pil_img):
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    data = pil_img.tobytes("raw", "RGBA")
    qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


# ------------------------- 底色色板映射 -------------------------
BG_HEX = {
    "white": "#FFFFFF",
    "blue": "#2F6FE0",
    "red": "#E0494D",
    "transparent": "#D7DAE2",
}
BG_LABEL = {"white": "白底", "blue": "蓝底", "red": "红底", "transparent": "透明"}


# ------------------------- 图片显示标签（支持框选/overlay） -------------------------
class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.setStyleSheet("background:#F1F2F6; border:1px solid #E7E9EF; border-radius:16px;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self._src = None
        self._scaled = None
        self._scale = 1.0
        self._fit_scale = 1.0
        self._user_zoom = 1.0
        self._pan = QPoint(0, 0)
        self._offset = QPoint(0, 0)
        self._overlay = None
        self._sel_start = None
        self._sel_cur = None
        self._selecting = False
        self._panning = False
        self._pan_start = None
        self._pan_origin = None
        self.parent_window = None

    def set_image(self, pixmap):
        self._src = pixmap if (pixmap is not None and not pixmap.isNull()) else None
        self._user_zoom = 1.0
        self._pan = QPoint(0, 0)
        self._overlay = None
        self._sel_start = None
        self._sel_cur = None
        self._update_scaled()

    def set_overlay(self, rect):
        self._overlay = rect
        self.update()

    def clear_overlay(self):
        self._overlay = None
        self._sel_start = None
        self._sel_cur = None
        self.update()

    def _update_scaled(self):
        if self._src is None:
            self._scaled = None
            return
        size = self.size()
        sw, sh = self._src.width(), self._src.height()
        fit = min(size.width() / sw, size.height() / sh) if (sw and sh) else 1.0
        self._fit_scale = fit
        self._scale = fit * self._user_zoom
        disp_w = max(1, int(sw * self._scale))
        disp_h = max(1, int(sh * self._scale))
        self._scaled = self._src.scaled(
            disp_w, disp_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self._recompute_offset()
        self.update()

    def _recompute_offset(self):
        if self._scaled is None:
            return
        size = self.size()
        dw = self._scaled.width()
        dh = self._scaled.height()
        self._offset = QPoint(int((size.width() - dw) / 2 + self._pan.x()),
                              int((size.height() - dh) / 2 + self._pan.y()))

    def reset_view(self):
        self._user_zoom = 1.0
        self._pan = QPoint(0, 0)
        self._update_scaled()
        if self.parent_window is not None and hasattr(self.parent_window, "lbl_zoom"):
            self.parent_window.lbl_zoom.setText("100%")

    def zoom_by(self, factor):
        if self._src is None:
            return
        self._user_zoom = max(1.0, min(8.0, self._user_zoom * factor))
        self._update_scaled()
        if self.parent_window is not None and hasattr(self.parent_window, "lbl_zoom"):
            self.parent_window.lbl_zoom.setText(f"{int(self._user_zoom * 100)}%")

    def wheelEvent(self, e):
        if self._src is None:
            return
        e.accept()
        pos = e.position().toPoint()
        img_x = (pos.x() - self._offset.x()) / self._scale
        img_y = (pos.y() - self._offset.y()) / self._scale
        factor = 1.15 if e.angleDelta().y() > 0 else 1.0 / 1.15
        nz = max(1.0, min(8.0, self._user_zoom * factor))
        if nz == self._user_zoom:
            return
        self._user_zoom = nz
        self._update_scaled()
        nd_x = img_x * self._scale + self._offset.x()
        nd_y = img_y * self._scale + self._offset.y()
        self._pan += QPoint(int(pos.x() - nd_x), int(pos.y() - nd_y))
        self._recompute_offset()
        if self.parent_window is not None and hasattr(self.parent_window, "lbl_zoom"):
            self.parent_window.lbl_zoom.setText(f"{int(self._user_zoom * 100)}%")
        self.update()

    def resizeEvent(self, event):
        self._update_scaled()
        super().resizeEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._scaled is None:
            return
        p = QPainter(self)
        p.drawPixmap(self._offset, self._scaled)
        if self._overlay is not None:
            r = self._to_disp(self._overlay)
            pen = QPen(QColor(91, 91, 232), 2.5, Qt.PenStyle.SolidLine)
            p.setPen(pen)
            p.drawRect(r)
        if self._sel_start is not None and self._sel_cur is not None:
            r = self._rect(self._sel_start, self._sel_cur)
            rd = self._to_disp(r)
            pen = QPen(QColor(47, 111, 224), 2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawRect(rd)

    def _to_disp(self, r):
        return QRect(int(r.x() * self._scale + self._offset.x()),
                     int(r.y() * self._scale + self._offset.y()),
                     int(r.width() * self._scale),
                     int(r.height() * self._scale))

    def _to_orig(self, pt):
        return QPoint(int((pt.x() - self._offset.x()) / self._scale),
                      int((pt.y() - self._offset.y()) / self._scale))

    def _rect(self, a, b):
        return QRect(min(a.x(), b.x()), min(a.y(), b.y()),
                     abs(a.x() - b.x()), abs(a.y() - b.y()))

    def mousePressEvent(self, e):
        if self._src is None:
            return
        if e.button() == Qt.MouseButton.RightButton or \
           (e.button() == Qt.MouseButton.LeftButton and
            (e.modifiers() & Qt.KeyboardModifier.ControlModifier)):
            self._panning = True
            self._pan_start = e.pos()
            self._pan_origin = QPoint(self._pan)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        self._selecting = True
        self._sel_start = self._to_orig(e.pos())
        self._sel_cur = self._sel_start
        self.update()

    def mouseMoveEvent(self, e):
        if self._panning:
            self._pan = self._pan_origin + (e.pos() - self._pan_start)
            self._recompute_offset()
            self.update()
            return
        if self._selecting:
            self._sel_cur = self._to_orig(e.pos())
            self.update()

    def mouseReleaseEvent(self, e):
        if self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        if self._selecting:
            self._selecting = False
            if self._sel_start is not None and self._sel_cur is not None:
                r = self._rect(self._sel_start, self._sel_cur)
                if r.width() > 5 and r.height() > 5:
                    self._overlay = r
                    if self.parent_window:
                        self.parent_window.on_crop_selected(r)
            self._sel_start = None
            self._sel_cur = None
            self.update()


# ------------------------- 人像定位工作线程（避免 UI 卡死） -------------------------
class DetectWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, image_bgr, model_name):
        super().__init__()
        self.image_bgr = image_bgr
        self.model_name = model_name

    def run(self):
        try:
            bbox = core.detect_person_bbox(self.image_bgr, self.model_name)
            self.finished.emit(bbox)
        except Exception as ex:
            self.error.emit(str(ex))


# ------------------------- 抠图工作线程 -------------------------
class CutWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, image_bgr, model_name):
        super().__init__()
        self.image_bgr = image_bgr
        self.model_name = model_name

    def run(self):
        try:
            rgba = core.remove_background(self.image_bgr, self.model_name)
            self.finished.emit(rgba)
        except Exception as ex:
            self.error.emit(str(ex))


# ------------------------- 统一 QSS 样式 -------------------------
QSS = """
QWidget {
    font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", "Noto Sans SC", sans-serif;
    font-size: 13px;
    color: #14161C;
}
QMainWindow { background: #F5F6F8; }
QLabel#title { font-size: 20px; font-weight: 600; color: #14161C; }
QLabel#privacy { color: #5B5BE8; font-weight: 600; font-size: 12px; }
QLabel#status { color: #5A606E; font-size: 11px; }
QLabel#tip { color: #9298A6; font-size: 11px; }
QLabel#zoom { color: #9298A6; font-size: 11px; }
.image-label {
    background: #F1F2F6;
    border: 1px solid #E7E9EF;
    border-radius: 16px;
}
QPushButton {
    background: #FFFFFF;
    border: 1px solid #D8DBE3;
    border-radius: 12px;
    padding: 10px 16px;
    color: #14161C;
    font-weight: 500;
}
QPushButton:hover { background: #F1F2F6; }
QPushButton:disabled { color: #9298A6; background: #F1F2F6; }
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366F1, stop:1 #8B5CF6);
    color: #FFFFFF; border: none; font-weight: 600; padding: 12px 20px;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6F71F3, stop:1 #9B6CF8);
}
QPushButton#primary:disabled { background: #E7E9EF; color: #9298A6; }
QPushButton#icon {
    background: #F1F2F6; border: none; border-radius: 12px; padding: 8px 10px;
}
QPushButton#icon:hover { background: #E7E9EF; }
QGroupBox {
    border: 1px solid #E7E9EF; border-radius: 16px; padding: 16px; margin-top: 10px;
    background: #FFFFFF;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 16px; padding: 0 6px;
    color: #5A606E; font-weight: 600; font-size: 12px;
}
QComboBox {
    background: #FFFFFF; border: 1px solid #D8DBE3; border-radius: 12px;
    padding: 9px 12px;
}
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView {
    background: #FFFFFF; border: 1px solid #E7E9EF; border-radius: 8px;
    selection-background-color: #ECECFB; outline: 0px;
}
QCheckBox { spacing: 8px; color: #14161C; }
QCheckBox::indicator {
    width: 18px; height: 18px; border-radius: 5px;
    border: 1px solid #D8DBE3; background: #FFFFFF;
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #6366F1, stop:1 #8B5CF6);
    border: none;
}
"""


# ------------------------- 主窗口 -------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("证件照工作室 · 本地处理")
        self.resize(1040, 660)
        self.original = None
        self.crop_rect = None
        self.fg_rgba = None
        self.result_rgba = None
        self.worker = None
        self.detect_worker = None
        self._last_cut_rect = None
        self._bg_name = "white"   # 当前底色
        self.bg_buttons = {}
        self._build_ui()

    def _swatch_style(self, color_hex, selected):
        border = "#5B5BE8" if selected else "transparent"
        return (f"background:{color_hex}; border-radius:18px; border:2px solid {border};"
                f"{'padding:2px;' if selected else ''}")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        # ============ 左：原图 + 操作 ============
        left = QVBoxLayout()
        left.setSpacing(14)

        # 标题区
        head = QHBoxLayout()
        title = QLabel("证件照工作室")
        title.setObjectName("title")
        privacy = QLabel("🔒 本地离线 · 数据不出本机")
        privacy.setObjectName("privacy")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(privacy)
        left.addLayout(head)

        self.src_label = ImageLabel()
        self.src_label.parent_window = self
        self.src_label.setObjectName("src")
        self.src_label.setProperty("class", "image-label")
        left.addWidget(self.src_label, 1)

        # 缩放/旋转工具条
        zrow = QHBoxLayout()
        zrow.setSpacing(8)
        self.btn_zoom_out = QPushButton("－")
        self.btn_zoom_in = QPushButton("＋")
        self.btn_fit = QPushButton("适应窗口")
        self.btn_rot_left = QPushButton("↺ 左转")
        self.btn_rot_right = QPushButton("↻ 右转")
        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setObjectName("zoom")
        for b in (self.btn_zoom_out, self.btn_zoom_in, self.btn_fit,
                  self.btn_rot_left, self.btn_rot_right):
            b.setObjectName("icon")
            b.setMaximumWidth(64 if b in (self.btn_rot_left, self.btn_rot_right) else 40)
        self.btn_zoom_out.clicked.connect(lambda: self.src_label.zoom_by(1 / 1.25))
        self.btn_zoom_in.clicked.connect(lambda: self.src_label.zoom_by(1.25))
        self.btn_fit.clicked.connect(self.src_label.reset_view)
        self.btn_rot_left.clicked.connect(self.rotate_src_left)
        self.btn_rot_right.clicked.connect(self.rotate_src_right)
        zrow.addWidget(self.btn_zoom_out)
        zrow.addWidget(self.btn_zoom_in)
        zrow.addWidget(self.btn_fit)
        zrow.addSpacing(12)
        zrow.addWidget(self.btn_rot_left)
        zrow.addWidget(self.btn_rot_right)
        zrow.addWidget(self.lbl_zoom)
        zrow.addStretch(1)
        left.addLayout(zrow)

        row = QHBoxLayout()
        row.setSpacing(10)
        btn_open = QPushButton("打开图片")
        btn_open.setObjectName("primary")
        btn_detect = QPushButton("自动检测头像")
        btn_clear = QPushButton("清除选区")
        btn_open.clicked.connect(self.open_image)
        btn_detect.clicked.connect(self.auto_detect)
        btn_clear.clicked.connect(self.clear_crop)
        row.addWidget(btn_open)
        row.addWidget(btn_detect)
        row.addWidget(btn_clear)
        left.addLayout(row)

        tip = QLabel("提示：可直接拖入图片；在左侧按住鼠标框选头像区域。滚轮缩放、右键拖动平移，或用 －/＋ 放大后精确框选；用 ↺左转/↻右转 调整图片方向。")
        tip.setObjectName("tip")
        tip.setWordWrap(True)
        left.addWidget(tip)
        root.addLayout(left, 1)

        # ============ 右：结果 + 选项 ============
        right = QVBoxLayout()
        right.setSpacing(14)
        res_title = QLabel("预览结果")
        res_title.setObjectName("title")
        right.addWidget(res_title)

        self.res_label = ImageLabel()
        self.res_label.setObjectName("res")
        self.res_label.setProperty("class", "image-label")
        right.addWidget(self.res_label, 1)

        opt = QGroupBox("输出选项")
        og = QVBoxLayout(opt)
        og.setSpacing(14)

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("抠图模型："))
        self.cmb_model = QComboBox()
        self.cmb_model.addItems([
            "u2netp（轻量·已内置·离线秒出）",
            "u2net_human_seg（更高精度·已内置·离线）",
            "u2net（通用·已内置·离线）",
        ])
        self.cmb_model.setCurrentIndex(1)
        h1.addWidget(self.cmb_model, 1)
        self.cmb_model.currentTextChanged.connect(self.on_model_changed)
        og.addLayout(h1)

        # 底色色板
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("底色："))
        for name in ("white", "blue", "red", "transparent"):
            b = QPushButton()
            b.setFixedSize(34, 34)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(self._swatch_style(BG_HEX[name], name == self._bg_name))
            b.clicked.connect(lambda _, n=name: self.on_bg_selected(n))
            self.bg_buttons[name] = b
            h2.addWidget(b)
        h2.addStretch(1)
        og.addLayout(h2)

        self.chk_trim = QCheckBox("去透明边（裁剪到头像）")
        self.chk_trim.setChecked(True)
        self.chk_trim.stateChanged.connect(lambda _: self.update_preview())
        og.addWidget(self.chk_trim)

        right.addWidget(opt)

        h4 = QHBoxLayout()
        h4.setSpacing(10)
        btn_cut = QPushButton("开始抠图")
        btn_cut.setObjectName("primary")
        btn_save = QPushButton("保存结果")
        self.btn_save = btn_save
        btn_save.setEnabled(False)
        btn_cut.clicked.connect(self.do_cut)
        btn_save.clicked.connect(self.save_result)
        h4.addWidget(btn_cut)
        h4.addWidget(btn_save)
        right.addLayout(h4)

        self.status = QLabel("就绪。请先打开一张身份证照片。")
        self.status.setObjectName("status")
        right.addWidget(self.status)
        root.addLayout(right, 1)

        self.setAcceptDrops(True)

    # ---- 拖拽 ----
    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        urls = e.mimeData().urls()
        if urls:
            self.load_path(urls[0].toLocalFile())

    # ---- 功能 ----
    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片 (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            self.load_path(path)

    def load_path(self, path):
        try:
            img = core.load_image(path)
        except Exception as ex:
            QMessageBox.warning(self, "错误", str(ex))
            return
        if self.detect_worker and self.detect_worker.isRunning():
            self.detect_worker.quit()
            self.detect_worker.wait(3000)
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(3000)
        self.original = img
        self.crop_rect = None
        self.fg_rgba = None
        self.result_rgba = None
        self._last_cut_rect = None
        self.btn_save.setEnabled(False)
        self.src_label.set_image(bgr_to_pixmap(img))
        self.res_label.set_image(QPixmap())
        self.status.setText(f"已载入：{os.path.basename(path)}（{img.shape[1]}×{img.shape[0]}），自动抠图中…")
        self.auto_detect()

    def auto_detect(self):
        if self.original is None:
            QMessageBox.information(self, "提示", "请先打开图片。")
            return
        if self.detect_worker and self.detect_worker.isRunning():
            return
        self.status.setText("正在精确定位人像…")
        model = self._model_name()
        self.detect_worker = DetectWorker(self.original, model)
        self.detect_worker.finished.connect(self.on_detect_done)
        self.detect_worker.error.connect(self.on_detect_error)
        self.detect_worker.start()

    def on_detect_done(self, bbox):
        if self.sender() != self.detect_worker:
            return
        if bbox is not None:
            self.crop_rect = bbox
            self.status.setText("已精确定位人像，正在校正方向…")
        else:
            self.crop_rect = core.pick_head_region(self.original)
            self.status.setText("未检测到明确人像，使用默认区域，正在校正方向…")
        if self.original.shape[0] > self.original.shape[1]:
            self.original, self.crop_rect = core.orient_landscape(self.original, self.crop_rect)
            self.src_label.set_image(bgr_to_pixmap(self.original))
            self.status.setText(self.status.text() + "（已旋转为横向）")
        self.src_label.set_overlay(QRect(*self.crop_rect))
        self.do_cut()

    def on_detect_error(self, msg):
        if self.sender() != self.detect_worker:
            return
        QMessageBox.critical(self, "人像定位失败", msg)
        self.status.setText("人像定位失败，请重试。")

    def clear_crop(self):
        self.crop_rect = None
        self.src_label.clear_overlay()
        self.status.setText("已清除选区，将处理整张图片。")

    def on_bg_selected(self, name):
        self._bg_name = name
        for n, b in self.bg_buttons.items():
            b.setStyleSheet(self._swatch_style(BG_HEX[n], n == name))
        self.update_preview()

    def on_crop_selected(self, rect):
        self.crop_rect = (rect.x(), rect.y(), rect.width(), rect.height())
        self._last_cut_rect = None
        self.status.setText(f"已框选区域：{rect.width()}×{rect.height()}")

    def _model_name(self):
        t = self.cmb_model.currentText()
        if "u2net_human_seg" in t:
            return "u2net_human_seg"
        if "u2netp" in t:
            return "u2netp"
        return "u2net"

    def on_model_changed(self):
        if self.original is None:
            return
        self._last_cut_rect = None
        self.do_cut()

    def rotate_src_left(self):
        self._rotate_src(clockwise=False)

    def rotate_src_right(self):
        self._rotate_src(clockwise=True)

    def _rotate_src(self, clockwise):
        if self.original is None:
            QMessageBox.information(self, "提示", "请先打开图片。")
            return
        self.original, self.crop_rect = core.rotate_image_and_rect(self.original, self.crop_rect, clockwise)
        self.src_label.set_image(bgr_to_pixmap(self.original))
        if self.crop_rect is not None:
            self.src_label.set_overlay(QRect(*self.crop_rect))
        else:
            self.src_label.clear_overlay()
        self._last_cut_rect = None
        self.status.setText("已旋转图片方向，正在重新抠图…")
        self.do_cut()

    def do_cut(self):
        if self.original is None:
            QMessageBox.information(self, "提示", "请先打开图片。")
            return
        if self.worker and self.worker.isRunning():
            return
        if self.detect_worker and self.detect_worker.isRunning():
            return
        if (self.fg_rgba is not None and self.crop_rect is not None
                and self.crop_rect == self._last_cut_rect):
            self.update_preview()
            return
        crop = core.crop_region(self.original, self.crop_rect) if self.crop_rect else self.original
        if crop is None or crop.size == 0:
            QMessageBox.critical(self, "抠图失败", "裁剪区域无效，请重新框选头像区域。")
            self.status.setText("裁剪区域无效，请重新框选。")
            return
        model = self._model_name()
        self.status.setText("正在抠图（内置模型·完全离线）…")
        self.worker = CutWorker(crop, model)
        self.worker.finished.connect(self.on_cut_done)
        self.worker.error.connect(self.on_cut_error)
        self.worker.start()

    def on_cut_done(self, rgba):
        if self.sender() != self.worker:
            return
        self.fg_rgba = rgba
        bx = core.content_bbox(rgba)
        if bx is not None and self.crop_rect is not None:
            cx, cy, cw, ch = self.crop_rect
            sx = rgba.width / cw if cw else 1.0
            sy = rgba.height / ch if ch else 1.0
            x0, y0, x1, y1 = bx
            nx = int(cx + x0 * sx)
            ny = int(cy + y0 * sy)
            nw = int((x1 - x0) * sx)
            nh = int((y1 - y0) * sy)
            pad = int(nw * 0.02)
            nx = max(0, nx - pad)
            ny = max(0, ny - pad)
            nw = min(self.original.shape[1] - nx, nw + 2 * pad)
            nh = min(self.original.shape[0] - ny, nh + 2 * pad)
            self.crop_rect = (nx, ny, nw, nh)
            self.src_label.set_overlay(QRect(nx, ny, nw, nh))
        self._last_cut_rect = self.crop_rect
        self.update_preview()
        self.btn_save.setEnabled(True)
        self.status.setText("抠图完成，已精确锁定人像。可手动框选微调，或调整底色后保存。")

    def on_cut_error(self, msg):
        if self.sender() != self.worker:
            return
        QMessageBox.critical(self, "抠图失败", msg)
        self.status.setText("抠图失败，请重试。")

    def _build_result(self):
        if self.fg_rgba is None:
            return None
        fg = self.fg_rgba
        if self.chk_trim.isChecked():
            fg = core.crop_to_content(fg)
        size = core.PHOTO_SIZES.get("500x670", (500, 670))
        return core.stretch_to_size(fg, size, self._bg_name)

    def update_preview(self):
        if self.fg_rgba is None:
            return
        res = self._build_result()
        self.result_rgba = res
        self.res_label.set_image(pil_to_pixmap(res))

    def save_result(self):
        if self.result_rgba is None:
            QMessageBox.information(self, "提示", "请先抠图。")
            return
        desktop = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        if not desktop:
            QMessageBox.warning(self, "提示", "未找到系统桌面目录，无法自动保存。")
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(desktop, f"头像_{ts}.png")
        try:
            core.save_result(self.result_rgba, path, self._bg_name)
        except Exception as ex:
            QMessageBox.critical(self, "保存失败", str(ex))
            return
        QMessageBox.information(self, "完成", f"已保存到桌面：\n{path}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        selftest()
        return
    app = App(sys.argv)
    app.setStyleSheet(QSS)
    sys.excepthook = _global_excepthook
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
