#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
#
#  ██╗   ██╗ █████╗ ███████╗██╗      ██████╗ ██████╗     ██╗   ██╗██████╗
#  ██║   ██║██╔══██╗██╔════╝██║     ██╔═══██╗██╔══██╗    ██║   ██║╚════██╗
#  ██║   ██║███████║█████╗  ██║     ██║   ██║██████╔╝    ██║   ██║ █████╔╝
#  ╚██╗ ██╔╝██╔══██║██╔══╝  ██║     ██║   ██║██╔══██╗    ╚██╗ ██╔╝██╔═══╝
#   ╚████╔╝ ██║  ██║███████╗███████╗╚██████╔╝██║  ██║     ╚████╔╝ ███████╗
#    ╚═══╝  ╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝      ╚═══╝  ╚══════╝
#
#  VAELOR v2.0 — COMPUTER USE AGENT — ULTIMATE EDITION
#  ─────────────────────────────────────────────────────────────────────────
#  • Wavy blue sea animated border overlay on all 4 screen edges
#  • User input locked while AI operates  (Ctrl+Shift+Q = emergency abort)
#  • Floating always-on-top reasoning popup  (live steps + screenshot thumb)
#  • Real smooth bezier cursor control  (user can watch it move)
#  • Full vision model AND text-only model support
#  • Robust retry logic  (circuit-breaker, non-retryable error fast-fail)
#  • 30+ tools, rich tool-result rendering, anti-stall engine
#  • Cross-platform  (Windows primary, Linux/macOS graceful fallback)
#
#  INSTALL:
#    pip install pyautogui pillow requests rich psutil pyperclip pynput
#    pip install opencv-python-headless   # optional
#
#  RUN:
#    python vaelor.py --key YOUR_OPENROUTER_KEY --model baidu/qianfan-ocr-fast:free
#    python vaelor.py --key KEY --task "open notepad and write hello world"
# =============================================================================

from __future__ import annotations

# ── Standard library ──────────────────────────────────────────────────────────
import ast
import base64
import colorsys
import contextlib
import copy
import ctypes
import ctypes.wintypes
import datetime
import functools
import hashlib
import io
import json
import logging
import math
import os
import platform
import queue
import random
import re
import shlex
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import traceback
import typing
import uuid
import tkinter as tk
import tkinter.font as tkfont
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Dict, Generator, List,
    Literal, Optional, Sequence, Tuple, Type, Union,
)

# ── Optional heavy imports ────────────────────────────────────────────────────
try:
    import pyautogui
    pyautogui.FAILSAFE   = True
    pyautogui.PAUSE      = 0.03
    HAS_PYAUTOGUI        = True
except ImportError:
    HAS_PYAUTOGUI        = False

try:
    from PIL import Image, ImageDraw, ImageGrab, ImageFont, ImageFilter, ImageEnhance
    HAS_PIL              = True
except ImportError:
    HAS_PIL              = False

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    HAS_REQUESTS         = True
except ImportError:
    HAS_REQUESTS         = False

try:
    from rich.console    import Console
    from rich.panel      import Panel
    from rich.syntax     import Syntax
    from rich.table      import Table
    from rich.progress   import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.layout     import Layout
    from rich.live       import Live
    from rich.markdown   import Markdown
    from rich.text       import Text
    from rich.tree       import Tree
    from rich.prompt     import Prompt, Confirm
    from rich.align      import Align
    from rich            import box as rbox
    HAS_RICH             = True
    console              = Console(highlight=True)
except ImportError:
    HAS_RICH             = False
    class _FC:
        def print(self, *a, **kw): print(*a)
        def rule(self, *a, **kw):  print("─" * 70)
        def log(self, *a, **kw):   print("[LOG]", *a)
    console = _FC()

try:
    import psutil
    HAS_PSUTIL           = True
except ImportError:
    HAS_PSUTIL           = False

try:
    import pyperclip
    HAS_CLIPBOARD        = True
except ImportError:
    HAS_CLIPBOARD        = False

try:
    from pynput import keyboard as pynput_keyboard
    from pynput import mouse    as pynput_mouse
    HAS_PYNPUT           = True
except ImportError:
    HAS_PYNPUT           = False

try:
    import cv2
    import numpy as np
    HAS_CV2              = True
except ImportError:
    HAS_CV2              = False


# =============================================================================
# §1  CONSTANTS & GLOBALS
# =============================================================================

VERSION               = "2.0.0"
AGENT_NAME            = "Vaelor"
MAX_STEPS             = 150
SCREENSHOT_QUAL       = 82           # JPEG quality for API (balance quality/size)
MAX_IMG_WIDTH         = 1366         # resize if wider
MAX_IMG_HEIGHT        = 768          # resize if taller
TOKEN_BUDGET          = 8192
CTX_WINDOW_MSGS       = 22
LOOP_SLEEP_MS         = 60
OPENROUTER_BASE       = "https://openrouter.ai/api/v1"
TOOL_RESULT_TRUNC     = 3000
LOG_DIR               = Path.home() / ".vaelor" / "logs"
SESSION_DIR           = Path.home() / ".vaelor" / "sessions"
CONFIG_PATH           = Path.home() / ".vaelor" / "config.json"
ABORT_HOTKEY          = "<ctrl>+<shift>+q"     # emergency kill
PAUSE_HOTKEY          = "<ctrl>+<shift>+p"     # pause/resume

# HTTP status codes that must NEVER be retried
NON_RETRYABLE_HTTP    = {400, 401, 403, 404, 405, 406, 410, 422, 451}

# ── Sea / ocean blue color palette for the overlay animation ─────────────────
SEA_PALETTE = [
    "#03045e", "#023e8a", "#0077b6", "#0096c7",
    "#00b4d8", "#48cae4", "#90e0ef", "#ade8f4", "#caf0f8",
]

# ── Vision-capable model identifiers (OpenRouter slugs) ──────────────────────
VISION_MODEL_HINTS: Tuple[str, ...] = (
    "gpt-4o", "gpt-4-vision", "gpt-4.1",
    "claude-3", "claude-3.5", "claude-4", "claude-sonnet", "claude-opus",
    "gemini", "gemma",
    "llava", "vision", "pixtral",
    "qwen-vl", "qwen2-vl", "qwen2.5-vl",
    "internvl", "phi-3-vision", "phi-4",
    "minicpm", "cogvlm", "idefics",
    "deepseek-vl", "moondream", "yi-vl",
    "qianfan-ocr", "baidu/qianfan",
    "mistral-pixtral", "llama-3.2-vision", "llama4",
)

# ── Global abort / pause events (shared across threads) ──────────────────────
ABORT_EVENT  = threading.Event()   # set to kill agent immediately
PAUSE_EVENT  = threading.Event()   # set to pause between steps

# ── Global queues for overlay ↔ agent communication ─────────────────────────
REASONING_QUEUE: queue.Queue = queue.Queue(maxsize=200)  # text updates
SCREENSHOT_QUEUE: queue.Queue= queue.Queue(maxsize=5)   # PIL Image objects


# =============================================================================
# §2  SYSTEM PROMPTS
# =============================================================================

SYSTEM_PROMPT_VISION = """\
You are Vaelor, an elite autonomous Computer Use Agent with VISION capability.
You receive a live screenshot at every reasoning step.

════════════════════════════════════════════════════════════
  NON-NEGOTIABLE OPERATING RULES
════════════════════════════════════════════════════════════

1.  PERCEIVE FIRST — always call `screenshot` at the start of each step so you
    see the current screen state before deciding anything.

2.  THINK, THEN ACT — use the `think` tool to plan before each non-trivial
    action. Never click blindly.

3.  VERIFY EVERY ACTION — after any click, type, or key press, call
    `screenshot` again to confirm the expected change occurred.

4.  ADAPT ON FAILURE — if the screen did not change as expected, analyse why
    and try a different approach immediately.

5.  ANTI-STALL RULE — if you issue the exact same tool call 3 times in a row
    without progress, you MUST try a completely different approach.

6.  TOKEN EFFICIENCY — never explain yourself unless asked. Only emit tool
    calls or a final answer. No filler prose.

7.  COMPLETE WITH EVIDENCE — call `task_complete` only after a final screenshot
    confirms the task is done. Include what you see as proof.

COORDINATE SYSTEM: origin (0,0) = top-left corner of the primary monitor.
All x, y values are absolute screen pixels.
"""

SYSTEM_PROMPT_TEXT = """\
You are Vaelor, an elite autonomous Computer Use Agent operating in TEXT MODE.
You CANNOT see the screen. Use tools to gather information and act.

════════════════════════════════════════════════════════════
  TEXT-MODE OPERATING RULES
════════════════════════════════════════════════════════════

1.  INFORMATION FIRST — call `list_windows`, `run_command`, `get_clipboard`,
    or `read_file` to understand current system state before acting.

2.  PREFER TERMINAL — use `run_command` to open apps (e.g. `start notepad`),
    check state (e.g. `tasklist`), and verify results.

3.  VERIFY VIA OUTPUT — after every GUI action, call `list_windows` or
    `run_command` to confirm the change happened.

4.  KEYBOARD-FIRST — use hotkeys and keyboard shortcuts rather than
    coordinate-based clicks when possible, since you cannot see the screen.

5.  ANTI-STALL — same action 3× without progress → completely different approach.

6.  TOKEN EFFICIENT — only emit tool calls or final answers.

7.  DONE — call `task_complete` only after terminal/command output confirms
    the task is fully complete.
"""


# =============================================================================
# §3  ENUMERATIONS & DATA CLASSES
# =============================================================================

class ActionType(str, Enum):
    SCREENSHOT       = "screenshot"
    CLICK            = "click"
    DOUBLE_CLICK     = "double_click"
    RIGHT_CLICK      = "right_click"
    MIDDLE_CLICK     = "middle_click"
    MOVE             = "move"
    DRAG             = "drag"
    SCROLL           = "scroll"
    TYPE_TEXT        = "type_text"
    KEY_PRESS        = "key_press"
    HOTKEY           = "hotkey"
    COPY             = "copy"
    PASTE            = "paste"
    GET_CLIPBOARD    = "get_clipboard"
    SET_CLIPBOARD    = "set_clipboard"
    OPEN_APP         = "open_app"
    CLOSE_APP        = "close_app"
    SWITCH_WINDOW    = "switch_window"
    LIST_WINDOWS     = "list_windows"
    RUN_COMMAND      = "run_command"
    READ_FILE        = "read_file"
    WRITE_FILE       = "write_file"
    LIST_DIR         = "list_dir"
    FIND_ON_SCREEN   = "find_on_screen"
    WAIT             = "wait"
    WAIT_FOR_CHANGE  = "wait_for_change"
    GET_SCREEN_INFO  = "get_screen_info"
    TASK_COMPLETE    = "task_complete"
    THINK            = "think"
    GET_MOUSE_POS    = "get_mouse_position"
    ZOOM_REGION      = "zoom_region"
    SEND_KEYS        = "send_keys"

