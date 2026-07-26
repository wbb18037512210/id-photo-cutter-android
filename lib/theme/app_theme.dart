import 'package:flutter/material.dart';

/// Aperture Design System —— 跨平台统一设计 token（安卓端实现）。
/// 颜色 / 间距 / 圆角 / 阴影 / 渐变 / 文本主题，全部集中在此，双端共用同一套数值。

class AppColors {
  // 强调色（亮暗一致）
  static const Color accent = Color(0xFF5B5BE8);
  static const Color accentStrong = Color(0xFF4636D6);
  static const Color accentSoft = Color(0xFFECECFB);
  static const Color onAccent = Color(0xFFFFFFFF);

  // 语义色
  static const Color success = Color(0xFF1F9D6B);
  static const Color warning = Color(0xFFE0A106);
  static const Color danger = Color(0xFFE5484D);

  // 证件照标准底色
  static const Color bgWhite = Color(0xFFFFFFFF);
  static const Color bgBlue = Color(0xFF2F6FE0);
  static const Color bgRed = Color(0xFFE0494D);

  // 亮色主题
  static const Color canvasLight = Color(0xFFF5F6F8);
  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color surface2Light = Color(0xFFFBFBFD);
  static const Color surface3Light = Color(0xFFF1F2F6);
  static const Color inkLight = Color(0xFF14161C);
  static const Color ink2Light = Color(0xFF5A606E);
  static const Color ink3Light = Color(0xFF9298A6);
  static const Color borderLight = Color(0xFFE7E9EF);
  static const Color borderStrongLight = Color(0xFFD8DBE3);

  // 暗色主题
  static const Color canvasDark = Color(0xFF0E0F13);
  static const Color surfaceDark = Color(0xFF17191F);
  static const Color surface2Dark = Color(0xFF1C1F27);
  static const Color surface3Dark = Color(0xFF252934);
  static const Color inkDark = Color(0xFFECEEF3);
  static const Color ink2Dark = Color(0xFFA4AAB6);
  static const Color ink3Dark = Color(0xFF6E7480);
  static const Color borderDark = Color(0xFF272B34);
  static const Color borderStrongDark = Color(0xFF363B46);
}

class AppSpacing {
  static const double s1 = 4;
  static const double s2 = 8;
  static const double s3 = 12;
  static const double s4 = 16;
  static const double s5 = 20;
  static const double s6 = 24;
  static const double s8 = 32;
  static const double s10 = 40;
  static const double s12 = 48;
  static const double s16 = 64;
}

class AppRadius {
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 22;
  static const double pill = 999;
}

class AppShadows {
  static List<BoxShadow> sm(BuildContext context) => [
        BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 2,
            offset: const Offset(0, 1)),
        BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 3,
            offset: const Offset(0, 1)),
      ];
  static List<BoxShadow> md(BuildContext context) => [
        BoxShadow(
            color: Colors.black.withValues(alpha: 0.08),
            blurRadius: 16,
            offset: const Offset(0, 6)),
      ];
  static List<BoxShadow> lg(BuildContext context) => [
        BoxShadow(
            color: Colors.black.withValues(alpha: 0.12),
            blurRadius: 40,
            offset: const Offset(0, 16)),
      ];
  static List<BoxShadow> accent(BuildContext context) => [
        BoxShadow(
            color: AppColors.accent.withValues(alpha: 0.30),
            blurRadius: 28,
            offset: const Offset(0, 10)),
      ];
}

class AppGradients {
  static const LinearGradient primary = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
  );
}

class AppTheme {
  static ThemeData light() => _build(
        brightness: Brightness.light,
        canvas: AppColors.canvasLight,
        surface: AppColors.surfaceLight,
        surface2: AppColors.surface2Light,
        surface3: AppColors.surface3Light,
        ink: AppColors.inkLight,
        ink2: AppColors.ink2Light,
        ink3: AppColors.ink3Light,
        border: AppColors.borderLight,
        borderStrong: AppColors.borderStrongLight,
      );

  static ThemeData dark() => _build(
        brightness: Brightness.dark,
        canvas: AppColors.canvasDark,
        surface: AppColors.surfaceDark,
        surface2: AppColors.surface2Dark,
        surface3: AppColors.surface3Dark,
        ink: AppColors.inkDark,
        ink2: AppColors.ink2Dark,
        ink3: AppColors.ink3Dark,
        border: AppColors.borderDark,
        borderStrong: AppColors.borderStrongDark,
      );

  static ThemeData _build({
    required Brightness brightness,
    required Color canvas,
    required Color surface,
    required Color surface2,
    required Color surface3,
    required Color ink,
    required Color ink2,
    required Color ink3,
    required Color border,
    required Color borderStrong,
  }) {
    final colorScheme = ColorScheme(
      brightness: brightness,
      primary: AppColors.accent,
      onPrimary: AppColors.onAccent,
      secondary: AppColors.accent,
      onSecondary: AppColors.onAccent,
      surface: surface,
      onSurface: ink,
      surfaceContainerHighest: surface3,
      outline: border,
      outlineVariant: borderStrong,
      error: AppColors.danger,
      onError: Colors.white,
      shadow: Colors.black,
    );

    final baseText = TextTheme(
      displayLarge: _t(ink, 32, 40, FontWeight.w700),
      displayMedium: _t(ink, 26, 34, FontWeight.w700),
      titleLarge: _t(ink, 20, 28, FontWeight.w600),
      titleMedium: _t(ink, 17, 24, FontWeight.w600),
      bodyLarge: _t(ink, 16, 24, FontWeight.w400),
      bodyMedium: _t(ink2, 14, 20, FontWeight.w400),
      labelLarge: _t(ink, 13, 18, FontWeight.w600),
      labelMedium: _t(ink2, 12, 16, FontWeight.w400),
      labelSmall: _t(ink3, 11, 14, FontWeight.w500),
    ).apply(fontFamilyFallback: const [
      'Inter',
      'PingFang SC',
      'Microsoft YaHei',
      'Noto Sans SC',
    ]);

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: canvas,
      fontFamilyFallback: const [
        'Inter',
        'PingFang SC',
        'Microsoft YaHei',
        'Noto Sans SC',
      ],
      textTheme: baseText,
      appBarTheme: AppBarTheme(
        backgroundColor: surface,
        foregroundColor: ink,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: _t(ink, 17, 24, FontWeight.w600),
        iconTheme: IconThemeData(color: ink2, size: 22),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.accent,
          foregroundColor: AppColors.onAccent,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppRadius.md)),
          textStyle: _t(ink, 13, 18, FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: ink,
          side: BorderSide(color: borderStrong),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppRadius.md)),
          textStyle: _t(ink, 13, 18, FontWeight.w600),
        ),
      ),
      cardTheme: CardThemeData(
        color: surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          side: BorderSide(color: border, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      dividerTheme: DividerThemeData(color: border, thickness: 1),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: ink,
        contentTextStyle: _t(Colors.white, 13, 18, FontWeight.w500),
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md)),
        elevation: 0,
      ),
      iconTheme: IconThemeData(color: ink2, size: 22),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppColors.accent,
      ),
    );
  }

  static TextStyle _t(Color c, double s, double h, FontWeight w) =>
      TextStyle(color: c, fontSize: s, height: h / s, fontWeight: w);
}
