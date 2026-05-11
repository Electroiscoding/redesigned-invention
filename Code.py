# =============================================================================
#  ██╗   ██╗ █████╗ ███████╗██╗      ██████╗ ██████╗
#  ██║   ██║██╔══██╗██╔════╝██║     ██╔═══██╗██╔══██╗
#  ██║   ██║███████║█████╗  ██║     ██║   ██║██████╔╝
#  ╚██╗ ██╔╝██╔══██║██╔══╝  ██║     ██║   ██║██╔══██╗
#   ╚████╔╝ ██║  ██║███████╗███████╗╚██████╔╝██║  ██║
#    ╚═══╝  ╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
#
#  Computer Use Agent Framework — Full Local Edition
#  Author : Vaelor Project
#  License: MIT
#  Python : 3.10+
#
#  INSTALL DEPS BEFORE RUNNING:
#    pip install pyautogui pillow requests rich psutil pyperclip
#    pip install opencv-python-headless   # optional, for better CV
#    pip install pygetwindow              # optional, Windows/macOS window mgmt
#
#  USAGE:
#    python vaelor.py --key YOUR_OPENROUTER_KEY --model openai/gpt-4o
#    python vaelor.py --key YOUR_KEY --model anthropic/claude-3.5-sonnet --task "Open notepad and type Hello World"
#    python vaelor.py --interactive   # opens REPL loop
# =============================================================================

from __future__ import annotations

import ast
import base64
import contextlib
import copy
import ctypes
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
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import traceback
import typing
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Dict, Generator, List, Literal,
    Optional, Sequence, Tuple, Type, Union,
)

# ── Optional heavy imports (graceful fallback) ────────────────────────────────
try:
    import pyautogui
    pyautogui.FAILSAFE = True          # move mouse to corner to abort
    pyautogui.PAUSE    = 0.05          # 50ms inter-action pause (speed)
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from rich.console    import Console
    from rich.panel      import Panel
    from rich.syntax     import Syntax
    from rich.table      import Table
    from rich.progress   import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.layout     import Layout
    from rich.live       import Live
    from rich.markdown   import Markdown
    from rich.text       import Text
    from rich.tree       import Tree
    from rich.prompt     import Prompt, Confirm
    from rich            import box as rbox
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    class _FallbackConsole:
        def print(self, *a, **kw): print(*a)
        def rule(self, *a, **kw): print("─" * 60)
        def log(self, *a, **kw): print(*a)
    console = _FallbackConsole()

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


# =============================================================================
# §1  CONSTANTS & CONFIGURATION
# =============================================================================

VERSION           = "1.0.0"
AGENT_NAME        = "Vaelor"
MAX_STEPS         = 150          # hard cap on reasoning steps per task
MAX_RETRIES       = 4            # retries on recoverable errors
SCREENSHOT_QUAL   = 85           # JPEG quality for API transmission (1-95)
MAX_IMG_DIM       = 1280         # max screenshot dimension (px) before resize
TOKEN_BUDGET      = 8192         # max tokens for model response
CTX_WINDOW_MSGS   = 20           # rolling conversation window kept in context
LOOP_SLEEP_MS     = 80           # ms between perception-action loops
ELEMENT_TIMEOUT   = 10.0         # seconds to wait for a UI element
OPENROUTER_BASE   = "https://openrouter.ai/api/v1"
TOOL_RESULT_TRUNC = 4096         # max chars in a tool result before truncation
LOG_DIR           = Path.home() / ".vaelor" / "logs"
SESSION_DIR       = Path.home() / ".vaelor" / "sessions"
CONFIG_PATH       = Path.home() / ".vaelor" / "config.json"

SYSTEM_PROMPT = """\
You are Vaelor, an elite autonomous Computer Use Agent. \
You control the user's desktop with pixel-perfect precision. \
You ALWAYS complete the assigned task — never give up, never hallucinate actions.

RULES (non-negotiable):
1. LOOK BEFORE YOU ACT — call `screenshot` at the start of every reasoning step.
2. THINK STEP-BY-STEP — break complex tasks into a chain of atomic tool calls.
3. VERIFY AFTER EVERY ACTION — re-screenshot and confirm the action had the expected effect.
4. CORRECT ON FAILURE — if an action fails or produces unexpected results, adapt immediately.
5. NEVER LOOP — if you take the same action ≥3 times without progress, try a different approach.
6. BE TOKEN-EFFICIENT — do not narrate; only output a tool call or a final answer.
7. FINAL ANSWER — when the task is fully complete, call `task_complete` with a concise summary.

COORDINATE SYSTEM: origin (0,0) is top-left of the primary monitor. \
All x,y values are absolute screen pixels.

You have access to the following tools (see tool definitions). \
Always choose the most direct path to the goal.
"""

# =============================================================================
# §2  ENUMERATIONS & DATA CLASSES
# =============================================================================

class ActionType(str, Enum):
    SCREENSHOT      = "screenshot"
    CLICK           = "click"
    DOUBLE_CLICK    = "double_click"
    RIGHT_CLICK     = "right_click"
    MIDDLE_CLICK    = "middle_click"
    MOVE            = "move"
    DRAG            = "drag"
    SCROLL          = "scroll"
    TYPE_TEXT       = "type_text"
    KEY_PRESS       = "key_press"
    HOTKEY          = "hotkey"
    COPY            = "copy"
    PASTE           = "paste"
    GET_CLIPBOARD   = "get_clipboard"
    SET_CLIPBOARD   = "set_clipboard"
    OPEN_APP        = "open_app"
    CLOSE_APP       = "close_app"
    SWITCH_WINDOW   = "switch_window"
    LIST_WINDOWS    = "list_windows"
    RUN_COMMAND     = "run_command"
    READ_FILE       = "read_file"
    WRITE_FILE      = "write_file"
    LIST_DIR        = "list_dir"
    FIND_ON_SCREEN  = "find_on_screen"
    WAIT            = "wait"
    WAIT_FOR_TEXT   = "wait_for_text"
    SCROLL_TO_TEXT  = "scroll_to_text"
    GET_SCREEN_INFO = "get_screen_info"
    TASK_COMPLETE   = "task_complete"
    THINK           = "think"
    NAVIGATE_URL    = "navigate_url"
    GET_URL         = "get_url"

class StepStatus(str, Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    SUCCESS  = "success"
    FAILED   = "failed"
    SKIPPED  = "skipped"

class ModelRole(str, Enum):
    USER      = "user"
    ASSISTANT = "assistant"
    SYSTEM    = "system"
    TOOL      = "tool"

@dataclass
class ScreenInfo:
    width:        int
    height:       int
    scale_factor: float = 1.0
    monitor_count: int  = 1

    def center(self) -> Tuple[int, int]:
        return self.width // 2, self.height // 2

@dataclass
class ActionResult:
    success:   bool
    output:    str                = ""
    error:     str                = ""
    screenshot: Optional[bytes]  = None   # PNG bytes if captured
    metadata:  Dict[str, Any]    = field(default_factory=dict)

    def truncated_output(self, limit: int = TOOL_RESULT_TRUNC) -> str:
        if len(self.output) > limit:
            half = limit // 2
            return self.output[:half] + f"\n…[{len(self.output)-limit} chars truncated]…\n" + self.output[-half:]
        return self.output

@dataclass
class ToolCall:
    id:        str
    name:      str
    arguments: Dict[str, Any]
    result:    Optional[ActionResult] = None
    ts_start:  float = field(default_factory=time.time)
    ts_end:    Optional[float]        = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.ts_end:
            return (self.ts_end - self.ts_start) * 1000
        return None

@dataclass
class AgentStep:
    index:      int
    model_msg:  str
    tool_calls: List[ToolCall] = field(default_factory=list)
    status:     StepStatus    = StepStatus.PENDING
    tokens_in:  int           = 0
    tokens_out: int           = 0

@dataclass
class TaskSession:
    id:          str                  = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task:        str                  = ""
    model:       str                  = ""
    steps:       List[AgentStep]      = field(default_factory=list)
    start_time:  float                = field(default_factory=time.time)
    end_time:    Optional[float]      = None
    success:     bool                 = False
    final_msg:   str                  = ""
    total_in:    int                  = 0
    total_out:   int                  = 0

    @property
    def elapsed(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self) -> Dict:
        return {
            "id":         self.id,
            "task":       self.task,
            "model":      self.model,
            "steps":      len(self.steps),
            "elapsed_s":  round(self.elapsed, 2),
            "success":    self.success,
            "final_msg":  self.final_msg,
            "tokens_in":  self.total_in,
            "tokens_out": self.total_out,
        }


# =============================================================================
# §3  LOGGING
# =============================================================================

class VaelorLogger:
    """
    Dual-output logger: rich console for interactive display +
    rotating file log for forensics.  Thread-safe.
    """
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
            "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%H:%M:%S",
        )
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(fmt)
        self._log = logging.getLogger("vaelor")
        self._log.setLevel(logging.DEBUG)
        if not self._log.handlers:
            self._log.addHandler(fh)
        self._path = path

    # ── public helpers ────────────────────────────────────────────────────────

    def info(self, msg: str, **kw):
        self._log.info(msg, **kw)
        if HAS_RICH:
            console.print(f"[dim]{msg}[/dim]")

    def success(self, msg: str):
        self._log.info("✓ " + msg)
        if HAS_RICH:
            console.print(f"[bold green]✓[/bold green] {msg}")
        else:
            print("✓", msg)

    def warn(self, msg: str):
        self._log.warning(msg)
        if HAS_RICH:
            console.print(f"[bold yellow]⚠[/bold yellow]  {msg}")
        else:
            print("⚠", msg)

    def error(self, msg: str):
        self._log.error(msg)
        if HAS_RICH:
            console.print(f"[bold red]✗[/bold red]  {msg}")
        else:
            print("✗", msg)

    def debug(self, msg: str):
        self._log.debug(msg)

    def tool(self, name: str, args: Dict, result: ActionResult):
        status = "✓" if result.success else "✗"
        color  = "green" if result.success else "red"
        self._log.debug(f"TOOL {status} {name}  args={args}  err={result.error}")
        if HAS_RICH:
            arg_str = ", ".join(f"{k}={repr(v)[:40]}" for k, v in args.items())
            console.print(f"  [{color}]{status}[/{color}] [bold cyan]{name}[/bold cyan]({arg_str})")

    def step(self, idx: int, msg: str):
        self._log.info(f"STEP {idx}  {msg[:120]}")
        if HAS_RICH:
            console.rule(f"[bold]Step {idx}[/bold]")
            console.print(Markdown(msg[:600]))
        else:
            print(f"\n── Step {idx} ──")
            print(msg[:600])

    @property
    def log_path(self) -> Path:
        return self._path


log = VaelorLogger()


# =============================================================================
# §4  CONFIGURATION MANAGER
# =============================================================================