class StepStatus(str, Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    SUCCESS  = "success"
    FAILED   = "failed"
    SKIPPED  = "skipped"
    ABORTED  = "aborted"

class OverlayState(str, Enum):
    HIDDEN  = "hidden"
    ACTIVE  = "active"
    PAUSED  = "paused"
    DONE    = "done"

@dataclass
class ScreenInfo:
    width:          int
    height:         int
    scale_factor:   float = 1.0
    monitor_count:  int   = 1

    def center(self) -> Tuple[int, int]:
        return self.width // 2, self.height // 2

    def clamp(self, x: int, y: int) -> Tuple[int, int]:
        return (
            max(1, min(x, self.width  - 1)),
            max(1, min(y, self.height - 1)),
        )

@dataclass
class ActionResult:
    success:    bool
    output:     str                   = ""
    error:      str                   = ""
    screenshot: Optional[bytes]       = None
    metadata:   Dict[str, Any]        = field(default_factory=dict)

    def truncated_output(self, limit: int = TOOL_RESULT_TRUNC) -> str:
        out = self.output or ""
        if len(out) > limit:
            half = limit // 2
            snip = f"\n…[{len(out) - limit} chars omitted]…\n"
            return out[:half] + snip + out[-half:]
        return out

    def full_for_context(self) -> str:
        """Return output+error combined for context injection."""
        parts = []
        if self.output:
            parts.append(self.output)
        if self.error and not self.success:
            parts.append(f"⚠ ERROR: {self.error}")
        return "\n".join(parts) or "(no output)"

@dataclass
class ToolCall:
    id:         str
    name:       str
    arguments:  Dict[str, Any]
    result:     Optional[ActionResult] = None
    ts_start:   float = field(default_factory=time.time)
    ts_end:     Optional[float]        = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.ts_end is not None:
            return (self.ts_end - self.ts_start) * 1000
        return None

    def pretty_args(self, max_len: int = 60) -> str:
        parts = []
        for k, v in self.arguments.items():
            sv = repr(v)
            if len(sv) > max_len:
                sv = sv[:max_len] + "…"
            parts.append(f"{k}={sv}")
        return ", ".join(parts)

@dataclass
class AgentStep:
    index:      int
    model_msg:  str
    tool_calls: List[ToolCall] = field(default_factory=list)
    status:     StepStatus    = StepStatus.PENDING
    tokens_in:  int           = 0
    tokens_out: int           = 0
    elapsed_ms: float         = 0.0

@dataclass
class TaskSession:
    id:          str                = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task:        str                = ""
    model:       str                = ""
    is_vision:   bool               = False
    steps:       List[AgentStep]    = field(default_factory=list)
    start_time:  float              = field(default_factory=time.time)
    end_time:    Optional[float]    = None
    success:     bool               = False
    aborted:     bool               = False
    final_msg:   str                = ""
    total_in:    int                = 0
    total_out:   int                = 0

    @property
    def elapsed(self) -> float:
        return (self.end_time or time.time()) - self.start_time

    def to_dict(self) -> Dict:
        return {
            "id":          self.id,
            "task":        self.task[:120],
            "model":       self.model,
            "is_vision":   self.is_vision,
            "steps":       len(self.steps),
            "elapsed_s":   round(self.elapsed, 2),
            "success":     self.success,
            "aborted":     self.aborted,
            "final_msg":   self.final_msg[:200],
            "tokens_in":   self.total_in,
            "tokens_out":  self.total_out,
        }

@dataclass
class CircuitBreakerState:
    failures:      int   = 0
    last_failure:  float = 0.0
    open:          bool  = False
    threshold:     int   = 5
    reset_after_s: float = 60.0

    def record_failure(self):
        self.failures     += 1
        self.last_failure  = time.time()
        if self.failures >= self.threshold:
            self.open = True

    def record_success(self):
        self.failures = 0
        self.open     = False

    def should_attempt(self) -> bool:
        if not self.open:
            return True
        if time.time() - self.last_failure > self.reset_after_s:
            self.open     = False
            self.failures  = 0
            return True
        return False


# =============================================================================
# §4  LOGGING
# =============================================================================

class VaelorLogger:
    _instance: Optional["VaelorLogger"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "VaelorLogger":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = LOG_DIR / f"vaelor_{ts}.log"
        fmt  = logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S"
        )
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(fmt)
        self._log  = logging.getLogger("vaelor")
        self._log.setLevel(logging.DEBUG)
        if not self._log.handlers:
            self._log.addHandler(fh)
        self._path = path

    def _rq(self, text: str):
        """Push text to the reasoning popup queue."""
        with contextlib.suppress(queue.Full):
            REASONING_QUEUE.put_nowait(text)

    def info(self, msg: str):
        self._log.info(msg)
        self._rq(f"ℹ {msg}")
        if HAS_RICH:
            console.print(f"[dim]{msg}[/dim]")

    def success(self, msg: str):
        self._log.info("✓ " + msg)
        self._rq(f"✓ {msg}")
        if HAS_RICH:
            console.print(f"[bold green]✓[/bold green] {msg}")
        else:
            print("✓", msg)

    def warn(self, msg: str):
        self._log.warning(msg)
        self._rq(f"⚠ {msg}")
        if HAS_RICH:
            console.print(f"[bold yellow]⚠[/bold yellow]  {msg}")
        else:
            print("⚠", msg)

    def error(self, msg: str):
        self._log.error(msg)
        self._rq(f"✗ {msg}")
        if HAS_RICH:
            console.print(f"[bold red]✗[/bold red]  {msg}")
        else:
            print("✗", msg)

    def debug(self, msg: str):
        self._log.debug(msg)

    def step(self, idx: int, msg: str):
        self._log.info(f"STEP {idx}  {msg[:150]}")
        self._rq(f"\n{'─'*40}\nStep {idx}\n{msg[:500]}")
        if HAS_RICH:
            console.rule(f"[bold cyan]Step {idx}[/bold cyan]")
            if msg.strip():
                console.print(Markdown(msg[:800]))
        else:
            print(f"\n── Step {idx} ──")
            print(msg[:500])

    def tool(self, name: str, args: Dict, result: ActionResult):
        icon   = "✓" if result.success else "✗"
        color  = "green" if result.success else "red"
        arg_s  = ", ".join(f"{k}={repr(v)[:35]}" for k, v in args.items())
        self._log.debug(f"TOOL {icon} {name}({arg_s})")
        self._rq(f"  {icon} {name}({arg_s[:80]})")
        if HAS_RICH:
            console.print(
                f"  [{color}]{icon}[/{color}] "
                f"[bold cyan]{name}[/bold cyan]"
                f"([dim]{arg_s[:90]}[/dim])"
            )

    def model_response(self, text: str):
        if text.strip():
            self._rq(f"\n🤖 {text[:600]}")
            if HAS_RICH:
                console.print(Panel(text[:600], title="[bold]Model[/bold]", border_style="blue"))

    @property
    def log_path(self) -> Path:
        return self._path


log = VaelorLogger()


# =============================================================================
# §5  CONFIGURATION MANAGER
# =============================================================================

class ConfigManager:
    DEFAULTS: Dict[str, Any] = {
        "openrouter_key":     "",
        "default_model":      "openai/gpt-4o",
        "screenshot_qual":    SCREENSHOT_QUAL,
        "max_steps":          MAX_STEPS,
        "loop_sleep_ms":      LOOP_SLEEP_MS,
        "safe_mode":          True,
        "save_sessions":      True,
        "save_screenshots":   False,
        "verbose":            False,
        "overlay_enabled":    True,
        "input_lock_enabled": True,
        "popup_enabled":      True,
        "mouse_speed":        0.35,        # seconds for a full-screen traverse
        "mouse_mode":         "bezier",    # bezier | linear | instant
        "abort_hotkey":       ABORT_HOTKEY,
        "pause_hotkey":       PAUSE_HOTKEY,
        "overlay_border_px":  60,
        "popup_opacity":      0.92,
    }

    def __init__(self, overrides: Optional[Dict] = None):
        self._d: Dict[str, Any] = copy.deepcopy(self.DEFAULTS)
        self._load_file()
        self._load_env()
        if overrides:
            self._d.update({k: v for k, v in overrides.items() if v is not None})

    def _load_file(self):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH) as f:
                    self._d.update(json.load(f))
            except Exception as e:
                log.warn(f"Config unreadable: {e}")

    def _load_env(self):
        mapping = {
            "OPENROUTER_API_KEY": "openrouter_key",
            "VAELOR_MODEL":       "default_model",
            "VAELOR_VERBOSE":     "verbose",
            "VAELOR_SAFE_MODE":   "safe_mode",
        }
        for env, key in mapping.items():
            val = os.environ.get(env)
            if val is not None:
                if isinstance(self.DEFAULTS.get(key), bool):
                    self._d[key] = val.lower() in ("1", "true", "yes")
                else:
                    self._d[key] = val

    def save(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(self._d, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._d.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._d[key]

    def __setitem__(self, key: str, value: Any):
        self._d[key] = value


# =============================================================================
# §6  MODEL CAPABILITY DETECTOR
# =============================================================================

def model_supports_vision(model_id: str) -> bool:
    """Return True if the model slug suggests vision/multimodal capability."""
    low = model_id.lower()
    return any(hint in low for hint in VISION_MODEL_HINTS)


def model_supports_tools(model_id: str) -> bool:
    """
    Most models on OpenRouter support function calling.
    Return False only for known text-completion-only slugs.
    """
    low = model_id.lower()
    no_tools = ("instruct", "base", "completion", ":free")
    # Many free models do support tools; only flag known exceptions
    known_no_tools = ("llama-2", "mistral-7b-instruct-v0.1")
    return not any(k in low for k in known_no_tools)


# =============================================================================
# §7  SCREEN CAPTURE ENGINE
# =============================================================================

class ScreenCapture:
    """
    Multi-backend screenshot engine.
    Produces JPEG bytes + base64 string ready for vision APIs.
    Also streams thumbnails to the overlay popup.
    """

    def __init__(self, cfg: ConfigManager):
        self._cfg   = cfg
        self._info  = self._detect_screen()
        self._lock  = threading.Lock()

    # ── public ───────────────────────────────────────────────────────────────

    def capture(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        annotate_cursor: bool = False,
    ) -> Tuple[bytes, str]:
        """
        Capture screen (or region).
        Returns (jpeg_bytes, base64_string).
        Also pushes a PIL thumbnail to SCREENSHOT_QUEUE.
        """
        with self._lock:
            img = self._grab(region)
            if annotate_cursor and HAS_PYAUTOGUI:
                img = self._draw_cursor(img, region)
            img = self._resize(img)
            # Push thumbnail for popup
            thumb = img.copy()
            thumb.thumbnail((320, 200), Image.LANCZOS)
            with contextlib.suppress(queue.Full):
                SCREENSHOT_QUEUE.put_nowait(thumb)
            # Encode
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=self._cfg.get("screenshot_qual", SCREENSHOT_QUAL))
            raw = buf.getvalue()
            b64 = base64.b64encode(raw).decode()
            return raw, b64

    def capture_region(self, x: int, y: int, w: int, h: int) -> Tuple[bytes, str]:
        return self.capture(region=(x, y, w, h))

    def capture_around(self, x: int, y: int, pad: int = 120) -> Tuple[bytes, str]:
        si = self._info
        x0 = max(0, x - pad); y0 = max(0, y - pad)
        x1 = min(si.width, x + pad); y1 = min(si.height, y + pad)
        return self.capture(region=(x0, y0, x1 - x0, y1 - y0))

    @property
    def screen_info(self) -> ScreenInfo:
        return self._info

    # ── internals ────────────────────────────────────────────────────────────

    def _grab(self, region: Optional[Tuple[int, int, int, int]]) -> "Image.Image":
        if not HAS_PIL:
            raise RuntimeError("Pillow required: pip install pillow")
        bbox = None
        if region:
            x, y, w, h = region
            bbox = (x, y, x + w, y + h)
        # Method 1: PIL ImageGrab (Windows/macOS)
        try:
            img = ImageGrab.grab(bbox=bbox, all_screens=True)
            return img.convert("RGB")
        except Exception:
            pass
        # Method 2: pyautogui
        if HAS_PYAUTOGUI:
            try:
                img = pyautogui.screenshot(region=region)
                return img.convert("RGB")
            except Exception:
                pass
        # Method 3: Linux scrot / gnome-screenshot / import
        if sys.platform.startswith("linux"):
            return self._grab_linux(bbox)
        raise RuntimeError("No screenshot backend available")

    def _grab_linux(self, bbox: Optional[Tuple]) -> "Image.Image":
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp = f.name
        try:
            if shutil.which("scrot"):
                cmd = ["scrot", "-z", tmp]
            elif shutil.which("gnome-screenshot"):
                cmd = ["gnome-screenshot", "-f", tmp]
            elif shutil.which("import"):
                cmd = ["import", "-window", "root", tmp]
            else:
                raise RuntimeError("Install scrot: sudo apt install scrot")
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            img = Image.open(tmp).convert("RGB")
            if bbox:
                img = img.crop(bbox)
            return img
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp)

    def _resize(self, img: "Image.Image") -> "Image.Image":
        w, h = img.size
        mw   = MAX_IMG_WIDTH
        mh   = MAX_IMG_HEIGHT
        if w > mw or h > mh:
            scale = min(mw / w, mh / h)
            img   = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        return img

    def _draw_cursor(self, img: "Image.Image", region) -> "Image.Image":
        """Draw a red crosshair at the current cursor position."""
        try:
            cx, cy = pyautogui.position()
            if region:
                rx, ry, rw, rh = region
                cx -= rx; cy -= ry
            draw = ImageDraw.Draw(img)
            r = 12
            draw.ellipse([(cx-r, cy-r), (cx+r, cy+r)], outline=(255,40,40), width=3)
            draw.line([(cx-r-5, cy), (cx+r+5, cy)], fill=(255,40,40), width=2)
            draw.line([(cx, cy-r-5), (cx, cy+r+5)], fill=(255,40,40), width=2)
        except Exception:
            pass
        return img

    def _detect_screen(self) -> ScreenInfo:
        if HAS_PYAUTOGUI:
            try:
                sw, sh = pyautogui.size()
                return ScreenInfo(width=sw, height=sh)
            except Exception:
                pass
        if HAS_PIL:
            try:
                img = ImageGrab.grab()
                return ScreenInfo(width=img.width, height=img.height)
            except Exception:
                pass
        return ScreenInfo(width=1920, height=1080)


# =============================================================================
# §8  MOUSE CONTROLLER  (real smooth bezier, visible movement)
# =============================================================================

class MouseController:
    """
    Human-like mouse controller with bezier curves.
    Every move is visible: cursor physically travels across the screen.
    """

    def __init__(self, screen: ScreenInfo, cfg: ConfigManager):
        self._si   = screen
        self._cfg  = cfg
        self._last = (screen.width // 2, screen.height // 2)

    # ── core actions ─────────────────────────────────────────────────────────

    def move(
        self,
        x: int,
        y: int,
        duration: Optional[float] = None,
        mode: Optional[str] = None,
    ) -> ActionResult:
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        x, y = self._si.clamp(x, y)
        dur   = duration if duration is not None else self._auto_duration(x, y)
        mmode = mode or self._cfg.get("mouse_mode", "bezier")
        try:
            if mmode == "instant":
                pyautogui.moveTo(x, y, _pause=False)
            elif mmode == "bezier":
                self._bezier(x, y, dur)
            else:
                pyautogui.moveTo(x, y, duration=dur, tween=pyautogui.easeInOutQuad)
            self._last = (x, y)
            return ActionResult(True, output=f"Moved → ({x},{y})")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def click(
        self,
        x: int,
        y: int,
        button:   str   = "left",
        clicks:   int   = 1,
        interval: float = 0.10,
    ) -> ActionResult:
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        x, y = self._si.clamp(x, y)
        try:
            # Move there first (visible travel)
            mv = self.move(x, y)
            if not mv.success:
                return mv
            time.sleep(0.06)                      # brief pause so user sees where we clicked
            pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)
            self._last = (x, y)
            label = f"{'Double-c' if clicks==2 else 'C'}lick[{button}] @ ({x},{y})"
            return ActionResult(True, output=label)
        except Exception as e:
            return ActionResult(False, error=str(e))

    def double_click(self, x: int, y: int) -> ActionResult:
        return self.click(x, y, clicks=2)

    def right_click(self, x: int, y: int) -> ActionResult:
        return self.click(x, y, button="right")

    def middle_click(self, x: int, y: int) -> ActionResult:
        return self.click(x, y, button="middle")

    def drag(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
        duration: float = 0.6,
        button:   str   = "left",
    ) -> ActionResult:
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        x1, y1 = self._si.clamp(x1, y1)
        x2, y2 = self._si.clamp(x2, y2)
        try:
            self.move(x1, y1)
            time.sleep(0.08)
            pyautogui.mouseDown(x1, y1, button=button)
            time.sleep(0.05)
            # Smooth drag via intermediate points
            steps = max(15, int(duration * 40))
            for i in range(1, steps + 1):
                t  = i / steps
                ix = int(x1 + (x2 - x1) * t)
                iy = int(y1 + (y2 - y1) * t)
                pyautogui.moveTo(ix, iy, _pause=False)
                time.sleep(duration / steps)
            pyautogui.mouseUp(x2, y2, button=button)
            self._last = (x2, y2)
            return ActionResult(True, output=f"Drag ({x1},{y1})→({x2},{y2})")
        except Exception as e:
            try:
                pyautogui.mouseUp()
            except Exception:
                pass
            return ActionResult(False, error=str(e))

    def scroll(
        self,
        x:         int,
        y:         int,
        amount:    int,
        direction: str = "vertical",
    ) -> ActionResult:
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        x, y = self._si.clamp(x, y)
        try:
            self.move(x, y, duration=0.15)
            time.sleep(0.05)
            if direction == "horizontal":
                pyautogui.hscroll(amount)
            else:
                # Scroll in chunks for smoother feel
                chunks = max(1, abs(amount))
                sign   = 1 if amount > 0 else -1
                for _ in range(chunks):
                    pyautogui.scroll(sign, x=x, y=y)
                    time.sleep(0.04)
            return ActionResult(True, output=f"Scroll {amount} @ ({x},{y})")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def position(self) -> Tuple[int, int]:
        if HAS_PYAUTOGUI:
            try:
                return tuple(pyautogui.position())
            except Exception:
                pass
        return self._last

    # ── bezier internals ─────────────────────────────────────────────────────

    def _auto_duration(self, tx: int, ty: int) -> float:
        """Scale move duration by distance (further = slightly longer)."""
        sx, sy = self._last
        dist   = math.hypot(tx - sx, ty - sy)
        base   = self._cfg.get("mouse_speed", 0.35)
        # 0.12s min, scale up with distance, cap at mouse_speed * 1.5
        return max(0.12, min(base * 1.5, base * (dist / 1200)))

    def _bezier(self, tx: int, ty: int, duration: float):
        """
        Move mouse along a cubic bezier path for realistic human-like motion.
        Two random control points introduce gentle curvature.
        """
        sx, sy = self.position()
        # Control points with gaussian noise
        spread = max(30, math.hypot(tx - sx, ty - sy) * 0.25)
        cp1x   = sx + random.gauss(0, spread)
        cp1y   = sy + random.gauss(0, spread)
        cp2x   = tx + random.gauss(0, spread)
        cp2y   = ty + random.gauss(0, spread)

        fps    = 80                             # target frames per second
        steps  = max(12, int(duration * fps))
        t_step = duration / steps

        for i in range(steps + 1):
            t   = i / steps
            it  = 1.0 - t
            # Cubic bezier formula
            px  = (it**3 * sx + 3*it**2*t * cp1x + 3*it*t**2 * cp2x + t**3 * tx)
            py  = (it**3 * sy + 3*it**2*t * cp1y + 3*it*t**2 * cp2y + t**3 * ty)
            pyautogui.moveTo(int(px), int(py), _pause=False)
            # Slight speed variation (fast in middle, slow at endpoints)
            ease = 1.0 + 0.4 * math.sin(math.pi * (i / steps))
            time.sleep(t_step / ease)


# =============================================================================
# §9  KEYBOARD CONTROLLER
# =============================================================================

