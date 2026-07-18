#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flutter create 之后执行：把 Google / Gradle 源换成国内镜像，并注入本地签名配置。

用法（在工程根目录运行，android/ 已生成）：
    python3 patch_android.py

本脚本会探测生成的构建脚本是 Kotlin DSL(.kts) 还是 Groovy(.gradle)，
并据此注入签名配置（release 构建用 android_build_sign/release-key.jks），
无需手工改。
"""
import os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
AND = os.path.join(ROOT, "android")
if not os.path.isdir(AND):
    print("[ERR] android/ 不存在，请先 flutter create --platforms=android .")
    sys.exit(1)

TENCENT_MAVEN = "https://mirrors.cloud.tencent.com/nexus/repository/maven-public/"
TENCENT_PLUGIN = "https://mirrors.cloud.tencent.com/nexus/repository/gradle-plugin/"
TENCENT_GRADLE = "https://mirrors.cloud.tencent.com/gradle/"

# 签名信息（与 android_build_sign/release-key.jks 对应，路径相对 android/ 目录）
KEYSTORE_REL = "../android_build_sign/release-key.jks"
STORE_PW = "idPhotoCutter2026"
KEY_ALIAS = "idphotocutter"
KEY_PW = "idPhotoCutter2026"


def patch_settings():
    for name in ("settings.gradle.kts", "settings.gradle"):
        p = os.path.join(AND, name)
        if os.path.exists(p):
            break
    else:
        print("[WARN] 未找到 settings.gradle(.kts)"); return
    is_kts = name.endswith(".kts")
    s = open(p, encoding="utf-8").read()
    s2 = s
    if is_kts:
        # Kotlin DSL：maven { url = uri("...") }
        s2 = re.sub(r"\bgoogle\s*\(\)", f'maven {{ url = uri("{TENCENT_MAVEN}") }}', s2)
        s2 = re.sub(r"\bmavenCentral\s*\(\)", f'maven {{ url = uri("{TENCENT_MAVEN}") }}', s2)
        s2 = re.sub(r"\bgradlePluginPortal\s*\(\)", f'maven {{ url = uri("{TENCENT_PLUGIN}") }}', s2)
        # 清理：把任何残留的 Groovy 风格 maven { url '...' } 转成 Kotlin 风格
        s2 = re.sub(r"maven\s*\{\s*url\s*'([^']+)'\s*\}",
                    r'maven { url = uri("\1") }', s2)
    else:
        s2 = re.sub(r"\bgoogle\s*\(\)", f"maven {{ url '{TENCENT_MAVEN}' }}", s2)
        s2 = re.sub(r"\bmavenCentral\s*\(\)", f"maven {{ url '{TENCENT_MAVEN}' }}", s2)
        s2 = re.sub(r"\bgradlePluginPortal\s*\(\)", f"maven {{ url '{TENCENT_PLUGIN}' }}", s2)
    if s2 != s:
        open(p, "w", encoding="utf-8").write(s2)
        print(f"[ok] 镜像注入 {name}")
    else:
        print(f"[WARN] {name} 无需替换（可能已是镜像）")


def patch_wrapper():
    p = os.path.join(AND, "gradle", "wrapper", "gradle-wrapper.properties")
    if not os.path.exists(p):
        print("[WARN] 未找到 gradle-wrapper.properties"); return
    s = open(p, encoding="utf-8").read()
    m = re.search(r"distributionUrl=https?\\?://[^/]+/.*?/gradle-([\d.]+)-all\.zip", s)
    if not m:
        print("[WARN] 未匹配 distributionUrl"); return
    new = f"distributionUrl={TENCENT_GRADLE}gradle-{m.group(1)}-all.zip"
    s2 = re.sub(r"distributionUrl=.*", new, s)
    open(p, "w", encoding="utf-8").write(s2)
    print(f"[ok] gradle 分发镜像 -> {new}")


def patch_gradle_props():
    p = os.path.join(AND, "gradle.properties")
    if not os.path.exists(p):
        print("[WARN] 未找到 gradle.properties"); return
    s = open(p, encoding="utf-8").read()
    if "-Xmx" not in s:
        s = s.rstrip() + "\norg.gradle.jvmargs=-Xmx3072m -XX:MaxMetaspaceSize=1024m\n"
        open(p, "w", encoding="utf-8").write(s)
        print("[ok] gradle.properties 提升堆内存 -Xmx3072m")
    else:
        print("[info] gradle.properties 已有 -Xmx，跳过")


def inject_signing():
    # 1) 探测 app 构建脚本 DSL
    kts = os.path.join(AND, "app", "build.gradle.kts")
    groovy = os.path.join(AND, "app", "build.gradle")
    if os.path.exists(kts):
        build_file, dsl = kts, "kts"
    elif os.path.exists(groovy):
        build_file, dsl = groovy, "groovy"
    else:
        print("[ERR] 未找到 app/build.gradle(.kts)"); return
    print(f"[info] 检测到构建脚本 DSL: {dsl} ({os.path.basename(build_file)})")

    s = open(build_file, encoding="utf-8").read()

    if dsl == "kts":
        signing_block = (
            '    signingConfigs {\n'
            f'        create("release") {{\n'
            f'            storeFile = file("{KEYSTORE_REL}")\n'
            f'            storePassword = "{STORE_PW}"\n'
            f'            keyAlias = "{KEY_ALIAS}"\n'
            f'            keyPassword = "{KEY_PW}"\n'
            '        }\n'
            '    }\n'
        )
        if 'create("release")' not in s:
            s = re.sub(r'(\n\s*)buildTypes\s*\{',
                       lambda m: m.group(1) + signing_block + m.group(1) + "buildTypes {",
                       s, count=1)
        s = re.sub(r'signingConfig\s*=\s*signingConfigs\.getByName\("debug"\)',
                   'signingConfig = signingConfigs.getByName("release")', s)
        s = re.sub(r'signingConfig\s*=\s*signingConfigs\.debug',
                   'signingConfig = signingConfigs.getByName("release")', s)
    else:
        signing_block = (
            '    signingConfigs {\n'
            '        release {\n'
            f"            storeFile file('{KEYSTORE_REL}')\n"
            f"            storePassword '{STORE_PW}'\n"
            f"            keyAlias '{KEY_ALIAS}'\n"
            f"            keyPassword '{KEY_PW}'\n"
            '        }\n'
            '    }\n'
        )
        if 'signingConfigs {' not in s:
            s = re.sub(r'(\n\s*)buildTypes\s*\{',
                       lambda m: m.group(1) + signing_block + m.group(1) + "buildTypes {",
                       s, count=1)
        s = re.sub(r'signingConfig\s+signingConfigs\.debug',
                   'signingConfig signingConfigs.release', s)
        s = re.sub(r'signingConfig\s*=\s*signingConfigs\.debug',
                   'signingConfig signingConfigs.release', s)

    open(build_file, "w", encoding="utf-8").write(s)
    print(f"[ok] 注入签名配置 -> {os.path.basename(build_file)}")

    # 2) 覆盖 Manifest / proguard 平台补丁
    pairs = [
        ("platform_patches/AndroidManifest.xml", "android/app/src/main/AndroidManifest.xml"),
        ("platform_patches/proguard-rules.pro", "android/app/proguard-rules.pro"),
    ]
    for src, dst in pairs:
        s = os.path.join(ROOT, src); d = os.path.join(ROOT, dst)
        if not os.path.exists(s):
            print(f"[WARN] 源缺失 {src}"); continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        open(d, "w", encoding="utf-8").write(open(s, encoding="utf-8").read())
        print(f"[ok] 注入 {dst}")


def fix_plugin_namespaces():
    """修复废弃插件在 AGP 8+ 缺少 namespace 的问题（如 image_gallery_saver）。
    这些插件的 android/build.gradle 只声明了 manifest 的 package，未声明 android{ namespace }，
    而新版 AGP 强制要求每个库模块有 namespace。直接给 pub 缓存里的插件补上。
    必须在 flutter pub get 之后运行（缓存已填充）。
    """
    import glob as _glob
    # 定位 pub 缓存的 hosted 目录
    cache = os.environ.get("PUB_CACHE")
    if not cache:
        if os.name == "nt":
            cache = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Pub", "Cache")
        else:
            cache = os.path.expanduser("~/.pub-cache")
    hosted = os.path.join(cache, "hosted")
    if not os.path.isdir(hosted):
        print(f"[WARN] 未找到 pub 缓存 hosted 目录: {hosted}（跳过 namespace 修复）")
        return
    patched = 0
    for bg in _glob.glob(os.path.join(hosted, "*", "*", "android", "build.gradle")):
        try:
            s = open(bg, encoding="utf-8").read()
        except Exception:
            continue
        if "com.android.library" not in s or "namespace" in s:
            continue
        d = os.path.dirname(bg)
        mf = os.path.join(d, "src", "main", "AndroidManifest.xml")
        pkg = None
        if os.path.exists(mf):
            m = re.search(r'package="([^"]+)"', open(mf, encoding="utf-8").read())
            if m:
                pkg = m.group(1)
        if not pkg:
            m = re.search(r"group '([^']+)'", s)
            if m:
                pkg = m.group(1)
        if not pkg:
            continue
        s2 = s.replace("android {", "android {\n    namespace '%s'\n" % pkg, 1)
        if s2 != s:
            open(bg, "w", encoding="utf-8").write(s2)
            patched += 1
            print(f"[ok] 补 namespace {pkg} -> {os.path.basename(os.path.dirname(os.path.dirname(bg)))}")
    print(f"[info] namespace 修复完成，共 {patched} 个插件")


if __name__ == "__main__":
    patch_settings()
    patch_wrapper()
    patch_gradle_props()
    fix_plugin_namespaces()
    inject_signing()
    print("PATCH_DONE")