class ConfigManager:
    """
    Loads / saves ~/.vaelor/config.json.
    Merges CLI args → env vars → file → defaults.
    """
    DEFAULTS: Dict[str, Any] = {
        "openrouter_key":   "",
        "default_model":    "openai/gpt-4o",
        "screenshot_qual":  SCREENSHOT_QUAL,
        "max_steps":        MAX_STEPS,
        "loop_sleep_ms":    LOOP_SLEEP_MS,
        "safe_mode":        True,         # require confirmation for destructive ops
        "save_sessions":    True,
        "save_screenshots": False,
        "verbose":          False,
    }

    def __init__(self, overrides: Optional[Dict] = None):
        self._data: Dict[str, Any] = copy.deepcopy(self.DEFAULTS)
        self._load_file()
        self._load_env()
        if overrides:
            self._data.update({k: v for k, v in overrides.items() if v is not None})

    def _load_file(self):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH) as f:
                    self._data.update(json.load(f))
            except Exception as e:
                log.warn(f"Config file unreadable: {e}")

    def _load_env(self):
        mapping = {
            "OPENROUTER_API_KEY": "openrouter_key",
            "VAELOR_MODEL":       "default_model",
            "VAELOR_SAFE_MODE":   "safe_mode",
            "VAELOR_VERBOSE":     "verbose",
        }
        for env, key in mapping.items():
            val = os.environ.get(env)
            if val is not None:
                if isinstance(self.DEFAULTS.get(key), bool):
                    self._data[key] = val.lower() in ("1", "true", "yes")
                else:
                    self._data[key] = val

    def save(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(self._data, f, indent=2)
        log.debug(f"Config saved → {CONFIG_PATH}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any):
        self._data[key] = value


# =============================================================================
# §5  SCREEN CAPTURE ENGINE
# =============================================================================

class ScreenCapture:
    """
    High-performance screenshot engine.
    Supports PIL ImageGrab, pyautogui, and scrot/gnome-screenshot fallbacks.
    Produces resized + quality-compressed JPEG bytes suitable for vision APIs.
    """

    def __init__(self, cfg: ConfigManager):
        self._cfg     = cfg
        self._info    = self._detect_screen()
        self._last_ts = 0.0
        self._last_b64: Optional[str] = None

    # ── public API ────────────────────────────────────────────────────────────

    def capture(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,  # (x, y, w, h)
        annotate: bool = False,
        mark_center: bool = False,
    ) -> Tuple[bytes, str]:
        """
        Returns (jpeg_bytes, base64_string).
        region=(x, y, w, h) crops; None = full screen.
        """
        img = self._grab(region)
        if annotate:
            img = self._draw_crosshair(img)
        if mark_center:
            img = self._draw_center(img)
        img = self._resize(img)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=self._cfg.get("screenshot_qual", SCREENSHOT_QUAL))
        raw = buf.getvalue()
        b64 = base64.b64encode(raw).decode()
        self._last_ts  = time.time()
        self._last_b64 = b64
        return raw, b64

    def capture_element(self, x: int, y: int, padding: int = 80) -> Tuple[bytes, str]:
        """Capture a tight region around a coordinate."""
        si = self._info
        x0 = max(0, x - padding)
        y0 = max(0, y - padding)
        x1 = min(si.width, x + padding)
        y1 = min(si.height, y + padding)
        return self.capture(region=(x0, y0, x1 - x0, y1 - y0))

    @property
    def screen_info(self) -> ScreenInfo:
        return self._info

    # ── internals ─────────────────────────────────────────────────────────────

    def _grab(self, region: Optional[Tuple[int, int, int, int]]) -> "Image.Image":
        if not HAS_PIL:
            raise RuntimeError("Pillow is required for screen capture (pip install pillow)")

        bbox = None
        if region:
            x, y, w, h = region
            bbox = (x, y, x + w, y + h)

        # Method 1: PIL ImageGrab (Windows + macOS)
        try:
            img = ImageGrab.grab(bbox=bbox, all_screens=True)
            return img.convert("RGB")
        except Exception:
            pass

        # Method 2: pyautogui screenshot
        if HAS_PYAUTOGUI:
            try:
                img = pyautogui.screenshot(region=region)
                return img.convert("RGB")
            except Exception:
                pass

        # Method 3: Linux scrot fallback
        if sys.platform.startswith("linux"):
            return self._grab_linux(bbox)

        raise RuntimeError("No screenshot backend available")

    def _grab_linux(self, bbox: Optional[Tuple]) -> "Image.Image":
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp = f.name
        try:
            if shutil.which("scrot"):
                cmd = ["scrot", tmp]
                if bbox:
                    x, y, x2, y2 = bbox
                    cmd = ["scrot", "-a", f"{x},{y},{x2-x},{y2-y}", tmp]
            elif shutil.which("gnome-screenshot"):
                cmd = ["gnome-screenshot", "-f", tmp]
            elif shutil.which("import"):  # ImageMagick
                cmd = ["import", "-window", "root", tmp]
            else:
                raise RuntimeError("No Linux screenshot tool found (scrot/gnome-screenshot/import)")
            subprocess.run(cmd, check=True, capture_output=True)
            img = Image.open(tmp).convert("RGB")
            if bbox and shutil.which("scrot") is None:
                img = img.crop(bbox)
            return img
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp)

    def _resize(self, img: "Image.Image") -> "Image.Image":
        max_dim = MAX_IMG_DIM
        w, h    = img.size
        scale   = min(max_dim / w, max_dim / h, 1.0)
        if scale < 1.0:
            nw, nh = int(w * scale), int(h * scale)
            img = img.resize((nw, nh), Image.LANCZOS)
        return img

    def _draw_crosshair(self, img: "Image.Image") -> "Image.Image":
        draw = ImageDraw.Draw(img)
        w, h = img.size
        cx, cy = w // 2, h // 2
        draw.line([(cx - 20, cy), (cx + 20, cy)], fill=(255, 0, 0), width=2)
        draw.line([(cx, cy - 20), (cx, cy + 20)], fill=(255, 0, 0), width=2)
        return img

    def _draw_center(self, img: "Image.Image") -> "Image.Image":
        draw = ImageDraw.Draw(img)
        w, h = img.size
        cx, cy = w // 2, h // 2
        r = 8
        draw.ellipse([(cx-r, cy-r), (cx+r, cy+r)], outline=(0, 255, 0), width=2)
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
        # Fallback: common resolution
        return ScreenInfo(width=1920, height=1080)


# =============================================================================
# §6  MOUSE CONTROLLER
# =============================================================================

class MouseController:
    """
    Precise, safe, human-like mouse controller.
    Supports linear, bezier, and teleport movement modes.
    Validates coordinates against screen bounds.
    """

    MOVE_MODES = Literal["linear", "bezier", "instant"]

    def __init__(self, screen: ScreenInfo, cfg: ConfigManager):
        self._screen = screen
        self._cfg    = cfg
        self._last_x = 0
        self._last_y = 0

    # ── coordinate helpers ────────────────────────────────────────────────────

    def _clamp(self, x: int, y: int) -> Tuple[int, int]:
        x = max(1, min(x, self._screen.width  - 1))
        y = max(1, min(y, self._screen.height - 1))
        return x, y

    def _validate(self, x: int, y: int) -> Tuple[int, int]:
        cx, cy = self._clamp(x, y)
        if (cx, cy) != (x, y):
            log.warn(f"Coordinates ({x},{y}) clamped to ({cx},{cy})")
        return cx, cy

    # ── public actions ────────────────────────────────────────────────────────

    def move(
        self,
        x: int,
        y: int,
        duration: float = 0.3,
        mode: str = "bezier",
    ) -> ActionResult:
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        x, y = self._validate(x, y)
        try:
            if mode == "instant":
                pyautogui.moveTo(x, y)
            elif mode == "bezier":
                self._bezier_move(x, y, duration)
            else:
                pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)
            self._last_x, self._last_y = x, y
            return ActionResult(True, output=f"Moved to ({x},{y})")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.08,
        move_duration: float = 0.25,
    ) -> ActionResult:
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        x, y = self._validate(x, y)
        try:
            mv = self.move(x, y, duration=move_duration)
            if not mv.success:
                return mv
            time.sleep(0.05)
            pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)
            self._last_x, self._last_y = x, y
            return ActionResult(
                True,
                output=f"{button.title()} click{'×'+str(clicks) if clicks>1 else ''} @ ({x},{y})",
            )
        except Exception as e:
            return ActionResult(False, error=str(e))

    def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float = 0.5,
        button: str = "left",
    ) -> ActionResult:
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        x1, y1 = self._validate(x1, y1)
        x2, y2 = self._validate(x2, y2)
        try:
            pyautogui.moveTo(x1, y1, duration=0.2)
            time.sleep(0.05)
            pyautogui.dragTo(x2, y2, duration=duration, button=button)
            return ActionResult(True, output=f"Drag ({x1},{y1})→({x2},{y2})")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def scroll(
        self,
        x: int,
        y: int,
        amount: int,           # positive = up, negative = down
        direction: str = "vertical",
    ) -> ActionResult:
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        x, y = self._validate(x, y)
        try:
            pyautogui.moveTo(x, y, duration=0.1)
            if direction == "horizontal":
                pyautogui.hscroll(amount)
            else:
                pyautogui.scroll(amount, x=x, y=y)
            return ActionResult(True, output=f"Scrolled {amount} at ({x},{y})")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def get_position(self) -> Tuple[int, int]:
        if HAS_PYAUTOGUI:
            return pyautogui.position()
        return self._last_x, self._last_y

    # ── bezier move helper ────────────────────────────────────────────────────

    def _bezier_move(self, tx: int, ty: int, duration: float):
        sx, sy = self.get_position()
        import random
        # Random control points for human-like curve
        cx1 = sx + random.randint(-80, 80)
        cy1 = sy + random.randint(-80, 80)
        cx2 = tx + random.randint(-80, 80)
        cy2 = ty + random.randint(-80, 80)
        steps = max(20, int(duration * 60))
        for i in range(steps + 1):
            t = i / steps
            it = 1 - t
            px = int(it**3*sx + 3*it**2*t*cx1 + 3*it*t**2*cx2 + t**3*tx)
            py = int(it**3*sy + 3*it**2*t*cy1 + 3*it*t**2*cy2 + t**3*ty)
            pyautogui.moveTo(px, py, _pause=False)
            time.sleep(duration / steps)


# =============================================================================
# §7  KEYBOARD CONTROLLER
# =============================================================================

