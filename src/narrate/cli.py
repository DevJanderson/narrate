"""narrate: read text aloud in Brazilian Portuguese with Kokoro.

Text comes from --text, from stdin, or else from the current selection
(the primary selection on Wayland or X11). Running it again while it speaks
stops it.
"""

from __future__ import annotations

import argparse
import ctypes.util
import glob
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path

from . import model
from .text import clean_markdown, split_chunks

LANG = "pt-br"
DEFAULT_VOICE = "pf_dora"
VOICES = ("pf_dora", "pm_alex", "pm_santa")
THREADS = 4
NICENESS = 10
SAMPLE_RATE = 24000
CHUNK_PAUSE_SECONDS = 0.25

# Where distributions install espeak-ng's data (Arch, Fedora, Debian/Ubuntu,
# source builds).
ESPEAK_DATA_CANDIDATES = (
    "/usr/share/espeak-ng-data",
    "/usr/lib64/espeak-ng-data",
    "/usr/lib/*/espeak-ng-data",
    "/usr/local/share/espeak-ng-data",
)


def _runtime_dir() -> Path:
    base = os.environ.get("XDG_RUNTIME_DIR")
    path = Path(base) / "narrate" if base else Path(f"/tmp/narrate-{os.getuid()}")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    return path


PID_FILE = _runtime_dir() / "narrate.pid"


def _notify(message: str) -> None:
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "--", "narrate", message], check=False)
    print(f"narrate: {message}", file=sys.stderr)


def _running_pid() -> int | None:
    try:
        pid = int(PID_FILE.read_text().strip())
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
    except (OSError, ValueError):
        return None
    return pid if pid != os.getpid() and b"narrate" in cmdline else None


def _stop_running() -> bool:
    pid = _running_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return False
    finally:
        # The killed process gets no chance to clean up after itself.
        PID_FILE.unlink(missing_ok=True)
    return True


def _selection_commands() -> list[list[str]]:
    commands = []
    if os.environ.get("WAYLAND_DISPLAY"):
        commands.append(["wl-paste", "--primary", "--no-newline"])
    if os.environ.get("DISPLAY"):
        commands.append(["xclip", "-out", "-selection", "primary"])
        commands.append(["xsel", "--primary", "--output"])
    return commands


def _read_selection() -> str | None:
    """The selected text, "" if nothing is selected, None if no tool to read it."""
    found_tool = False
    for command in _selection_commands():
        try:
            result = subprocess.run(
                command, check=False, capture_output=True, text=True, timeout=2
            )
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            found_tool = True
            continue
        found_tool = True
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    return "" if found_tool else None


def _espeak_config():
    """Prefer the system espeak-ng; the copy bundled with kokoro-onnx's
    dependency has had packaging bugs. None falls back to that copy."""
    from kokoro_onnx.config import EspeakConfig

    library = ctypes.util.find_library("espeak-ng")
    if not library:
        return None
    for pattern in ESPEAK_DATA_CANDIDATES:
        for data_path in sorted(glob.glob(pattern)):
            if os.path.isfile(os.path.join(data_path, "phontab")):
                return EspeakConfig(lib_path=library, data_path=data_path)
    return None


def _load_kokoro():
    import onnxruntime as rt
    from kokoro_onnx import Kokoro

    options = rt.SessionOptions()
    options.intra_op_num_threads = THREADS
    options.inter_op_num_threads = 1
    session = rt.InferenceSession(
        str(model.MODEL_PATH), sess_options=options, providers=["CPUExecutionProvider"]
    )
    return Kokoro.from_session(session, str(model.VOICES_PATH), espeak_config=_espeak_config())


def _speak(chunks: list[str], voice: str, speed: float) -> None:
    import numpy as np
    import sounddevice as sd

    kokoro = _load_kokoro()
    audio_queue: queue.Queue = queue.Queue(maxsize=2)

    def produce() -> None:
        try:
            for chunk in chunks:
                audio, _ = kokoro.create(chunk, voice=voice, speed=speed, lang=LANG)
                audio_queue.put(audio)
        except Exception as error:  # noqa: BLE001 - reported by the player
            audio_queue.put(error)
        finally:
            audio_queue.put(None)

    threading.Thread(target=produce, daemon=True).start()

    pause = np.zeros((int(CHUNK_PAUSE_SECONDS * SAMPLE_RATE), 1), dtype=np.float32)
    with sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        while (item := audio_queue.get()) is not None:
            if isinstance(item, Exception):
                raise item
            stream.write(np.asarray(item, dtype=np.float32).reshape(-1, 1))
            stream.write(pause)


def _speed(value: str) -> float:
    speed = float(value)
    if not 0.5 <= speed <= 2.0:
        raise argparse.ArgumentTypeError("use um valor entre 0.5 e 2.0")
    return speed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="narrate",
        description="Lê texto em voz alta em português do Brasil. Lê o texto de "
        "--text, da entrada padrão ou o texto selecionado; rodar de novo "
        "enquanto fala interrompe a leitura.",
    )
    parser.add_argument("--text", help="texto a ler, em vez da entrada padrão ou da seleção")
    parser.add_argument("--voice", choices=VOICES,
                        default=os.environ.get("NARRATE_VOICE", DEFAULT_VOICE),
                        help=f"voz (padrão: {DEFAULT_VOICE})")
    parser.add_argument("--speed", type=_speed, default=os.environ.get("NARRATE_SPEED", "1.0"),
                        help="velocidade de 0.5 a 2.0 (padrão: 1.0)")
    parser.add_argument("--stop", action="store_true", help="interrompe a leitura em andamento")
    parser.add_argument("--download-model", action="store_true",
                        help=f"baixa o modelo Kokoro (~340 MB) para {model.DATA_DIR}")
    args = parser.parse_args(argv)

    if args.download_model:
        model.download()
        return 0

    if args.stop:
        _stop_running()
        return 0

    text = args.text
    if text is None and not sys.stdin.isatty():
        text = sys.stdin.read()
    explicit = bool(text and text.strip())

    # From the selection, a second press means "stop"; given text replaces
    # whatever is being read.
    if _stop_running() and not explicit:
        return 0

    if not model.is_downloaded():
        _notify("Modelo não encontrado. Rode: narrate --download-model")
        return 1

    if not explicit:
        text = _read_selection()
        if text is None:
            _notify("Não consegui ler a seleção. Instale wl-clipboard (Wayland) ou xclip (X11).")
            return 1
    chunks = split_chunks(clean_markdown(text))
    if not chunks:
        _notify("Nenhum texto selecionado.")
        return 0

    # SIGTERM keeps its default action: a Python handler would only run after
    # the blocking audio write returns, so stopping would lag by a whole chunk.
    PID_FILE.write_text(str(os.getpid()))
    try:
        os.nice(NICENESS)
        _speak(chunks, args.voice, args.speed)
    except Exception as error:  # noqa: BLE001 - surface any failure to the user
        _notify(f"Erro: {error}")
        return 1
    finally:
        if _running_pid() is None:
            PID_FILE.unlink(missing_ok=True)
    return 0
