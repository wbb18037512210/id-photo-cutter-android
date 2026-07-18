import os, re, glob

cache = "/c/Users/Administrator/AppData/Local/Pub/Cache/hosted"
patched = []
for bg in glob.glob(os.path.join(cache, "*", "*", "android", "build.gradle")):
    s = open(bg, encoding="utf-8").read()
    if "com.android.library" not in s:
        continue
    if "namespace" in s:
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
    # 注入 namespace 到 android { 块首行
    new_block = "android {\n    namespace '%s'\n" % pkg
    s2 = s.replace("android {", new_block, 1)
    if s2 != s:
        open(bg, "w", encoding="utf-8").write(s2)
        patched.append((pkg, bg))

print("PATCHED_COUNT=%d" % len(patched))
for pkg, bg in patched:
    print("  + %s  ->  %s" % (pkg, bg))