class KeyboardController:
    """
    Keyboard input: typing, hotkeys, special keys.
    Handles text injection with clipboard fallback for speed.
    """

    # Map of friendly names → pyautogui key names
    KEY_ALIASES: Dict[str, str] = {
        "enter":     "enter",
        "return":    "enter",
        "tab":       "tab",
        "escape":    "escape",
        "esc":       "escape",
        "space":     "space",
        "backspace": "backspace",
        "delete":    "delete",
        "del":       "delete",
        "up":        "up",
        "down":      "down",
        "left":      "left",
        "right":     "right",
        "home":      "home",
        "end":       "end",
        "pageup":    "pageup",
        "pagedown":  "pagedown",
        "f1":  "f1",  "f2":  "f2",  "f3":  "f3",  "f4":  "f4",
        "f5":  "f5",  "f6":  "f6",  "f7":  "f7",  "f8":  "f8",
        "f9":  "f9",  "f10": "f10", "f11": "f11", "f12": "f12",
        "ctrl":  "ctrl",  "control": "ctrl",
        "alt":   "alt",
        "shift": "shift",
        "cmd":   "command",
        "win":   "winleft",
        "super": "winleft",
    }

    def __init__(self, cfg: ConfigManager):
        self._cfg = cfg

    def type_text(
        self,
        text: str,
        interval: float = 0.02,
        use_clipboard: bool = False,
    ) -> ActionResult:
        """Type text into the focused element."""
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        try:
            if use_clipboard and HAS_CLIPBOARD:
                # Clipboard method: fast for long strings
                old = pyperclip.paste()
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v") if sys.platform != "darwin" \
                    else pyautogui.hotkey("command", "v")
                time.sleep(0.1)
                pyperclip.copy(old)   # restore clipboard
            else:
                # Direct typing (handles unicode better)
                pyautogui.typewrite(text, interval=interval)
            return ActionResult(True, output=f"Typed: {text[:80]}{'…' if len(text)>80 else ''}")
        except Exception as e:
            # Fallback: try one char at a time
            try:
                for ch in text:
                    pyautogui.press(ch)
                return ActionResult(True, output=f"Typed (char-by-char): {text[:80]}")
            except Exception as e2:
                return ActionResult(False, error=f"{e} / fallback: {e2}")

    def key_press(self, key: str) -> ActionResult:
        """Press a single key."""
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        try:
            k = self.KEY_ALIASES.get(key.lower(), key.lower())
            pyautogui.press(k)
            return ActionResult(True, output=f"Pressed: {key}")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def hotkey(self, *keys: str) -> ActionResult:
        """Press a keyboard shortcut (e.g. ctrl+c)."""
        if not HAS_PYAUTOGUI:
            return ActionResult(False, error="pyautogui not installed")
        try:
            resolved = [self.KEY_ALIASES.get(k.lower(), k.lower()) for k in keys]
            pyautogui.hotkey(*resolved)
            return ActionResult(True, output=f"Hotkey: {'+'.join(keys)}")
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
# §8  CLIPBOARD MANAGER
# =============================================================================

class ClipboardManager:
    def get(self) -> ActionResult:
        if HAS_CLIPBOARD:
            try:
                txt = pyperclip.paste()
                return ActionResult(True, output=txt)
            except Exception as e:
                return ActionResult(False, error=str(e))
        # Fallback: xclip / xsel on Linux
        if sys.platform.startswith("linux"):
            for tool in ("xclip -selection clipboard -o", "xsel --clipboard --output"):
                try:
                    r = subprocess.run(shlex.split(tool), capture_output=True, text=True, timeout=3)
                    if r.returncode == 0:
                        return ActionResult(True, output=r.stdout)
                except Exception:
                    continue
        return ActionResult(False, error="No clipboard backend available")

    def set(self, text: str) -> ActionResult:
        if HAS_CLIPBOARD:
            try:
                pyperclip.copy(text)
                return ActionResult(True, output=f"Clipboard set ({len(text)} chars)")
            except Exception as e:
                return ActionResult(False, error=str(e))
        return ActionResult(False, error="No clipboard backend available")


# =============================================================================
# §9  APPLICATION & WINDOW MANAGER
# =============================================================================

class AppManager:
    """
    Cross-platform application launcher, window lister, and switcher.
    Uses platform-appropriate mechanisms (subprocess, xdotool, AppleScript, Win32).
    """

    def __init__(self, cfg: ConfigManager):
        self._cfg = cfg
        self._os  = sys.platform

    # ── launch ────────────────────────────────────────────────────────────────

    def open(self, app_name: str) -> ActionResult:
        """Launch an application by name or path."""
        try:
            if self._os == "darwin":
                return self._open_macos(app_name)
            elif self._os == "win32":
                return self._open_windows(app_name)
            else:
                return self._open_linux(app_name)
        except Exception as e:
            return ActionResult(False, error=str(e))

    def _open_macos(self, name: str) -> ActionResult:
        # Try `open -a` first, then direct path
        for cmd in [["open", "-a", name], [name]]:
            r = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)
            return ActionResult(True, output=f"Launched {name} (macOS)")
        return ActionResult(False, error=f"Cannot open {name}")

    def _open_windows(self, name: str) -> ActionResult:
        try:
            os.startfile(name)
        except AttributeError:
            subprocess.Popen(["start", name], shell=True)
        time.sleep(1.5)
        return ActionResult(True, output=f"Launched {name} (Windows)")

    def _open_linux(self, name: str) -> ActionResult:
        procs = [
            [name],
            ["xdg-open", name],
            ["gtk-launch", name],
        ]
        for cmd in procs:
            if shutil.which(cmd[0]):
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1.5)
                return ActionResult(True, output=f"Launched {name} (Linux)")
        return ActionResult(False, error=f"Cannot find launcher for {name}")

    # ── window management ─────────────────────────────────────────────────────

    def list_windows(self) -> ActionResult:
        """List visible windows."""
        try:
            if self._os == "win32":
                return self._list_windows_win()
            elif self._os == "darwin":
                return self._list_windows_mac()
            else:
                return self._list_windows_linux()
        except Exception as e:
            return ActionResult(False, error=str(e))

    def _list_windows_linux(self) -> ActionResult:
        if shutil.which("xdotool"):
            r = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--name", ""],
                capture_output=True, text=True, timeout=5,
            )
            ids  = r.stdout.strip().split()
            wins = []
            for wid in ids[:30]:
                nr = subprocess.run(
                    ["xdotool", "getwindowname", wid],
                    capture_output=True, text=True, timeout=2,
                )
                name = nr.stdout.strip()
                if name:
                    wins.append(f"{wid}: {name}")
            return ActionResult(True, output="\n".join(wins) or "No windows found")
        return ActionResult(False, error="xdotool not installed")

    def _list_windows_mac(self) -> ActionResult:
        script = """
        tell application "System Events"
            set wins to {}
            repeat with proc in (processes whose background only is false)
                set procName to name of proc
                repeat with win in windows of proc
                    set end of wins to procName & ": " & name of win
                end repeat
            end repeat
            return wins as string
        end tell
        """
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
        return ActionResult(True, output=r.stdout.strip() or "No windows found")

    def _list_windows_win(self) -> ActionResult:
        try:
            import ctypes
            wins = []
            def cb(hwnd, _):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    buf = ctypes.create_unicode_buffer(256)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                    if buf.value:
                        wins.append(f"{hwnd}: {buf.value}")
            ctypes.windll.user32.EnumWindows(
                ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(cb), 0
            )
            return ActionResult(True, output="\n".join(wins[:40]))
        except Exception as e:
            return ActionResult(False, error=str(e))

    def switch_to(self, window_title: str) -> ActionResult:
        """Bring a window matching title to focus."""
        try:
            if self._os == "darwin":
                script = f'tell application "{window_title}" to activate'
                subprocess.run(["osascript", "-e", script], check=True, timeout=5)
                return ActionResult(True, output=f"Switched to {window_title}")
            elif self._os.startswith("linux") and shutil.which("xdotool"):
                r = subprocess.run(
                    ["xdotool", "search", "--name", window_title, "windowactivate", "--sync"],
                    capture_output=True, text=True, timeout=5,
                )
                if r.returncode == 0:
                    return ActionResult(True, output=f"Switched to {window_title}")
            elif self._os == "win32":
                if HAS_PYAUTOGUI:
                    import pygetwindow as gw
                    wins = gw.getWindowsWithTitle(window_title)
                    if wins:
                        wins[0].activate()
                        return ActionResult(True, output=f"Switched to {window_title}")
            return ActionResult(False, error=f"Window '{window_title}' not found")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def close_app(self, app_name: str) -> ActionResult:
        """Gracefully close an application."""
        if HAS_PSUTIL:
            for proc in psutil.process_iter(["name", "pid"]):
                if app_name.lower() in (proc.info["name"] or "").lower():
                    proc.terminate()
                    return ActionResult(True, output=f"Terminated {app_name} (pid={proc.pid})")
        return ActionResult(False, error=f"Process '{app_name}' not found (psutil required)")


# =============================================================================
# §10  TERMINAL / SHELL CONTROLLER
# =============================================================================

class TerminalController:
    """
    Execute shell commands, capture stdout/stderr, manage a persistent shell.
    Supports timeout, environment injection, and working-directory control.
    """

    def __init__(self, cfg: ConfigManager):
        self._cfg    = cfg
        self._cwd    = Path.home()
        self._env    = {**os.environ}
        self._history: List[Dict] = []

    def run(
        self,
        command: str,
        timeout: float = 30.0,
        cwd: Optional[str] = None,
        capture_stderr: bool = True,
    ) -> ActionResult:
        """Run a shell command and return stdout."""
        work_dir = Path(cwd) if cwd else self._cwd
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(work_dir),
                env=self._env,
            )
            combined = proc.stdout
            if capture_stderr and proc.stderr:
                combined += "\nSTDERR:\n" + proc.stderr
            entry = {
                "cmd":    command,
                "rc":     proc.returncode,
                "stdout": proc.stdout[:2000],
            }
            self._history.append(entry)
            if proc.returncode != 0:
                return ActionResult(
                    False,
                    output=combined,
                    error=f"Exit code {proc.returncode}",
                    metadata={"returncode": proc.returncode},
                )
            return ActionResult(True, output=combined or "(no output)", metadata={"returncode": 0})
        except subprocess.TimeoutExpired:
            return ActionResult(False, error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def cd(self, path: str) -> ActionResult:
        target = (self._cwd / path).resolve()
        if target.is_dir():
            self._cwd = target
            return ActionResult(True, output=f"CWD: {self._cwd}")
        return ActionResult(False, error=f"Directory not found: {target}")

    def read_file(self, path: str, max_bytes: int = 65536) -> ActionResult:
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return ActionResult(False, error=f"File not found: {p}")
            size = p.stat().st_size
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_bytes)
            note = f"\n…[truncated, total {size} bytes]" if size > max_bytes else ""
            return ActionResult(True, output=content + note, metadata={"size": size, "path": str(p)})
        except Exception as e:
            return ActionResult(False, error=str(e))

    def write_file(self, path: str, content: str, append: bool = False) -> ActionResult:
        try:
            p = Path(path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(p, mode, encoding="utf-8") as f:
                f.write(content)
            return ActionResult(True, output=f"{'Appended' if append else 'Wrote'} {len(content)} chars → {p}")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def list_dir(self, path: str = ".") -> ActionResult:
        try:
            p = (self._cwd / path).resolve()
            if not p.is_dir():
                return ActionResult(False, error=f"Not a directory: {p}")
            entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
            lines = []
            for e in entries[:200]:
                icon = "📁" if e.is_dir() else "📄"
                size = ""
                if e.is_file():
                    try:
                        size = f"  {e.stat().st_size:,}b"
                    except Exception:
                        pass
                lines.append(f"{icon} {e.name}{size}")
            return ActionResult(True, output="\n".join(lines) or "(empty)", metadata={"path": str(p)})
        except Exception as e:
            return ActionResult(False, error=str(e))


# =============================================================================
# §11  VISUAL ELEMENT FINDER  (find text / color on screen)
# =============================================================================

class VisualFinder:
    """
    Locate UI elements on screen by colour region, text match (OCR-free),
    or template matching (when OpenCV available).
    For text detection we rely on sending screenshots to the vision model.
    """

    def __init__(self, screen: ScreenCapture, cfg: ConfigManager):
        self._screen = screen
        self._cfg    = cfg

    def find_color_region(
        self,
        r: int, g: int, b: int,
        tolerance: int = 20,
    ) -> ActionResult:
        """Find all pixels matching an RGB color (±tolerance)."""
        if not HAS_PIL:
            return ActionResult(False, error="Pillow required")
        raw, _ = self._screen.capture()
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        arr = list(img.getdata())
        matches = []
        w, h    = img.size
        for idx, (pr, pg, pb) in enumerate(arr):
            if abs(pr-r)<=tolerance and abs(pg-g)<=tolerance and abs(pb-b)<=tolerance:
                x_px = idx % w
                y_px = idx // w
                matches.append((x_px, y_px))
        if not matches:
            return ActionResult(False, error=f"Color ({r},{g},{b}) not found")
        # Return centroid of first cluster
        xs = [m[0] for m in matches[:500]]
        ys = [m[1] for m in matches[:500]]
        cx, cy = int(sum(xs)/len(xs)), int(sum(ys)/len(ys))
        return ActionResult(
            True,
            output=f"Found {len(matches)} pixels. Centroid: ({cx},{cy})",
            metadata={"x": cx, "y": cy, "count": len(matches)},
        )

    def template_match(self, template_path: str, threshold: float = 0.8) -> ActionResult:
        """Find a template image on screen using OpenCV."""
        if not HAS_CV2:
            return ActionResult(False, error="opencv-python required for template matching")
        if not Path(template_path).exists():
            return ActionResult(False, error=f"Template not found: {template_path}")
        raw, _ = self._screen.capture()
        screen_arr = np.frombuffer(raw, dtype=np.uint8)
        screen_img = cv2.imdecode(screen_arr, cv2.IMREAD_COLOR)
        tmpl       = cv2.imread(template_path, cv2.IMREAD_COLOR)
        result     = cv2.matchTemplate(screen_img, tmpl, cv2.TM_CCOEFF_NORMED)
        _, maxval, _, maxloc = cv2.minMaxLoc(result)
        if maxval < threshold:
            return ActionResult(False, error=f"Template not found (best match: {maxval:.2f})")
        th, tw = tmpl.shape[:2]
        cx = maxloc[0] + tw // 2
        cy = maxloc[1] + th // 2
        return ActionResult(
            True,
            output=f"Template found @ ({cx},{cy}), confidence={maxval:.2f}",
            metadata={"x": cx, "y": cy, "confidence": maxval},
        )

    def wait_for_change(self, timeout: float = 10.0, threshold: float = 0.02) -> ActionResult:
        """Wait until the screen changes (useful after triggering an action)."""
        if not HAS_PIL:
            return ActionResult(False, error="Pillow required")
        _, b64_before = self._screen.capture()
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.25)
            _, b64_after = self._screen.capture()
            if b64_before != b64_after:
                return ActionResult(True, output="Screen changed")
        return ActionResult(False, error=f"Screen did not change within {timeout}s")


