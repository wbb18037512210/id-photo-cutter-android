#!/usr/bin/env bash
# ============================================================
#  一键打包并签名 APK（macOS / Linux）
#  前置：flutter、JDK 17、Android SDK 已加入 PATH
#  用法：bash build_and_sign.sh   （在工程根目录执行）
# ============================================================
set -e
cd "$(dirname "$0")"

echo "==================================================="
echo "  身份证头像抠图 - 打包并签名 release APK"
echo "==================================================="

# 0) 前置检查
command -v flutter >/dev/null 2>&1 || { echo "[ERROR] 未检测到 flutter，请先安装 Flutter SDK 并加入 PATH"; exit 1; }
command -v java   >/dev/null 2>&1 || { echo "[ERROR] 未检测到 java(JDK 17)，请安装 JDK 17 并加入 PATH"; exit 1; }

# 1) 模型文件检查
if [ ! -f "assets/models/u2net_human_seg.onnx" ]; then
  echo "[ERROR] 缺少模型文件 assets/models/u2net_human_seg.onnx"
  echo "  请从桌面版 id-photo-cutter/models/ 复制 u2net_human_seg.onnx 到本工程 assets/models/"
  echo "  （或改用更小的 u2netp.onnx，改 lib/core/segmenter.dart 的 MODEL_ASSET 即可）"
  exit 1
fi

# 2) 拉取依赖
echo "[2/5] flutter pub get"
flutter pub get

# 3) 生成/补齐 Android 工程
echo "[3/5] flutter create --platforms=android ."
flutter create --platforms=android .

# 4) 注入签名配置 + 平台补丁
echo "[4/5] 注入签名配置与 AndroidManifest/proguard 补丁"
cp -f android_build_sign/key.properties android/key.properties
cp -f android_build_sign/build.gradle.kts android/app/build.gradle.kts
cp -f platform_patches/AndroidManifest.xml android/app/src/main/AndroidManifest.xml
[ -f android/app/proguard-rules.pro ] || cp -f platform_patches/proguard-rules.pro android/app/proguard-rules.pro

# 5) 构建并自动签名
echo "[5/5] flutter build apk --release"
flutter build apk --release

echo ""
echo "==================================================="
echo "  完成！已签名 APK 位于："
echo "  build/app/outputs/flutter-apk/app-release.apk"
echo "==================================================="
echo "安装到手机： adb install build/app/outputs/flutter-apk/app-release.apk"
echo "（keystore: android_build_sign/release-key.jks  alias=idphotocutter）"
