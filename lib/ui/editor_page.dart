import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;
import 'package:image_gallery_saver/image_gallery_saver.dart';
import '../core/segmenter.dart';
import '../core/image_processor.dart';
import '../theme/app_theme.dart';
import '../theme/app_widgets.dart';
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
  BgMode _bg = BgMode.white;
  int _sizeIndex = 2; // 默认「标准 500×670」，与原行为一致
  Uint8List? _displayBytes;
  Uint8List? _previewBytes;
  bool _loading = true;
  bool _busy = false;
  String _error = '';

  SizePreset get _preset => kSizePresets[_sizeIndex];

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

  Future<void> _redetectInternal() async {
    final mask = await _segmenter.predictMask(_p!.original);
    final up = resizeMaskBilinear(mask, 320, 320, _p!.width, _p!.height);
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
    final out = exportIdPhoto(_p!, _crop,
        bg: _bg, outW: _preset.w, outH: _preset.h);
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
    _crop = ccw
        ? rotateCropCCW(_crop, ow, oh)
        : rotateCropCW(_crop, ow, oh);
    _refreshDisplay();
  }

  Future<void> _save() async {
    if (_busy || _p == null) return;
    setState(() => _busy = true);
    try {
      final out = exportIdPhoto(_p!, _crop,
          bg: _bg, outW: _preset.w, outH: _preset.h);
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
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(m), behavior: SnackBarBehavior.floating),
      );
    }
  }

  String _pad(int n) => n.toString().padLeft(2, '0');

  @override
  void dispose() {
    _segmenter.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      backgroundColor: dark ? AppColors.canvasDark : AppColors.canvasLight,
      extendBodyBehindAppBar: true,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(56),
        child: _TopBar(
          busy: _busy,
          onRedetect: _redetect,
          onBack: () => Navigator.of(context).maybePop(),
        ),
      ),
      body: _loading
          ? const Center(child: _LoadingShimmer())
          : _error.isNotEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.s6),
                    child: Text(_error,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: AppColors.danger)),
                  ),
                )
              : Stack(
                  children: [
                    Positioned.fill(
                      child: _p == null || _displayBytes == null
                          ? const SizedBox.shrink()
                          : CropCanvas(
                              image: _p!,
                              displayBytes: _displayBytes!,
                              crop: _crop,
                              onChanged: _onCropChanged,
                            ),
                    ),
                    Positioned(
                      left: 0,
                      right: 0,
                      bottom: 0,
                      child: _EditorSheet(
                        bg: _bg,
                        sizeIndex: _sizeIndex,
                        previewBytes: _previewBytes,
                        preset: _preset,
                        busy: _busy,
                        onBg: (m) {
                          _bg = m;
                          _computePreview();
                          setState(() {});
                        },
                        onSize: (i) {
                          _sizeIndex = i;
                          _computePreview();
                          setState(() {});
                        },
                        onRotateL: () => _rotateSource(true),
                        onRotateR: () => _rotateSource(false),
                        onZoomIn: () => _zoomCrop(1.1),
                        onZoomOut: () => _zoomCrop(0.9),
                        onSave: _save,
                      ),
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

/// 沉浸式顶部栏：返回 / 标题 / 重新检测。
class _TopBar extends StatelessWidget {
  final bool busy;
  final VoidCallback onRedetect;
  final VoidCallback onBack;
  const _TopBar(
      {required this.busy, required this.onRedetect, required this.onBack});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context)
            .colorScheme
            .surface
            .withValues(alpha: 0.86),
        border: Border(
          bottom: BorderSide(color: cs.outline.withValues(alpha: 0.5), width: 1),
        ),
      ),
      child: SafeArea(
        bottom: false,
        child: SizedBox(
          height: 56,
          child: Row(
            children: [
              const SizedBox(width: AppSpacing.s2),
              _ToolbarIcon(icon: Icons.arrow_back_rounded, onTap: onBack),
              const SizedBox(width: AppSpacing.s2),
              Expanded(
                child: Text('编辑证件照',
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.w600)),
              ),
              _ToolbarIcon(
                icon: Icons.auto_awesome_rounded,
                tooltip: '重新检测人像',
                onTap: busy ? null : onRedetect,
              ),
              const SizedBox(width: AppSpacing.s2),
            ],
          ),
        ),
      ),
    );
  }
}

class _ToolbarIcon extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;
  final String? tooltip;
  const _ToolbarIcon({required this.icon, this.onTap, this.tooltip});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.md),
        onTap: onTap,
        child: Container(
          width: 40,
          height: 40,
          alignment: Alignment.center,
          child: Icon(icon,
              size: 22,
              color: onTap == null ? cs.onSurfaceVariant : cs.onSurface),
        ),
      ),
    );
  }
}

/// 底部抽屉工具栏。
class _EditorSheet extends StatelessWidget {
  final BgMode bg;
  final int sizeIndex;
  final Uint8List? previewBytes;
  final SizePreset preset;
  final bool busy;
  final ValueChanged<BgMode> onBg;
  final ValueChanged<int> onSize;
  final VoidCallback onRotateL;
  final VoidCallback onRotateR;
  final VoidCallback onZoomIn;
  final VoidCallback onZoomOut;
  final VoidCallback onSave;