# =============================================================================
# §12  TOOL REGISTRY & DEFINITIONS
# =============================================================================

@dataclass
class ToolDefinition:
    name:        str
    description: str
    parameters:  Dict[str, Any]   # JSON Schema object
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
    """
    Central registry of all agent tools.
    Builds OpenAI-compatible function-calling schemas.
    Dispatches tool calls to handler functions.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool
        log.debug(f"Tool registered: {tool.name}")

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def schemas(self) -> List[Dict]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def dispatch(self, name: str, args: Dict) -> ActionResult:
        tool = self._tools.get(name)
        if tool is None:
            return ActionResult(False, error=f"Unknown tool: {name}")
        if tool.handler is None:
            return ActionResult(False, error=f"Tool '{name}' has no handler attached")
        try:
            return tool.handler(**args)
        except TypeError as e:
            return ActionResult(False, error=f"Bad arguments for {name}: {e}")
        except Exception as e:
            return ActionResult(False, error=f"Tool '{name}' raised: {traceback.format_exc(limit=3)}")


# =============================================================================
# §13  TOOL BUILDER  (wires hardware controllers → tool definitions)
# =============================================================================

class ToolBuilder:
    """
    Constructs and wires all ToolDefinitions against the hardware controllers.
    Returns a fully-populated ToolRegistry.
    """

    def __init__(
        self,
        screen:    ScreenCapture,
        mouse:     MouseController,
        keyboard:  KeyboardController,
        clipboard: ClipboardManager,
        apps:      AppManager,
        terminal:  TerminalController,
        finder:    VisualFinder,
        cfg:       ConfigManager,
    ):
        self._sc  = screen
        self._mo  = mouse
        self._kb  = keyboard
        self._cb  = clipboard
        self._ap  = apps
        self._te  = terminal
        self._fi  = finder
        self._cfg = cfg

    def build(self) -> ToolRegistry:
        reg = ToolRegistry()
        for tool in self._all_tools():
            reg.register(tool)
        return reg

    # ─────────────────────────────────────────────────────────────────────────
    # TOOL DEFINITIONS (each is a ToolDefinition + inline handler lambda/func)
    # ─────────────────────────────────────────────────────────────────────────

    def _all_tools(self) -> List[ToolDefinition]:
        sc, mo, kb, cb, ap, te, fi = (
            self._sc, self._mo, self._kb, self._cb, self._ap, self._te, self._fi
        )

        def _screenshot(
            region_x: int = None, region_y: int = None,
            region_w: int = None, region_h: int = None,
        ) -> ActionResult:
            region = None
            if all(v is not None for v in [region_x, region_y, region_w, region_h]):
                region = (region_x, region_y, region_w, region_h)
            raw, b64 = sc.capture(region=region)
            return ActionResult(
                True,
                output="Screenshot captured.",
                screenshot=raw,
                metadata={"b64": b64, "size": len(raw)},
            )

        def _get_screen_info() -> ActionResult:
            si = sc.screen_info
            return ActionResult(
                True,
                output=(
                    f"Screen: {si.width}×{si.height}px, "
                    f"scale={si.scale_factor}, monitors={si.monitor_count}"
                ),
                metadata=asdict(si),
            )

        def _click(x: int, y: int, button: str = "left", clicks: int = 1) -> ActionResult:
            return mo.click(x, y, button=button, clicks=clicks)

        def _double_click(x: int, y: int) -> ActionResult:
            return mo.click(x, y, clicks=2)

        def _right_click(x: int, y: int) -> ActionResult:
            return mo.click(x, y, button="right")

        def _middle_click(x: int, y: int) -> ActionResult:
            return mo.click(x, y, button="middle")

        def _move(x: int, y: int, duration: float = 0.3) -> ActionResult:
            return mo.move(x, y, duration=duration)

        def _drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> ActionResult:
            return mo.drag(x1, y1, x2, y2, duration=duration)

        def _scroll(x: int, y: int, amount: int, direction: str = "vertical") -> ActionResult:
            return mo.scroll(x, y, amount, direction=direction)

        def _type_text(text: str, interval: float = 0.02) -> ActionResult:
            return kb.type_text(text, interval=interval, use_clipboard=len(text) > 200)

        def _key_press(key: str) -> ActionResult:
            return kb.key_press(key)

        def _hotkey(keys: str) -> ActionResult:
            parts = [k.strip() for k in keys.replace("+", " ").split()]
            return kb.hotkey(*parts)

        def _copy() -> ActionResult:
            return kb.copy()

        def _paste() -> ActionResult:
            return kb.paste()

        def _get_clipboard() -> ActionResult:
            return cb.get()

        def _set_clipboard(text: str) -> ActionResult:
            return cb.set(text)

        def _open_app(app_name: str) -> ActionResult:
            return ap.open(app_name)

        def _close_app(app_name: str) -> ActionResult:
            return ap.close_app(app_name)

        def _switch_window(title: str) -> ActionResult:
            return ap.switch_to(title)

        def _list_windows() -> ActionResult:
            return ap.list_windows()

        def _run_command(command: str, timeout: float = 30.0, cwd: str = None) -> ActionResult:
            return te.run(command, timeout=timeout, cwd=cwd)

        def _read_file(path: str) -> ActionResult:
            return te.read_file(path)

        def _write_file(path: str, content: str, append: bool = False) -> ActionResult:
            return te.write_file(path, content, append=append)

        def _list_dir(path: str = ".") -> ActionResult:
            return te.list_dir(path)

        def _find_on_screen(color_r: int = None, color_g: int = None, color_b: int = None,
                             template_path: str = None) -> ActionResult:
            if template_path:
                return fi.template_match(template_path)
            if all(v is not None for v in [color_r, color_g, color_b]):
                return fi.find_color_region(color_r, color_g, color_b)
            return ActionResult(False, error="Provide color (r,g,b) or template_path")

        def _wait(seconds: float) -> ActionResult:
            time.sleep(min(seconds, 30.0))
            return ActionResult(True, output=f"Waited {seconds}s")

        def _wait_for_change(timeout: float = 10.0) -> ActionResult:
            return fi.wait_for_change(timeout=timeout)

        def _task_complete(summary: str) -> ActionResult:
            return ActionResult(
                True,
                output=summary,
                metadata={"__task_done__": True},
            )

        def _think(thought: str) -> ActionResult:
            """Internal scratchpad — lets the model reason without acting."""
            log.debug(f"[THINK] {thought}")
            return ActionResult(True, output="Thought recorded.")

        # ── Build ToolDefinition list ─────────────────────────────────────────

        P = lambda t, d, **extra: {"type": t, "description": d, **extra}

        return [
            ToolDefinition(
                name="screenshot",
                description=(
                    "Capture the current screen state. "
                    "ALWAYS call this before deciding what to do next. "
                    "Optionally crop to a specific region."
                ),
                parameters={
                    "region_x": P("integer", "Left edge of crop region (pixels)"),
                    "region_y": P("integer", "Top edge of crop region (pixels)"),
                    "region_w": P("integer", "Width of crop region (pixels)"),
                    "region_h": P("integer", "Height of crop region (pixels)"),
                },
                required=[],
                handler=_screenshot,
            ),
            ToolDefinition(
                name="get_screen_info",
                description="Return screen dimensions and monitor count.",
                parameters={},
                required=[],
                handler=_get_screen_info,
            ),
            ToolDefinition(
                name="click",
                description="Click at screen coordinates.",
                parameters={
                    "x":      P("integer", "Horizontal coordinate (pixels from left)"),
                    "y":      P("integer", "Vertical coordinate (pixels from top)"),
                    "button": P("string",  "Mouse button: 'left', 'right', 'middle'",
                                enum=["left", "right", "middle"]),
                    "clicks": P("integer", "Number of clicks (1=single, 2=double)"),
                },
                required=["x", "y"],
                handler=_click,
            ),
            ToolDefinition(
                name="double_click",
                description="Double-click at coordinates (opens files, selects words).",
                parameters={
                    "x": P("integer", "X coordinate"),
                    "y": P("integer", "Y coordinate"),
                },
                required=["x", "y"],
                handler=_double_click,
            ),
            ToolDefinition(
                name="right_click",
                description="Right-click at coordinates to open context menu.",
                parameters={
                    "x": P("integer", "X coordinate"),
                    "y": P("integer", "Y coordinate"),
                },
                required=["x", "y"],
                handler=_right_click,
            ),
            ToolDefinition(
                name="middle_click",
                description="Middle-click (opens links in new tab, closes tabs).",
                parameters={
                    "x": P("integer", "X coordinate"),
                    "y": P("integer", "Y coordinate"),
                },
                required=["x", "y"],
                handler=_middle_click,
            ),
            ToolDefinition(
                name="move",
                description="Move mouse cursor to coordinates without clicking.",
                parameters={
                    "x":        P("integer", "X coordinate"),
                    "y":        P("integer", "Y coordinate"),
                    "duration": P("number",  "Move duration in seconds (default 0.3)"),
                },
                required=["x", "y"],
                handler=_move,
            ),
            ToolDefinition(
                name="drag",
                description="Click-and-drag from one position to another.",
                parameters={
                    "x1":       P("integer", "Start X"),
                    "y1":       P("integer", "Start Y"),
                    "x2":       P("integer", "End X"),
                    "y2":       P("integer", "End Y"),
                    "duration": P("number",  "Drag duration in seconds"),
                },
                required=["x1", "y1", "x2", "y2"],
                handler=_drag,
            ),
            ToolDefinition(
                name="scroll",
                description=(
                    "Scroll the mouse wheel at a position. "
                    "Positive amount = scroll UP, negative = scroll DOWN."
                ),
                parameters={
                    "x":         P("integer", "X coordinate to scroll at"),
                    "y":         P("integer", "Y coordinate to scroll at"),
                    "amount":    P("integer", "Scroll clicks: positive=up, negative=down"),
                    "direction": P("string",  "Scroll axis",
                                   enum=["vertical", "horizontal"]),
                },
                required=["x", "y", "amount"],
                handler=_scroll,
            ),
            ToolDefinition(
                name="type_text",
                description=(
                    "Type text into the currently focused element. "
                    "Click the target field first. "
                    "Supports unicode. For passwords, use this tool directly."
                ),
                parameters={
                    "text":     P("string", "Text to type"),
                    "interval": P("number", "Delay between keystrokes in seconds (default 0.02)"),
                },
                required=["text"],
                handler=_type_text,
            ),
            ToolDefinition(
                name="key_press",
                description=(
                    "Press a single key. Use for navigation, confirmation, etc. "
                    "Key names: enter, escape, tab, space, backspace, delete, "
                    "up, down, left, right, home, end, pageup, pagedown, f1-f12."
                ),
                parameters={
                    "key": P("string", "Key name (e.g. 'enter', 'escape', 'tab', 'f5')"),
                },
                required=["key"],
                handler=_key_press,
            ),
            ToolDefinition(
                name="hotkey",
                description=(
                    "Press a keyboard shortcut. "
                    "Examples: 'ctrl+c', 'ctrl+shift+t', 'alt+f4', 'cmd+space'."
                ),
                parameters={
                    "keys": P("string", "Keys joined with '+', e.g. 'ctrl+c'"),
                },
                required=["keys"],
                handler=_hotkey,
            ),
            ToolDefinition(
                name="copy",
                description="Copy selected text/content to clipboard (Ctrl+C / Cmd+C).",
                parameters={},
                required=[],
                handler=_copy,
            ),
            ToolDefinition(
                name="paste",
                description="Paste clipboard content into focused element (Ctrl+V / Cmd+V).",
                parameters={},
                required=[],
                handler=_paste,
            ),
            ToolDefinition(
                name="get_clipboard",
                description="Read the current clipboard content as text.",
                parameters={},
                required=[],
                handler=_get_clipboard,
            ),
            ToolDefinition(
                name="set_clipboard",
                description="Write text to the clipboard.",
                parameters={
                    "text": P("string", "Text to place in clipboard"),
                },
                required=["text"],
                handler=_set_clipboard,
            ),
            ToolDefinition(
                name="open_app",
                description=(
                    "Launch an application by name or path. "
                    "Examples: 'firefox', 'notepad', 'Terminal', 'code', 'chrome'."
                ),
                parameters={
                    "app_name": P("string", "Application name or executable path"),
                },
                required=["app_name"],
                handler=_open_app,
            ),
            ToolDefinition(
                name="close_app",
                description="Terminate a running application by process name.",
                parameters={
                    "app_name": P("string", "Process name to kill (e.g. 'firefox', 'notepad')"),
                },
                required=["app_name"],
                handler=_close_app,
            ),
            ToolDefinition(
                name="switch_window",
                description="Bring a window with matching title to foreground focus.",
                parameters={
                    "title": P("string", "Partial or full window title to match"),
                },
                required=["title"],
                handler=_switch_window,
            ),
            ToolDefinition(
                name="list_windows",
                description="List all currently visible windows with their titles.",
                parameters={},
                required=[],
                handler=_list_windows,
            ),
            ToolDefinition(
                name="run_command",
                description=(
                    "Execute a shell command and return stdout + stderr. "
                    "Use for file operations, git, pip, npm, system commands, etc."
                ),
                parameters={
                    "command": P("string",  "Shell command to execute"),
                    "timeout": P("number",  "Timeout in seconds (default 30)"),
                    "cwd":     P("string",  "Working directory path"),
                },
                required=["command"],
                handler=_run_command,
            ),
            ToolDefinition(
                name="read_file",
                description="Read and return the contents of a file (up to 64KB).",
                parameters={
                    "path": P("string", "Absolute or relative file path"),
                },
                required=["path"],
                handler=_read_file,
            ),
            ToolDefinition(
                name="write_file",
                description="Write or append text content to a file.",
                parameters={
                    "path":    P("string",  "File path to write"),
                    "content": P("string",  "Text content to write"),
                    "append":  P("boolean", "If true, append to existing file"),
                },
                required=["path", "content"],
                handler=_write_file,
            ),
            ToolDefinition(
                name="list_dir",
                description="List files and folders in a directory.",
                parameters={
                    "path": P("string", "Directory path (default: current working dir)"),
                },
                required=[],
                handler=_list_dir,
            ),
            ToolDefinition(
                name="find_on_screen",
                description=(
                    "Find a UI element by colour or template image. "
                    "Provide either (color_r, color_g, color_b) or template_path."
                ),
                parameters={
                    "color_r":       P("integer", "Red component 0-255"),
                    "color_g":       P("integer", "Green component 0-255"),
                    "color_b":       P("integer", "Blue component 0-255"),
                    "template_path": P("string",  "Path to PNG template image"),
                },
                required=[],
                handler=_find_on_screen,
            ),
            ToolDefinition(
                name="wait",
                description="Pause execution for a number of seconds (max 30).",
                parameters={
                    "seconds": P("number", "Duration to wait"),
                },
                required=["seconds"],
                handler=_wait,
            ),
            ToolDefinition(
                name="wait_for_change",
                description=(
                    "Wait until the screen visually changes (useful after triggering an action). "
                    "Returns as soon as the screen updates."
                ),
                parameters={
                    "timeout": P("number", "Max wait time in seconds (default 10)"),
                },
                required=[],
                handler=_wait_for_change,
            ),
            ToolDefinition(
                name="think",
                description=(
                    "Internal reasoning scratchpad. "
                    "Use this to plan, reconsider, or note observations "
                    "WITHOUT taking any action. Does not affect the screen."
                ),
                parameters={
                    "thought": P("string", "Your reasoning / plan"),
                },
                required=["thought"],
                handler=_think,
            ),
            ToolDefinition(
                name="task_complete",
                description=(
                    "Signal that the assigned task is fully completed. "
                    "Provide a concise human-readable summary of what was accomplished."
                ),
                parameters={
                    "summary": P("string", "What was done and the final state"),
                },
                required=["summary"],
                handler=_task_complete,
            ),
        ]


# =============================================================================
# §14  OPENROUTER CLIENT
# =============================================================================

class OpenRouterClient:
    """
    Wraps the OpenRouter API (OpenAI-compatible).
    Handles:
      • Vision (base64 image in content)
      • Function / tool calling
      • Streaming (optional)
      • Retry with exponential back-off
      • Token counting (approximate via char heuristic)
    """

    def __init__(self, api_key: str, model: str, cfg: ConfigManager):
        if not HAS_REQUESTS:
            raise RuntimeError("pip install requests")
        self._key   = api_key
        self._model = model
        self._cfg   = cfg
        self._base  = OPENROUTER_BASE
        self._sess  = requests.Session()
        self._sess.headers.update({
            "Authorization":  f"Bearer {api_key}",
            "Content-Type":   "application/json",
            "HTTP-Referer":   "https://vaelor.ai",
            "X-Title":        "Vaelor CUA",
        })
        self._request_count = 0
        self._total_in      = 0
        self._total_out     = 0

    # ── public ────────────────────────────────────────────────────────────────

    def chat(
        self,
        messages:     List[Dict],
        tools:        Optional[List[Dict]] = None,
        max_tokens:   int = TOKEN_BUDGET,
        temperature:  float = 0.1,        # low temp = deterministic, task-focused
        stream:       bool = False,
    ) -> Dict:
        """
        Send messages to OpenRouter and return the parsed response dict.
        Retries up to MAX_RETRIES on transient errors.
        """
        payload: Dict[str, Any] = {
            "model":       self._model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
        }
        if tools:
            payload["tools"]       = tools
            payload["tool_choice"] = "auto"
        if stream:
            payload["stream"] = True

        last_err = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = self._sess.post(
                    f"{self._base}/chat/completions",
                    json=payload,
                    timeout=120,
                )
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    log.warn(f"Rate-limited; retrying in {wait}s…")
                    time.sleep(wait)
                    continue
                if resp.status_code >= 500:
                    wait = 2 ** attempt
                    log.warn(f"Server error {resp.status_code}; retrying in {wait}s…")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                self._request_count += 1
                usage = data.get("usage", {})
                self._total_in  += usage.get("prompt_tokens", 0)
                self._total_out += usage.get("completion_tokens", 0)
                return data
            except requests.exceptions.Timeout:
                last_err = "Request timed out"
                log.warn(f"Timeout on attempt {attempt+1}")
                time.sleep(2 ** attempt)
            except requests.exceptions.ConnectionError as e:
                last_err = str(e)
                log.warn(f"Connection error: {e}")
                time.sleep(2 ** attempt)
            except Exception as e:
                last_err = str(e)
                log.error(f"API error: {e}")
                break
        raise RuntimeError(f"OpenRouter request failed after {MAX_RETRIES} retries: {last_err}")

    def list_models(self) -> List[Dict]:
        """Fetch available models from OpenRouter."""
        try:
            r = self._sess.get(f"{self._base}/models", timeout=15)
            r.raise_for_status()
            return r.json().get("data", [])
        except Exception as e:
            log.error(f"Cannot fetch models: {e}")
            return []

    @property
    def stats(self) -> Dict:
        return {
            "requests":   self._request_count,
            "tokens_in":  self._total_in,
            "tokens_out": self._total_out,
            "model":      self._model,
        }

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def build_vision_message(b64: str, text: str = "") -> Dict:
        """Wrap a base64 image in an OpenAI vision content block."""
        content: List[Dict] = [
            {
                "type":      "image_url",
                "image_url": {
                    "url":    f"data:image/jpeg;base64,{b64}",
                    "detail": "high",
                },
            }
        ]
        if text:
            content.insert(0, {"type": "text", "text": text})
        return {"role": "user", "content": content}

    @staticmethod
    def extract_tool_calls(response: Dict) -> List[Dict]:
        """Pull tool_calls out of a completion response."""
        msg = response.get("choices", [{}])[0].get("message", {})
        return msg.get("tool_calls") or []

    @staticmethod
    def extract_text(response: Dict) -> str:
        """Pull text content out of a completion response."""
        msg = response.get("choices", [{}])[0].get("message", {})
        content = msg.get("content") or ""
        return content


# =============================================================================
# §15  CONTEXT MANAGER (rolling conversation window)
# =============================================================================

class ContextManager:
    """
    Maintains a sliding window of messages for the model.
    Ensures the context never explodes in token count by:
      1. Keeping only the last N conversation turns.
      2. Replacing old screenshot blobs with a text placeholder.
      3. Compressing long tool results.
    """

    def __init__(self, window: int = CTX_WINDOW_MSGS):
        self._window   = window
        self._messages: List[Dict] = []
        self._system   = SYSTEM_PROMPT

    def add_system(self, text: str):
        self._system = text

    def add_user(self, text: str):
        self._messages.append({"role": "user", "content": text})
        self._trim()

    def add_user_vision(self, b64: str, text: str = ""):
        msg = OpenRouterClient.build_vision_message(b64, text)
        self._messages.append(msg)
        self._trim()

    def add_assistant(self, content: str, tool_calls: Optional[List] = None):
        msg: Dict[str, Any] = {"role": "assistant", "content": content or ""}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self._messages.append(msg)

    def add_tool_result(self, tool_call_id: str, name: str, result: ActionResult):
        output = result.truncated_output()
        if result.error and not result.success:
            output = f"ERROR: {result.error}\n{output}"
        self._messages.append({
            "role":         "tool",
            "tool_call_id": tool_call_id,
            "name":         name,
            "content":      output,
        })

    def build(self) -> List[Dict]:
        system_msg = {"role": "system", "content": self._system}
        return [system_msg] + self._compress_old_screenshots()

    def _trim(self):
        if len(self._messages) > self._window * 2:
            # Keep first 2 (task setup) and last window messages
            self._messages = self._messages[:2] + self._messages[-(self._window * 2 - 2):]

    def _compress_old_screenshots(self) -> List[Dict]:
        """Strip image blobs from all but the most recent screenshot message."""
        msgs     = self._messages
        last_img = None
        for i in range(len(msgs) - 1, -1, -1):
            msg = msgs[i]
            if isinstance(msg.get("content"), list):
                for block in msg["content"]:
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
                # Replace vision content with text summary
                text_parts = [
                    b["text"] for b in msg["content"]
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                result.append({
                    "role":    msg["role"],
                    "content": " ".join(text_parts) + " [screenshot omitted]",
                })
            else:
                result.append(msg)
        return result

    def clear(self):
        self._messages.clear()

    @property
    def message_count(self) -> int:
        return len(self._messages)


# =============================================================================
# §16  REASONING LOOP  (the brain)
# =============================================================================

class ReasoningLoop:
    """
    Implements the core  perceive → reason → act → verify  cycle.

    Each iteration:
      1. Captures a screenshot → encodes as base64.
      2. Builds the current context window.
      3. Sends to the LLM with tool schemas.
      4. Parses response for tool_calls.
      5. Executes each tool_call through ToolRegistry.
      6. Records results in context.
      7. Checks for task_complete signal or step limit.
    """

    def __init__(
        self,
        client:   OpenRouterClient,
        registry: ToolRegistry,
        context:  ContextManager,
        screen:   ScreenCapture,
        cfg:      ConfigManager,
    ):
        self._client   = client
        self._registry = registry
        self._context  = context
        self._screen   = screen
        self._cfg      = cfg
        self._step     = 0
        self._done     = False
        self._result   = ""
        self._stall_checker: Dict[str, int] = defaultdict(int)

    # ── public ────────────────────────────────────────────────────────────────

    def run(self, task: str, session: TaskSession) -> TaskSession:
        """
        Execute a full task.  Returns the completed session.
        """
        log.info(f"Task: {task}")
        self._context.clear()
        self._context.add_user(f"TASK: {task}")
        self._step = 0
        self._done = False

        while self._step < MAX_STEPS and not self._done:
            self._step += 1
            try:
                step_obj = self._single_step(session)
                session.steps.append(step_obj)
                session.total_in  += step_obj.tokens_in
                session.total_out += step_obj.tokens_out
            except KeyboardInterrupt:
                log.warn("Interrupted by user.")
                break
            except Exception as e:
                log.error(f"Step {self._step} crashed: {traceback.format_exc(limit=5)}")
                session.steps.append(AgentStep(
                    index=self._step,
                    model_msg=f"[ERROR] {e}",
                    status=StepStatus.FAILED,
                ))
                if MAX_RETRIES and self._step < MAX_STEPS - 1:
                    time.sleep(1)
                    continue
                break

            time.sleep(self._cfg.get("loop_sleep_ms", LOOP_SLEEP_MS) / 1000)

        session.end_time  = time.time()
        session.success   = self._done
        session.final_msg = self._result
        self._display_summary(session)
        return session

    # ── single reasoning step ─────────────────────────────────────────────────

    def _single_step(self, session: TaskSession) -> AgentStep:
        step = AgentStep(index=self._step, model_msg="", status=StepStatus.RUNNING)
        log.step(self._step, f"Thinking… (context msgs: {self._context.message_count})")

        # 1. Capture screen and inject into context
        _, b64 = self._screen.capture()
        self._context.add_user_vision(b64, "Current screen state:")

        # 2. Build messages + call model
        messages = self._context.build()
        tools    = self._registry.schemas()

        response = self._client.chat(
            messages=messages,
            tools=tools,
            max_tokens=TOKEN_BUDGET,
            temperature=0.05,
        )

        usage = response.get("usage", {})
        step.tokens_in  = usage.get("prompt_tokens", 0)
        step.tokens_out = usage.get("completion_tokens", 0)

        # 3. Parse response
        text       = OpenRouterClient.extract_text(response)
        tool_calls = OpenRouterClient.extract_tool_calls(response)
        step.model_msg = text or "(tool calls only)"
        log.step(self._step, step.model_msg)

        # 4. Add assistant message to context
        raw_tool_calls = (
            response["choices"][0]["message"].get("tool_calls") or []
            if response.get("choices") else []
        )
        self._context.add_assistant(text, raw_tool_calls or None)

        # 5. Execute tool calls
        if not tool_calls and not text:
            log.warn("Model produced no output — nudging.")
            self._context.add_user(
                "You produced no output. Take a screenshot, observe the screen, and decide what to do next."
            )
            step.status = StepStatus.SKIPPED
            return step

        if not tool_calls:
            # Model responded with text only — treat as clarification / plan
            step.status = StepStatus.SUCCESS
            return step

        for tc in tool_calls:
            tc_id   = tc.get("id", str(uuid.uuid4()))
            fn_name = tc.get("function", {}).get("name", "")
            try:
                fn_args = json.loads(tc.get("function", {}).get("arguments", "{}"))
            except json.JSONDecodeError:
                fn_args = {}

            tool_call_obj = ToolCall(id=tc_id, name=fn_name, arguments=fn_args)
            tool_call_obj.ts_start = time.time()

            # Anti-stall check
            sig = f"{fn_name}:{json.dumps(fn_args, sort_keys=True)}"
            self._stall_checker[sig] += 1
            if self._stall_checker[sig] >= 3:
                log.warn(f"STALL detected: {fn_name} called with same args ×3")
                self._context.add_user(
                    f"You have called {fn_name} with the same arguments 3 times in a row. "
                    "The approach is not working. Try something completely different."
                )
                break

            result = self._registry.dispatch(fn_name, fn_args)
            tool_call_obj.result = result
            tool_call_obj.ts_end = time.time()
            step.tool_calls.append(tool_call_obj)
            log.tool(fn_name, fn_args, result)

            # Inject screenshot into result if screenshot tool was called
            if fn_name == "screenshot" and result.success:
                b64_new = result.metadata.get("b64", "")
                if b64_new:
                    self._context.add_tool_result(tc_id, fn_name, result)
                    # Also add the image for visual inspection
                    self._context.add_user_vision(b64_new, "")
                    continue

            self._context.add_tool_result(tc_id, fn_name, result)

            # Check task_complete signal
            if fn_name == "task_complete" and result.metadata.get("__task_done__"):
                self._done   = True
                self._result = fn_args.get("summary", "Task completed.")
                step.status  = StepStatus.SUCCESS
                return step

        step.status = StepStatus.SUCCESS
        return step

    # ── display ───────────────────────────────────────────────────────────────

    def _display_summary(self, session: TaskSession):
        if HAS_RICH:
            table = Table(box=rbox.ROUNDED, title="[bold]Session Summary[/bold]", show_header=False)
            table.add_column("Key",   style="cyan")
            table.add_column("Value", style="white")
            table.add_row("Session ID",  session.id)
            table.add_row("Task",        session.task[:80])
            table.add_row("Model",       session.model)
            table.add_row("Steps",       str(len(session.steps)))
            table.add_row("Elapsed",     f"{session.elapsed:.1f}s")
            table.add_row("Success",     "✓" if session.success else "✗")
            table.add_row("Tokens in",   f"{session.total_in:,}")
            table.add_row("Tokens out",  f"{session.total_out:,}")
            table.add_row("Result",      session.final_msg[:120])
            console.print(table)
        else:
            print(f"\n=== Session {session.id} ===")
            for k, v in session.to_dict().items():
                print(f"  {k}: {v}")


# =============================================================================
# §17  MAIN AGENT  (public API)
# =============================================================================

class VaelorAgent:
    """
    Top-level Computer Use Agent.

    Wires together every subsystem and exposes a clean interface:
      agent = VaelorAgent(api_key="...", model="openai/gpt-4o")
      session = agent.run("Open Firefox and search for 'Vaelor CUA'")
    """

    def __init__(
        self,
        api_key:  str,
        model:    str,
        cfg_overrides: Optional[Dict] = None,
    ):
        cfg_overrides = cfg_overrides or {}
        cfg_overrides["openrouter_key"]  = api_key
        cfg_overrides["default_model"]   = model

        self.cfg      = ConfigManager(cfg_overrides)
        self.model    = model

        # ── Hardware controllers ──────────────────────────────────────────────
        self.screen    = ScreenCapture(self.cfg)
        self.mouse     = MouseController(self.screen.screen_info, self.cfg)
        self.keyboard  = KeyboardController(self.cfg)
        self.clipboard = ClipboardManager()
        self.apps      = AppManager(self.cfg)
        self.terminal  = TerminalController(self.cfg)
        self.finder    = VisualFinder(self.screen, self.cfg)

        # ── LLM client ───────────────────────────────────────────────────────
        self.client = OpenRouterClient(api_key, model, self.cfg)

        # ── Tool system ───────────────────────────────────────────────────────
        builder       = ToolBuilder(
            self.screen, self.mouse, self.keyboard, self.clipboard,
            self.apps, self.terminal, self.finder, self.cfg,
        )
        self.registry = builder.build()
        self.context  = ContextManager()
        self.loop     = ReasoningLoop(
            self.client, self.registry, self.context, self.screen, self.cfg
        )
        self._sessions: List[TaskSession] = []
        log.success(f"VaelorAgent ready  model={model}  tools={len(self.registry.names())}")

    # ── public methods ────────────────────────────────────────────────────────

    def run(self, task: str) -> TaskSession:
        """Execute a task. Blocks until done or step limit reached."""
        session = TaskSession(task=task, model=self.model)
        session = self.loop.run(task, session)
        self._sessions.append(session)
        if self.cfg.get("save_sessions"):
            self._save_session(session)
        return session

    def screenshot(self) -> Tuple[bytes, str]:
        """Take a screenshot. Returns (bytes, base64)."""
        return self.screen.capture()

    def list_tools(self) -> List[str]:
        return self.registry.names()

    def set_model(self, model: str):
        """Switch models mid-session."""
        self.model  = model
        self.client = OpenRouterClient(self.cfg.get("openrouter_key"), model, self.cfg)
        self.loop._client = self.client
        log.success(f"Model switched to {model}")

    def get_stats(self) -> Dict:
        return {
            **self.client.stats,
            "sessions":    len(self._sessions),
            "screen":      asdict(self.screen.screen_info),
            "tools":       len(self.registry.names()),
        }

    # ── internal ──────────────────────────────────────────────────────────────

    def _save_session(self, session: TaskSession):
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        path = SESSION_DIR / f"{session.id}.json"
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)
        log.debug(f"Session saved → {path}")


# =============================================================================
# §18  INTERACTIVE REPL  (local CLI)
# =============================================================================

class VaelorREPL:
    """
    Interactive command-line interface for local testing.
    Supports multi-line task input, model switching, stats display,
    screenshot preview, and session history.
    """

    COMMANDS = {
        "/help":       "Show this help",
        "/models":     "List available OpenRouter models",
        "/model <id>": "Switch model",
        "/stats":      "Show token/session statistics",
        "/tools":      "List registered tools",
        "/ss":         "Take and save a screenshot",
        "/history":    "Show session history",
        "/clear":      "Clear conversation context",
        "/config":     "Show current config",
        "/quit":       "Exit Vaelor",
    }

    def __init__(self, agent: VaelorAgent):
        self._agent = agent

    def run(self):
        self._banner()
        while True:
            try:
                raw = self._input()
                if not raw:
                    continue
                if raw.startswith("/"):
                    should_exit = self._handle_command(raw)
                    if should_exit:
                        break
                else:
                    self._run_task(raw)
            except KeyboardInterrupt:
                print()
                if Confirm.ask("[yellow]Exit Vaelor?[/yellow]") if HAS_RICH else input("Exit? [y/N] ") == "y":
                    break

    def _input(self) -> str:
        if HAS_RICH:
            return Prompt.ask("[bold cyan]vaelor[/bold cyan]").strip()
        return input("vaelor> ").strip()

    def _run_task(self, task: str):
        if HAS_RICH:
            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(f"Running: {task[:60]}…")
                session = self._agent.run(task)
        else:
            print(f"Running: {task}")
            session = self._agent.run(task)

        status = "✓ DONE" if session.success else "✗ INCOMPLETE"
        if HAS_RICH:
            color = "green" if session.success else "red"
            console.print(
                Panel(
                    f"[bold]{status}[/bold]\n{session.final_msg}",
                    border_style=color,
                    title=f"Session {session.id}",
                )
            )
        else:
            print(f"\n{status}: {session.final_msg}")

    def _handle_command(self, raw: str) -> bool:
        parts = raw.split(maxsplit=1)
        cmd   = parts[0].lower()
        arg   = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/quit", "/exit", "/q"):
            log.success("Goodbye.")
            return True

        elif cmd == "/help":
            if HAS_RICH:
                t = Table(title="Commands", box=rbox.SIMPLE)
                t.add_column("Command", style="cyan")
                t.add_column("Description")
                for c, d in self.COMMANDS.items():
                    t.add_row(c, d)
                console.print(t)
            else:
                for c, d in self.COMMANDS.items():
                    print(f"  {c:20s} {d}")

        elif cmd == "/models":
            models = self._agent.client.list_models()
            if HAS_RICH:
                t = Table(title="Available Models", box=rbox.SIMPLE)
                t.add_column("ID",           style="cyan")
                t.add_column("Context",      style="green")
                t.add_column("Input $/M",    style="yellow")
                for m in sorted(models, key=lambda x: x.get("id", ""))[:60]:
                    pricing = m.get("pricing", {})
                    t.add_row(
                        m.get("id", ""),
                        str(m.get("context_length", "")),
                        str(pricing.get("prompt", "")),
                    )
                console.print(t)
            else:
                for m in models[:30]:
                    print(m.get("id"))

        elif cmd == "/model":
            if arg:
                self._agent.set_model(arg)
            else:
                print(f"Current model: {self._agent.model}")

        elif cmd == "/stats":
            stats = self._agent.get_stats()
            if HAS_RICH:
                t = Table(box=rbox.SIMPLE, show_header=False)
                t.add_column("K", style="cyan")
                t.add_column("V")
                for k, v in stats.items():
                    t.add_row(str(k), str(v))
                console.print(t)
            else:
                for k, v in stats.items():
                    print(f"  {k}: {v}")

        elif cmd == "/tools":
            names = self._agent.list_tools()
            if HAS_RICH:
                tree = Tree("[bold cyan]Registered Tools[/bold cyan]")
                for n in names:
                    tree.add(n)
                console.print(tree)
            else:
                print("\n".join(names))

        elif cmd == "/ss":
            raw_bytes, _ = self._agent.screenshot()
            ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = Path(f"vaelor_screenshot_{ts}.jpg")
            path.write_bytes(raw_bytes)
            log.success(f"Screenshot saved → {path}")

        elif cmd == "/history":
            sessions = self._agent._sessions
            if not sessions:
                print("No sessions yet.")
            else:
                if HAS_RICH:
                    t = Table(box=rbox.SIMPLE)
                    t.add_column("ID")
                    t.add_column("Task")
                    t.add_column("Steps")
                    t.add_column("OK")
                    for s in sessions[-20:]:
                        t.add_row(s.id, s.task[:50], str(len(s.steps)), "✓" if s.success else "✗")
                    console.print(t)
                else:
                    for s in sessions[-10:]:
                        print(f"  [{s.id}] {s.task[:40]} — {'OK' if s.success else 'FAIL'}")

        elif cmd == "/clear":
            self._agent.context.clear()
            log.success("Context cleared.")

        elif cmd == "/config":
            if HAS_RICH:
                console.print_json(json.dumps(self._agent.cfg._data, indent=2))
            else:
                print(json.dumps(self._agent.cfg._data, indent=2))

        else:
            log.warn(f"Unknown command: {cmd}.  Type /help for help.")

        return False

    def _banner(self):
        art = r"""
  ██╗   ██╗ █████╗ ███████╗██╗      ██████╗ ██████╗
  ██║   ██║██╔══██╗██╔════╝██║     ██╔═══██╗██╔══██╗
  ██║   ██║███████║█████╗  ██║     ██║   ██║██████╔╝
  ╚██╗ ██╔╝██╔══██║██╔══╝  ██║     ██║   ██║██╔══██╗
   ╚████╔╝ ██║  ██║███████╗███████╗╚██████╔╝██║  ██║
    ╚═══╝  ╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
        Computer Use Agent  v{v}  — local edition
        """
        if HAS_RICH:
            console.print(Panel(art.format(v=VERSION), border_style="cyan"))
            console.print(
                f"[dim]Model:[/dim] [bold]{self._agent.model}[/bold]   "
                f"[dim]Tools:[/dim] [bold]{len(self._agent.list_tools())}[/bold]   "
                f"[dim]Type [bold]/help[/bold] for commands, or just describe your task.[/dim]"
            )
        else:
            print(art.format(v=VERSION))
            print(f"Model: {self._agent.model}  |  Type /help or enter a task.")


# =============================================================================
# §19  DEPENDENCY CHECKER
# =============================================================================

def check_dependencies() -> Dict[str, bool]:
    """Check all optional dependencies and report status."""
    checks = {
        "requests":              HAS_REQUESTS,
        "pyautogui":             HAS_PYAUTOGUI,
        "pillow":                HAS_PIL,
        "rich":                  HAS_RICH,
        "psutil":                HAS_PSUTIL,
        "pyperclip":             HAS_CLIPBOARD,
        "opencv-python":         HAS_CV2,
    }
    if HAS_RICH:
        t = Table(title="Dependency Check", box=rbox.SIMPLE)
        t.add_column("Package",   style="cyan")
        t.add_column("Status")
        for pkg, ok in checks.items():
            t.add_row(pkg, "[green]✓ installed[/green]" if ok else "[yellow]✗ missing (optional)[/yellow]")
        console.print(t)
        missing_critical = [p for p, ok in checks.items() if not ok and p in ("requests", "pyautogui", "pillow")]
        if missing_critical:
            console.print(f"[bold red]CRITICAL MISSING:[/bold red] pip install {' '.join(missing_critical)}")
    else:
        for pkg, ok in checks.items():
            print(f"  {'✓' if ok else '✗'} {pkg}")
    return checks


# =============================================================================
# §20  CLI ENTRYPOINT
# =============================================================================

def parse_args() -> "argparse.Namespace":
    import argparse
    parser = argparse.ArgumentParser(
        prog="vaelor",
        description="Vaelor — Computer Use Agent (local edition)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python vaelor.py --key sk-or-... --model openai/gpt-4o
          python vaelor.py --key sk-or-... --task "Open Terminal and run 'ls -la'"
          python vaelor.py --key sk-or-... --model anthropic/claude-3.5-sonnet --interactive
          python vaelor.py --check-deps
        """),
    )
    parser.add_argument("--key",         "-k", default="",            help="OpenRouter API key")
    parser.add_argument("--model",       "-m", default="",            help="Model ID (e.g. openai/gpt-4o)")
    parser.add_argument("--task",        "-t", default="",            help="Task to execute (non-interactive)")
    parser.add_argument("--interactive", "-i", action="store_true",   help="Launch REPL (default if no --task)")
    parser.add_argument("--check-deps",        action="store_true",   help="Check dependencies and exit")
    parser.add_argument("--max-steps",         type=int, default=MAX_STEPS)
    parser.add_argument("--safe-mode",         action="store_true",   default=True)
    parser.add_argument("--verbose",     "-v", action="store_true")
    parser.add_argument("--list-models",       action="store_true",   help="List available models and exit")
    parser.add_argument("--no-save",           action="store_true",   help="Do not save sessions to disk")
    return parser.parse_args()