class KeyboardController:
    """
    Advanced keyboard controller.
    Handles unicode, special keys, hotkeys, and send_keys sequences.
    """

    KEY_ALIASES: Dict[str, str] = {
        "enter": "enter", "return": "enter",
        "tab": "tab", "escape": "escape", "esc": "escape",
        "space": "space", "backspace": "backspace",
        "delete": "delete", "del": "delete",
        "up": "up", "down": "down", "left": "left", "right": "right",
        "home": "home", "end": "end",
        "pageup": "pageup", "pgup": "pageup",
        "pagedown": "pagedown", "pgdn": "pagedown",
        "insert": "insert", "ins": "insert",
        "ctrl": "ctrl", "control": "ctrl",
        "alt": "alt", "shift": "shift",
        "cmd": "command", "win": "winleft", "super": "winleft",
        "f1":  "f1",  "f2":  "f2",  "f3":  "f3",  "f4":  "f4",
        "f5":  "f5",  "f6":  "f6",  "f7":  "f7",  "f8":  "f8",
        "f9":  "f9",  "f10": "f10", "f11": "f11", "f12": "f12",
        "printscreen": "printscreen", "scrolllock": "scrolllock",
        "pause": "pause", "capslock": "capslock", "numlock": "numlock",
    }

    def __init__(self, cfg: ConfigManager):
        self._cfg = cfg

    def type_text(
        self,
        text:           str,
        interval:       float = 0.025,
        use_clipboard:  bool  = False,
    ) -> ActionResult:
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        if not text:
            return ActionResult(True, output="(empty text, nothing typed)")
        try:
            if use_clipboard or len(text) > 150:
                return self._type_via_clipboard(text)
            # Type character by character (better unicode support)
            for ch in text:
                try:
                    pyautogui.typewrite(ch, interval=interval)
                except Exception:
                    # pyautogui fails on some unicode — use clipboard fallback for that char
                    if HAS_CLIPBOARD:
                        old = pyperclip.paste()
                        pyperclip.copy(ch)
                        self._paste_shortcut()
                        pyperclip.copy(old)
            return ActionResult(True, output=f"Typed: {text[:60]}{'…' if len(text)>60 else ''}")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def _type_via_clipboard(self, text: str) -> ActionResult:
        if not HAS_CLIPBOARD:
            return ActionResult(False, error="pyperclip not installed for clipboard typing")
        try:
            old = pyperclip.paste()
            pyperclip.copy(text)
            time.sleep(0.05)
            self._paste_shortcut()
            time.sleep(0.1)
            pyperclip.copy(old)
            return ActionResult(True, output=f"Typed via clipboard: {text[:60]}…")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def _paste_shortcut(self):
        if sys.platform == "darwin":
            pyautogui.hotkey("command", "v")
        else:
            pyautogui.hotkey("ctrl", "v")

    def key_press(self, key: str) -> ActionResult:
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        try:
            k = self.KEY_ALIASES.get(key.lower(), key.lower())
            pyautogui.press(k)
            return ActionResult(True, output=f"Key: {key}")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def hotkey(self, *keys: str) -> ActionResult:
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        try:
            resolved = [self.KEY_ALIASES.get(k.lower(), k.lower()) for k in keys]
            pyautogui.hotkey(*resolved)
            return ActionResult(True, output=f"Hotkey: {'+'.join(keys)}")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def send_keys(self, sequence: str) -> ActionResult:
        """
        Send a key sequence string like 'hello{enter}world{tab}'.
        Supports {key_name} for special keys and normal chars.
        """
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        try:
            pattern = re.compile(r'\{([^}]+)\}|(.)', re.DOTALL)
            for match in pattern.finditer(sequence):
                special, char = match.group(1), match.group(2)
                if special:
                    k = self.KEY_ALIASES.get(special.lower(), special.lower())
                    pyautogui.press(k)
                    time.sleep(0.03)
                elif char:
                    pyautogui.typewrite(char, interval=0.025)
            return ActionResult(True, output=f"Sent: {sequence[:60]}")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def copy(self) -> ActionResult:
        mod = "command" if sys.platform == "darwin" else "ctrl"
        return self.hotkey(mod, "c")

    def paste(self) -> ActionResult:
        mod = "command" if sys.platform == "darwin" else "ctrl"
        return self.hotkey(mod, "v")

    def select_all(self) -> ActionResult:
        mod = "command" if sys.platform == "darwin" else "ctrl"
        return self.hotkey(mod, "a")


# =============================================================================
# §10  CLIPBOARD MANAGER
# =============================================================================

class ClipboardManager:
    def get(self) -> ActionResult:
        if HAS_CLIPBOARD:
            try:
                return ActionResult(True, output=pyperclip.paste() or "")
            except Exception as e:
                return ActionResult(False, error=str(e))
        if sys.platform.startswith("linux"):
            for cmd in ("xclip -selection clipboard -o", "xsel --clipboard --output"):
                try:
                    r = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=4)
                    if r.returncode == 0:
                        return ActionResult(True, output=r.stdout)
                except Exception:
                    continue
        return ActionResult(False, error="No clipboard backend (pip install pyperclip)")

    def set(self, text: str) -> ActionResult:
        if HAS_CLIPBOARD:
            try:
                pyperclip.copy(text)
                return ActionResult(True, output=f"Clipboard set ({len(text)} chars)")
            except Exception as e:
                return ActionResult(False, error=str(e))
        return ActionResult(False, error="No clipboard backend (pip install pyperclip)")


# =============================================================================
# §11  INPUT BLOCKER  — locks user keyboard + mouse during AI control
# =============================================================================

class InputBlocker:
    """
    Prevents the user from accidentally interfering while AI controls the PC.
    Uses platform-appropriate mechanisms:
      Windows  → ctypes BlockInput  (most reliable)
      Linux    → pynput suppress listener
      macOS    → pynput suppress listener
    The abort/pause hotkeys bypass the block.
    """

    def __init__(self, cfg: ConfigManager):
        self._cfg       = cfg
        self._enabled   = cfg.get("input_lock_enabled", True)
        self._blocked   = False
        self._listener  = None          # pynput listener (non-Windows)
        self._lock      = threading.Lock()

    # ── public ───────────────────────────────────────────────────────────────

    def block(self):
        """Lock out user keyboard and mouse."""
        if not self._enabled:
            return
        with self._lock:
            if self._blocked:
                return
            self._blocked = True
            if sys.platform == "win32":
                self._block_windows()
            elif HAS_PYNPUT:
                self._block_pynput()
            else:
                log.warn("Input blocker: no backend available on this OS (install pynput)")

    def unblock(self):
        """Restore user keyboard and mouse."""
        with self._lock:
            if not self._blocked:
                return
            self._blocked = False
            if sys.platform == "win32":
                self._unblock_windows()
            elif self._listener is not None:
                self._stop_pynput()

    @property
    def is_blocked(self) -> bool:
        return self._blocked

    # ── Windows ──────────────────────────────────────────────────────────────

    def _block_windows(self):
        try:
            ctypes.windll.user32.BlockInput(True)
            log.debug("Input blocked (Windows BlockInput)")
        except Exception as e:
            log.warn(f"BlockInput failed: {e}")

    def _unblock_windows(self):
        try:
            ctypes.windll.user32.BlockInput(False)
            log.debug("Input unblocked (Windows)")
        except Exception as e:
            log.warn(f"UnblockInput failed: {e}")

    # ── pynput (Linux / macOS) ────────────────────────────────────────────────

    def _block_pynput(self):
        """Suppress all keyboard and mouse events via pynput."""

        def on_key(key):
            # Allow abort and pause through
            try:
                abort_combo = {
                    pynput_keyboard.Key.ctrl_l,
                    pynput_keyboard.Key.shift,
                    pynput_keyboard.KeyCode.from_char('q'),
                }
                # Simple check: if Ctrl+Shift+Q, unblock and abort
                return False    # suppress everything else
            except Exception:
                return False

        try:
            self._listener = pynput_keyboard.Listener(
                on_press=on_key, suppress=True
            )
            self._listener.start()
            log.debug("Input blocked (pynput)")
        except Exception as e:
            log.warn(f"pynput block failed: {e}")

    def _stop_pynput(self):
        try:
            if self._listener:
                self._listener.stop()
                self._listener = None
            log.debug("Input unblocked (pynput)")
        except Exception as e:
            log.warn(f"pynput unblock failed: {e}")


# =============================================================================
# §12  WAVY BORDER OVERLAY   (animated sea-blue tkinter overlay on all 4 sides)
# =============================================================================

class WavyBorderOverlay:
    """
    Full-screen tkinter overlay that draws animated ocean-wave borders on all
    four sides of the monitor while Vaelor is active.

    The center is transparent so the user can see what the AI is doing.
    The overlay passes all mouse clicks through to windows beneath it.
    """

    BORDER_PX  = 58          # wave band thickness (pixels)
    FPS        = 40          # animation frames per second
    WAVE_SPEED = 0.08        # phase advance per frame

    def __init__(self, cfg: ConfigManager):
        self._cfg     = cfg
        self._enabled = cfg.get("overlay_enabled", True)
        self._root:   Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None
        self._thread: Optional[threading.Thread] = None
        self._t       = 0.0
        self._state   = OverlayState.HIDDEN
        self._state_q: queue.Queue = queue.Queue()

    # ── public ───────────────────────────────────────────────────────────────

    def show(self):
        if not self._enabled:
            return
        if self._thread and self._thread.is_alive():
            self._state_q.put(OverlayState.ACTIVE)
            return
        self._state = OverlayState.ACTIVE
        self._thread = threading.Thread(target=self._tk_main, daemon=True, name="vaelor-overlay")
        self._thread.start()

    def pause(self):
        self._state_q.put(OverlayState.PAUSED)

    def resume(self):
        self._state_q.put(OverlayState.ACTIVE)

    def hide(self):
        self._state_q.put(OverlayState.DONE)

    # ── tkinter main (runs in its own thread) ─────────────────────────────────

    def _tk_main(self):
        try:
            root = tk.Tk()
            self._root   = root
            root.title("VaelorOverlay")
            root.overrideredirect(True)         # no title bar, no borders

            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            root.geometry(f"{sw}x{sh}+0+0")
            root.attributes("-topmost", True)

            # Transparent center trick
            TRANSPARENT = "#010101"
            root.configure(bg=TRANSPARENT)
            root.wm_attributes("-transparentcolor", TRANSPARENT)

            canvas = tk.Canvas(
                root, width=sw, height=sh,
                bg=TRANSPARENT, highlightthickness=0,
            )
            canvas.pack()
            self._canvas = canvas
            self._sw     = sw
            self._sh     = sh

            # Make window click-through on Windows
            if sys.platform == "win32":
                self._make_clickthrough_win32(root)

            self._animate_frame()
            root.mainloop()
        except Exception as e:
            log.warn(f"Overlay error: {e}")

    def _make_clickthrough_win32(self, root: tk.Tk):
        """Set WS_EX_TRANSPARENT so mouse events pass through the overlay."""
        try:
            GWL_EXSTYLE       = -20
            WS_EX_LAYERED     = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            hwnd = ctypes.windll.user32.FindWindowW(None, "VaelorOverlay")
            if hwnd:
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(
                    hwnd, GWL_EXSTYLE,
                    style | WS_EX_LAYERED | WS_EX_TRANSPARENT,
                )
        except Exception as e:
            log.debug(f"click-through setup: {e}")

    # ── animation ─────────────────────────────────────────────────────────────

    def _animate_frame(self):
        if self._root is None:
            return
        # Process state changes
        while not self._state_q.empty():
            try:
                self._state = self._state_q.get_nowait()
            except queue.Empty:
                break

        if self._state == OverlayState.DONE:
            self._root.destroy()
            self._root = None
            return

        if self._canvas:
            self._canvas.delete("wave")
            if self._state == OverlayState.ACTIVE:
                self._draw_all_sides()
            elif self._state == OverlayState.PAUSED:
                self._draw_paused()
            self._t += self.WAVE_SPEED

        delay = max(10, int(1000 / self.FPS))
        if self._root:
            self._root.after(delay, self._animate_frame)

    def _draw_all_sides(self):
        sw, sh = self._sw, self._sh
        bp     = self.BORDER_PX
        t      = self._t
        c      = self._canvas

        # Draw status text at top-center
        c.create_text(
            sw // 2, bp // 2,
            text=f"◉  VAELOR ACTIVE  —  Ctrl+Shift+Q to abort",
            fill="#00b4d8",
            font=("Consolas", 11, "bold"),
            tags="wave",
        )

        self._draw_top(sw, bp, t)
        self._draw_bottom(sw, sh, bp, t)
        self._draw_left(sh, bp, t)
        self._draw_right(sw, sh, bp, t)

    def _draw_top(self, sw: int, bp: int, t: float):
        c = self._canvas
        # Multiple wave layers from thickest (back) to thinnest (front)
        for layer in range(bp, 4, -4):
            pts = []
            for x in range(0, sw + 8, 4):
                phase = x * 0.022 + t + layer * 0.08
                y = layer + math.sin(phase) * 10 + math.sin(x * 0.038 + t * 1.4) * 5
                pts.extend([x, max(0, y)])
            pts += [sw, 0, 0, 0]
            col = self._sea_color(layer / bp, t)
            if len(pts) >= 6:
                c.create_polygon(pts, fill=col, outline="", tags="wave")

    def _draw_bottom(self, sw: int, sh: int, bp: int, t: float):
        c = self._canvas
        for layer in range(bp, 4, -4):
            pts = []
            for x in range(0, sw + 8, 4):
                phase = x * 0.022 - t + layer * 0.08
                y = sh - layer + math.sin(phase) * 10 + math.sin(x * 0.038 - t * 1.4) * 5
                pts.extend([x, min(sh, y)])
            pts += [sw, sh, 0, sh]
            col = self._sea_color(layer / bp, t + 1.5)
            if len(pts) >= 6:
                c.create_polygon(pts, fill=col, outline="", tags="wave")

    def _draw_left(self, sh: int, bp: int, t: float):
        c = self._canvas
        for layer in range(bp, 4, -4):
            pts = []
            for y in range(0, sh + 8, 4):
                phase = y * 0.022 + t * 0.9 + layer * 0.08
                x = layer + math.sin(phase) * 8 + math.sin(y * 0.038 + t) * 4
                pts.extend([max(0, x), y])
            pts += [0, sh, 0, 0]
            col = self._sea_color(layer / bp, t + 3.0)
            if len(pts) >= 6:
                c.create_polygon(pts, fill=col, outline="", tags="wave")

    def _draw_right(self, sw: int, sh: int, bp: int, t: float):
        c = self._canvas
        for layer in range(bp, 4, -4):
            pts = []
            for y in range(0, sh + 8, 4):
                phase = y * 0.022 - t * 0.9 + layer * 0.08
                x = sw - layer + math.sin(phase) * 8 + math.sin(y * 0.038 - t) * 4
                pts.extend([min(sw, x), y])
            pts += [sw, sh, sw, 0]
            col = self._sea_color(layer / bp, t + 4.5)
            if len(pts) >= 6:
                c.create_polygon(pts, fill=col, outline="", tags="wave")

    def _draw_paused(self):
        sw, sh = self._sw, self._sh
        bp     = self.BORDER_PX
        t      = self._t
        c      = self._canvas
        # Slower, dimmer wave when paused
        for x in range(0, sw + 8, 6):
            y = bp // 2 + math.sin(x * 0.03 + t * 0.4) * 8
            c.create_oval(x-2, y-2, x+2, y+2, fill="#023e8a", outline="", tags="wave")
        for x in range(0, sw + 8, 6):
            y = sh - bp // 2 + math.sin(x * 0.03 - t * 0.4) * 8
            c.create_oval(x-2, y-2, x+2, y+2, fill="#023e8a", outline="", tags="wave")
        c.create_text(
            sw // 2, sh // 2,
            text="⏸  VAELOR PAUSED  —  Ctrl+Shift+P to resume",
            fill="#48cae4", font=("Consolas", 13, "bold"), tags="wave",
        )

    @staticmethod
    def _sea_color(ratio: float, t: float) -> str:
        """Return a hex color from the sea palette, animated by time."""
        n     = len(SEA_PALETTE)
        wave  = math.sin(ratio * math.pi + t * 0.5) * 0.5 + 0.5
        idx   = int(wave * (n - 1))
        return SEA_PALETTE[max(0, min(n - 1, idx))]


# =============================================================================
# §13  REASONING POPUP  (floating always-on-top window: live AI thoughts + screenshot)
# =============================================================================

