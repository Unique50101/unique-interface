"""Start an opt-in, temporary HTTPS relay for one running UI."""
import hashlib
import os
import platform
import queue
import re
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

VERSION = "2026.11.2"
CHECKSUMS = {
    "cloudflared-linux-amd64": "56f13335143ec0e22772963290683a84a04114a35ec64cbc794a4d39ff9bb8cf",
    "cloudflared-linux-arm64": "04a7b7f08bce85d56b26ffe1fdbfbb21a074495a363d16f0783c40e25b5c5281",
    "cloudflared-darwin-amd64.tgz": "6153d9ec629174882a3adbff2f7dc5a24b4f3bdd7ccc38eaa84fba26eb890311",
    "cloudflared-darwin-arm64.tgz": "f6d58eeec91ad1ec5fd1f7e4a587303772929b2625be5d24068033851c36ff55",
    "cloudflared-windows-amd64.exe": "555b46c85582461d189cac30d14ad05480d612613801be9f110b8ce08c5b2113",
}


def executable():
    installed = shutil.which("cloudflared")
    if installed:
        return installed
    system = platform.system().lower()
    arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine().lower(), platform.machine().lower())
    ext = {"darwin": ".tgz", "windows": ".exe"}.get(system, "")
    asset = f"cloudflared-{system}-{arch}{ext}"
    if asset not in CHECKSUMS:
        raise RuntimeError("Install cloudflared on PATH to enable public sharing on this platform.")
    cache = Path.home() / ".cache" / "unique-interface" / VERSION / asset.replace(".tgz", "-archive")
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / ("cloudflared.exe" if system == "windows" else "cloudflared")
    if target.is_file():
        return str(target)
    with tempfile.TemporaryDirectory(dir=cache) as tmp:
        archive = Path(tmp) / asset
        url = f"https://github.com/cloudflare/cloudflared/releases/download/{VERSION}/{asset}"
        with urllib.request.urlopen(url, timeout=90) as response, archive.open("wb") as out:
            shutil.copyfileobj(response, out)
        digest = hashlib.sha256()
        with archive.open("rb") as source:
            for chunk in iter(lambda: source.read(1 << 20), b""):
                digest.update(chunk)
        if digest.hexdigest() != CHECKSUMS[asset]:
            raise RuntimeError("The cloudflared download failed checksum verification.")
        binary = archive
        if ext == ".tgz":
            binary = Path(tmp) / "client"
            with tarfile.open(archive) as bundle, binary.open("wb") as out:
                member = next(m for m in bundle if m.isfile() and Path(m.name).name == "cloudflared")
                with bundle.extractfile(member) as src:
                    shutil.copyfileobj(src, out)
        binary.chmod(0o700)
        os.replace(binary, target)
    return str(target)


def stop(process):
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def connect(local_url, register):
    process = subprocess.Popen([executable(), "tunnel", "--no-autoupdate", "--protocol", "http2",
                                "--url", local_url], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, errors="replace")
    urls = queue.Queue()

    def read():
        for line in process.stdout:
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com\b", line)
            if match and match.group() != "https://api.trycloudflare.com":
                urls.put(match.group())
        urls.put(None)

    threading.Thread(target=read, daemon=True).start()
    try:
        url = urls.get(timeout=60)
        if not url:
            raise RuntimeError("The public relay exited before issuing a URL.")
        register(url)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline and process.poll() is None:
            try:
                with urllib.request.urlopen(url + "/health", timeout=4) as response:
                    if response.read(100) == b"unique-interface-ready":
                        return process, url
            except OSError:
                pass
            time.sleep(1)
        raise RuntimeError("The relay URL was issued but the running app could not be reached.")
    except BaseException:
        stop(process)
        raise
