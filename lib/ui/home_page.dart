import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../theme/app_theme.dart';
import '../theme/app_widgets.dart';
import 'editor_page.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  Future<void> _pick(ImageSource source, BuildContext context) async {
    final picker = ImagePicker();
    final xfile = await picker.pickImage(source: source, imageQuality: 100);
    if (xfile == null) return;
    final bytes = await xfile.readAsBytes();
    if (!context.mounted) return;
    Navigator.of(context).push(
      PageRouteBuilder(
        pageBuilder: (_, __, ___) => EditorPage(originalBytes: bytes),
        transitionsBuilder: (_, anim, __, child) => FadeTransition(
          opacity: anim,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0, 0.03),
              end: Offset.zero,
            ).animate(CurvedAnimation(parent: anim, curve: Curves.easeOut)),
            child: child,
          ),
        ),
        transitionDuration: const Duration(milliseconds: 220),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.s6,
            vertical: AppSpacing.s8,
          ),
          child: Column(
            children: [
              const PrivacyBadge(),
              const SizedBox(height: AppSpacing.s10),
              const AppLogo(size: 88),
              const SizedBox(height: AppSpacing.s5),
              Text('证件照工作室',
                  style: Theme.of(context)
                      .textTheme
                      .displayLarge
                      ?.copyWith(letterSpacing: -0.5)),
              const SizedBox(height: AppSpacing.s2),
              Text('本地离线 · 一键生成标准证件照',
                  style: Theme.of(context)
                      .textTheme
                      .bodyLarge
                      ?.copyWith(color: cs.onSurfaceVariant)),
              const SizedBox(height: AppSpacing.s8),
              AppCard(
                elevation: 1,
                child: Column(
                  children: [
                    AppButton(
                      label: '从相册选择',
                      icon: Icons.photo_library_rounded,
                      variant: AppButtonVariant.primary,
                      fullWidth: true,
                      onPressed: () => _pick(ImageSource.gallery, context),
                    ),
                    const SizedBox(height: AppSpacing.s3),
                    AppButton(
                      label: '拍照',
                      icon: Icons.camera_alt_rounded,
                      variant: AppButtonVariant.secondary,
                      fullWidth: true,
                      onPressed: () => _pick(ImageSource.camera, context),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.s5),
              Wrap(
                spacing: AppSpacing.s2,
                runSpacing: AppSpacing.s2,
                alignment: WrapAlignment.center,
                children: const [
                  _FeatureChip(icon: Icons.auto_awesome_rounded, label: 'AI 自动抠图'),
                  _FeatureChip(icon: Icons.photo_size_select_actual_rounded, label: '标准尺寸排版'),
                  _FeatureChip(icon: Icons.shield_outlined, label: '隐私保护'),
                ],
              ),
              const SizedBox(height: AppSpacing.s8),
              Text(
                '打开图片后自动抠图、自动校正方向，\n可拖动 / 缩放选区，一键导出标准证件照。',
                textAlign: TextAlign.center,
                style: Theme.of(context)
                    .textTheme
                    .labelMedium
                    ?.copyWith(color: cs.onSurfaceVariant),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FeatureChip extends StatelessWidget {
  final IconData icon;
  final String label;
  const _FeatureChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: cs.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(AppRadius.pill),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: AppColors.accent),
          const SizedBox(width: 6),
          Text(label,
              style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: cs.onSurface,
                  height: 16 / 12)),
        ],
      ),
    );
  }
}