class ReasoningPopup:
    """
    A compact floating Tkinter window that shows:
      • Live AI reasoning text (scrolling log)
      • Last screenshot thumbnail
      • Current step counter
      • Abort / Pause buttons
    Runs in its own daemon thread so it never blocks the agent.
    """

    WIDTH   = 420
    HEIGHT  = 580
    PADDING = 10

    def __init__(self, cfg: ConfigManager):
        self._cfg     = cfg
        self._enabled = cfg.get("popup_enabled", True)
        self._thread: Optional[threading.Thread] = None
        self._root:   Optional[tk.Tk]            = None
        self._text_w: Optional[tk.Text]          = None
        self._img_lbl: Optional[tk.Label]        = None
        self._step_var: Optional[tk.StringVar]   = None
        self._alive   = threading.Event()

    def start(self, model: str, task: str):
        if not self._enabled:
            return
        if self._thread and self._thread.is_alive():
            return
        self._model = model
        self._task  = task
        self._thread = threading.Thread(
            target=self._tk_main, daemon=True, name="vaelor-popup"
        )
        self._thread.start()

    def stop(self):
        self._alive.clear()

    # ── tkinter main ─────────────────────────────────────────────────────────

    def _tk_main(self):
        self._alive.set()
        try:
            root = tk.Tk()
            self._root = root
            root.title("Vaelor — Reasoning")
            root.geometry(f"{self.WIDTH}x{self.HEIGHT}+20+20")
            root.attributes("-topmost", True)
            root.attributes("-alpha", self._cfg.get("popup_opacity", 0.92))
            root.configure(bg="#0a0f1e")
            root.resizable(True, True)

            self._build_ui(root)
            # Poll queues every 120ms
            self._poll()
            root.mainloop()
        except Exception as e:
            log.debug(f"Popup error: {e}")
        finally:
            self._alive.clear()

    def _build_ui(self, root: tk.Tk):
        P    = self.PADDING
        bg   = "#0a0f1e"
        fg   = "#caf0f8"
        acc  = "#00b4d8"

        # ── header ───────────────────────────────────────────────────────────
        hdr = tk.Frame(root, bg="#03045e", pady=4)
        hdr.pack(fill="x")
        tk.Label(
            hdr, text="◉  VAELOR", bg="#03045e", fg=acc,
            font=("Consolas", 12, "bold"),
        ).pack(side="left", padx=8)
        self._step_var = tk.StringVar(value="Step: —")
        tk.Label(
            hdr, textvariable=self._step_var,
            bg="#03045e", fg="#90e0ef", font=("Consolas", 9),
        ).pack(side="right", padx=8)

        # ── model / task labels ──────────────────────────────────────────────
        info = tk.Frame(root, bg=bg, pady=2)
        info.pack(fill="x", padx=P)
        tk.Label(
            info, text=f"Model: {self._model}", bg=bg, fg="#48cae4",
            font=("Consolas", 8), anchor="w",
        ).pack(fill="x")
        task_short = self._task[:70] + ("…" if len(self._task) > 70 else "")
        tk.Label(
            info, text=f"Task: {task_short}", bg=bg, fg="#ade8f4",
            font=("Consolas", 8), anchor="w", wraplength=self.WIDTH - 20,
        ).pack(fill="x")

        # ── screenshot thumbnail ─────────────────────────────────────────────
        img_frame = tk.Frame(root, bg="#0d1b2a", bd=1, relief="solid")
        img_frame.pack(fill="x", padx=P, pady=(4, 0))
        self._img_lbl = tk.Label(img_frame, bg="#0d1b2a", text="[screenshot]",
                                  fg="#023e8a", font=("Consolas", 8))
        self._img_lbl.pack()

        # ── reasoning text ───────────────────────────────────────────────────
        txt_frame = tk.Frame(root, bg=bg)
        txt_frame.pack(fill="both", expand=True, padx=P, pady=(4, 0))

        scrollbar = tk.Scrollbar(txt_frame)
        scrollbar.pack(side="right", fill="y")

        self._text_w = tk.Text(
            txt_frame, bg="#0d1b2a", fg=fg,
            font=("Consolas", 8), wrap="word",
            yscrollcommand=scrollbar.set,
            state="disabled", bd=0, padx=4, pady=4,
        )
        self._text_w.pack(fill="both", expand=True)
        scrollbar.config(command=self._text_w.yview)

        # Tags for colored output
        self._text_w.tag_config("success", foreground="#48cae4")
        self._text_w.tag_config("error",   foreground="#ff6b6b")
        self._text_w.tag_config("warn",    foreground="#ffd166")
        self._text_w.tag_config("step",    foreground="#00b4d8", font=("Consolas", 9, "bold"))
        self._text_w.tag_config("tool",    foreground="#90e0ef")
        self._text_w.tag_config("model",   foreground="#caf0f8")

        # ── control buttons ──────────────────────────────────────────────────
        btn_frame = tk.Frame(root, bg=bg, pady=4)
        btn_frame.pack(fill="x", padx=P)

        tk.Button(
            btn_frame, text="⏸ Pause (Ctrl+Shift+P)",
            bg="#023e8a", fg="#caf0f8", font=("Consolas", 8),
            relief="flat", cursor="hand2",
            command=lambda: PAUSE_EVENT.set() if not PAUSE_EVENT.is_set() else PAUSE_EVENT.clear(),
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            btn_frame, text="✕ Abort (Ctrl+Shift+Q)",
            bg="#7b0000", fg="#ffd6d6", font=("Consolas", 8),
            relief="flat", cursor="hand2",
            command=lambda: ABORT_EVENT.set(),
        ).pack(side="left")

    def _poll(self):
        if not self._alive.is_set():
            return
        # Pull reasoning text
        count = 0
        while count < 30:
            try:
                msg = REASONING_QUEUE.get_nowait()
                self._append_text(msg)
                count += 1
            except queue.Empty:
                break
        # Pull screenshot thumbnail
        thumb = None
        while True:
            try:
                thumb = SCREENSHOT_QUEUE.get_nowait()
            except queue.Empty:
                break
        if thumb is not None and self._img_lbl:
            try:
                from PIL import ImageTk
                tk_img = ImageTk.PhotoImage(thumb)
                self._img_lbl.configure(image=tk_img, text="")
                self._img_lbl.image = tk_img  # hold reference
            except Exception:
                pass

        if self._root:
            self._root.after(120, self._poll)

    def _append_text(self, msg: str):
        if self._text_w is None:
            return
        # Determine tag from message prefix
        tag = "model"
        if msg.startswith("✓"):
            tag = "success"
        elif msg.startswith("✗") or "ERROR" in msg:
            tag = "error"
        elif msg.startswith("⚠"):
            tag = "warn"
        elif "Step" in msg and "─" in msg:
            tag = "step"
        elif msg.strip().startswith("✓") or msg.strip().startswith("✗"):
            tag = "tool"

        self._text_w.configure(state="normal")
        self._text_w.insert("end", msg + "\n", tag)
        self._text_w.see("end")
        self._text_w.configure(state="disabled")

    def update_step(self, step: int, total: int = MAX_STEPS):
        if self._step_var:
            with contextlib.suppress(Exception):
                self._step_var.set(f"Step: {step}/{total}")


# =============================================================================
# §14  HOTKEY MANAGER  (Ctrl+Shift+Q = abort, Ctrl+Shift+P = pause)
# =============================================================================

class HotkeyManager:
    """
    Listens for the abort and pause hotkeys even while input is blocked.
    Uses pynput's keyboard listener with suppress=False so it co-exists
    with the InputBlocker.
    """

    def __init__(self, input_blocker: "InputBlocker"):
        self._blocker  = input_blocker
        self._listener = None
        self._pressed: set = set()
        self._abort_combo = {
            pynput_keyboard.Key.ctrl_l,
            pynput_keyboard.Key.shift,
        } if HAS_PYNPUT else set()
        self._abort_char  = 'q'
        self._pause_char  = 'p'

    def start(self):
        if not HAS_PYNPUT:
            log.warn("pynput not installed — hotkeys unavailable (pip install pynput)")
            return
        self._listener = pynput_keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            suppress=False,
        )
        self._listener.start()
        log.debug("HotkeyManager started")

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass

    def _on_press(self, key):
        self._pressed.add(key)
        mods = {
            pynput_keyboard.Key.ctrl_l,
            pynput_keyboard.Key.ctrl_r,
        }
        shifts = {
            pynput_keyboard.Key.shift,
            pynput_keyboard.Key.shift_l,
            pynput_keyboard.Key.shift_r,
        }
        has_ctrl  = bool(self._pressed & mods)
        has_shift = bool(self._pressed & shifts)

        try:
            ch = key.char.lower() if hasattr(key, 'char') and key.char else None
        except Exception:
            ch = None

        if has_ctrl and has_shift and ch == self._abort_char:
            log.warn("ABORT HOTKEY pressed — stopping Vaelor")
            ABORT_EVENT.set()
            self._blocker.unblock()

        if has_ctrl and has_shift and ch == self._pause_char:
            if PAUSE_EVENT.is_set():
                PAUSE_EVENT.clear()
                log.info("Resumed by hotkey")
            else:
                PAUSE_EVENT.set()
                log.info("Paused by hotkey — press Ctrl+Shift+P to resume")

    def _on_release(self, key):
        self._pressed.discard(key)


# =============================================================================
# §15  APPLICATION & WINDOW MANAGER
# =============================================================================

class AppManager:
    def __init__(self, cfg: ConfigManager):
        self._cfg = cfg
        self._os  = sys.platform

    def open(self, app_name: str) -> ActionResult:
        try:
            if self._os == "darwin":
                return self._open_mac(app_name)
            elif self._os == "win32":
                return self._open_win(app_name)
            else:
                return self._open_linux(app_name)
        except Exception as e:
            return ActionResult(False, error=str(e))

    def _open_win(self, name: str) -> ActionResult:
        try:
            os.startfile(name)
        except Exception:
            try:
                subprocess.Popen(
                    ["start", "", name], shell=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                return ActionResult(False, error=str(e))
        time.sleep(1.8)
        return ActionResult(True, output=f"Launched: {name}")

    def _open_mac(self, name: str) -> ActionResult:
        subprocess.Popen(
            ["open", "-a", name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(1.8)
        return ActionResult(True, output=f"Launched: {name} (macOS)")

    def _open_linux(self, name: str) -> ActionResult:
        for cmd in ([name], ["xdg-open", name], ["gtk-launch", name]):
            if shutil.which(cmd[0]):
                subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                time.sleep(1.8)
                return ActionResult(True, output=f"Launched: {name}")
        return ActionResult(False, error=f"Cannot find launcher for '{name}'")

    def list_windows(self) -> ActionResult:
        try:
            if self._os == "win32":
                return self._list_win()
            elif self._os == "darwin":
                return self._list_mac()
            else:
                return self._list_linux()
        except Exception as e:
            return ActionResult(False, error=str(e))

    def _list_win(self) -> ActionResult:
        wins: List[str] = []
        try:
            EnumWindowsProc = ctypes.WINFUNCTYPE(
                ctypes.c_bool, ctypes.c_int, ctypes.c_int
            )

            def callback(hwnd, _):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    buf = ctypes.create_unicode_buffer(512)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
                    if buf.value.strip():
                        wins.append(f"HWND={hwnd}: {buf.value}")
                return True

            ctypes.windll.user32.EnumWindows(EnumWindowsProc(callback), 0)
            return ActionResult(True, output="\n".join(wins[:60]) or "No windows")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def _list_mac(self) -> ActionResult:
        script = (
            'tell application "System Events"\n'
            '  set r to {}\n'
            '  repeat with proc in (processes whose background only is false)\n'
            '    set end of r to name of proc\n'
            '  end repeat\n'
            '  return r as string\n'
            'end tell'
        )
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=8)
        return ActionResult(True, output=r.stdout.strip() or "No windows")

    def _list_linux(self) -> ActionResult:
        if shutil.which("xdotool"):
            r = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--name", ""],
                capture_output=True, text=True, timeout=5,
            )
            ids   = r.stdout.strip().split()[:40]
            lines = []
            for wid in ids:
                nr = subprocess.run(
                    ["xdotool", "getwindowname", wid],
                    capture_output=True, text=True, timeout=2,
                )
                name = nr.stdout.strip()
                if name:
                    lines.append(f"{wid}: {name}")
            return ActionResult(True, output="\n".join(lines) or "No windows")
        if shutil.which("wmctrl"):
            r = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=5)
            return ActionResult(True, output=r.stdout.strip())
        return ActionResult(False, error="Install xdotool or wmctrl")

    def switch_to(self, title: str) -> ActionResult:
        try:
            if self._os == "darwin":
                sc = f'tell application "{title}" to activate'
                subprocess.run(["osascript", "-e", sc], timeout=5)
                return ActionResult(True, output=f"Switched to: {title}")
            elif self._os.startswith("linux") and shutil.which("xdotool"):
                r = subprocess.run(
                    ["xdotool", "search", "--name", title, "windowactivate", "--sync"],
                    capture_output=True, text=True, timeout=6,
                )
                if r.returncode == 0:
                    return ActionResult(True, output=f"Switched to: {title}")
                return ActionResult(False, error=f"Window not found: {title}")
            elif self._os == "win32":
                wins: List[Tuple[int, str]] = []

                def cb(hwnd, _):
                    if ctypes.windll.user32.IsWindowVisible(hwnd):
                        buf = ctypes.create_unicode_buffer(512)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
                        if title.lower() in buf.value.lower():
                            wins.append((hwnd, buf.value))
                    return True

                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
                ctypes.windll.user32.EnumWindows(EnumWindowsProc(cb), 0)
                if wins:
                    hwnd = wins[0][0]
                    ctypes.windll.user32.ShowWindow(hwnd, 9)   # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    return ActionResult(True, output=f"Switched to: {wins[0][1]}")
                return ActionResult(False, error=f"Window '{title}' not found")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def close_app(self, app_name: str) -> ActionResult:
        if HAS_PSUTIL:
            killed = []
            for proc in psutil.process_iter(["name", "pid"]):
                if app_name.lower() in (proc.info.get("name") or "").lower():
                    try:
                        proc.terminate()
                        killed.append(f"{proc.info['name']}(pid={proc.pid})")
                    except Exception:
                        pass
            if killed:
                return ActionResult(True, output=f"Terminated: {', '.join(killed)}")
        return ActionResult(False, error=f"Process '{app_name}' not found")


# =============================================================================
# §16  TERMINAL CONTROLLER
# =============================================================================

class TerminalController:
    def __init__(self, cfg: ConfigManager):
        self._cfg  = cfg
        self._cwd  = Path.home()
        self._env  = {**os.environ}
        self._hist: List[Dict] = []

    def run(
        self,
        command: str,
        timeout: float = 45.0,
        cwd: Optional[str] = None,
        capture_stderr: bool = True,
    ) -> ActionResult:
        workdir = Path(cwd).resolve() if cwd else self._cwd
        try:
            proc = subprocess.run(
                command, shell=True,
                capture_output=True, text=True,
                timeout=timeout, cwd=str(workdir), env=self._env,
            )
            out = proc.stdout or ""
            if capture_stderr and proc.stderr:
                out += ("\nSTDERR:\n" + proc.stderr) if out else proc.stderr
            self._hist.append({"cmd": command, "rc": proc.returncode})
            if proc.returncode != 0:
                return ActionResult(
                    False, output=out,
                    error=f"Exit code {proc.returncode}",
                    metadata={"returncode": proc.returncode},
                )
            return ActionResult(True, output=out or "(no output)",
                                metadata={"returncode": 0})
        except subprocess.TimeoutExpired:
            return ActionResult(False, error=f"Timed out after {timeout}s")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def read_file(self, path: str, max_bytes: int = 65536) -> ActionResult:
        try:
            p = Path(path).expanduser().resolve()
            if not p.exists():
                return ActionResult(False, error=f"Not found: {p}")
            size = p.stat().st_size
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_bytes)
            note = f"\n…[truncated — total {size:,} bytes]" if size > max_bytes else ""
            return ActionResult(True, output=content + note, metadata={"size": size, "path": str(p)})
        except Exception as e:
            return ActionResult(False, error=str(e))

    def write_file(self, path: str, content: str, append: bool = False) -> ActionResult:
        try:
            p = Path(path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a" if append else "w", encoding="utf-8") as f:
                f.write(content)
            return ActionResult(True, output=f"{'Appended' if append else 'Wrote'} {len(content)} chars → {p}")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def list_dir(self, path: str = ".") -> ActionResult:
        try:
            p = (self._cwd / path).resolve()
            if not p.is_dir():
                return ActionResult(False, error=f"Not a directory: {p}")
            entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))[:300]
            lines = []
            for e in entries:
                icon = "📁" if e.is_dir() else "📄"
                size = ""
                if e.is_file():
                    with contextlib.suppress(OSError):
                        size = f"  {e.stat().st_size:,}B"
                lines.append(f"{icon} {e.name}{size}")
            return ActionResult(True, output="\n".join(lines) or "(empty)", metadata={"path": str(p)})
        except Exception as e:
            return ActionResult(False, error=str(e))


# =============================================================================
# §17  VISUAL ELEMENT FINDER
# =============================================================================

