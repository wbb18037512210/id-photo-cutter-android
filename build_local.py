#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本机（沙箱）实际编译并签名 release APK 的编排脚本。
前提：download_tools.py 已把 Flutter / JDK17 下到 ../_tools/，且模型已放入 assets/models/。
用法：python3 build_local.py    （会后台跑很久，建议 run_in_background）
"""
import os, sys, glob, subprocess, shutil

ROOT = os.path.abspath(os.path.dirname(__file__))
TOOLS = os.path.normpath(os.path.join(ROOT, "..", "_tools"))
LOG = os.path.join(ROOT, "build_log.txt")

# ---- 定位工具 ----
flutter = os.path.join(TOOLS, "flutter", "bin", "flutter.bat")
if not os.path.exists(flutter):
    flutter = os.path.join(TOOLS, "flutter", "bin", "flutter")
if not os.path.exists(flutter):
    print("[FATAL] 找不到 Flutter: " + flutter); sys.exit(1)

jdk_cands = sorted(glob.glob(os.path.join(TOOLS, "jdk17", "jdk-17*")))
if not jdk_cands:
    print("[FATAL] 找不到 JDK17"); sys.exit(1)
JAVA_HOME = jdk_cands[0]
print("[info] JAVA_HOME =", JAVA_HOME)

android_sdk = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME") or r"C:\Android"

# ---- 环境 ----
env = dict(os.environ)
env["JAVA_HOME"] = JAVA_HOME
env["ANDROID_SDK_ROOT"] = android_sdk
env["ANDROID_HOME"] = android_sdk
env["FLUTTER_STORAGE_BASE_URL"] = "https://storage.flutter-io.cn"
env["PUB_HOSTED_URL"] = "https://mirrors.cloud.tencent.com/dart-pub/"
env["PATH"] = os.pathsep.join([
    os.path.join(TOOLS, "flutter", "bin"),
    os.path.join(JAVA_HOME, "bin"),
    env.get("PATH", ""),
])
# 避免 Gradle 守护进程在沙箱里卡死
env["GRADLE_OPTS"] = (env.get("GRADLE_OPTS", "") + " -Dorg.gradle.daemon=false").strip()

def run(step, args):
    print(f"\n===== [{step}] {' '.join(args)} =====", flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"\n===== [{step}] {' '.join(args)} =====\n")
    p = subprocess.run(args, cwd=ROOT, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                       encoding="utf-8", errors="replace")
    # 实时写日志
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(p.stdout or "")
    # 终端也输出末尾，便于观察进度
    tail = (p.stdout or "")[-1500:]
    print(tail, flush=True)
    if p.returncode != 0:
        print(f"[FATAL] 步骤 [{step}] 失败，返回码 {p.returncode}。详见 build_log.txt", flush=True)
        sys.exit(p.returncode)
    print(f"[ok] [{step}] 完成", flush=True)

# 清空旧日志
open(LOG, "w", encoding="utf-8").close()

run("pub_get", [flutter, "pub", "get"])
run("create", [flutter, "create", "--platforms=android", "."])
run("patch", [sys.executable, "patch_android.py"])
# buildTypes 默认 minifyEnabled 由模板决定；对 release 显式关闭压缩以保 onnxruntime JNI
run("build", [flutter, "build", "apk", "--release", "--no-pub"])

apk = os.path.join(ROOT, "build", "app", "outputs", "flutter-apk", "app-release.apk")
if os.path.exists(apk):
    print("\n[SUCCESS] 已签名 APK:", apk, flush=True)
    print("大小(bytes):", os.path.getsize(apk), flush=True)
else:
    print("\n[FATAL] 未找到产物 app-release.apk", flush=True)
    sys.exit(2)
print("BUILD_LOCAL_DONE", flush=True)