  const _EditorSheet({
    required this.bg,
    required this.sizeIndex,
    required this.previewBytes,
    required this.preset,
    required this.busy,
    required this.onBg,
    required this.onSize,
    required this.onRotateL,
    required this.onRotateR,
    required this.onZoomIn,
    required this.onZoomOut,
    required this.onSave,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final aspect = preset.h / preset.w;
    return Container(
      decoration: BoxDecoration(
        color: cs.surface,
        borderRadius:
            const BorderRadius.vertical(top: Radius.circular(AppRadius.xl)),
        border: Border.all(color: cs.outline, width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.10),
            blurRadius: 30,
            offset: const Offset(0, -8),
          ),
        ],
      ),
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.s5, AppSpacing.s4, AppSpacing.s5, AppSpacing.s5),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // 预览 + 规格
          Row(
            children: [
              Container(
                width: 52,
                height: 52 * aspect,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(AppRadius.sm),
                  border: Border.all(color: cs.outlineVariant, width: 1),
                  color: bg == BgMode.transparent ? null : Colors.white,
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.sm),
                  child: previewBytes != null
                      ? Image.memory(previewBytes!, fit: BoxFit.cover)
                      : null,
                ),
              ),
              const SizedBox(width: AppSpacing.s3),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(preset.name,
                        style: Theme.of(context)
                            .textTheme
                            .titleMedium
                            ?.copyWith(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 2),
                    Text('${preset.w} × ${preset.h} px',
                        style: Theme.of(context)
                            .textTheme
                            .labelMedium
                            ?.copyWith(color: cs.onSurfaceVariant)),
                  ],
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: AppColors.accentSoft,
                  borderRadius: BorderRadius.circular(AppRadius.pill),
                ),
                child: const Text('已抠图',
                    style: TextStyle(
                        color: AppColors.accent,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        height: 14 / 11)),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.s4),
          // 底色色板
          Row(
            children: [
              SizedBox(
                width: 44,
                child: Text('底色',
                    style: Theme.of(context)
                        .textTheme
                        .labelMedium
                        ?.copyWith(color: cs.onSurfaceVariant)),
              ),
              const SizedBox(width: AppSpacing.s2),
              BgSwatch(
                color: AppColors.bgWhite,
                selected: bg == BgMode.white,
                onTap: () => onBg(BgMode.white),
              ),
              const SizedBox(width: AppSpacing.s3),
              BgSwatch(
                color: AppColors.bgBlue,
                selected: bg == BgMode.blue,
                onTap: () => onBg(BgMode.blue),
              ),
              const SizedBox(width: AppSpacing.s3),
              BgSwatch(
                color: AppColors.bgRed,
                selected: bg == BgMode.red,
                onTap: () => onBg(BgMode.red),
              ),
              const SizedBox(width: AppSpacing.s3),
              BgSwatch(
                transparent: true,
                selected: bg == BgMode.transparent,
                onTap: () => onBg(BgMode.transparent),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.s4),
          // 尺寸分段
          SizedBox(
            width: double.infinity,
            child: SegmentedButton<int>(
              segments: [
                for (int i = 0; i < kSizePresets.length; i++)
                  ButtonSegment(
                      value: i, label: Text(kSizePresets[i].name)),
              ],
              selected: {sizeIndex},
              onSelectionChanged: (s) => onSize(s.first),
              style: ButtonStyle(
                visualDensity: VisualDensity.compact,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.s4),
          // 操作行
          Row(
            children: [
              _SheetTonal(icon: Icons.rotate_left_rounded, onTap: busy ? null : onRotateL),
              const SizedBox(width: AppSpacing.s2),
              _SheetTonal(icon: Icons.rotate_right_rounded, onTap: busy ? null : onRotateR),
              const SizedBox(width: AppSpacing.s2),
              _SheetTonal(icon: Icons.zoom_out_rounded, onTap: busy ? null : onZoomOut),
              const SizedBox(width: AppSpacing.s2),
              _SheetTonal(icon: Icons.zoom_in_rounded, onTap: busy ? null : onZoomIn),
              const SizedBox(width: AppSpacing.s3),
              Expanded(
                child: AppButton(
                  label: '保存',
                  icon: Icons.save_alt_rounded,
                  variant: AppButtonVariant.primary,
                  busy: busy,
                  fullWidth: true,
                  onPressed: busy ? null : onSave,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SheetTonal extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;
  const _SheetTonal({required this.icon, this.onTap});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Material(
      color: cs.surfaceContainerHighest,
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.md),
        onTap: onTap,
        child: SizedBox(
          width: 44,
          height: 44,
          child: Icon(icon, size: 20, color: onTap == null ? cs.onSurfaceVariant : cs.onSurface),
        ),
      ),
    );
  }
}

/// AI 推理中的柔和加载占位。
class _LoadingShimmer extends StatelessWidget {
  const _LoadingShimmer();

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const SizedBox(
          width: 36,
          height: 36,
          child: CircularProgressIndicator(strokeWidth: 3, strokeCap: StrokeCap.round),
        ),
        const SizedBox(height: AppSpacing.s4),
        Text('AI 正在抠图…',
            style: Theme.of(context)
                .textTheme
                .bodyLarge
                ?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant)),
      ],
    );
  }
}