def main():
    args = parse_args()

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
        log.error("API key required.  Set OPENROUTER_API_KEY or pass --key.")
        sys.exit(1)

    # ── Resolve model ─────────────────────────────────────────────────────────
    model = args.model or ConfigManager().get("default_model", "openai/gpt-4o")

    # ── Build overrides dict ──────────────────────────────────────────────────
    overrides = {
        "openrouter_key":  api_key,
        "default_model":   model,
        "max_steps":       args.max_steps,
        "safe_mode":       args.safe_mode,
        "verbose":         args.verbose,
        "save_sessions":   not args.no_save,
    }

    # ── Instantiate agent ─────────────────────────────────────────────────────
    agent = VaelorAgent(api_key=api_key, model=model, cfg_overrides=overrides)

    if args.list_models:
        models = agent.client.list_models()
        for m in sorted(models, key=lambda x: x.get("id", "")):
            print(m.get("id"))
        sys.exit(0)

    if args.task:
        # Non-interactive single-task mode
        session = agent.run(args.task)
        code = 0 if session.success else 1
        sys.exit(code)
    else:
        # REPL mode (default)
        repl = VaelorREPL(agent)
        repl.run()


# =============================================================================
# §21  SIGNAL HANDLERS & SAFETY SHUTDOWN
# =============================================================================

