# 防止 R8 / ProGuard 压缩掉 ONNX Runtime 的 JNI 绑定
-keep class ai.onnxruntime.** { *; }
-keep class com.microsoft.onnxruntime.** { *; }