class VisualFinder:
    def __init__(self, screen: "ScreenCapture", cfg: ConfigManager):
        self._screen = screen
        self._cfg    = cfg

    def find_color(self, r: int, g: int, b: int, tol: int = 25) -> ActionResult:
        if not HAS_PIL:
            return ActionResult(False, error="Pillow required")
        raw, _ = self._screen.capture()
        img    = Image.open(io.BytesIO(raw)).convert("RGB")
        w, h   = img.size
        pixels = list(img.getdata())
        hits   = [
            (i % w, i // w) for i, (pr, pg, pb) in enumerate(pixels)
            if abs(pr-r) <= tol and abs(pg-g) <= tol and abs(pb-b) <= tol
        ]
        if not hits:
            return ActionResult(False, error=f"Color ({r},{g},{b}) ±{tol} not found")
        sample = hits[:500]
        cx     = int(sum(p[0] for p in sample) / len(sample))
        cy     = int(sum(p[1] for p in sample) / len(sample))
        return ActionResult(
            True,
            output=f"Found {len(hits)} pixels. Centroid: ({cx},{cy})",
            metadata={"x": cx, "y": cy, "count": len(hits)},
        )

    def template_match(self, template_path: str, threshold: float = 0.78) -> ActionResult:
        if not HAS_CV2:
            return ActionResult(False, error="opencv-python-headless required")
        if not Path(template_path).exists():
            return ActionResult(False, error=f"Template not found: {template_path}")
        raw, _     = self._screen.capture()
        buf        = np.frombuffer(raw, dtype=np.uint8)
        screen_img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        tmpl       = cv2.imread(template_path)
        res        = cv2.matchTemplate(screen_img, tmpl, cv2.TM_CCOEFF_NORMED)
        _, maxv, _, maxloc = cv2.minMaxLoc(res)
        if maxv < threshold:
            return ActionResult(False, error=f"Template not found (best={maxv:.2f}, need≥{threshold})")
        th, tw = tmpl.shape[:2]
        cx, cy = maxloc[0] + tw // 2, maxloc[1] + th // 2
        return ActionResult(
            True,
            output=f"Template found @ ({cx},{cy}) conf={maxv:.2f}",
            metadata={"x": cx, "y": cy, "confidence": maxv},
        )

    def wait_for_change(self, timeout: float = 12.0, poll: float = 0.3) -> ActionResult:
        if not HAS_PIL:
            return ActionResult(False, error="Pillow required")
        _, b64_before = self._screen.capture()
        deadline      = time.time() + timeout
        while time.time() < deadline:
            time.sleep(poll)
            _, b64_after = self._screen.capture()
            if b64_before != b64_after:
                return ActionResult(True, output="Screen changed")
        return ActionResult(False, error=f"No change in {timeout}s")

    def zoom_region(self, x: int, y: int, w: int, h: int) -> ActionResult:
        """Capture a zoomed crop for detailed inspection."""
        raw, b64 = self._screen.capture(region=(x, y, w, h))
        return ActionResult(
            True, output=f"Zoomed region ({x},{y},{w},{h})",
            screenshot=raw, metadata={"b64": b64},
        )


# =============================================================================
# §18  TOOL REGISTRY & TOOL DEFINITION
# =============================================================================

@dataclass
class ToolDefinition:
    name:        str
    description: str
    parameters:  Dict[str, Any]
    required:    List[str]        = field(default_factory=list)
    handler:     Optional[Callable] = field(default=None, compare=False, repr=False)

    def to_openai_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name":        self.name,
                "description": self.description,
                "parameters": {
                    "type":       "object",
                    "properties": self.parameters,
                    "required":   self.required,
                },
            },
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def schemas(self) -> List[Dict]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def dispatch(self, name: str, args: Dict) -> ActionResult:
        tool = self._tools.get(name)
        if tool is None:
            return ActionResult(False, error=f"Unknown tool: '{name}'. Available: {self.names()}")
        if tool.handler is None:
            return ActionResult(False, error=f"Tool '{name}' has no handler")
        try:
            return tool.handler(**args)
        except TypeError as e:
            return ActionResult(False, error=f"Bad args for '{name}': {e}")
        except Exception:
            return ActionResult(False, error=traceback.format_exc(limit=4))


# =============================================================================
# §19  TOOL BUILDER  — wires all 30+ tools
# =============================================================================

class ToolBuilder:
    def __init__(
        self,
        screen:    "ScreenCapture",
        mouse:     "MouseController",
        keyboard:  "KeyboardController",
        clipboard: "ClipboardManager",
        apps:      "AppManager",
        terminal:  "TerminalController",
        finder:    "VisualFinder",
        cfg:       "ConfigManager",
    ):
        self.sc  = screen
        self.mo  = mouse
        self.kb  = keyboard
        self.cb  = clipboard
        self.ap  = apps
        self.te  = terminal
        self.fi  = finder
        self.cfg = cfg

    def build(self) -> ToolRegistry:
        reg = ToolRegistry()
        for t in self._all_tools():
            reg.register(t)
        log.debug(f"ToolRegistry: {len(reg.names())} tools registered")
        return reg

    # ── shorthand ─────────────────────────────────────────────────────────────
    @staticmethod
    def _p(typ: str, desc: str, **extra) -> Dict:
        return {"type": typ, "description": desc, **extra}

    def _all_tools(self) -> List[ToolDefinition]:
        sc, mo, kb, cb, ap, te, fi = (
            self.sc, self.mo, self.kb, self.cb, self.ap, self.te, self.fi
        )
        P = self._p

        # ── screenshot ────────────────────────────────────────────────────────
        def _screenshot(
            region_x: int = None, region_y: int = None,
            region_w: int = None, region_h: int = None,
            annotate_cursor: bool = True,
        ) -> ActionResult:
            region = None
            if all(v is not None for v in [region_x, region_y, region_w, region_h]):
                region = (region_x, region_y, region_w, region_h)
            raw, b64 = sc.capture(region=region, annotate_cursor=annotate_cursor)
            return ActionResult(
                True, output="Screenshot captured.",
                screenshot=raw, metadata={"b64": b64, "size": len(raw)},
            )

        # ── get_screen_info ───────────────────────────────────────────────────
        def _get_screen_info() -> ActionResult:
            si = sc.screen_info
            return ActionResult(
                True,
                output=f"Screen: {si.width}×{si.height}px | scale={si.scale_factor} | monitors={si.monitor_count}",
                metadata=asdict(si),
            )

        # ── get_mouse_position ────────────────────────────────────────────────
        def _get_mouse_position() -> ActionResult:
            x, y = mo.position()
            return ActionResult(True, output=f"Cursor @ ({x},{y})", metadata={"x": x, "y": y})

        # ── click ─────────────────────────────────────────────────────────────
        def _click(x: int, y: int, button: str = "left", clicks: int = 1) -> ActionResult:
            return mo.click(x, y, button=button, clicks=clicks)

        # ── double_click ──────────────────────────────────────────────────────
        def _double_click(x: int, y: int) -> ActionResult:
            return mo.double_click(x, y)

        # ── right_click ───────────────────────────────────────────────────────
        def _right_click(x: int, y: int) -> ActionResult:
            return mo.right_click(x, y)

        # ── middle_click ──────────────────────────────────────────────────────
        def _middle_click(x: int, y: int) -> ActionResult:
            return mo.middle_click(x, y)

        # ── move ──────────────────────────────────────────────────────────────
        def _move(x: int, y: int, duration: float = None) -> ActionResult:
            return mo.move(x, y, duration=duration)

        # ── drag ──────────────────────────────────────────────────────────────
        def _drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.6) -> ActionResult:
            return mo.drag(x1, y1, x2, y2, duration=duration)

        # ── scroll ────────────────────────────────────────────────────────────
        def _scroll(x: int, y: int, amount: int, direction: str = "vertical") -> ActionResult:
            return mo.scroll(x, y, amount, direction=direction)

        # ── type_text ─────────────────────────────────────────────────────────
        def _type_text(text: str, interval: float = 0.025) -> ActionResult:
            return kb.type_text(text, interval=interval, use_clipboard=len(text) > 200)

        # ── key_press ─────────────────────────────────────────────────────────
        def _key_press(key: str) -> ActionResult:
            return kb.key_press(key)

        # ── hotkey ────────────────────────────────────────────────────────────
        def _hotkey(keys: str) -> ActionResult:
            parts = [k.strip() for k in re.split(r'[+\s]+', keys)]
            return kb.hotkey(*parts)

        # ── send_keys ─────────────────────────────────────────────────────────
        def _send_keys(sequence: str) -> ActionResult:
            return kb.send_keys(sequence)

        # ── copy ──────────────────────────────────────────────────────────────
        def _copy() -> ActionResult:
            return kb.copy()

        # ── paste ─────────────────────────────────────────────────────────────
        def _paste() -> ActionResult:
            return kb.paste()

        # ── get_clipboard ─────────────────────────────────────────────────────
        def _get_clipboard() -> ActionResult:
            return cb.get()

        # ── set_clipboard ─────────────────────────────────────────────────────
        def _set_clipboard(text: str) -> ActionResult:
            return cb.set(text)

        # ── open_app ──────────────────────────────────────────────────────────
        def _open_app(app_name: str) -> ActionResult:
            return ap.open(app_name)

        # ── close_app ─────────────────────────────────────────────────────────
        def _close_app(app_name: str) -> ActionResult:
            return ap.close_app(app_name)

        # ── switch_window ─────────────────────────────────────────────────────
        def _switch_window(title: str) -> ActionResult:
            return ap.switch_to(title)

        # ── list_windows ──────────────────────────────────────────────────────
        def _list_windows() -> ActionResult:
            return ap.list_windows()

        # ── run_command ───────────────────────────────────────────────────────
        def _run_command(command: str, timeout: float = 45.0, cwd: str = None) -> ActionResult:
            return te.run(command, timeout=timeout, cwd=cwd)

        # ── read_file ─────────────────────────────────────────────────────────
        def _read_file(path: str) -> ActionResult:
            return te.read_file(path)

        # ── write_file ────────────────────────────────────────────────────────
        def _write_file(path: str, content: str, append: bool = False) -> ActionResult:
            return te.write_file(path, content, append=append)

        # ── list_dir ──────────────────────────────────────────────────────────
        def _list_dir(path: str = ".") -> ActionResult:
            return te.list_dir(path)

        # ── find_on_screen ────────────────────────────────────────────────────
        def _find_on_screen(
            color_r: int = None, color_g: int = None, color_b: int = None,
            template_path: str = None,
        ) -> ActionResult:
            if template_path:
                return fi.template_match(template_path)
            if all(v is not None for v in [color_r, color_g, color_b]):
                return fi.find_color(color_r, color_g, color_b)
            return ActionResult(False, error="Provide color_r/g/b or template_path")

        # ── zoom_region ───────────────────────────────────────────────────────
        def _zoom_region(x: int, y: int, w: int, h: int) -> ActionResult:
            return fi.zoom_region(x, y, w, h)

        # ── wait ──────────────────────────────────────────────────────────────
        def _wait(seconds: float) -> ActionResult:
            t = min(float(seconds), 60.0)
            time.sleep(t)
            return ActionResult(True, output=f"Waited {t}s")

        # ── wait_for_change ───────────────────────────────────────────────────
        def _wait_for_change(timeout: float = 12.0) -> ActionResult:
            return fi.wait_for_change(timeout=timeout)

        # ── think ─────────────────────────────────────────────────────────────
        def _think(thought: str) -> ActionResult:
            log.debug(f"[THINK] {thought[:300]}")
            REASONING_QUEUE.put_nowait(f"💭 {thought[:400]}")
            return ActionResult(True, output="Thought recorded — no action taken.")

        # ── task_complete ─────────────────────────────────────────────────────
        def _task_complete(summary: str) -> ActionResult:
            return ActionResult(
                True, output=summary,
                metadata={"__task_done__": True},
            )

        # ─────────────────────────────────────────────────────────────────────
        # BUILD LIST
        # ─────────────────────────────────────────────────────────────────────

        return [
            ToolDefinition(
                "screenshot",
                "Capture the current screen. ALWAYS call this at the start of every step to see what is on screen. "
                "Optionally crop to a region for a zoomed view.",
                {
                    "region_x":       P("integer", "Left edge of crop (px)"),
                    "region_y":       P("integer", "Top edge of crop (px)"),
                    "region_w":       P("integer", "Width of crop (px)"),
                    "region_h":       P("integer", "Height of crop (px)"),
                    "annotate_cursor": P("boolean", "Draw cursor position on image"),
                },
                [], _screenshot,
            ),
            ToolDefinition(
                "get_screen_info",
                "Return screen resolution, scale factor, and monitor count.",
                {}, [], _get_screen_info,
            ),
            ToolDefinition(
                "get_mouse_position",
                "Return the current mouse cursor position in screen pixels.",
                {}, [], _get_mouse_position,
            ),
            ToolDefinition(
                "click",
                "Move cursor to (x,y) and click. Cursor movement is visible. "
                "Use button='right' for context menus, 'middle' for middle-click.",
                {
                    "x":      P("integer", "Horizontal coordinate (px from left)"),
                    "y":      P("integer", "Vertical coordinate (px from top)"),
                    "button": P("string",  "left | right | middle", enum=["left","right","middle"]),
                    "clicks": P("integer", "1=single, 2=double"),
                },
                ["x", "y"], _click,
            ),
            ToolDefinition(
                "double_click",
                "Double-click at (x,y). Shorthand for click with clicks=2.",
                {"x": P("integer","X"), "y": P("integer","Y")},
                ["x", "y"], _double_click,
            ),
            ToolDefinition(
                "right_click",
                "Right-click at (x,y) to open context menu.",
                {"x": P("integer","X"), "y": P("integer","Y")},
                ["x", "y"], _right_click,
            ),
            ToolDefinition(
                "middle_click",
                "Middle-click at (x,y) — opens links in new tabs, closes tabs.",
                {"x": P("integer","X"), "y": P("integer","Y")},
                ["x", "y"], _middle_click,
            ),
            ToolDefinition(
                "move",
                "Move the mouse cursor to (x,y) WITHOUT clicking. Useful for hovering to reveal tooltips or menus.",
                {
                    "x":        P("integer","X coordinate"),
                    "y":        P("integer","Y coordinate"),
                    "duration": P("number", "Move duration (seconds). Omit for auto."),
                },
                ["x", "y"], _move,
            ),
            ToolDefinition(
                "drag",
                "Click-and-drag from (x1,y1) to (x2,y2). Useful for sliders, file moves, selection.",
                {
                    "x1": P("integer","Start X"), "y1": P("integer","Start Y"),
                    "x2": P("integer","End X"),   "y2": P("integer","End Y"),
                    "duration": P("number","Drag duration in seconds"),
                },
                ["x1","y1","x2","y2"], _drag,
            ),
            ToolDefinition(
                "scroll",
                "Scroll at (x,y). Positive amount = up, negative = down.",
                {
                    "x":         P("integer","X coordinate"),
                    "y":         P("integer","Y coordinate"),
                    "amount":    P("integer","Scroll clicks: >0 up, <0 down"),
                    "direction": P("string", "vertical | horizontal", enum=["vertical","horizontal"]),
                },
                ["x","y","amount"], _scroll,
            ),
            ToolDefinition(
                "type_text",
                "Type text into the focused element. Click the target field first. "
                "Supports unicode. Long strings use clipboard paste automatically.",
                {
                    "text":     P("string","Text to type"),
                    "interval": P("number","Delay between keystrokes in seconds (default 0.025)"),
                },
                ["text"], _type_text,
            ),
            ToolDefinition(
                "key_press",
                "Press a single key by name. Supported: enter, escape, tab, space, backspace, "
                "delete, up, down, left, right, home, end, pageup, pagedown, f1-f12, etc.",
                {"key": P("string","Key name e.g. 'enter', 'escape', 'f5'")},
                ["key"], _key_press,
            ),
            ToolDefinition(
                "hotkey",
                "Press a keyboard shortcut. Keys joined with '+'. "
                "Examples: 'ctrl+c', 'ctrl+shift+t', 'alt+f4', 'win+d'.",
                {"keys": P("string","Keys joined with '+' e.g. 'ctrl+c'")},
                ["keys"], _hotkey,
            ),
            ToolDefinition(
                "send_keys",
                "Send a sequence of keystrokes including special keys in {braces}. "
                "Example: 'hello{enter}world{tab}' or '{ctrl}a{del}'.",
                {"sequence": P("string","Key sequence e.g. 'Hello{enter}World'")},
                ["sequence"], _send_keys,
            ),
            ToolDefinition(
                "copy",
                "Copy selected content to clipboard (Ctrl+C or Cmd+C).",
                {}, [], _copy,
            ),
            ToolDefinition(
                "paste",
                "Paste clipboard content into focused element (Ctrl+V or Cmd+V).",
                {}, [], _paste,
            ),
            ToolDefinition(
                "get_clipboard",
                "Read and return the current clipboard text content.",
                {}, [], _get_clipboard,
            ),
            ToolDefinition(
                "set_clipboard",
                "Write text to the clipboard.",
                {"text": P("string","Text to put in clipboard")},
                ["text"], _set_clipboard,
            ),
            ToolDefinition(
                "open_app",
                "Launch an application by name or path. "
                "Examples: 'notepad', 'firefox', 'code', 'Terminal', 'chrome'.",
                {"app_name": P("string","Application name or path")},
                ["app_name"], _open_app,
            ),
            ToolDefinition(
                "close_app",
                "Terminate a running application by process name.",
                {"app_name": P("string","Process name e.g. 'notepad', 'firefox'")},
                ["app_name"], _close_app,
            ),
            ToolDefinition(
                "switch_window",
                "Bring the window whose title matches the given string to focus.",
                {"title": P("string","Partial or full window title")},
                ["title"], _switch_window,
            ),
            ToolDefinition(
                "list_windows",
                "List all currently visible windows with their titles and handles.",
                {}, [], _list_windows,
            ),
            ToolDefinition(
                "run_command",
                "Run a shell command. Returns stdout+stderr. "
                "Use for file ops, git, pip, system info, opening apps via CLI.",
                {
                    "command": P("string","Shell command to execute"),
                    "timeout": P("number","Max seconds to wait (default 45)"),
                    "cwd":     P("string","Working directory path"),
                },
                ["command"], _run_command,
            ),
            ToolDefinition(
                "read_file",
                "Read and return file contents (up to 64KB).",
                {"path": P("string","File path (absolute or relative)")},
                ["path"], _read_file,
            ),
            ToolDefinition(
                "write_file",
                "Write or append text to a file. Creates parent directories.",
                {
                    "path":    P("string","File path"),
                    "content": P("string","Text to write"),
                    "append":  P("boolean","If true, append instead of overwrite"),
                },
                ["path","content"], _write_file,
            ),
            ToolDefinition(
                "list_dir",
                "List files and folders in a directory.",
                {"path": P("string","Directory path (default: home directory)")},
                [], _list_dir,
            ),
            ToolDefinition(
                "find_on_screen",
                "Find a UI element by colour or template image match. "
                "Provide RGB values OR a template_path, not both.",
                {
                    "color_r":       P("integer","Red   0-255"),
                    "color_g":       P("integer","Green 0-255"),
                    "color_b":       P("integer","Blue  0-255"),
                    "template_path": P("string", "Path to a PNG template image"),
                },
                [], _find_on_screen,
            ),
            ToolDefinition(
                "zoom_region",
                "Capture and return a zoomed-in screenshot of a specific screen region for detailed inspection.",
                {
                    "x": P("integer","Left edge"),
                    "y": P("integer","Top edge"),
                    "w": P("integer","Width"),
                    "h": P("integer","Height"),
                },
                ["x","y","w","h"], _zoom_region,
            ),
            ToolDefinition(
                "wait",
                "Pause execution for N seconds (max 60). Use sparingly.",
                {"seconds": P("number","Duration to wait")},
                ["seconds"], _wait,
            ),
            ToolDefinition(
                "wait_for_change",
                "Wait until the screen visually changes (useful after triggering loading actions).",
                {"timeout": P("number","Max wait seconds (default 12)")},
                [], _wait_for_change,
            ),
            ToolDefinition(
                "think",
                "Internal reasoning scratchpad. Record observations and plans WITHOUT taking any action. "
                "Use before complex decisions.",
                {"thought": P("string","Your reasoning, plan, or observation")},
                ["thought"], _think,
            ),
            ToolDefinition(
                "task_complete",
                "Signal that the task is FULLY complete. "
                "Only call this after a final screenshot or command confirms success. "
                "Provide a concise summary of what was accomplished and evidence.",
                {"summary": P("string","What was done and proof it worked")},
                ["summary"], _task_complete,
            ),
        ]