def _graceful_exit(signum, frame):
    if HAS_RICH:
        console.print("\n[yellow]Signal received — shutting down Vaelor gracefully.[/yellow]")
    else:
        print("\nShutting down…")
    # Move mouse to a safe corner to trigger pyautogui failsafe reset
    if HAS_PYAUTOGUI:
        with contextlib.suppress(Exception):
            pyautogui.moveTo(0, 0)
    sys.exit(0)

signal.signal(signal.SIGINT,  _graceful_exit)
signal.signal(signal.SIGTERM, _graceful_exit)


# =============================================================================
# §22  SELF-TEST SUITE  (run with: python vaelor.py --self-test)
# =============================================================================

class SelfTestSuite:
    """
    Runs lightweight unit tests against every subsystem
    WITHOUT needing a real OpenRouter key or a real screen.
    """

    def __init__(self):
        self._passed = 0
        self._failed = 0

    def run(self):
        console.rule("[bold]Vaelor Self-Test[/bold]") if HAS_RICH else print("=== Self-Test ===")
        self._test_config()
        self._test_action_result()
        self._test_context_manager()
        self._test_tool_registry()
        self._test_keyboard_aliases()
        self._test_terminal_controller()
        self._print_summary()

    def _assert(self, condition: bool, msg: str):
        if condition:
            self._passed += 1
            log.success(f"PASS  {msg}")
        else:
            self._failed += 1
            log.error(f"FAIL  {msg}")

    def _test_config(self):
        cfg = ConfigManager({"openrouter_key": "test", "verbose": True})
        self._assert(cfg["openrouter_key"] == "test",  "ConfigManager: key injection")
        self._assert(cfg["verbose"] is True,           "ConfigManager: bool override")
        self._assert(cfg.get("max_steps") == MAX_STEPS, "ConfigManager: default fallback")

    def _test_action_result(self):
        r = ActionResult(True, output="A" * 5000)
        t = r.truncated_output(limit=100)
        self._assert(len(t) <= 200,        "ActionResult: truncation length")
        self._assert("truncated" in t,     "ActionResult: truncation label")

        r2 = ActionResult(False, error="oops")
        self._assert(not r2.success,       "ActionResult: failure flag")

    def _test_context_manager(self):
        ctx = ContextManager(window=5)
        for i in range(12):
            ctx.add_user(f"msg {i}")
        msgs = ctx.build()
        self._assert(len(msgs) <= 12,      "ContextManager: window trim")
        self._assert(msgs[0]["role"] == "system", "ContextManager: system first")

    def _test_tool_registry(self):
        reg  = ToolRegistry()
        tool = ToolDefinition(
            name="dummy",
            description="A test tool",
            parameters={"x": {"type": "integer", "description": "x"}},
            required=["x"],
            handler=lambda x: ActionResult(True, output=str(x * 2)),
        )
        reg.register(tool)
        self._assert("dummy" in reg.names(),      "ToolRegistry: registration")
        result = reg.dispatch("dummy", {"x": 21})
        self._assert(result.success,              "ToolRegistry: dispatch success")
        self._assert(result.output == "42",       "ToolRegistry: handler output")
        bad = reg.dispatch("nonexistent", {})
        self._assert(not bad.success,             "ToolRegistry: unknown tool → fail")

    def _test_keyboard_aliases(self):
        kb = KeyboardController(ConfigManager())
        self._assert(kb.KEY_ALIASES["esc"] == "escape",   "KB: esc alias")
        self._assert(kb.KEY_ALIASES["cmd"] == "command",  "KB: cmd alias")
        self._assert(kb.KEY_ALIASES["enter"] == "enter",  "KB: enter passthrough")

    def _test_terminal_controller(self):
        cfg = ConfigManager()
        te  = TerminalController(cfg)
        r   = te.run("echo hello_vaelor", timeout=5)
        self._assert(r.success,                         "Terminal: echo success")
        self._assert("hello_vaelor" in r.output,        "Terminal: echo output")
        r2  = te.run("this_cmd_does_not_exist_xyz")
        self._assert(not r2.success,                    "Terminal: bad cmd → fail")
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("unit test content")
            tmp = f.name
        r3 = te.read_file(tmp)
        self._assert(r3.success,                        "Terminal: read_file success")
        self._assert("unit test content" in r3.output,  "Terminal: read_file content")
        os.unlink(tmp)

    def _print_summary(self):
        total = self._passed + self._failed
        if HAS_RICH:
            color = "green" if self._failed == 0 else "red"
            console.print(
                f"\n[{color}]Results: {self._passed}/{total} passed "
                f"({'ALL OK' if self._failed == 0 else f'{self._failed} FAILED'})[/{color}]"
            )
        else:
            print(f"\nResults: {self._passed}/{total} passed")


