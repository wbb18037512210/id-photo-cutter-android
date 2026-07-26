import 'package:flutter/material.dart';
import 'app_theme.dart';

/// 可复用 UI 组件：AppLogo / 按钮 / 卡片 / 底色色板 / 隐私徽章。
/// 统一遵循 Aperture Design System 的 token 与微交互。

/// 应用标识：渐变圆角方块 + 白色证件剪影。
class AppLogo extends StatelessWidget {
  final double size;
  const AppLogo({super.key, this.size = 72});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: AppGradients.primary,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadows.accent(context),
      ),
      child: Icon(Icons.badge_rounded, size: size * 0.56, color: Colors.white),
    );
  }
}

enum AppButtonVariant { primary, secondary, tonal }

class AppButton extends StatefulWidget {
  final String label;
  final IconData? icon;
  final VoidCallback? onPressed;
  final bool fullWidth;
  final bool busy;
  final AppButtonVariant variant;
  final double? height;

  const AppButton({
    super.key,
    required this.label,
    this.icon,
    this.onPressed,
    this.fullWidth = false,
    this.busy = false,
    this.variant = AppButtonVariant.primary,
    this.height,
  });

  @override
  State<AppButton> createState() => _AppButtonState();
}

class _AppButtonState extends State<AppButton> {
  bool _pressed = false;

  void _press(bool v) {
    if (mounted) setState(() => _pressed = v);
  }

  @override
  Widget build(BuildContext context) {
    final disabled = widget.onPressed == null || widget.busy;
    final h = widget.height ?? (widget.variant == AppButtonVariant.primary ? 52.0 : 48.0);

    Widget inner = widget.busy
        ? const SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(
                strokeWidth: 2, color: Colors.white, strokeCap: StrokeCap.round),
          )
        : Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (widget.icon != null) ...[
                Icon(widget.icon, size: 20),
                const SizedBox(width: AppSpacing.s2),
              ],
              Text(widget.label),
            ],
          );

    Widget btn;
    switch (widget.variant) {
      case AppButtonVariant.primary:
        btn = Container(
          decoration: BoxDecoration(
            gradient: disabled ? null : AppGradients.primary,
            color: disabled ? Theme.of(context).colorScheme.surfaceContainerHighest : null,
            borderRadius: BorderRadius.circular(AppRadius.md),
            boxShadow: disabled ? null : AppShadows.accent(context),
          ),
          child: Material(
            color: Colors.transparent,
            borderRadius: BorderRadius.circular(AppRadius.md),
            child: InkWell(
              borderRadius: BorderRadius.circular(AppRadius.md),
              onTap: disabled ? null : widget.onPressed,
              onTapDown: disabled ? null : (_) => _press(true),
              onTapUp: disabled ? null : (_) => _press(false),
              onTapCancel: disabled ? null : () => _press(false),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                child: DefaultTextStyle(
                  style: TextStyle(
                    color: disabled ? Theme.of(context).colorScheme.onSurfaceVariant : AppColors.onAccent,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    height: 18 / 13,
                  ),
                  child: inner,
                ),
              ),
            ),
          ),
        );
        break;
      case AppButtonVariant.secondary:
        btn = Container(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
          ),
          child: Material(
            color: Colors.transparent,
            borderRadius: BorderRadius.circular(AppRadius.md),
            child: InkWell(
              borderRadius: BorderRadius.circular(AppRadius.md),
              onTap: disabled ? null : widget.onPressed,
              onTapDown: disabled ? null : (_) => _press(true),
              onTapUp: disabled ? null : (_) => _press(false),
              onTapCancel: disabled ? null : () => _press(false),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                child: DefaultTextStyle(
                  style: TextStyle(
                    color: disabled
                        ? Theme.of(context).colorScheme.onSurfaceVariant
                        : Theme.of(context).colorScheme.onSurface,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    height: 18 / 13,
                  ),
                  child: inner,
                ),
              ),
            ),
          ),
        );
        break;
      case AppButtonVariant.tonal:
        btn = Container(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          child: Material(
            color: Colors.transparent,
            borderRadius: BorderRadius.circular(AppRadius.md),
            child: InkWell(
              borderRadius: BorderRadius.circular(AppRadius.md),
              onTap: disabled ? null : widget.onPressed,
              onTapDown: disabled ? null : (_) => _press(true),
              onTapUp: disabled ? null : (_) => _press(false),
              onTapCancel: disabled ? null : () => _press(false),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: DefaultTextStyle(
                  style: TextStyle(
                    color: disabled
                        ? Theme.of(context).colorScheme.onSurfaceVariant
                        : Theme.of(context).colorScheme.onSurface,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    height: 18 / 13,
                  ),
                  child: inner,
                ),
              ),
            ),
          ),
        );
        break;
    }

    final scaled = AnimatedScale(
      scale: _pressed ? 0.97 : 1.0,
      duration: const Duration(milliseconds: 120),
      curve: Curves.easeOut,
      child: btn,
    );
    final sized = SizedBox(height: h, child: Center(child: scaled));
    return widget.fullWidth
        ? SizedBox(width: double.infinity, child: sized)
        : sized;
  }
}