# =============================================================================
# §20  OPENROUTER CLIENT  (robust retry + circuit breaker)
# =============================================================================

class OpenRouterClient:
    """
    OpenAI-compatible client for OpenRouter.
    Features:
      • Immediate fail on non-retryable HTTP codes (400/401/403/404/422)
      • Exponential back-off on 429 / 5xx
      • Circuit breaker: opens after 5 consecutive failures, resets after 60s
      • Automatic content-type adaptation (vision vs text)
      • Token usage tracking
    """

    def __init__(self, api_key: str, model: str, cfg: ConfigManager):
        if not HAS_REQUESTS:
            raise RuntimeError("pip install requests")
        self._key      = api_key.strip()
        self._model    = model
        self._cfg      = cfg
        self._base     = OPENROUTER_BASE
        self._is_vision = model_supports_vision(model)
        self._cb       = CircuitBreakerState()
        self._req_count = 0
        self._total_in  = 0
        self._total_out = 0

        # Requests session with connection pooling
        self._sess = requests.Session()
        adapter    = HTTPAdapter(max_retries=0)   # we handle retries ourselves
        self._sess.mount("https://", adapter)
        self._sess.headers.update({
            "Authorization": f"Bearer {self._key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://vaelor.ai",
            "X-Title":       "Vaelor CUA v2",
        })

    # ── public ───────────────────────────────────────────────────────────────

    def chat(
        self,
        messages:    List[Dict],
        tools:       Optional[List[Dict]] = None,
        max_tokens:  int   = TOKEN_BUDGET,
        temperature: float = 0.05,
    ) -> Dict:
        """
        Send to OpenRouter.  Returns parsed JSON response.
        Raises RuntimeError on unrecoverable failure.
        """
        if not self._cb.should_attempt():
            raise RuntimeError(
                f"Circuit breaker OPEN: too many consecutive failures on {self._model}. "
                f"Will retry after {self._cb.reset_after_s}s."
            )

        payload: Dict[str, Any] = {
            "model":       self._model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
        }
        if tools:
            payload["tools"]       = tools
            payload["tool_choice"] = "auto"

        last_err: str = "unknown"
        max_retries   = 4

        for attempt in range(max_retries):
            # Check abort between retries
            if ABORT_EVENT.is_set():
                raise RuntimeError("Aborted by user")
            try:
                resp = self._sess.post(
                    f"{self._base}/chat/completions",
                    json=payload,
                    timeout=120,
                )

                # ── Non-retryable client errors ──────────────────────────────
                if resp.status_code in NON_RETRYABLE_HTTP:
                    try:
                        detail = resp.json()
                    except Exception:
                        detail = resp.text[:400]
                    hint = ""
                    if resp.status_code in (400, 404):
                        hint = (
                            "\nHINT: 400/404 often means the model does not support "
                            "vision/image input. Use a vision model or the code will "
                            "automatically fall back to text-mode."
                        )
                    raise RuntimeError(
                        f"HTTP {resp.status_code} (non-retryable): {detail}{hint}"
                    )

                # ── Rate limit ────────────────────────────────────────────────
                if resp.status_code == 429:
                    wait = min(60, 2 ** attempt + random.uniform(0, 1))
                    log.warn(f"Rate-limited — retrying in {wait:.1f}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    continue

                # ── Server errors (retryable) ─────────────────────────────────
                if resp.status_code >= 500:
                    wait = min(30, 2 ** attempt + random.uniform(0, 1))
                    log.warn(f"Server error {resp.status_code} — retrying in {wait:.1f}s")
                    time.sleep(wait)
                    last_err = f"HTTP {resp.status_code}"
                    continue

                resp.raise_for_status()
                data = resp.json()
                self._req_count += 1
                self._cb.record_success()
                usage = data.get("usage", {})
                self._total_in  += usage.get("prompt_tokens", 0)
                self._total_out += usage.get("completion_tokens", 0)
                return data

            except RuntimeError:
                self._cb.record_failure()
                raise
            except requests.exceptions.Timeout:
                last_err = "Request timed out (120s)"
                log.warn(f"Timeout on attempt {attempt+1}")
                time.sleep(2 ** attempt)
            except requests.exceptions.ConnectionError as e:
                last_err = f"Connection error: {e}"
                log.warn(last_err)
                time.sleep(2 ** attempt)
            except Exception as e:
                last_err = str(e)
                log.error(f"Unexpected API error: {e}")
                break

        self._cb.record_failure()
        raise RuntimeError(
            f"OpenRouter failed after {max_retries} retries on model '{self._model}': {last_err}"
        )

    def list_models(self) -> List[Dict]:
        try:
            r = self._sess.get(f"{self._base}/models", timeout=15)
            r.raise_for_status()
            return r.json().get("data", [])
        except Exception as e:
            log.error(f"list_models: {e}")
            return []

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def build_vision_content(b64: str, text: str = "") -> List[Dict]:
        content: List[Dict] = []
        if text:
            content.append({"type": "text", "text": text})
        content.append({
            "type":      "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"},
        })
        return content

    @staticmethod
    def extract_tool_calls(response: Dict) -> List[Dict]:
        msg = response.get("choices", [{}])[0].get("message", {})
        return msg.get("tool_calls") or []

    @staticmethod
    def extract_text(response: Dict) -> str:
        msg = response.get("choices", [{}])[0].get("message", {})
        return msg.get("content") or ""

    @property
    def is_vision(self) -> bool:
        return self._is_vision

    @property
    def stats(self) -> Dict:
        return {
            "model":      self._model,
            "is_vision":  self._is_vision,
            "requests":   self._req_count,
            "tokens_in":  self._total_in,
            "tokens_out": self._total_out,
            "cb_open":    self._cb.open,
        }


# =============================================================================
# §21  CONTEXT MANAGER
# =============================================================================

