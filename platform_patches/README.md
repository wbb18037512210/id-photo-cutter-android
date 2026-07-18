# 安卓平台补丁（应用步骤见项目根目录 README.md）

本目录里的文件需要覆盖到 `flutter create` 生成的安卓工程里，否则会缺权限或打包后 ONNX 推理崩溃。

## 1. AndroidManifest.xml
覆盖：`android/app/src/main/AndroidManifest.xml`

作用：声明相册/相机/存储权限，并把 App 名称改成“身份证头像抠图”。

## 2. proguard-rules.pro
覆盖：`android/app/proguard-rules.pro`

作用：保留 ONNX Runtime 的 JNI 类，避免 Release 构建被 R8 误删导致运行时崩溃。

## 3. minSdk（手动改一行）
打开 `android/app/build.gradle`，在 `defaultConfig` 里确认：

    defaultConfig {
        ...
        minSdk = 21   // 必须 >= 21（ONNX Runtime Mobile 要求）
        targetSdk = 34
        ...
    }

如果你的 Flutter 版本生成的默认 minSdk 已经 >= 21，则无需改动。

> 提示：ONNX Runtime Mobile 在 Android 5.0（API 21）及以上均可运行；
> 若想启用 NNAPI 硬件加速可把 minSdk 提到 27，但通常没必要。
