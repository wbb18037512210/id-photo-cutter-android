"""
main.py — 身份证头像抠图桌面软件（PyQt6，完全本地处理）

运行：python main.py
打包：pyinstaller --onefile --windowed --name 头像抠图 main.py
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
    # 记录到文件便于排查
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


# ------------------------- 图片显示标签（支持框选/overlay） -------------------------
class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.setStyleSheet("border:1px solid #bbb; background:#ececec;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self._src = None           # 原始 QPixmap
        self._scaled = None
        self._scale = 1.0
        self._fit_scale = 1.0
        self._user_zoom = 1.0      # 用户缩放倍数（1.0 = 适应窗口）
        self._pan = QPoint(0, 0)   # 平移偏移（像素）
        self._offset = QPoint(0, 0)
        self._overlay = None       # QRect（原图像素坐标）
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
            pen = QPen(QColor(220, 60, 60), 2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawRect(r)
        if self._sel_start is not None and self._sel_cur is not None:
            r = self._rect(self._sel_start, self._sel_cur)
            rd = self._to_disp(r)
            pen = QPen(QColor(40, 130, 240), 2, Qt.PenStyle.DashLine)
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
        # 右键 / Ctrl+左键：平移视图
        if e.button() == Qt.MouseButton.RightButton or \
           (e.button() == Qt.MouseButton.LeftButton and
            (e.modifiers() & Qt.KeyboardModifier.ControlModifier)):
            self._panning = True
            self._pan_start = e.pos()
            self._pan_origin = QPoint(self._pan)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        # 否则：框选头像区域
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
    finished = pyqtSignal(object)   # bbox tuple or None
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


# ------------------------- 主窗口 -------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("身份证头像抠图 · 本地处理")
        self.resize(960, 620)
        self.original = None        # BGR numpy
        self.crop_rect = None       # (x,y,w,h) 原图坐标
        self.fg_rgba = None         # 抠好的前景 RGBA
        self.result_rgba = None     # 最终（含底色/尺寸）
        self.worker = None
        self.detect_worker = None   # 人像定位线程
        self._last_cut_rect = None  # 上次已抠图的区域（避免重复抠图）
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # 左侧：原图 + 操作
        left = QVBoxLayout()
        self.src_label = ImageLabel()
        self.src_label.parent_window = self
        left.addWidget(self.src_label, 1)

        # 缩放/旋转工具条（放大/缩小/适应窗口/左转/右转 + 倍率显示）
        zrow = QHBoxLayout()
        self.btn_zoom_out = QPushButton("－")
        self.btn_zoom_in = QPushButton("＋")
        self.btn_fit = QPushButton("适应窗口")
        self.btn_rot_left = QPushButton("↺ 左转")
        self.btn_rot_right = QPushButton("↻ 右转")
        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setStyleSheet("color:#666; font-size:11px;")
        self.btn_zoom_out.setMaximumWidth(34)
        self.btn_zoom_in.setMaximumWidth(34)
        self.btn_rot_left.setMaximumWidth(56)
        self.btn_rot_right.setMaximumWidth(56)
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

        btn_open = QPushButton("打开图片")
        btn_open.clicked.connect(self.open_image)
        btn_detect = QPushButton("自动检测头像")
        btn_detect.clicked.connect(self.auto_detect)
        btn_clear = QPushButton("清除选区")
        btn_clear.clicked.connect(self.clear_crop)
        row = QHBoxLayout()
        row.addWidget(btn_open)
        row.addWidget(btn_detect)
        row.addWidget(btn_clear)
        left.addLayout(row)
        tip = QLabel("提示：可直接拖入图片；在左侧按住鼠标框选头像区域。滚轮缩放、右键拖动平移，或用 －/＋ 放大后精确框选；用 ↺左转/↻右转 调整图片方向。")
        tip.setStyleSheet("color:#666; font-size:11px;")
        left.addWidget(tip)
        root.addLayout(left, 1)

        # 右侧：结果 + 选项
        right = QVBoxLayout()
        self.res_label = ImageLabel()
        right.addWidget(self.res_label, 1)

        opt = QGroupBox("输出选项")
        og = QVBoxLayout(opt)

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("抠图模型："))
        self.cmb_model = QComboBox()
        self.cmb_model.addItems([
            "u2netp（轻量·已内置·离线秒出）",
            "u2net_human_seg（更高精度·已内置·离线）",
            "u2net（通用·已内置·离线）",
        ])
        self.cmb_model.setCurrentIndex(1)  # 默认高精度模型 u2net_human_seg
        h1.addWidget(self.cmb_model)
        self.cmb_model.currentTextChanged.connect(self.on_model_changed)
        og.addLayout(h1)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("底色："))
        self.cmb_bg = QComboBox()
        self.cmb_bg.addItems(["透明", "白底", "蓝底", "红底"])
        self.cmb_bg.setCurrentText("白底")  # 默认白底
        self.cmb_bg.currentTextChanged.connect(lambda _: self.update_preview())
        h2.addWidget(self.cmb_bg)
        og.addLayout(h2)

        self.chk_trim = QCheckBox("去透明边（裁剪到头像）")
        self.chk_trim.setChecked(True)
        self.chk_trim.stateChanged.connect(lambda _: self.update_preview())
        og.addWidget(self.chk_trim)

        right.addWidget(opt)

        btn_cut = QPushButton("开始抠图")
        btn_cut.clicked.connect(self.do_cut)
        btn_save = QPushButton("保存结果")
        btn_save.clicked.connect(self.save_result)
        self.btn_save = btn_save
        btn_save.setEnabled(False)
        h4 = QHBoxLayout()
        h4.addWidget(btn_cut)
        h4.addWidget(btn_save)
        right.addLayout(h4)

        self.status = QLabel("就绪。请先打开一张身份证照片。")
        self.status.setStyleSheet("color:#444; font-size:11px;")
        right.addWidget(self.status)
        root.addLayout(right, 1)

        # 支持拖拽
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
        # 切换图片时停止旧线程
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
        # 打开/拖入图片后自动开始抠图（自动定位头像并生成结果）
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
        # 忽略旧线程的结果（例如用户已切换图片）
        if self.sender() != self.detect_worker:
            return
        if bbox is not None:
            self.crop_rect = bbox
            self.status.setText("已精确定位人像，正在校正方向…")
        else:
            # 兜底：未检测到前景时使用身份证默认区域
            self.crop_rect = core.pick_head_region(self.original)
            self.status.setText("未检测到明确人像，使用默认区域，正在校正方向…")
        # 自动检测头像后，将图片方向修正为横向长方形（并同步映射头像框）
        if self.original.shape[0] > self.original.shape[1]:
            self.original, self.crop_rect = core.orient_landscape(self.original, self.crop_rect)
            self.src_label.set_image(bgr_to_pixmap(self.original))
            self.status.setText(self.status.text() + "（已旋转为横向）")
        self.src_label.set_overlay(QRect(*self.crop_rect))
        # 继续抠图流程
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
        # 切换抠图模型后，强制用新模型重新抠图（不重新自动检测人像）
        if self.original is None:
            return
        self._last_cut_rect = None
        self.do_cut()

    def rotate_src_left(self):
        """工具栏「左转」按钮：逆时针旋转 90°。"""
        self._rotate_src(clockwise=False)

    def rotate_src_right(self):
        """工具栏「右转」按钮：顺时针旋转 90°。"""
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
        # 同一区域已抠过图，直接刷新预览，避免重复推理
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
        # 忽略旧线程的结果（例如用户已切换图片）
        if self.sender() != self.worker:
            return
        self.fg_rgba = rgba
        # 用前景蒙版反推精确人像框，修正自动检测/框选的误差
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
        self.status.setText("抠图完成，已精确锁定人像。可手动框选微调，或调整底色/尺寸后保存。")

    def on_cut_error(self, msg):
        if self.sender() != self.worker:
            return
        QMessageBox.critical(self, "抠图失败", msg)
        self.status.setText("抠图失败，请重试。")

    def _build_result(self):
        if self.fg_rgba is None:
            return None
        bg = self.cmb_bg.currentText()
        bg_name = {"透明": "transparent", "白底": "white", "蓝底": "blue", "红底": "red"}[bg]
        fg = self.fg_rgba
        if self.chk_trim.isChecked():
            fg = core.crop_to_content(fg)
        # 结果一律拉伸到 500×670（无论是否框选、框多大）
        size = core.PHOTO_SIZES.get("500x670", (500, 670))
        return core.stretch_to_size(fg, size, bg_name)

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
        bg = self.cmb_bg.currentText()
        bg_name = {"透明": "transparent", "白底": "white", "蓝底": "blue", "红底": "red"}[bg]
        try:
            core.save_result(self.result_rgba, path, bg_name)
        except Exception as ex:
            QMessageBox.critical(self, "保存失败", str(ex))
            return
        QMessageBox.information(self, "完成", f"已保存到桌面：\n{path}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        selftest()
        return
    app = App(sys.argv)
    sys.excepthook = _global_excepthook
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