class ContextManager:
    """
    Manages the conversation window sent to the model.
    - Rolling window: keeps last N turns
    - Strips old image blobs (only last screenshot is kept as image)
    - Compresses long tool results
    """

    def __init__(self, system: str, window: int = CTX_WINDOW_MSGS):
        self._system   = system
        self._window   = window
        self._messages: List[Dict] = []

    def add_user(self, text: str):
        self._messages.append({"role": "user", "content": text})
        self._trim()

    def add_user_vision(self, b64: str, text: str = ""):
        content = OpenRouterClient.build_vision_content(b64, text)
        self._messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant(self, text: str, raw_tool_calls: Optional[List] = None):
        msg: Dict[str, Any] = {"role": "assistant", "content": text or ""}
        if raw_tool_calls:
            msg["tool_calls"] = raw_tool_calls
        self._messages.append(msg)

    def add_tool_result(self, tc_id: str, name: str, result: ActionResult):
        content = result.full_for_context()
        if len(content) > TOOL_RESULT_TRUNC:
            content = result.truncated_output(TOOL_RESULT_TRUNC)
        self._messages.append({
            "role":         "tool",
            "tool_call_id": tc_id,
            "name":         name,
            "content":      content,
        })

    def build(self) -> List[Dict]:
        sys_msg = {"role": "system", "content": self._system}
        return [sys_msg] + self._strip_old_images()

    def clear(self):
        self._messages.clear()

    @property
    def count(self) -> int:
        return len(self._messages)

    # ── internals ─────────────────────────────────────────────────────────────

    def _trim(self):
        limit = self._window * 2
        if len(self._messages) > limit:
            # Always keep first 2 messages (task setup), trim middle
            self._messages = self._messages[:2] + self._messages[-(limit - 2):]

    def _strip_old_images(self) -> List[Dict]:
        """Keep image data only in the most recent vision message."""
        msgs      = self._messages
        last_img  = None
        for i in range(len(msgs) - 1, -1, -1):
            if isinstance(msgs[i].get("content"), list):
                for block in msgs[i]["content"]:
                    if isinstance(block, dict) and block.get("type") == "image_url":
                        last_img = i
                        break
            if last_img is not None:
                break

        result = []
        for i, msg in enumerate(msgs):
            if i == last_img:
                result.append(msg)
            elif isinstance(msg.get("content"), list):
                # Replace with text summary
                texts = [
                    b.get("text", "") for b in msg["content"]
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                result.append({
                    "role":    msg["role"],
                    "content": " ".join(texts) + " [screenshot data omitted to save tokens]",
                })
            else:
                result.append(msg)
        return result


# =============================================================================
# §22  REASONING LOOP  (the beating heart)
# =============================================================================

class ReasoningLoop:
    """
    Core perceive → reason → act → verify loop.

    Each iteration:
      1. Check abort/pause flags
      2. Capture screenshot (vision) OR collect system state (text)
      3. Build context and call model
      4. Parse tool_calls from response
      5. Execute each tool with full logging
      6. Update context with results
      7. Detect task_complete or stall
      8. Update popup with step info
    """

    def __init__(
        self,
        client:   "OpenRouterClient",
        registry: "ToolRegistry",
        context:  "ContextManager",
        screen:   "ScreenCapture",
        apps:     "AppManager",
        terminal: "TerminalController",
        popup:    "ReasoningPopup",
        cfg:      "ConfigManager",
    ):
        self._client   = client
        self._registry = registry
        self._context  = context
        self._screen   = screen
        self._apps     = apps
        self._terminal = terminal
        self._popup    = popup
        self._cfg      = cfg

        self._step     = 0
        self._done     = False
        self._result   = ""
        self._stall:   Dict[str, int] = defaultdict(int)

    def run(self, task: str, session: TaskSession) -> TaskSession:
        log.info(f"Task started: {task}")
        self._context.clear()
        self._context.add_user(f"TASK: {task}")
        self._step = 0
        self._done = False
        ABORT_EVENT.clear()

        while self._step < MAX_STEPS and not self._done:
            # ── Abort check ──────────────────────────────────────────────────
            if ABORT_EVENT.is_set():
                log.warn("Task aborted by user (Ctrl+Shift+Q)")
                session.aborted = True
                break

            # ── Pause check ──────────────────────────────────────────────────
            if PAUSE_EVENT.is_set():
                log.info("Paused — waiting for Ctrl+Shift+P to resume…")
                while PAUSE_EVENT.is_set() and not ABORT_EVENT.is_set():
                    time.sleep(0.5)
                if ABORT_EVENT.is_set():
                    session.aborted = True
                    break
                log.info("Resumed.")

            self._step += 1
            self._popup.update_step(self._step, MAX_STEPS)

            t0 = time.time()
            try:
                step_obj = self._single_step(session)
                step_obj.elapsed_ms = (time.time() - t0) * 1000
                session.steps.append(step_obj)
                session.total_in  += step_obj.tokens_in
                session.total_out += step_obj.tokens_out
            except KeyboardInterrupt:
                log.warn("KeyboardInterrupt during step")
                break
            except RuntimeError as e:
                err_msg = str(e)
                log.error(f"Step {self._step}: {err_msg}")
                # If it's a non-retryable error, abort task to prevent storm
                if any(code in err_msg for code in ["400", "401", "403", "404", "non-retryable"]):
                    log.error("Non-retryable error — aborting task to prevent retry storm.")
                    session.final_msg = f"Fatal API error: {err_msg[:200]}"
                    break
                session.steps.append(AgentStep(
                    index=self._step, model_msg=f"[ERROR] {err_msg}",
                    status=StepStatus.FAILED,
                ))
                time.sleep(min(4, 2 ** max(0, self._step - 1)))
                continue
            except Exception as e:
                log.error(f"Step {self._step} unexpected: {traceback.format_exc(limit=4)}")
                session.steps.append(AgentStep(
                    index=self._step, model_msg=f"[CRASH] {e}",
                    status=StepStatus.FAILED,
                ))
                time.sleep(2)
                continue

            sleep_ms = self._cfg.get("loop_sleep_ms", LOOP_SLEEP_MS)
            time.sleep(sleep_ms / 1000)

        session.end_time  = time.time()
        session.success   = self._done
        if not session.final_msg:
            session.final_msg = self._result
        self._show_summary(session)
        return session

    # ── single step ───────────────────────────────────────────────────────────

    def _single_step(self, session: TaskSession) -> AgentStep:
        step = AgentStep(index=self._step, model_msg="", status=StepStatus.RUNNING)
        log.step(self._step, f"Thinking… (ctx={self._context.count} msgs)")

        # ── 1. Inject screen state into context ──────────────────────────────
        if self._client.is_vision:
            _, b64 = self._screen.capture(annotate_cursor=True)
            self._context.add_user_vision(b64, f"[Step {self._step}] Current screen:")
        else:
            state_text = self._collect_text_state()
            self._context.add_user(f"[Step {self._step} — TEXT MODE]\n{state_text}")

        # ── 2. Call model ─────────────────────────────────────────────────────
        messages = self._context.build()
        tools    = self._registry.schemas()

        response = self._client.chat(
            messages=messages,
            tools=tools,
            max_tokens=TOKEN_BUDGET,
            temperature=0.05,
        )

        usage          = response.get("usage", {})
        step.tokens_in  = usage.get("prompt_tokens", 0)
        step.tokens_out = usage.get("completion_tokens", 0)

        text        = OpenRouterClient.extract_text(response)
        tool_calls  = OpenRouterClient.extract_tool_calls(response)
        raw_tcs     = (response.get("choices", [{}])[0]
                       .get("message", {}).get("tool_calls")) or []

        step.model_msg = text or "(tool calls only)"
        log.model_response(text)

        # ── 3. Add assistant turn to context ──────────────────────────────────
        self._context.add_assistant(text, raw_tcs or None)

        # ── 4. Handle no output ───────────────────────────────────────────────
        if not tool_calls and not text:
            log.warn("Model produced no output — nudging.")
            self._context.add_user(
                "You produced no output. Take a screenshot, study the screen, and decide your next action."
            )
            step.status = StepStatus.SKIPPED
            return step

        if not tool_calls:
            step.status = StepStatus.SUCCESS
            return step

        # ── 5. Execute tool calls ─────────────────────────────────────────────
        for tc in tool_calls:
            if ABORT_EVENT.is_set():
                break

            tc_id   = tc.get("id", str(uuid.uuid4()))
            fn_name = tc.get("function", {}).get("name", "")
            try:
                fn_args = json.loads(tc.get("function", {}).get("arguments", "{}") or "{}")
            except json.JSONDecodeError:
                fn_args = {}

            tc_obj           = ToolCall(id=tc_id, name=fn_name, arguments=fn_args)
            tc_obj.ts_start  = time.time()

            # ── Anti-stall guard ──────────────────────────────────────────────
            stall_key = f"{fn_name}:{json.dumps(fn_args, sort_keys=True)}"
            self._stall[stall_key] += 1
            if self._stall[stall_key] >= 3:
                log.warn(f"STALL: {fn_name} called with identical args ×3!")
                self._context.add_user(
                    f"⚠ STALL DETECTED: You called '{fn_name}' with the same arguments "
                    f"3 times in a row without progress. You MUST try a completely different "
                    f"approach. Consider: different coordinates, different app, different method."
                )
                # Reset stall counter for this key so the message is sent once
                self._stall[stall_key] = 0
                break

            result          = self._registry.dispatch(fn_name, fn_args)
            tc_obj.result   = result
            tc_obj.ts_end   = time.time()
            step.tool_calls.append(tc_obj)
            log.tool(fn_name, fn_args, result)

            # ── Inject screenshot into context if screenshot tool was called ──
            if fn_name == "screenshot" and result.success:
                b64_new = result.metadata.get("b64", "")
                if b64_new and self._client.is_vision:
                    self._context.add_tool_result(tc_id, fn_name, result)
                    # Extra image message so model sees what was captured
                    self._context.add_user_vision(b64_new, "")
                    continue

            # ── Zoom region also returns an image ─────────────────────────────
            if fn_name == "zoom_region" and result.success and result.metadata.get("b64"):
                if self._client.is_vision:
                    self._context.add_tool_result(tc_id, fn_name, result)
                    self._context.add_user_vision(result.metadata["b64"], "Zoomed region:")
                    continue

            self._context.add_tool_result(tc_id, fn_name, result)

            # ── Task complete signal ──────────────────────────────────────────
            if fn_name == "task_complete" and result.metadata.get("__task_done__"):
                self._done   = True
                self._result = fn_args.get("summary", "Task complete.")
                step.status  = StepStatus.SUCCESS
                log.success(f"Task complete: {self._result}")
                return step

        step.status = StepStatus.SUCCESS
        return step

    # ── text-mode state collector ─────────────────────────────────────────────

    def _collect_text_state(self) -> str:
        """Gather text-based system state when vision is unavailable."""
        parts = ["=== SYSTEM STATE (text mode) ==="]
        # Windows list
        wr = self._apps.list_windows()
        if wr.success:
            lines = wr.output.splitlines()[:15]
            parts.append("Open windows:\n" + "\n".join(lines))
        # Clipboard
        cr = self._collect_clipboard()
        if cr:
            parts.append(f"Clipboard: {cr[:200]}")
        # Recent terminal output hint
        parts.append("Use run_command, list_windows, read_file to gather more info.")
        return "\n\n".join(parts)

    def _collect_clipboard(self) -> str:
        if HAS_CLIPBOARD:
            try:
                return pyperclip.paste() or ""
            except Exception:
                pass
        return ""

    # ── summary display ───────────────────────────────────────────────────────

    def _show_summary(self, session: TaskSession):
        if HAS_RICH:
            t = Table(box=rbox.ROUNDED, title="[bold cyan]Session Summary[/bold cyan]", show_header=False)
            t.add_column("Key",   style="cyan",  no_wrap=True)
            t.add_column("Value", style="white")
            rows = [
                ("Session ID",  session.id),
                ("Task",        session.task[:80]),
                ("Model",       session.model),
                ("Vision",      "yes" if session.is_vision else "no (text mode)"),
                ("Steps",       str(len(session.steps))),
                ("Elapsed",     f"{session.elapsed:.1f}s"),
                ("Status",      ("✓ SUCCESS" if session.success
                                 else ("⚡ ABORTED" if session.aborted else "✗ INCOMPLETE"))),
                ("Tokens in",   f"{session.total_in:,}"),
                ("Tokens out",  f"{session.total_out:,}"),
                ("Result",      session.final_msg[:120]),
            ]
            for k, v in rows:
                t.add_row(k, v)
            console.print(t)
        else:
            print("\n=== Session Summary ===")
            for k, v in session.to_dict().items():
                print(f"  {k}: {v}")


# =============================================================================
# §23  MAIN AGENT  (public interface)
# =============================================================================

class VaelorAgent:
    """
    Top-level Computer Use Agent.

    Usage:
        agent = VaelorAgent(api_key="...", model="openai/gpt-4o")
        session = agent.run("Open Notepad and write Hello World")
    """

    def __init__(
        self,
        api_key:       str,
        model:         str,
        cfg_overrides: Optional[Dict] = None,
    ):
        ov = cfg_overrides or {}
        ov["openrouter_key"] = api_key
        ov["default_model"]  = model

        self.cfg        = ConfigManager(ov)
        self.model      = model
        self.is_vision  = model_supports_vision(model)

        # ── Hardware controllers ──────────────────────────────────────────────
        self.screen    = ScreenCapture(self.cfg)
        self.mouse     = MouseController(self.screen.screen_info, self.cfg)
        self.keyboard  = KeyboardController(self.cfg)
        self.clipboard = ClipboardManager()
        self.apps      = AppManager(self.cfg)
        self.terminal  = TerminalController(self.cfg)
        self.finder    = VisualFinder(self.screen, self.cfg)

        # ── UI / overlay systems ──────────────────────────────────────────────
        self.input_blocker = InputBlocker(self.cfg)
        self.overlay       = WavyBorderOverlay(self.cfg)
        self.popup         = ReasoningPopup(self.cfg)
        self.hotkeys       = HotkeyManager(self.input_blocker)

        # ── LLM ──────────────────────────────────────────────────────────────
        self.client    = OpenRouterClient(api_key, model, self.cfg)
        system_prompt  = SYSTEM_PROMPT_VISION if self.is_vision else SYSTEM_PROMPT_TEXT
        self.context   = ContextManager(system=system_prompt)

        # ── Tools ─────────────────────────────────────────────────────────────
        builder        = ToolBuilder(
            self.screen, self.mouse, self.keyboard, self.clipboard,
            self.apps, self.terminal, self.finder, self.cfg,
        )
        self.registry  = builder.build()
        self.loop      = ReasoningLoop(
            self.client, self.registry, self.context,
            self.screen, self.apps, self.terminal,
            self.popup, self.cfg,
        )

        self._sessions: List[TaskSession] = []
        self._memory:   "AgentMemory"     = AgentMemory()

        # ── Start hotkey listener ─────────────────────────────────────────────
        self.hotkeys.start()

        mode_str = "VISION" if self.is_vision else "TEXT-ONLY"
        log.success(
            f"VaelorAgent v{VERSION} ready | model={model} | "
            f"mode={mode_str} | tools={len(self.registry.names())}"
        )

    # ── public API ────────────────────────────────────────────────────────────

    def run(self, task: str) -> TaskSession:
        """
        Execute a task.
        - Starts wavy border overlay
        - Locks user input
        - Runs the reasoning loop
        - Restores input and removes overlay when done
        """
        session              = TaskSession(task=task, model=self.model, is_vision=self.is_vision)
        ABORT_EVENT.clear()
        PAUSE_EVENT.clear()

        # ── Show UI elements ──────────────────────────────────────────────────
        self.popup.start(model=self.model, task=task)
        self.overlay.show()
        time.sleep(0.4)                  # let overlay render before blocking input
        self.input_blocker.block()

        try:
            session = self.loop.run(task, session)
        finally:
            # ── ALWAYS restore, even on crash ─────────────────────────────────
            self.input_blocker.unblock()
            self.overlay.hide()
            time.sleep(0.25)
            self.popup.stop()

        self._sessions.append(session)
        if self.cfg.get("save_sessions", True):
            self._save_session(session)
        return session

    def screenshot(self) -> Tuple[bytes, str]:
        return self.screen.capture()

    def list_tools(self) -> List[str]:
        return self.registry.names()

    def set_model(self, model: str):
        """Hot-swap the LLM model."""
        self.model      = model
        self.is_vision  = model_supports_vision(model)
        self.client     = OpenRouterClient(self.cfg.get("openrouter_key"), model, self.cfg)
        sys_prompt      = SYSTEM_PROMPT_VISION if self.is_vision else SYSTEM_PROMPT_TEXT
        self.context    = ContextManager(system=sys_prompt)
        self.loop._client   = self.client
        self.loop._context  = self.context
        mode = "VISION" if self.is_vision else "TEXT-ONLY"
        log.success(f"Model → {model} ({mode})")

    def get_stats(self) -> Dict:
        return {
            **self.client.stats,
            "sessions":       len(self._sessions),
            "screen":         asdict(self.screen.screen_info),
            "tools":          len(self.registry.names()),
            "memory_keys":    len(self._memory.all_keys()),
        }

    def remember(self, key: str, value: Any):
        self._memory.store(key, value)

    def recall(self, key: str) -> Any:
        return self._memory.recall(key)

    def _save_session(self, session: TaskSession):
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        p = SESSION_DIR / f"{session.id}.json"
        with open(p, "w") as f:
            json.dump(session.to_dict(), f, indent=2)
        log.debug(f"Session saved → {p}")


# =============================================================================
# §24  PERSISTENT MEMORY
# =============================================================================

class AgentMemory:
    _PATH = Path.home() / ".vaelor" / "memory.json"

    def __init__(self):
        self._mem: Dict[str, Any] = {}
        self._load()

    def store(self, key: str, value: Any):
        self._mem[key] = {"value": value, "ts": time.time()}
        self._save()

    def recall(self, key: str, default: Any = None) -> Any:
        e = self._mem.get(key)
        return e["value"] if e else default

    def forget(self, key: str):
        self._mem.pop(key, None)
        self._save()

    def all_keys(self) -> List[str]:
        return list(self._mem.keys())

    def to_context_str(self, max_items: int = 8) -> str:
        if not self._mem:
            return ""
        items = sorted(self._mem.items(), key=lambda x: x[1]["ts"], reverse=True)[:max_items]
        return "\n".join(f"[MEM] {k}: {v['value']}" for k, v in items)

    def _load(self):
        if self._PATH.exists():
            try:
                with open(self._PATH) as f:
                    self._mem = json.load(f)
            except Exception:
                self._mem = {}

    def _save(self):
        self._PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self._PATH, "w") as f:
            json.dump(self._mem, f, indent=2)


# =============================================================================
# §25  INTERACTIVE REPL
# =============================================================================

class VaelorREPL:
    COMMANDS = {
        "/help":          "Show this help",
        "/model <id>":    "Switch model",
        "/models":        "List available OpenRouter models",
        "/stats":         "Token + session statistics",
        "/tools":         "List registered tools",
        "/ss":            "Take a screenshot now",
        "/history":       "Recent sessions",
        "/clear":         "Clear conversation context",
        "/memory":        "Show persistent memory",
        "/remember k=v":  "Store a memory key=value",
        "/config":        "Show current config",
        "/check":         "Check dependencies",
        "/quit":          "Exit Vaelor",
    }

    def __init__(self, agent: VaelorAgent):
        self._agent = agent

    def run(self):
        self._banner()
        while True:
            try:
                raw = self._prompt()
                if not raw.strip():
                    continue
                if raw.strip().startswith("/"):
                    if self._handle_cmd(raw.strip()):
                        break
                else:
                    self._execute_task(raw.strip())
            except KeyboardInterrupt:
                print()
                ans = input("Exit Vaelor? [y/N] ").strip().lower()
                if ans == "y":
                    break

    def _prompt(self) -> str:
        mode_icon = "👁" if self._agent.is_vision else "📝"
        if HAS_RICH:
            return Prompt.ask(f"[bold cyan]vaelor[/bold cyan]{mode_icon}")
        return input(f"vaelor> ")

    def _execute_task(self, task: str):
        if HAS_RICH:
            console.rule(f"[bold cyan]Running task[/bold cyan]")
        session = self._agent.run(task)
        color   = "green" if session.success else ("yellow" if session.aborted else "red")
        status  = "✓ DONE" if session.success else ("⚡ ABORTED" if session.aborted else "✗ INCOMPLETE")
        if HAS_RICH:
            console.print(Panel(
                f"[bold]{status}[/bold]\n\n{session.final_msg}",
                border_style=color,
                title=f"[bold]Session {session.id}[/bold]",
            ))
        else:
            print(f"\n{status}: {session.final_msg}")

    def _handle_cmd(self, raw: str) -> bool:
        parts = raw.split(maxsplit=1)
        cmd   = parts[0].lower()
        arg   = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/quit", "/exit", "/q"):
            self._agent.hotkeys.stop()
            log.success("Goodbye. Stay autonomous.")
            return True

        elif cmd == "/help":
            if HAS_RICH:
                t = Table(title="Vaelor Commands", box=rbox.SIMPLE)
                t.add_column("Command", style="cyan")
                t.add_column("Description")
                for c, d in self.COMMANDS.items():
                    t.add_row(c, d)
                console.print(t)
            else:
                for c, d in self.COMMANDS.items():
                    print(f"  {c:25s} {d}")

        elif cmd == "/models":
            mods = self._agent.client.list_models()
            if HAS_RICH:
                t = Table(box=rbox.SIMPLE, title="Available Models")
                t.add_column("ID",         style="cyan")
                t.add_column("Context",    style="green")
                t.add_column("Vision",     style="magenta")
                t.add_column("$/M in",     style="yellow")
                for m in sorted(mods, key=lambda x: x.get("id",""))[:80]:
                    pricing = m.get("pricing", {})
                    vis     = "👁" if model_supports_vision(m.get("id","")) else ""
                    t.add_row(
                        m.get("id",""),
                        str(m.get("context_length","")),
                        vis,
                        str(pricing.get("prompt","")),
                    )
                console.print(t)
            else:
                for m in mods[:40]:
                    print(m.get("id"))

        elif cmd == "/model":
            if arg:
                self._agent.set_model(arg)
            else:
                mode = "VISION" if self._agent.is_vision else "TEXT-ONLY"
                print(f"Current: {self._agent.model} ({mode})")

        elif cmd == "/stats":
            s = self._agent.get_stats()
            if HAS_RICH:
                t = Table(box=rbox.SIMPLE, show_header=False)
                t.add_column("K", style="cyan"); t.add_column("V")
                for k, v in s.items():
                    t.add_row(str(k), str(v))
                console.print(t)
            else:
                for k, v in s.items():
                    print(f"  {k}: {v}")

        elif cmd == "/tools":
            names = self._agent.list_tools()
            if HAS_RICH:
                tree = Tree("[bold cyan]Registered Tools[/bold cyan]")
                for n in names:
                    tree.add(n)
                console.print(tree)
            else:
                print("\n".join(f"  {n}" for n in names))

        elif cmd == "/ss":
            raw_b, _ = self._agent.screenshot()
            ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            p        = Path(f"vaelor_ss_{ts}.jpg")
            p.write_bytes(raw_b)
            log.success(f"Screenshot → {p}")

        elif cmd == "/history":
            sess = self._agent._sessions
            if not sess:
                print("No sessions yet.")
            elif HAS_RICH:
                t = Table(box=rbox.SIMPLE)
                t.add_column("ID"); t.add_column("Task"); t.add_column("Steps"); t.add_column("OK")
                for s in sess[-20:]:
                    t.add_row(s.id, s.task[:50], str(len(s.steps)), "✓" if s.success else "✗")
                console.print(t)
            else:
                for s in sess[-10:]:
                    print(f"  [{s.id}] {s.task[:40]} {'OK' if s.success else 'FAIL'}")

        elif cmd == "/clear":
            self._agent.context.clear()
            log.success("Context cleared.")

        elif cmd == "/memory":
            keys = self._agent._memory.all_keys()
            if not keys:
                print("Memory is empty.")
            else:
                for k in keys:
                    v = self._agent.recall(k)
                    print(f"  {k} = {v}")

        elif cmd == "/remember":
            if "=" in arg:
                k, v = arg.split("=", 1)
                self._agent.remember(k.strip(), v.strip())
                log.success(f"Stored: {k.strip()} = {v.strip()}")
            else:
                print("Usage: /remember key=value")

        elif cmd == "/config":
            if HAS_RICH:
                import pprint
                console.print_json(json.dumps(self._agent.cfg._d, indent=2))
            else:
                print(json.dumps(self._agent.cfg._d, indent=2))

        elif cmd == "/check":
            check_dependencies()

        else:
            log.warn(f"Unknown command: {cmd}. Type /help.")

        return False

    def _banner(self):
        art = r"""
  ██╗   ██╗ █████╗ ███████╗██╗      ██████╗ ██████╗     ██╗   ██╗██████╗
  ██║   ██║██╔══██╗██╔════╝██║     ██╔═══██╗██╔══██╗    ██║   ██║╚════██╗
  ██║   ██║███████║█████╗  ██║     ██║   ██║██████╔╝    ██║   ██║ █████╔╝
  ╚██╗ ██╔╝██╔══██║██╔══╝  ██║     ██║   ██║██╔══██╗    ╚██╗ ██╔╝██╔═══╝
   ╚████╔╝ ██║  ██║███████╗███████╗╚██████╔╝██║  ██║     ╚████╔╝ ███████╗
    ╚═══╝  ╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝      ╚═══╝  ╚══════╝
  Computer Use Agent  v{v}  ·  Ultimate Edition
"""
        if HAS_RICH:
            console.print(Panel(art.format(v=VERSION), border_style="cyan", padding=(0,2)))
            mode = "[green]VISION[/green]" if self._agent.is_vision else "[yellow]TEXT-ONLY[/yellow]"
            console.print(
                f"  Model: [bold]{self._agent.model}[/bold]  "
                f"Mode: {mode}  "
                f"Tools: [bold]{len(self._agent.list_tools())}[/bold]\n"
                f"  [dim]Ctrl+Shift+Q = abort  ·  Ctrl+Shift+P = pause  ·  /help for commands[/dim]"
            )
        else:
            print(art.format(v=VERSION))
            print(f"Model: {self._agent.model} | {'VISION' if self._agent.is_vision else 'TEXT'}")


