# 身份证头像抠图 · Android 版

本地离线运行的身份证头像抠图 App（Flutter + ONNX Runtime Mobile）。
**完全在手机端推理，不上传任何服务器**，复用桌面版同款 `u2net_human_seg.onnx` 模型。

> 💡 **也有 Windows 桌面版**：仓库 `desktop/` 目录是同一套算法的 PyQt6 桌面程序源码，
> 已打包为 `id-photo-cutter-windows-x64.zip` 放在 **Releases**（解压后双击 `头像抠图.exe` 即可用，完全离线、三个模型内置）。

功能与桌面版对齐：
- 打开图片（相册/拍照）后**自动抠图**、**自动校正方向为横向**
- **自动检测人像**并框选（可“重新检测”）
- 选区可**拖动 / 缩放 / 左右旋转源图**
- 结果**强制拉伸到 500×670**，默认**白底**（也可选透明）
- 一键**保存到相册**（文件名 `头像_时间`）

---

## 一、环境要求（你本机需提前装好）

1. **Flutter SDK** ≥ 3.19（建议最新稳定版）
   安装后确认：`flutter doctor` 中 Android toolchain 就绪。
   - 下载：https://docs.flutter.dev/get-started/install
2. **JDK 17**（Flutter 3.x 编译必须，仅有 JRE 不够）
   - 下载：https://adoptium.net 选 Temurin 17
3. **Android SDK**（build-tools 34、platforms android-34、platform-tools）
   - 通过 Android Studio 的 SDK Manager 或 `sdkmanager` 装好。
4. 一台 Android 手机（Android 5.0+）或模拟器。

> ✅ **已出包（Android + Windows 双端）**：
> - **Android**：`app-release.apk`（v1.0.0，已签名 v1+v2+v3，模型 `u2net_human_seg.onnx` 已内置）→ 见 **Releases** 下载安装。
> - **Windows 桌面版**：`id-photo-cutter-windows-x64.zip`（独立 PyQt6 程序，三个模型全部内置，完全离线双击即用）→ 见 **Releases** 下载解压运行。
>
> 下方步骤用于你在本机从源码重新构建（Android 见第二节起；Windows 见 `desktop/` 目录，内含打包脚本 `build_exe.bat`）。

---

## 二、放置模型文件（必须先做）

App 需要本地模型 `u2net_human_seg.onnx`（约 176 MB，你桌面版里已有）。

把模型复制到工程目录：

    id-photo-cutter-android/assets/models/u2net_human_seg.onnx

来源（任选其一）：
- 桌面版工程：`id-photo-cutter/models/u2net_human_seg.onnx`
- 本机 rembg 缓存：`%USERPROFILE%\.u2net\u2net_human_seg.onnx`

> 想用更小的模型（更快、精度略低）：把 `u2netp.onnx`（约 4.7 MB）放进来，
> 并修改 `lib/core/segmenter.dart` 里的
> `MODEL_ASSET = 'assets/models/u2netp.onnx'`。

---

## 三、打包并签名 APK（推荐：一键脚本）

工程已内置**签名密钥**与**一键脚本**，本机运行即产出**已签名**的 release APK：

- 密钥库：`android_build_sign/release-key.jks`（alias=`idphotocutter`，RSA 2048，有效期 25 年）
- 配置：`android_build_sign/key.properties`、`android_build_sign/build.gradle.kts`（已含 `signingConfigs`，release 自动签名）
- 脚本：`build_and_sign.bat`（Windows）/ `build_and_sign.sh`（macOS/Linux）

### 一键出包

```bash
# Windows：先放好模型（见第二节），双击 build_and_sign.bat 或在工程根目录执行：
build_and_sign.bat

# macOS / Linux：
bash build_and_sign.sh
```

脚本会自动：① 检查模型 → ② `flutter pub get` → ③ 生成 android 工程 →
④ 注入签名配置 + 覆盖 AndroidManifest/proguard → ⑤ `flutter build apk --release`（自动 v1+v2+v3 签名）。

产物：`build/app/outputs/flutter-apk/app-release.apk`
安装：`adb install build/app/outputs/flutter-apk/app-release.apk`

> 不想用内置密钥？删除 `android/key.properties` 即回退为未签名构建；
> 或用自己的密钥：替换 `android_build_sign/release-key.jks` 并改 `key.properties` 的
> `storePassword / keyAlias / keyPassword`。

### 手动分步（等价操作）

```bash
flutter pub get
flutter create --platforms=android .
cp android_build_sign/key.properties   android/key.properties
cp android_build_sign/build.gradle.kts android/app/build.gradle.kts
cp platform_patches/AndroidManifest.xml android/app/src/main/AndroidManifest.xml
cp platform_patches/proguard-rules.pro  android/app/proguard-rules.pro
flutter build apk --release
```

### 已有未签名 apk → 仅做对齐 + 签名（用 Android SDK 自带 apksigner）

```bash
# 对齐
"%ANDROID_HOME%/build-tools/34.0.0/zipalign" -p 4 app-unsigned.apk app-unsigned-aligned.apk
# 签名
"%ANDROID_HOME%/build-tools/34.0.0/apksigner" sign ^
  --ks android_build_sign/release-key.jks ^
  --ks-key-alias idphotocutter ^
  --ks-pass pass:idPhotoCutter2026 ^
  --key-pass pass:idPhotoCutter2026 ^
  --out app-release.apk app-unsigned-aligned.apk
# 校验
"%ANDROID_HOME%/build-tools/34.0.0/apksigner" verify --verbose app-release.apk
```

---

## 四、运行测试（坐标映射正确性）

不需要手机，纯 Dart 单测验证旋转/拉伸/合成的坐标映射：

```bash
flutter test
```

覆盖：正向映射保面积、红块落点、rotateCCW 后落点、白底合成。

---

## 五、项目结构

```
lib/
  main.dart                 入口
  core/
    segmenter.dart          ONNX 加载 + u2net 推理（320 蒙版）
    image_processor.dart   归一化/横屏校正/人像框/旋转/拉伸合成
  ui/
    home_page.dart          首页（选图/拍照）
    editor_page.dart        编辑器（自动检测/预览/旋转/保存）
    widgets/crop_canvas.dart 可交互选区画布
assets/models/             模型放这里（见上）
test/transform_test.dart   坐标映射单测
platform_patches/          安卓 Manifest / proguard / minSdk 补丁
```

## 六、隐私说明

所有图像与模型推理均在设备本地完成，不会联网、不会上传任何个人信息。
唯一用到的网络权限是 Flutter 模板默认的 `INTERNET`（本 App 实际不发任何网络请求）。

---

## 七、常见问题

- **打包后打开闪退 / 推理崩溃**：检查 `proguard-rules.pro` 是否覆盖成功（必须保留 `ai.onnxruntime.**`）。
- **`minSdk` 报错**：把 `android/app/build.gradle` 里 `minSdk` 改成 21。
- **模型缺失报错**：确认 `assets/models/u2net_human_seg.onnx` 已放置，`flutter pub get` 后重新 `flutter build apk`。
- **Android 13 以下保存失败**：老系统需要存储权限，可在手机设置里手动授予“文件和媒体”权限，或集成 `permission_handler` 运行时申请。