# =============================================================================
# §23  EXTRA: WORKFLOW TEMPLATES
#      Pre-built multi-step task templates the user can call by name.
# =============================================================================

WORKFLOW_TEMPLATES: Dict[str, str] = {
    "open_browser_and_search": (
        "Open the default web browser, navigate to https://www.google.com, "
        "click the search box, type '{query}', and press Enter. "
        "Wait for results to load, then take a screenshot of the results page."
    ),
    "take_note": (
        "Open a text editor (Notepad on Windows, TextEdit on macOS, or gedit on Linux). "
        "Type the following note: '{content}'. "
        "Save the file to the Desktop with filename '{filename}'."
    ),
    "run_python_script": (
        "Open a terminal. "
        "Navigate to {directory}. "
        "Run the Python script: python {script}. "
        "Capture and report all output."
    ),
    "capture_and_summarize": (
        "Take a full-screen screenshot. "
        "Describe in detail what is currently visible on the screen, "
        "including all open applications, visible text, and UI state."
    ),
    "fill_web_form": (
        "Navigate to {url}. "
        "Fill in the form with the following data: {form_data}. "
        "Click Submit. "
        "Confirm success by checking for a confirmation message."
    ),
}


def expand_template(name: str, **kwargs) -> str:
    tmpl = WORKFLOW_TEMPLATES.get(name)
    if not tmpl:
        raise ValueError(f"Unknown template: {name}. Available: {list(WORKFLOW_TEMPLATES)}")
    return tmpl.format(**kwargs)