# =============================================================================
# §26  DEPENDENCY CHECKER
# =============================================================================

def check_dependencies() -> Dict[str, bool]:
    checks = {
        "requests":            HAS_REQUESTS,
        "pyautogui":           HAS_PYAUTOGUI,
        "pillow":              HAS_PIL,
        "rich":                HAS_RICH,
        "psutil":              HAS_PSUTIL,
        "pyperclip":           HAS_CLIPBOARD,
        "pynput":              HAS_PYNPUT,
        "opencv-python":       HAS_CV2,
        "tkinter (stdlib)":    True,   # always available in CPython
    }
    if HAS_RICH:
        t = Table(title="Dependency Status", box=rbox.SIMPLE)
        t.add_column("Package",  style="cyan")
        t.add_column("Status")
        t.add_column("Role")
        roles = {
            "requests":         "API calls",
            "pyautogui":        "Mouse + keyboard control",
            "pillow":           "Screenshots",
            "rich":             "Pretty output",
            "psutil":           "Process management",
            "pyperclip":        "Clipboard",
            "pynput":           "Hotkeys + input blocker",
            "opencv-python":    "Template matching",
            "tkinter (stdlib)": "Overlay + popup",
        }
        for pkg, ok in checks.items():
            status = "[green]✓ installed[/green]" if ok else "[yellow]✗ missing[/yellow]"
            t.add_row(pkg, status, roles.get(pkg, ""))
        console.print(t)
        critical = [p for p, ok in checks.items() if not ok and p in ("requests","pyautogui","pillow")]
        if critical:
            console.print(f"[red]Install critical packages:[/red]  pip install {' '.join(critical)}")
        optional = [p for p, ok in checks.items() if not ok and p not in critical and p != "tkinter (stdlib)"]
        if optional:
            console.print(f"[yellow]Install optional:[/yellow]  pip install {' '.join(optional)}")
    else:
        for pkg, ok in checks.items():
            print(f"  {'✓' if ok else '✗'} {pkg}")
    return checks


# =============================================================================
# §27  SIGNAL HANDLERS
# =============================================================================

def _graceful_exit(signum, frame):
    if HAS_RICH:
        console.print("\n[yellow]Signal received — shutting down gracefully.[/yellow]")
    else:
        print("\nShutdown…")
    ABORT_EVENT.set()
    # Unblock input (safety)
    if sys.platform == "win32":
        with contextlib.suppress(Exception):
            ctypes.windll.user32.BlockInput(False)
    if HAS_PYAUTOGUI:
        with contextlib.suppress(Exception):
            pyautogui.moveTo(1, 1)  # trigger failsafe reset
    sys.exit(0)

signal.signal(signal.SIGINT,  _graceful_exit)
signal.signal(signal.SIGTERM, _graceful_exit)


# =============================================================================
# §28  SELF-TEST SUITE
# =============================================================================

class SelfTestSuite:
    def __init__(self):
        self._pass = 0
        self._fail = 0

    def run(self):
        if HAS_RICH:
            console.rule("[bold]Vaelor Self-Test Suite[/bold]")
        self._test_config()
        self._test_action_result()
        self._test_context_manager()
        self._test_tool_registry()
        self._test_keyboard_aliases()
        self._test_terminal()
        self._test_vision_detection()
        self._test_circuit_breaker()
        self._print_summary()

    def _ok(self, cond: bool, msg: str):
        if cond:
            self._pass += 1
            log.success(f"PASS  {msg}")
        else:
            self._fail += 1
            log.error(f"FAIL  {msg}")

    def _test_config(self):
        cfg = ConfigManager({"openrouter_key": "test-key", "verbose": True})
        self._ok(cfg["openrouter_key"] == "test-key",  "Config: key injection")
        self._ok(cfg["verbose"] is True,               "Config: bool override")
        self._ok(cfg.get("max_steps") == MAX_STEPS,    "Config: default fallback")
        self._ok(cfg.get("nonexistent", 42) == 42,     "Config: missing key default")

    def _test_action_result(self):
        r = ActionResult(True, output="A" * 5000)
        t = r.truncated_output(limit=100)
        self._ok(len(t) < 300,                         "ActionResult: truncation size")
        self._ok("truncated" in t,                     "ActionResult: truncation label present")
        r2 = ActionResult(False, error="oops", output="some output")
        self._ok(not r2.success,                       "ActionResult: failure flag")
        self._ok("oops" in r2.full_for_context(),      "ActionResult: full_for_context")

    def _test_context_manager(self):
        ctx = ContextManager(system="test system", window=5)
        for i in range(14):
            ctx.add_user(f"msg {i}")
        msgs = ctx.build()
        self._ok(msgs[0]["role"] == "system",           "Context: system first")
        self._ok(len(msgs) <= 14,                       "Context: window trim")

    def _test_tool_registry(self):
        reg = ToolRegistry()
        td  = ToolDefinition(
            "test_add", "Add two numbers",
            {"a": {"type":"integer","description":"a"},
             "b": {"type":"integer","description":"b"}},
            ["a","b"],
            lambda a, b: ActionResult(True, output=str(a + b)),
        )
        reg.register(td)
        self._ok("test_add" in reg.names(),             "ToolRegistry: registration")
        r = reg.dispatch("test_add", {"a": 19, "b": 23})
        self._ok(r.success,                             "ToolRegistry: dispatch ok")
        self._ok(r.output == "42",                      "ToolRegistry: correct output")
        r2 = reg.dispatch("nonexistent", {})
        self._ok(not r2.success,                        "ToolRegistry: unknown tool → fail")

    def _test_keyboard_aliases(self):
        kb = KeyboardController(ConfigManager())
        self._ok(kb.KEY_ALIASES["esc"]   == "escape",  "KB aliases: esc")
        self._ok(kb.KEY_ALIASES["enter"] == "enter",   "KB aliases: enter")
        self._ok(kb.KEY_ALIASES["cmd"]   == "command", "KB aliases: cmd")
        self._ok(kb.KEY_ALIASES["del"]   == "delete",  "KB aliases: del")

    def _test_terminal(self):
        te = TerminalController(ConfigManager())
        r  = te.run("echo vaelor_test", timeout=8)
        self._ok(r.success,                             "Terminal: echo ok")
        self._ok("vaelor_test" in r.output,             "Terminal: echo content")
        r2 = te.run("command_that_does_not_exist_xyz_123")
        self._ok(not r2.success,                        "Terminal: bad command → fail")
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello vaelor"); tmp = f.name
        r3 = te.read_file(tmp)
        self._ok(r3.success,                            "Terminal: read_file ok")
        self._ok("hello vaelor" in r3.output,           "Terminal: read_file content")
        os.unlink(tmp)

    def _test_vision_detection(self):
        self._ok(model_supports_vision("openai/gpt-4o"),                    "Vision detect: gpt-4o")
        self._ok(model_supports_vision("baidu/qianfan-ocr-fast:free"),      "Vision detect: qianfan-ocr")
        self._ok(model_supports_vision("anthropic/claude-3.5-sonnet"),      "Vision detect: claude-3.5")
        self._ok(not model_supports_vision("mistralai/mistral-7b-instruct"),"Vision detect: mistral-7b → False")
        self._ok(not model_supports_vision("meta-llama/llama-2-70b-chat"),  "Vision detect: llama-2 → False")

    def _test_circuit_breaker(self):
        cb = CircuitBreakerState(threshold=3, reset_after_s=1.0)
        self._ok(cb.should_attempt(),              "CB: initially open to attempts")
        cb.record_failure(); cb.record_failure(); cb.record_failure()
        self._ok(cb.open,                          "CB: opens after threshold")
        self._ok(not cb.should_attempt(),          "CB: blocks when open")
        time.sleep(1.1)
        self._ok(cb.should_attempt(),              "CB: resets after timeout")

    def _print_summary(self):
        total = self._pass + self._fail
        if HAS_RICH:
            color = "green" if self._fail == 0 else "red"
            console.print(
                f"\n[{color}]Tests: {self._pass}/{total} passed "
                f"({'ALL OK ✓' if self._fail == 0 else f'{self._fail} FAILED ✗'})[/{color}]"
            )
        else:
            print(f"\nTests: {self._pass}/{total} passed")


# =============================================================================
# §29  WORKFLOW TEMPLATES
# =============================================================================

WORKFLOW_TEMPLATES: Dict[str, str] = {
    "open_browser_search": (
        "Open the default web browser. Navigate to https://www.google.com. "
        "Click the search box, type '{query}', press Enter. "
        "Wait for results. Take a final screenshot."
    ),
    "write_note": (
        "Open Notepad (Windows) or TextEdit (macOS) or gedit (Linux). "
        "Type the following text exactly:\n{content}\n"
        "Save the file to the Desktop with filename '{filename}'."
    ),
    "run_script": (
        "Open a terminal. Navigate to {directory}. "
        "Run: python {script}. "
        "Capture all output. Report what happened."
    ),
    "describe_screen": (
        "Take a full-screen screenshot. Describe in detail everything visible: "
        "all open applications, windows, text content, UI elements, and system state."
    ),
    "fill_form": (
        "Navigate to {url}. "
        "Fill in these fields: {form_data}. "
        "Click Submit. Confirm success."
    ),
    "install_package": (
        "Open a terminal. Run: pip install {package}. "
        "Wait for completion. Verify installation with: python -c \"import {module}; print('OK')\"."
    ),
}

def expand_template(name: str, **kwargs) -> str:
    tmpl = WORKFLOW_TEMPLATES.get(name)
    if not tmpl:
        raise ValueError(f"Unknown template '{name}'. Available: {list(WORKFLOW_TEMPLATES)}")
    return tmpl.format(**kwargs)


# =============================================================================
# §30  BROWSER HELPER
# =============================================================================

class BrowserHelper:
    def __init__(self, agent: VaelorAgent):
        self._a = agent

    def navigate(self, url: str) -> TaskSession:
        return self._a.run(
            f"In the open browser, click the address bar, clear it, "
            f"type '{url}', press Enter, wait for full page load."
        )

    def search(self, query: str) -> TaskSession:
        return self._a.run(expand_template("open_browser_search", query=query))

    def click_text(self, text: str) -> TaskSession:
        return self._a.run(
            f"On the current web page, find and click the element, link, or button "
            f"that contains the text: '{text}'."
        )

    def fill_and_submit(self, url: str, fields: Dict[str, str]) -> TaskSession:
        fd = "; ".join(f"'{k}' = '{v}'" for k, v in fields.items())
        return self._a.run(expand_template("fill_form", url=url, form_data=fd))


# =============================================================================
# §31  CLI ENTRYPOINT
# =============================================================================

def parse_args():
    import argparse
    p = argparse.ArgumentParser(
        prog="vaelor",
        description="Vaelor v2.0 — Computer Use Agent — Ultimate Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python vaelor.py --key sk-or-... --model baidu/qianfan-ocr-fast:free
          python vaelor.py --key sk-or-... --model openai/gpt-4o --task "open notepad"
          python vaelor.py --key sk-or-... --model mistralai/mistral-7b-instruct --task "list files"
          python vaelor.py --self-test
          python vaelor.py --check-deps
          python vaelor.py --list-models --key sk-or-...
        """),
    )
    p.add_argument("--key",           "-k", default="",          help="OpenRouter API key")
    p.add_argument("--model",         "-m", default="",          help="Model slug")
    p.add_argument("--task",          "-t", default="",          help="Task (non-interactive)")
    p.add_argument("--interactive",   "-i", action="store_true", help="Force REPL mode")
    p.add_argument("--check-deps",          action="store_true", help="Check deps and exit")
    p.add_argument("--self-test",           action="store_true", help="Run unit tests and exit")
    p.add_argument("--list-models",         action="store_true", help="List models and exit")
    p.add_argument("--no-overlay",          action="store_true", help="Disable wave overlay")
    p.add_argument("--no-popup",            action="store_true", help="Disable reasoning popup")
    p.add_argument("--no-lock",             action="store_true", help="Disable input locking")
    p.add_argument("--max-steps",    type=int, default=MAX_STEPS)
    p.add_argument("--mouse-speed",  type=float, default=0.35,  help="Mouse move duration (s)")
    p.add_argument("--mouse-mode",   default="bezier",          help="bezier|linear|instant")
    p.add_argument("--no-save",             action="store_true", help="Don't save sessions")
    p.add_argument("--verbose",      "-v",  action="store_true")
    return p.parse_args()


def main():
    args = parse_args()

    if args.self_test:
        SelfTestSuite().run()
        sys.exit(0)

    if args.check_deps:
        check_dependencies()
        sys.exit(0)

    # ── Resolve API key ───────────────────────────────────────────────────────
    api_key = (
        args.key
        or os.environ.get("OPENROUTER_API_KEY", "")
        or ConfigManager().get("openrouter_key", "")
    )
    if not api_key:
        if HAS_RICH:
            api_key = Prompt.ask("[bold yellow]OpenRouter API Key[/bold yellow]", password=True)
        else:
            api_key = input("OpenRouter API Key: ").strip()
    if not api_key:
        log.error("API key required. Set OPENROUTER_API_KEY or pass --key.")
        sys.exit(1)

    # ── Resolve model ─────────────────────────────────────────────────────────
    model = args.model or ConfigManager().get("default_model", "openai/gpt-4o")

    # ── Config overrides ──────────────────────────────────────────────────────
    overrides = {
        "openrouter_key":     api_key,
        "default_model":      model,
        "max_steps":          args.max_steps,
        "mouse_speed":        args.mouse_speed,
        "mouse_mode":         args.mouse_mode,
        "overlay_enabled":    not args.no_overlay,
        "popup_enabled":      not args.no_popup,
        "input_lock_enabled": not args.no_lock,
        "save_sessions":      not args.no_save,
        "verbose":            args.verbose,
    }

    # ── Build agent ───────────────────────────────────────────────────────────
    agent = VaelorAgent(api_key=api_key, model=model, cfg_overrides=overrides)

    if args.list_models:
        mods = agent.client.list_models()
        for m in sorted(mods, key=lambda x: x.get("id", "")):
            vis = " [vision]" if model_supports_vision(m.get("id","")) else ""
            print(f"{m.get('id')}{vis}")
        sys.exit(0)

    if args.task:
        session = agent.run(args.task)
        sys.exit(0 if session.success else 1)
    else:
        repl = VaelorREPL(agent)
        repl.run()


# =============================================================================
# ENTRY
# =============================================================================

if __name__ == "__main__":
    main()