/// 通用卡片容器。
class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final double? elevation;
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.s5),
    this.elevation,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: Theme.of(context).colorScheme.outline, width: 1),
        boxShadow: elevation != null ? AppShadows.sm(context) : null,
      ),
      child: child,
    );
  }
}

/// 透明底色用的棋盘格绘制。
class _CheckerPainter extends CustomPainter {
  final Color a;
  final Color b;
  const _CheckerPainter(this.a, this.b);
  @override
  void paint(Canvas canvas, Size size) {
    final cell = size.width / 4;
    final paint = Paint();
    for (int y = 0; y < 4; y++) {
      for (int x = 0; x < 4; x++) {
        paint.color = ((x + y) % 2 == 0) ? a : b;
        canvas.drawRect(Rect.fromLTWH(x * cell, y * cell, cell, cell), paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _CheckerPainter old) => old.a != a || old.b != b;
}

/// 底色色板样本：白 / 蓝 / 红 / 透明。选中态加强调色环 + 对勾。
class BgSwatch extends StatelessWidget {
  final Color color;
  final bool transparent;
  final bool selected;
  final VoidCallback onTap;
  final double size;

  const BgSwatch({
    super.key,
    this.color = Colors.white,
    this.transparent = false,
    required this.selected,
    required this.onTap,
    this.size = 36,
  });

  @override
  Widget build(BuildContext context) {
    final fill = transparent ? const Color(0xFFF1F2F6) : color;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: size + (selected ? 6 : 0),
        height: size + (selected ? 6 : 0),
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(
            color: selected ? AppColors.accent : Colors.transparent,
            width: 2,
          ),
        ),
        child: Padding(
          padding: EdgeInsets.all(selected ? 3 : 0),
          child: Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: transparent ? null : fill,
              border: Border.all(color: Theme.of(context).colorScheme.outline, width: 1),
              boxShadow: selected ? AppShadows.accent(context) : null,
            ),
            foregroundDecoration: selected
                ? const BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.black38,
                  )
                : null,
            child: ClipOval(
              child: transparent
                  ? CustomPaint(
                      painter: _CheckerPainter(
                        const Color(0xFFEAEAF0),
                        const Color(0xFFD7DAE2),
                      ),
                      size: Size.square(size),
                    )
                  : null,
            ),
          ),
        ),
      ),
    );
  }
}

/// 隐私信任徽章。
class PrivacyBadge extends StatelessWidget {
  final String text;
  const PrivacyBadge({super.key, this.text = '本地离线 · 数据不出本机'});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.accentSoft,
        borderRadius: BorderRadius.circular(AppRadius.pill),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.lock_outline_rounded, size: 14, color: AppColors.accent),
          const SizedBox(width: 6),
          Text(text,
              style: TextStyle(
                  color: AppColors.accent,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  height: 16 / 12)),
        ],
      ),
    );
  }
}
