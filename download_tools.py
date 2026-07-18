import os, zipfile, urllib.request

ROOT = r"C:/Users/Administrator/WorkBuddy/2026-07-15-15-03-23/_tools"
os.makedirs(ROOT, exist_ok=True)

def read(p):
    return open(p, encoding="utf-8").read().strip()

FL = read("_flutter_dl.txt")
JDK = read("_jdk_dl.txt")

def download(url, dest, label):
    print(f"[dl] {label}\n  {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
        total = 0
        while True:
            b = r.read(1024 * 1024)
            if not b:
                break
            f.write(b); total += len(b)
            if total % (50 * 1024 * 1024) < 1024 * 1024:
                print(f"  ... {total/1024/1024:.0f} MB", flush=True)
    print(f"[ok] {label}: {total/1024/1024:.1f} MB", flush=True)

def unzip(zpath, outdir):
    print(f"[unzip] {zpath}", flush=True)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(outdir)
    print(f"[ok] unzipped", flush=True)

download(FL, os.path.join(ROOT, "flutter.zip"), "Flutter")
unzip(os.path.join(ROOT, "flutter.zip"), ROOT)
print("FLUTTER_DIR=" + os.path.join(ROOT, "flutter"), flush=True)

download(JDK, os.path.join(ROOT, "jdk17.zip"), "JDK 17")
unzip(os.path.join(ROOT, "jdk17.zip"), os.path.join(ROOT, "jdk17"))
for d in os.listdir(os.path.join(ROOT, "jdk17")):
    if d.startswith("jdk-17"):
        print("JAVA_HOME=" + os.path.join(ROOT, "jdk17", d), flush=True)
        break
print("ALL_DONE", flush=True)
