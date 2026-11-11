"""Where the Kokoro model lives and how to download it."""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

RELEASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"
# fp32 rather than int8: on a laptop CPU (Core Ultra 5 125H) it synthesized
# about 1.6x faster, and it is the reference quality.
MODEL_FILE = "kokoro-v1.0.onnx"
VOICES_FILE = "voices-v1.0.bin"

DATA_DIR = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "narrate"
MODEL_PATH = DATA_DIR / MODEL_FILE
VOICES_PATH = DATA_DIR / VOICES_FILE


def is_downloaded() -> bool:
    return MODEL_PATH.is_file() and VOICES_PATH.is_file()


def _fetch(url: str, dest: Path) -> None:
    partial = dest.with_suffix(dest.suffix + ".part")
    print(f"Baixando {dest.name}...")
    with urllib.request.urlopen(url) as response, open(partial, "wb") as out:
        total = int(response.headers.get("Content-Length", 0))
        done = 0
        while chunk := response.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done / 1e6:5.0f} / {total / 1e6:.0f} MB", end="", flush=True)
    print()
    partial.rename(dest)


def download() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, path in ((MODEL_FILE, MODEL_PATH), (VOICES_FILE, VOICES_PATH)):
        if path.is_file():
            print(f"Já baixado: {path}")
            continue
        _fetch(f"{RELEASE_URL}/{name}", path)
    print(f"Pronto. Arquivos em {DATA_DIR}")