# =============================================================================
# §24  EXTRA: PERSISTENT MEMORY / KNOWLEDGE BASE
# =============================================================================

class AgentMemory:
    """
    Simple key-value persistent memory for the agent.
    Stores facts / observations across sessions.
    Backed by a JSON file in ~/.vaelor/memory.json.
    """

    _PATH = Path.home() / ".vaelor" / "memory.json"

    def __init__(self):
        self._mem: Dict[str, Any] = {}
        self._load()

    def store(self, key: str, value: Any):
        self._mem[key] = {"value": value, "ts": time.time()}
        self._save()

    def recall(self, key: str, default: Any = None) -> Any:
        entry = self._mem.get(key)
        return entry["value"] if entry else default

    def forget(self, key: str):
        self._mem.pop(key, None)
        self._save()

    def all_keys(self) -> List[str]:
        return list(self._mem.keys())

    def to_context_string(self, max_items: int = 10) -> str:
        if not self._mem:
            return ""
        items = sorted(self._mem.items(), key=lambda x: x[1]["ts"], reverse=True)[:max_items]
        lines = [f"[MEMORY] {k}: {v['value']}" for k, v in items]
        return "\n".join(lines)

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
# §25  EXTRA: BROWSER-SPECIFIC HELPERS
# =============================================================================

class BrowserHelper:
    """
    High-level browser automation helpers built on top of the core tools.
    These generate typed task strings for the agent to execute.
    """

    def __init__(self, agent: VaelorAgent):
        self._agent = agent

    def navigate(self, url: str) -> TaskSession:
        return self._agent.run(
            f"In the currently open browser, click the address bar, "
            f"clear it, type '{url}', and press Enter. "
            f"Wait for the page to fully load."
        )

    def search_google(self, query: str) -> TaskSession:
        return self._agent.run(
            f"Open a web browser, go to https://www.google.com, "
            f"click the search field, type '{query}', press Enter, "
            f"and wait for results."
        )

    def click_link_text(self, link_text: str) -> TaskSession:
        return self._agent.run(
            f"On the current web page, find and click the link or button "
            f"with the text '{link_text}'."
        )

    def fill_and_submit(self, url: str, fields: Dict[str, str]) -> TaskSession:
        fields_str = "; ".join(f"'{k}' = '{v}'" for k, v in fields.items())
        return self._agent.run(
            f"Navigate to {url}. "
            f"Fill in the following form fields: {fields_str}. "
            f"Then click the Submit or primary action button."
        )

    def screenshot_page(self) -> TaskSession:
        return self._agent.run(
            "Take a full-screen screenshot of the current browser page "
            "and describe all visible content."
        )


# =============================================================================
# §26  EXTRA: IDE / CODE HELPER
# =============================================================================

class IDEHelper:
    """
    Task builders for common IDE operations.
    Works with VS Code, PyCharm, Cursor, or any editor the user has open.
    """

    def __init__(self, agent: VaelorAgent):
        self._agent = agent

    def open_file(self, path: str) -> TaskSession:
        return self._agent.run(
            f"In the currently open IDE or text editor, open the file at: {path}. "
            f"Use the File > Open menu or Ctrl+O / Cmd+O shortcut."
        )

    def run_in_terminal(self, command: str) -> TaskSession:
        return self._agent.run(
            f"Open the integrated terminal in the IDE (usually Ctrl+` or View > Terminal). "
            f"Type and execute: {command}. "
            f"Wait for it to complete and report the output."
        )

    def find_and_replace(self, find: str, replace: str) -> TaskSession:
        return self._agent.run(
            f"In the current editor, open Find & Replace (Ctrl+H or Cmd+H). "
            f"Set find to: '{find}', replace to: '{replace}', "
            f"then click 'Replace All'."
        )

    def save_all(self) -> TaskSession:
        return self._agent.run(
            "Save all open files in the current editor "
            "(Ctrl+K S in VS Code, or Ctrl+Shift+S / Cmd+Option+S elsewhere)."
        )


# =============================================================================
# MAIN ENTRY
# =============================================================================

if __name__ == "__main__":
    import argparse as _argparse

    # Handle --self-test separately before full arg parse
    if "--self-test" in sys.argv:
        SelfTestSuite().run()
        sys.exit(0)

    main()
