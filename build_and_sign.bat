@echo off
REM ============================================================
REM  一键打包并签名 APK（Windows）
REM  前置：Flutter SDK、JDK 17、Android SDK 已加入 PATH
REM  用法：双击运行，或在工程根目录执行 build_and_sign.bat
REM ============================================================
setlocal
cd /d %~dp0

echo ===================================================
echo  身份证头像抠图 - 打包并签名 release APK
echo ===================================================

REM 0) 前置检查
where flutter >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未检测到 flutter，请先安装 Flutter SDK (https://flutter.dev) 并加入 PATH
  pause & exit /b 1
)
where java >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未检测到 java(JDK 17)，请安装 JDK 17 并加入 PATH
  pause & exit /b 1
)

REM 1) 模型文件检查（离线抠图必需，176MB，需自备）
if not exist "assets\models\u2net_human_seg.onnx" (
  echo [ERROR] 缺少模型文件 assets\models\u2net_human_seg.onnx
  echo   请从桌面版 id-photo-cutter\models\ 复制 u2net_human_seg.onnx 到本工程 assets\models\
  echo   （或改用更小的 u2netp.onnx，改 lib\core\segmenter.dart 的 MODEL_ASSET 即可）
  pause & exit /b 1
)

REM 2) 拉取依赖
echo [2/5] flutter pub get
call flutter pub get
if errorlevel 1 pause & exit /b 1

REM 3) 生成/补齐 Android 工程
echo [3/5] flutter create --platforms=android .
call flutter create --platforms=android .
if errorlevel 1 pause & exit /b 1

REM 4) 注入签名配置 + 平台补丁
echo [4/5] 注入签名配置与 AndroidManifest/proguard 补丁
copy /Y android_build_sign\key.properties android\key.properties
copy /Y android_build_sign\build.gradle.kts android\app\build.gradle.kts
copy /Y platform_patches\AndroidManifest.xml android\app\src\main\AndroidManifest.xml
if not exist android\app\proguard-rules.pro copy /Y platform_patches\proguard-rules.pro android\app\proguard-rules.pro

REM 5) 构建并自动签名
echo [5/5] flutter build apk --release
call flutter build apk --release
if errorlevel 1 pause & exit /b 1

echo.
echo ===================================================
echo  完成！已签名 APK 位于：
echo  build\app\outputs\flutter-apk\app-release.apk
echo ===================================================
echo 安装到手机： adb install build\app\outputs\flutter-apk\app-release.apk
echo （keystore: android_build_sign\release-key.jks  alias=idphotocutter）
pause
