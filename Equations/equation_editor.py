# Equation Editor for Talon
import gzip
import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import time
import urllib.parse
import urllib.request
import urllib.error
import zlib
import egui
from talon import Context, Module, actions, speech_system, ui
from talon.egui import Window

mod = Module()
ctx = Context()

mod.mode("math_recording", desc="Continuous recording mode for math equations")
mod.mode("equation_editing", desc="Waits for a longer spoken equation edit")
mod.list("math_vocab", desc="Explicit math terms and single letters for high-accuracy recognition")

ctx.lists["user.math_vocab"] = {
    "a": "a", "ay": "a", "b": "b", "bee": "b", "c": "c", "see": "c",
    "d": "d", "dee": "d", "e": "e", "ee": "e", "f": "f", "ef": "f",
    "g": "g", "gee": "g", "h": "h", "i": "i", "eye": "i", "j": "j",
    "k": "k", "kay": "k", "l": "l", "el": "l", "m": "m", "em": "m",
    "n": "n", "en": "n", "o": "o", "oh": "o", "p": "p", "pee": "p",
    "q": "q", "cue": "q", "r": "r", "are": "r", "s": "s", "es": "s",
    "t": "t", "tee": "t", "u": "u", "you": "u", "v": "v", "vee": "v",
    "w": "w", "x": "x", "ex": "x", "y": "y", "why": "y", "z": "z", "zee": "z",
    "air": "a", "bat": "b", "cap": "c", "drum": "d", "each": "e",
    "fine": "f", "gust": "g", "harp": "h", "sit": "i", "jury": "j",
    "crunch": "k", "look": "l", "made": "m", "near": "n", "odd": "o",
    "pit": "p", "quench": "q", "red": "r", "sun": "s", "trap": "t",
    "urge": "u", "vest": "v", "whale": "w", "plex": "x", "yank": "y", "zip": "z",
    "alpha": "alpha", "beta": "beta", "gamma": "gamma", "delta": "delta",
    "epsilon": "epsilon", "theta": "theta", "lambda": "lambda", "mu": "mu",
    "pi": "pi", "pie": "pi", "rho": "rho", "sigma": "sigma", "tau": "tau",
    "phi": "phi", "omega": "omega", "infinity": "infinity",
    "squared": "squared", "cubed": "cubed", "to the power of": "to the power of",
    "to the": "to the", "sub": "sub", "subscript": "subscript",
    "plus": "plus", "minus": "minus", "times": "times", "divided by": "divided by",
    "over": "over", "all over": "all over", "equals": "equals", "equal to": "equals",
    "not equal to": "not equal to", "less than": "less than", "greater than": "greater than",
    "plus or minus": "plus or minus", "square root of": "square root of", "root": "root",
    "integral": "integral", "integral from": "integral from", "sum from": "sum from",
    "limit as": "limit as", "approaches": "approaches", "derivative of": "derivative of",
    "partial": "partial", "sine": "sin", "cosine": "cos", "tangent": "tan",
    "natural log": "ln", "log": "log", "d x": "dx", "d y": "dy", "d t": "dt",
    # Physics and engineering phrasing
    "change in": "change in", "delta": "delta", "capital": "capital", "uppercase": "uppercase",
    "lowercase": "lowercase", "constant": "constant", "is constant": "is constant",
    "with respect to": "with respect to", "rate of change": "rate of change",
    "per second": "per second", "per meter": "per meter", "per kilogram": "per kilogram",
    "vector": "vector", "vector arrow": "vector arrow", "hat": "hat", "unit vector": "unit vector",
    "dot product": "dot product", "cross product": "cross product", "magnitude": "magnitude",
    "proportional to": "proportional to", "approximately": "approximately",
    "tends to": "tends to", "goes to": "goes to", "maps to": "maps to",
    "arrow": "arrow", "right arrow": "right arrow", "left arrow": "left arrow",
    "implies": "implies", "if and only if": "if and only if", "therefore": "therefore",
    "infinity": "infinity", "negative infinity": "negative infinity",
    "degrees": "degrees", "radians": "radians", "newtons": "newtons", "joules": "joules",
    "watts": "watts", "volts": "volts", "amps": "amps", "ohms": "ohms",
    "h bar": "hbar", "planck": "Planck", "boltzmann": "Boltzmann",
    "electric field": "electric field", "magnetic field": "magnetic field",
    "momentum": "momentum", "angular momentum": "angular momentum",
    "kinetic energy": "kinetic energy", "potential energy": "potential energy",
    "heat capacity": "heat capacity", "specific heat": "specific heat",
    "entropy": "entropy", "temperature": "temperature", "volume": "volume",
    "pressure": "pressure", "power": "power", "work": "work", "moles": "moles",
    "mole": "mole", "kelvin": "kelvin", "celsius": "Celsius",
    "degrees Celsius": "degrees Celsius", "Avogadro": "Avogadro",
    "Avogadro's number": "Avogadro's number", "reversible": "reversible",
    "irreversible": "irreversible", "quasi static": "quasi-static",
    "equilibrium": "equilibrium", "multiplicity": "multiplicity",
    "P max": r"P_{\max}", "T one": "T_1", "T two": "T_2",
    # Helpful editing keywords
    "replace": "replace", "with": "with", "change": "change", "remove": "remove",
    "delete": "delete", "numerator": "numerator", "denominator": "denominator",
    "exponent": "exponent", "upper bound": "upper bound", "lower bound": "lower bound",
    "left side": "left side", "right side": "right side", "term": "term",
}

FXEDITOR_KEY_FILE = Path(__file__).parent / "fxeditor_key.txt"
FXTEX_RENDER_URL = "https://fxtex.codecogs.com/png.json?"
EQUATION_STATE_FILE = Path(__file__).parent / "equation_editor_state.json"

# Recording buffer state
_math_buffer = []
_recording_active = False
_pending_recording_action_phrase = None

# Equation history state for in-place editing & undo
# Each entry is a dict: {"latex": str, "rendered": str, "delete_count": int}
_equation_history = []
_document_items = []
_document_items_by_window = {}
_equation_history_by_window = {}
_scribe_context_by_window = {}
_current_document_key = None
_saved_equations = {}
_saved_equation_counter = 0
_saved_equations_visible = False
_equation_gallery_window = None
_equation_gallery_max_height = 700
_equation_gallery_image_width = 240
_scribe_context = []
_pending_equation_code = None
_pending_document_key = None
_pending_equation_edit_confirmation = False

_EQUATION_CODE_WORDS = (
    "maple", "river", "copper", "tiger", "comet", "velvet", "rocket", "willow",
    "pepper", "planet", "jacket", "pocket", "lemon", "castle", "silver", "window",
    "basket", "candle", "dolphin", "forest", "guitar", "magnet", "marble", "noodle",
    "orbit", "panda", "quartz", "ribbon", "saddle", "tulip", "wagon", "zebra",
    "anchor", "button", "dragon", "engine", "feather", "garden", "hammer", "island",
    "jungle", "kitten", "lantern", "mountain", "nickel", "ocean", "piano", "rainbow",
    "sunset", "ticket", "umbrella", "violet", "zipper",
)
MAX_EQUATION_CODES = 512

# HUD state
_hud_status = ""
_hud_heard = ""
_hud_result = ""

def _current_document_state():
    """Returns the current document's mutable lists for persistence."""
    if _current_document_key is None:
        return
    _document_items_by_window[_current_document_key] = _document_items
    _equation_history_by_window[_current_document_key] = _equation_history
    _scribe_context_by_window[_current_document_key] = _scribe_context

def _persist_equation_state():
    """Writes equation sources and per-document references to a local JSON file."""
    _current_document_state()
    payload = {
        "version": 1,
        "next_code_index": _saved_equation_counter,
        "equations": {
            code: {
                "latex": equation["latex"],
                "preview_png": base64.b64encode(equation["preview_png"]).decode("ascii"),
            }
            for code, equation in _saved_equations.items()
        },
        "documents": {
            key: {
                "items": items,
                "history": _equation_history_by_window.get(key, []),
                "scribe_context": _scribe_context_by_window.get(key, []),
            }
            for key, items in _document_items_by_window.items()
        },
    }
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=EQUATION_STATE_FILE.parent,
            suffix=".tmp", delete=False,
        ) as state_file:
            json.dump(payload, state_file, ensure_ascii=False, separators=(",", ":"))
            temp_path = state_file.name
        os.replace(temp_path, EQUATION_STATE_FILE)
    except (OSError, TypeError, ValueError) as e:
        print(f"[Equation Editor State Save Error] {e}")
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

def _load_equation_state():
    """Restores saved equation images and document references after Talon starts."""
    global _saved_equations, _saved_equation_counter
    global _document_items_by_window, _equation_history_by_window
    global _scribe_context_by_window
    if not EQUATION_STATE_FILE.exists():
        return
    try:
        payload = json.loads(EQUATION_STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise ValueError("unsupported equation state version")
        raw_equations = payload.get("equations", {})
        raw_documents = payload.get("documents", {})
        if not isinstance(raw_equations, dict) or not isinstance(raw_documents, dict):
            raise ValueError("equation state collections must be objects")
        saved_equations = {}
        for code, equation in raw_equations.items():
            if not isinstance(code, str) or not isinstance(equation, dict):
                continue
            latex_eq = equation.get("latex")
            preview_png = base64.b64decode(equation.get("preview_png", ""), validate=True)
            if not isinstance(latex_eq, str) or not latex_eq.strip():
                continue
            if not preview_png.startswith(b"\x89PNG\r\n\x1a\n"):
                continue
            saved_equations[code] = {"latex": latex_eq, "preview_png": preview_png}
        loaded_items = {}
        loaded_history = {}
        loaded_context = {}
        for key, document in raw_documents.items():
            if not isinstance(key, str) or not isinstance(document, dict):
                continue
            items = document.get("items", [])
            history = document.get("history", [])
            context = document.get("scribe_context", [])
            loaded_items[key] = [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
            loaded_history[key] = [item for item in history if isinstance(item, dict)] if isinstance(history, list) else []
            loaded_context[key] = [item for item in context if isinstance(item, str)] if isinstance(context, list) else []
        next_code_index = payload.get("next_code_index", 0)
        if not isinstance(next_code_index, int) or next_code_index < 0:
            next_code_index = 0
        _saved_equations = saved_equations
        _document_items_by_window = loaded_items
        _equation_history_by_window = loaded_history
        _scribe_context_by_window = loaded_context
        _saved_equation_counter = max(next_code_index, len(saved_equations))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"[Equation Editor State Load Error] {e}")

def _refresh_active_document_state() -> str:
    """Reloads the saved index from disk and binds it to the active window."""
    global _current_document_key, _document_items, _equation_history, _scribe_context
    _load_equation_state()
    _current_document_key = None
    _document_items = []
    _equation_history = []
    _scribe_context = []
    return _sync_document_items()

_load_equation_state()

def _wrap_hud_text(text: str, width: int = 66, max_lines: int = 7) -> str:
    """Wraps long dictation in the HUD and keeps the newest lines visible."""
    lines = []
    for paragraph in text.splitlines() or [text]:
        lines.extend(textwrap.wrap(
            paragraph,
            width=width,
            break_long_words=True,
            break_on_hyphens=False,
        ) or [""])
    if len(lines) > max_lines:
        keep_top = min(3, max(0, max_lines - 2))
        keep_bottom = max(0, max_lines - keep_top - 1)
        original_lines = lines
        lines = original_lines[:keep_top] + ["… earlier text hidden …"]
        if keep_bottom:
            lines.extend(original_lines[-keep_bottom:])
    return "\n".join(lines)

def _spoken_code(code: str) -> str:
    """Returns the distinct word code exactly as it should be spoken."""
    return code

def _equation_code_for_index(index: int) -> str:
    """Creates a speech-friendly unique code from recognizable words."""
    if not 0 <= index < MAX_EQUATION_CODES:
        raise IndexError(f"Equation code capacity ({MAX_EQUATION_CODES}) has been reached")
    word_count = len(_EQUATION_CODE_WORDS)
    if index < word_count:
        return _EQUATION_CODE_WORDS[index]
    group, word_index = divmod(index, word_count)
    return f"{_EQUATION_CODE_WORDS[group - 1]} {_EQUATION_CODE_WORDS[word_index]}"

async def _render_equation_gallery(ui):
    """Draw the labeled equation editor in Talon's modern UI window."""
    egui.install_image_loaders(ui.ctx())
    ui.label("Equation Editor")
    if _hud_status:
        ui.label(_wrap_hud_text(f"Status: {_hud_status}", width=34, max_lines=3))
    if _hud_heard:
        ui.label(_wrap_hud_text(f"Heard: {_hud_heard}", width=34, max_lines=4))
    if _hud_result:
        ui.label(_wrap_hud_text(f"Output: {_hud_result}", width=34, max_lines=4))
    if _hud_status or _hud_heard or _hud_result:
        ui.separator()
    ui.label("Say 'edit' plus a code to select it, check the document, then say 'confirm equation edit' to change it.")
    ui.label("Say 'paste' plus a code to insert a copy, or 'close equation editor' when done.")
    ui.label("Say 'new equation' to start dictating, or 'paste all' to insert every saved equation.")
    ui.separator()
    if not _saved_equations_visible:
        ui.label("Saved equations are hidden. Say 'open equation editor' to view them.")
        return
    document_codes = {
        item.get("label") for item in _document_items
        if item.get("kind") == "equation" and item.get("label")
    }
    document_equations = [
        (code, equation) for code, equation in _saved_equations.items()
        if code in document_codes
    ]
    if not document_equations:
        ui.label("No remembered equations for this document yet.")
        return

    async with egui.ScrollArea.vertical().max_height(_equation_gallery_max_height).show() as library_ui:
        for code, equation in document_equations:
            library_ui.label(
                f"{code} — edit {_spoken_code(code)} | paste {_spoken_code(code)}"
            )
            image = (
                egui.Image.from_bytes(
                    f"bytes://custom-math/{code}/{hashlib.sha256(equation['preview_png']).hexdigest()}",
                    egui.Bytes.from_bytes(equation["preview_png"]),
                )
                .max_width(_equation_gallery_image_width)
                .max_height(70)
                .alt_text(f"Saved equation {code}")
            )
            library_ui.add(image)
            library_ui.separator()

def _show_equation_gallery():
    """Shows and refreshes the persistent saved-equation preview gallery."""
    global _equation_gallery_window, _equation_gallery_max_height, _equation_gallery_image_width
    if _equation_gallery_window is None:
        _equation_gallery_window = Window()
    _equation_gallery_window.set_content(_render_equation_gallery)
    _equation_gallery_window.title = "Equation Editor"
    _equation_gallery_window.draggable = False
    _equation_gallery_window.decorated = True
    _equation_gallery_window.toplevel = True
    _equation_gallery_window.focusable = False
    _equation_gallery_window.autosize = False
    try:
        _equation_gallery_window.resizable = False
    except AttributeError:
        pass
    try:
        screen = ui.main_screen()
        panel_width = max(280, round(screen.width * 0.2))
        _equation_gallery_window.rect = ui.Rect(
            round(screen.x), round(screen.y), panel_width, round(screen.height)
        )
        _equation_gallery_max_height = max(300, round(screen.height) - 90)
        _equation_gallery_image_width = max(120, min(260, panel_width - 32))
    except (AttributeError, RuntimeError, TypeError, ValueError):
        # Keep Talon's default window geometry when screen metrics are not yet
        # available during startup or a display change.
        pass
    _equation_gallery_window.show()
    _equation_gallery_window.refresh()

def _save_equation(latex_eq: str, preview_png: bytes) -> str:
    """Stores an equation for reuse and returns its short spoken/display code."""
    global _saved_equation_counter
    code = _equation_code_for_index(_saved_equation_counter)
    _saved_equation_counter += 1
    _saved_equations[code] = {"latex": latex_eq, "preview_png": preview_png}
    _persist_equation_state()
    return code

def _update_saved_equation(code: str, latex_eq: str, preview_png: bytes):
    """Updates the stored equation while keeping its spoken label stable."""
    _saved_equations[code] = {"latex": latex_eq, "preview_png": preview_png}
    _persist_equation_state()
    if _equation_gallery_window:
        _equation_gallery_window.refresh()

def _equation_key_distance(index: int) -> int:
    """Counts left-arrow steps from document end to just before a labeled image."""
    if index < 0 or index >= len(_document_items):
        raise IndexError("Equation label is not present in the scribed document")
    return sum(item["delete_count"] for item in _document_items[index:])

def _sync_document_items() -> str:
    """Keeps equation positions separate for each active document window."""
    global _document_items, _equation_history, _scribe_context
    global _document_items_by_window, _equation_history_by_window
    global _scribe_context_by_window, _current_document_key
    try:
        window = ui.active_window()
        app_name = window.app.name
        title = window.title
        document_key = f"{app_name}|{title}"
    except Exception:
        document_key = "unknown document"
    if document_key != _current_document_key:
        _current_document_state()
        _document_items = _document_items_by_window.setdefault(document_key, [])
        _equation_history = _equation_history_by_window.setdefault(document_key, [])
        _scribe_context = _scribe_context_by_window.setdefault(document_key, [])
        _current_document_key = document_key
        _persist_equation_state()
    return document_key

def show_hud(status: str, heard: str = "", result: str = ""):
    """Updates the status section and keeps the Equation Editor open."""
    global _hud_status, _hud_heard, _hud_result
    _hud_status = status
    _hud_heard = heard
    _hud_result = result
    try:
        _show_equation_gallery()
    except Exception as e:
        # A UI failure must not break voice recording or the command that
        # updated the status. The error remains visible in Talon's log.
        print(f"[Equation Editor Window Error] {e}")
def _hide_equation_windows():
    """Hides the persistent Equation Editor when the user asks."""
    global _saved_equations_visible
    if _equation_gallery_window:
        _equation_gallery_window.hide()
    _saved_equations_visible = False

def _recording_phrase_listener(event):
    """Capture each recognized phrase before Talon's command grammar handles it.

    This preserves speech that does not match the math grammar, which is
    especially useful for longer dictation segments.
    """
    global _math_buffer, _pending_recording_action_phrase
    if not _recording_active or "parsed" not in event:
        return

    words = list(event["parsed"]._unmapped)
    spoken_text = " ".join(words).strip()
    _pending_recording_action_phrase = None
    if not spoken_text:
        return

    control_phrases = {
        "done equation", "finish equation", "end equation", "cancel equation",
        "scratch chunk", "undo chunk", "new equation", "new equations",
        "start equation", "start equations", "begin equation", "begin equations",
        "next equation", "next equations", "paste all", "paste all equations",
        "open equation editor", "show equation editor", "open saved equations",
        "equation editor", "show equations", "open equations",
        "show saved equations", "close equation editor", "confirm equation edit",
    }
    if spoken_text.lower() in control_phrases:
        return

    _math_buffer.append(spoken_text)
    _pending_recording_action_phrase = spoken_text.casefold()
    show_hud(
        "RECORDING (speak naturally; say 'done equation' to write, or 'new equation' to start another)",
        heard=" ".join(_math_buffer),
    )

def _recording_append_action(spoken_text: str):
    """Records a catchall grammar phrase only if the pre-phrase hook missed it."""
    global _math_buffer, _pending_recording_action_phrase
    normalized = spoken_text.strip()
    if not _recording_active or not normalized:
        _pending_recording_action_phrase = None
        return
    if _pending_recording_action_phrase == normalized.casefold():
        _pending_recording_action_phrase = None
        return
    _pending_recording_action_phrase = None
    _math_buffer.append(normalized)
    show_hud("RECORDING", heard=" ".join(_math_buffer))

def _begin_math_recording():
    """Enables recording once, retaining any active dictation buffer."""
    global _math_buffer, _recording_active
    if not _recording_active:
        _math_buffer = []
        _recording_active = True
        try:
            actions.mode.enable("user.math_recording")
        except Exception:
            _recording_active = False
            raise
    show_hud(
        "RECORDING EQUATION (say 'done equation' to write or 'cancel equation' to discard)",
        heard=" ".join(_math_buffer) or "(waiting...)",
    )

speech_system.register("pre:phrase", _recording_phrase_listener)

SCRIBE_SYSTEM_PROMPT = (
    "You are a precise physics-homework scribe for a person who dictates instead of typing. "
    "The input contains the current spoken request and may contain earlier dictation/output as "
    "context. Follow the speaker's latest intent and produce only the content they asked to put "
    "in the document.\n"
    "Rules:\n"
    "1. Respect requests such as 'only equations', 'write this in words', and 'write the sentence'. "
    "Do not add explanations, corrections, suggestions, headings, or answers the speaker did not ask for.\n"
    "2. Preserve the speaker's stated mathematics, even if it appears wrong. Do not silently repair "
    "physics, algebra, signs, or assumptions. Correct capitalization and clear speech-recognition "
    "homophones; apply the speaker's own latest correction and discard only the false start they "
    "explicitly took back.\n"
    "3. When asked to solve, substitute, evaluate, or use a mathematical skill, show the requested "
    "work and compute the result. Keep reasonable significant figures and units. Use defined "
    "constants precisely (for example, k_B = 1.380649×10^-23 J K^-1, "
    "N_A = 6.02214076×10^23 mol^-1, and R = 8.314462618 J mol^-1 K^-1). "
    "Do not invent missing values.\n"
    "4. Understand natural physics dictation: Greek letters, subscripts, superscripts, fractions, "
    "derivatives, integrals, limits, units, and capital/lowercase symbols. 'Change in' usually means "
    "\\Delta; 'd over d' and 'partial derivative' should use standard notation.\n"
    "5. Use earlier context only to resolve references or retrieve requested earlier work. Return "
    "only the new or revised content asked for now; do not repeat the whole document unless asked. "
    "A note explicitly marked 'no need to write anything' produces no document content.\n"
    "6. Output each item in order using exactly this format:\n"
    "---ITEM---\nTYPE: EQUATION\nLaTeX equation(s)\n"
    "or\n---ITEM---\nTYPE: TEXT\nExact requested prose paragraph\n"
    "Use one item per equation or paragraph. Put multi-line math inside one EQUATION item. "
    "If there is nothing to write, output exactly NO_OUTPUT. Do not use markdown fences, dollar "
    "delimiters, or any text outside these item blocks.\n"
    "Example input: 'Only equations. E equals m c squared. Actually change E to y. Then write "
    "the sentence: energy is conserved.'\n"
    "Example output:\n"
    "---ITEM---\nTYPE: EQUATION\ny = mc^2\n"
    "---ITEM---\nTYPE: TEXT\nEnergy is conserved."
)

EDIT_SCRIBE_SYSTEM_PROMPT = (
    "You are a careful voice scribe editor. You receive CURRENT_ITEM_TYPE, CURRENT_ITEM, and "
    "EDIT_INSTRUCTION. Apply only the requested edit, preserve all unrelated content and the "
    "current type unless the user explicitly asks to change it. Honor corrections and homophones. "
    "Do not correct the user's physics or algebra, add suggestions, or explain. Return exactly "
    "TYPE: EQUATION or TYPE: TEXT on the first line, followed by the complete updated item. "
    "Equation content must be valid LaTeX without dollar signs; text content must be plain prose. "
    "Do not use markdown fences or any content outside the updated item."
)

@mod.capture(rule="({user.math_vocab} | <phrase>)+")
def math_phrase(m) -> str:
    words = []
    for item in m:
        if isinstance(item, str):
            words.append(item)
        else:
            words.extend(item)
    return " ".join(words)

_cached_groq_model = None

def get_groq_model(token: str) -> str:
    """Finds the best active model available on the user's Groq account."""
    global _cached_groq_model
    if _cached_groq_model:
        return _cached_groq_model

    preferences = [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "llama3-8b-8192",
        "llama3-70b-8192",
        "mixtral-8x7b-32768",
        "qwen/qwen3.8-27b",
    ]

    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/models",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "TalonVoice-Math/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            model_ids = sorted({m["id"] for m in data.get("data", [])})

            for p in preferences:
                if p in model_ids:
                    _cached_groq_model = p
                    return _cached_groq_model

            for m_id in model_ids:
                if "whisper" not in m_id and "guard" not in m_id:
                    _cached_groq_model = m_id
                    return _cached_groq_model
    except Exception as e:
        print(f"[Groq Model Auto-Detect] {e}")

    _cached_groq_model = "llama-3.1-8b-instant"
    return _cached_groq_model

def get_auth_and_config():
    """Load the Groq API key and select an available Groq model."""
    token_sources = [
        Path(__file__).parent / "api_token.txt",
        Path(__file__).parent / "groq_token.txt",
    ]

    token = None
    for tf in token_sources:
        if tf.exists():
            try:
                content = tf.read_text(encoding="utf-8").strip()
            except Exception:
                continue

            # Extract a Groq API key even if the file includes surrounding notes.
            m = re.search(r'gsk_[a-zA-Z0-9_\-\.]+', content)
            if m:
                token = m.group(0).strip().strip("'\"")
                break

            # Fallback: first non-comment line
            lines = [l.strip().strip("'\"") for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
            if lines:
                token = lines[0]
                break

    if not token:
        token = os.environ.get("GROQ_API_KEY")

    if not token:
        return None, None, None, None

    if not token.startswith("gsk_"):
        raise ValueError("A Groq API key (starting with gsk_) is required in api_token.txt or GROQ_API_KEY.")

    model = get_groq_model(token)
    return token, "https://api.groq.com/openai/v1/chat/completions", model, f"Groq ({model})"

def call_equation_model(system_prompt: str, user_text: str) -> str:
    """Calls Groq using its OpenAI-compatible Chat Completions API."""
    token, endpoint, model_name, provider = get_auth_and_config()
    if not token:
        raise ValueError(
            f"API key not found! Please paste your key into:\n{Path(__file__).parent / 'api_token.txt'}"
        )

    body = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.0
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Authorization": f"Bearer {token}",
            "User-Agent": "TalonVoice-Math/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            raw_bytes = response.read()
            # Decompress if server sent gzip or deflate
            if raw_bytes.startswith(b"\x1f\x8b") or "gzip" in response.headers.get("Content-Encoding", "").lower():
                raw_bytes = gzip.decompress(raw_bytes)
            elif "deflate" in response.headers.get("Content-Encoding", "").lower():
                raw_bytes = zlib.decompress(raw_bytes)

            raw_text = raw_bytes.decode("utf-8", errors="replace")
            if not raw_text.strip():
                raise RuntimeError(f"Server returned empty response (HTTP {response.status})")

            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError as jde:
                raise RuntimeError(f"Server returned non-JSON response: {raw_text[:200]}") from jde
    except urllib.error.HTTPError as e:
        error_msg = f"HTTP {e.code}: {e.reason}"
        try:
            err_bytes = e.read()
            if err_bytes.startswith(b"\x1f\x8b") or "gzip" in e.headers.get("Content-Encoding", "").lower():
                err_bytes = gzip.decompress(err_bytes)
            elif "deflate" in e.headers.get("Content-Encoding", "").lower():
                err_bytes = zlib.decompress(err_bytes)
            err_text = err_bytes.decode("utf-8", errors="replace")
            err_data = json.loads(err_text)
            if "message" in err_data:
                error_msg = f"API Error: {err_data['message']}"
            elif "error" in err_data:
                if isinstance(err_data["error"], dict) and "message" in err_data["error"]:
                    error_msg = f"API Error: {err_data['error']['message']}"
                else:
                    error_msg = f"API Error: {err_data['error']}"
        except Exception:
            pass
        raise RuntimeError(error_msg) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    content = re.sub(r"^```(?:latex)?\n?|\n?```$", "", content).strip()
    content = content.strip("$").strip()
    if not content:
        raise RuntimeError("The math model returned an empty response")
    return content

def _delete_previous_item_in_document(char_count: int):
    """Deletes the previous scribed item at the cursor before replacing it."""
    if char_count > 0:
        actions.key(f"backspace:{char_count}")
        actions.sleep("80ms")

def _paste_shortcut():
    """Pastes from the native clipboard on Windows or macOS."""
    system = platform.system()
    if system == "Darwin":
        actions.key("cmd-v")
    elif system == "Windows":
        actions.key("ctrl-v")
    else:
        raise RuntimeError("Equation-image paste is currently supported on Windows and macOS only")

def _get_fxeditor_key():
    """Returns an optional fxEditor application key without exposing it in logs."""
    key = os.environ.get("FXEDITOR_API_KEY", "").strip()
    if not key and FXEDITOR_KEY_FILE.exists():
        try:
            key = FXEDITOR_KEY_FILE.read_text(encoding="utf-8").splitlines()[0].strip()
        except (OSError, IndexError):
            key = ""
    return key

def _render_fxeditor_png(latex_eq: str) -> bytes:
    """Renders LaTeX to a PNG through fxTeX, the rendering API used by fxEditor."""
    if not latex_eq.strip():
        raise RuntimeError("The math model returned an empty equation")
    # 192 DPI gives Google Docs a crisp image while keeping paste sizes reasonable.
    markup = r"\dpi{192}\bg{white} " + latex_eq
    req = urllib.request.Request(
        FXTEX_RENDER_URL + urllib.parse.quote(markup, safe=""),
        headers={"Accept": "application/json", "User-Agent": "TalonVoice-Math/1.0"},
    )
    key = _get_fxeditor_key()
    if key:
        req.add_header("X-API-Key", key)

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"fxEditor render failed (HTTP {e.code})") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"fxEditor network error: {e.reason}") from e

    result = payload.get("latex", {})
    if not result.get("valid", False):
        errors = "; ".join(result.get("errors", [])) or "invalid LaTeX"
        raise RuntimeError(f"fxEditor could not render the equation: {errors}")
    try:
        png_bytes = base64.b64decode(result["base64"], validate=True)
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError("fxEditor returned no PNG image") from e
    if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("fxEditor returned an empty or invalid PNG image")
    return png_bytes

def _copy_png_to_native_clipboard(png_bytes: bytes):
    """Places a PNG on the system clipboard, ready for a Google Docs paste."""
    system = platform.system()
    if system not in ("Windows", "Darwin"):
        raise RuntimeError("Equation-image paste is currently supported on Windows and macOS only")

    if system == "Windows":
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
        user32.RegisterClipboardFormatW.restype = wintypes.UINT
        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.OpenClipboard.restype = wintypes.BOOL
        user32.EmptyClipboard.restype = wintypes.BOOL
        user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        user32.SetClipboardData.restype = wintypes.HANDLE
        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = wintypes.HANDLE
        kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
        kernel32.GlobalUnlock.restype = wintypes.BOOL
        kernel32.GlobalFree.argtypes = [wintypes.HANDLE]
        kernel32.GlobalFree.restype = wintypes.HANDLE

        png_format = user32.RegisterClipboardFormatW("PNG")
        if not png_format:
            raise RuntimeError("Windows could not register the PNG clipboard format")
        memory_handle = kernel32.GlobalAlloc(0x0002, len(png_bytes))  # GMEM_MOVEABLE
        if not memory_handle:
            raise RuntimeError("Windows could not allocate clipboard memory for the equation")
        pointer = kernel32.GlobalLock(memory_handle)
        if not pointer:
            kernel32.GlobalFree(memory_handle)
            raise RuntimeError("Windows could not lock clipboard memory for the equation")
        ctypes.memmove(pointer, png_bytes, len(png_bytes))
        kernel32.GlobalUnlock(memory_handle)

        opened = False
        try:
            for _ in range(20):
                if user32.OpenClipboard(None):
                    opened = True
                    break
                time.sleep(0.05)
            if not opened:
                raise RuntimeError("The clipboard is busy; equation image was not replaced")
            if not user32.EmptyClipboard():
                raise RuntimeError("Windows could not prepare the clipboard for the equation")
            if not user32.SetClipboardData(png_format, memory_handle):
                raise RuntimeError("Windows could not place the equation image on the clipboard")
            memory_handle = None  # Windows owns it after SetClipboardData succeeds.
        finally:
            if opened:
                user32.CloseClipboard()
            if memory_handle:
                kernel32.GlobalFree(memory_handle)
        return

    image_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as image_file:
            image_file.write(png_bytes)
            image_path = image_file.name

        # Pass the generated path as an AppleScript argument so unusual user
        # or temporary-directory characters cannot break the script string.
        script = 'on run argv\n set the clipboard to (read (POSIX file (item 1 of argv)) as «class PNGf»)\nend run'
        result = subprocess.run(
            ["osascript", "-e", script, image_path], capture_output=True, text=True, timeout=5,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "could not copy PNG to the system clipboard")
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("copying the equation image timed out; the clipboard may be busy") from e
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"could not copy PNG to the system clipboard: {e}") from e
    finally:
        if image_path:
            try:
                os.unlink(image_path)
            except OSError:
                pass

def _paste_equation_png(png_bytes: bytes):
    """Pastes an equation in a centered paragraph and restores left alignment below it."""
    _copy_png_to_native_clipboard(png_bytes)
    system = platform.system()
    if system == "Darwin":
        center_key, left_key = "cmd-shift-e", "cmd-shift-l"
    elif system == "Windows":
        center_key, left_key = "ctrl-shift-e", "ctrl-shift-l"
    else:
        raise RuntimeError("Equation-image paste is currently supported on Windows and macOS only")
    actions.key(center_key)
    actions.sleep("100ms")
    _paste_shortcut()
    actions.sleep("100ms")
    actions.key("enter")
    actions.key(left_key)
    return png_bytes

def _replace_selected_equation_png(png_bytes: bytes):
    """Deletes the selected inline equation, pastes its replacement in place."""
    _copy_png_to_native_clipboard(png_bytes)
    actions.sleep("100ms")
    actions.key("backspace")
    actions.sleep("100ms")
    _paste_shortcut()
    actions.sleep("100ms")

def _select_document_equation(code: str):
    """Moves to the tracked equation and freshly selects its inline image."""
    matches = [
        index for index, item in enumerate(_document_items)
        if item.get("kind") == "equation" and item.get("label") == code
    ]
    if not matches:
        raise RuntimeError(f"Equation {_spoken_code(code)} is no longer tracked in this document")
    actions.key("ctrl-end")
    distance = _equation_key_distance(matches[-1])
    if distance:
        actions.key(f"left:{distance}")
    actions.key("shift-right")

def _paste_and_record(latex_eq: str, heard_label: str):
    """Renders and pastes a LaTeX equation image, then saves it for this-session edits."""
    global _equation_history, _document_items
    show_hud("Rendering equation image...", heard=heard_label)
    preview_png = _render_fxeditor_png(latex_eq)
    document_key = _sync_document_items()
    saved_code = _save_equation(latex_eq, preview_png)
    _paste_equation_png(preview_png)
    final_output = f"[equation image] — label {_spoken_code(saved_code)}"
    # Each equation image is followed by a newline.
    delete_count = 2
    document_index = len(_document_items)

    _equation_history.append({
        "kind": "equation",
        "latex": latex_eq,
        "content": latex_eq,
        "rendered": final_output,
        "delete_count": delete_count,
        "saved_code": saved_code,
        "document_index": document_index,
        "document_key": document_key,
    })
    _document_items.append({
        "kind": "equation",
        "content": latex_eq,
        "label": saved_code,
        "delete_count": delete_count,
    })
    _persist_equation_state()

    show_hud("Done!", heard=heard_label, result=final_output)

def _paste_text_and_record(text: str, heard_label: str):
    """Inserts a dictated prose item and tracks it for spoken edits and undo."""
    global _equation_history, _document_items
    text = text.strip()
    if not text:
        return
    show_hud("Writing requested text...", heard=heard_label)
    document_key = _sync_document_items()
    actions.insert(text)
    actions.key("enter")
    document_index = len(_document_items)
    _equation_history.append({
        "kind": "text",
        "content": text,
        "rendered": text,
        "delete_count": len(text) + 1,
        "saved_code": None,
        "document_index": document_index,
        "document_key": document_key,
    })
    _document_items.append({
        "kind": "text",
        "content": text,
        "label": None,
        "delete_count": len(text) + 1,
    })
    _persist_equation_state()
    show_hud("Done!", heard=heard_label, result=text)

def _parse_scribe_items(response: str) -> list[dict[str, str]]:
    """Parses tagged equation and prose items; accepts old separator-only answers."""
    response = re.sub(r"^\x60{3}[^\n]*\n?|\n?\x60{3}$", "", response.strip()).strip()
    if response.upper() == "NO_OUTPUT":
        return []

    blocks = re.split(r"(?m)^---ITEM---\s*$", response)
    if len(blocks) == 1:
        # Backwards compatibility with the earlier equation-only response format.
        equations = re.split(r"\s*---EQUATION---\s*", response)
        return [
            {"kind": "equation", "content": item.strip()}
            for item in equations
            if item.strip()
        ]

    items = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        match = re.match(r"(?is)^TYPE:\s*(EQUATION|TEXT)\s*\n(.*)$", block)
        if not match:
            raise RuntimeError("The scribe returned an item without an EQUATION or TEXT type")
        kind = "equation" if match.group(1).upper() == "EQUATION" else "text"
        content = match.group(2).strip()
        if content:
            items.append({"kind": kind, "content": content})
    return items

def _recent_scribe_context(max_chars: int = 12000) -> str:
    """Returns recent context within a bounded prompt size."""
    selected = []
    total_chars = 0
    for item in reversed(_scribe_context):
        extra = len(item) + 1
        if not selected and len(item) > max_chars:
            selected.append(item[-max_chars:])
            break
        if selected and total_chars + extra > max_chars:
            break
        selected.append(item)
        total_chars += extra
    return "\n".join(reversed(selected))

def _make_equation_batch(spoken_chunks: list[str]):
    """Turns naturally paused speech into ordered prose and equation document items."""
    global _scribe_context
    batch_text = "\n\n".join(spoken_chunks)
    prior_context = _recent_scribe_context()
    user_text = (
        f"EARLIER DICTATION AND WRITTEN ITEMS (context only):\n{prior_context or '(none)'}"
        f"\n\nCURRENT REQUEST (write only what is requested here):\n{batch_text}"
    )
    show_hud(
        f"Preparing {len(spoken_chunks)} speech segments...",
        heard=batch_text,
    )
    response = call_equation_model(SCRIBE_SYSTEM_PROMPT, user_text)
    items = _parse_scribe_items(response)
    _scribe_context.append(f"SPEAKER: {batch_text}")

    if not items:
        _scribe_context = _scribe_context[-100:]
        _persist_equation_state()
        show_hud("Done equations — nothing to add.", heard=batch_text)
        return

    completed = 0
    for item in items:
        try:
            if item["kind"] == "equation":
                _paste_and_record(item["content"], batch_text)
                _scribe_context.append(f"EQUATION: {item['content']}")
            else:
                _paste_text_and_record(item["content"], batch_text)
                _scribe_context.append(f"TEXT: {item['content']}")
            completed += 1
        except Exception as e:
            # Keep already-pasted equations available for editing and report progress.
            raise RuntimeError(
                f"Document item {completed + 1} of {len(items)} could not be written. "
                f"{completed} earlier item(s) were completed. {e}"
            ) from e
    _scribe_context = _scribe_context[-100:]
    _persist_equation_state()
    show_hud("Done equations.", heard=batch_text)

@mod.action_class
class Actions:
    def equation_make(spoken_text: str):
        """Scribes a dictated equation or requested text into the active document."""
        try:
            _make_equation_batch([spoken_text])
        except Exception as e:
            print(f"[Equation Editor Error] {e}")
            show_hud(f"Error: {e}", heard=spoken_text)

    def equation_edit_last(edit_instruction: str):
        """Edits the last equation or prose item in-place based on spoken instructions."""
        global _equation_history, _document_items, _scribe_context
        if not _equation_history:
            show_hud("No scribed item from this session to edit.")
            return

        last_state = _equation_history[-1]
        document_key = _sync_document_items()
        if last_state.get("document_key") != document_key:
            show_hud("The latest scribed item belongs to a different document.")
            return
        prev_kind = last_state.get("kind", "equation")
        prev_content = last_state.get("content", last_state.get("latex", ""))
        prev_rendered = last_state["rendered"]

        try:
            show_hud(f"Editing: {prev_rendered}", heard=edit_instruction)
            user_prompt = (
                f"CURRENT_ITEM_TYPE: {prev_kind.upper()}\n"
                f"CURRENT_ITEM:\n{prev_content}\n\nEDIT_INSTRUCTION: {edit_instruction}"
            )
            updated_item = call_equation_model(EDIT_SCRIBE_SYSTEM_PROMPT, user_prompt)
            match = re.match(r"(?is)^TYPE:\s*(EQUATION|TEXT)\s*\n(.*)$", updated_item.strip())
            if not match or not match.group(2).strip():
                raise RuntimeError("The editor did not return a valid updated item")
            new_kind = "equation" if match.group(1).upper() == "EQUATION" else "text"
            new_content = match.group(2).strip()
            preview_png = _render_fxeditor_png(new_content) if new_kind == "equation" else None
            document_index = last_state.get("document_index", len(_document_items) - 1)
            # Render first so a render/API error leaves the current document item intact.
            _delete_previous_item_in_document(last_state["delete_count"])
            if new_kind == "equation":
                if prev_kind == "equation" and last_state.get("saved_code"):
                    saved_code = last_state["saved_code"]
                    _update_saved_equation(saved_code, new_content, preview_png)
                else:
                    saved_code = _save_equation(new_content, preview_png)
                _paste_equation_png(preview_png)
                rendered = f"[equation image] — saved as {saved_code}"
                delete_count = 2
            else:
                actions.insert(new_content)
                actions.key("enter")
                saved_code = None
                rendered = new_content
                delete_count = len(new_content) + 1
            if 0 <= document_index < len(_document_items):
                _document_items[document_index] = {
                    "kind": new_kind,
                    "content": new_content,
                    "label": saved_code,
                    "delete_count": delete_count,
                }
            _equation_history.append({
                "kind": new_kind,
                "latex": new_content if new_kind == "equation" else "",
                "content": new_content,
                "rendered": rendered,
                "delete_count": delete_count,
                "saved_code": saved_code,
                "document_index": document_index,
                "document_key": document_key,
                "replaces_previous": True,
            })
            _scribe_context.append(f"EDITED {prev_kind.upper()}: {new_content}")
            _scribe_context = _scribe_context[-100:]
            _persist_equation_state()
            show_hud("Done!", heard=f"Edit: {edit_instruction}", result=rendered)
        except Exception as e:
            print(f"[Equation Editor Edit Error] {e}")
            show_hud(f"Edit Error: {e}", heard=edit_instruction)

    def equation_edit_by_label_start(code: str):
        """Selects a labeled equation and asks the user to verify it before editing."""
        global _pending_equation_code, _pending_document_key
        global _pending_equation_edit_confirmation
        _pending_equation_code = None
        _pending_document_key = None
        _pending_equation_edit_confirmation = False
        document_key = _refresh_active_document_state()
        matches = [
            index for index, item in enumerate(_document_items)
            if item.get("kind") == "equation" and item.get("label") == code
        ]
        if not matches or code not in _saved_equations:
            show_hud(
                f"Equation {_spoken_code(code)} is not in the current scribed document.",
                result="Labels are available for equations created during this Talon session.",
            )
            return

        try:
            _select_document_equation(code)
        except Exception as e:
            show_hud(f"Could not select equation {_spoken_code(code)}.", result=str(e))
            return

        _pending_equation_code = code
        _pending_document_key = document_key
        _pending_equation_edit_confirmation = True
        show_hud(
            f"Equation {_spoken_code(code)} is selected. Check it in the document, then say 'confirm equation edit' to continue, or 'cancel edit'.",
        )

    def equation_edit_by_label_confirm():
        """Starts listening for a change after the selected equation is verified."""
        global _pending_equation_edit_confirmation
        global _pending_equation_code, _pending_document_key
        if not _pending_equation_edit_confirmation or not _pending_equation_code:
            show_hud("Choose an equation with 'edit' and its code first.")
            return
        try:
            document_key = _sync_document_items()
            if document_key != _pending_document_key:
                raise RuntimeError("The active document changed; choose the equation again")
            if not any(
                item.get("kind") == "equation" and item.get("label") == _pending_equation_code
                for item in _document_items
            ):
                raise RuntimeError("The selected equation is no longer tracked in this document")
        except Exception as e:
            show_hud("Could not confirm the equation edit.", result=str(e))
            _pending_equation_code = None
            _pending_document_key = None
            _pending_equation_edit_confirmation = False
            return
        _pending_equation_edit_confirmation = False
        actions.mode.enable("user.equation_editing")
        show_hud(
            f"Editing equation {_spoken_code(_pending_equation_code)}. Speak the change, or say 'cancel edit'."
        )

    def equation_edit_by_label(code: str, edit_instruction: str):
        """Edits one labeled equation in place, preserving its label and document position."""
        global _pending_equation_code, _pending_document_key, _pending_equation_edit_confirmation
        global _scribe_context, _document_items
        try:
            document_key = _sync_document_items()
            if document_key != _pending_document_key:
                raise RuntimeError("The active document changed; the equation was not replaced")
            equation = _saved_equations.get(code)
            if not equation:
                raise RuntimeError(f"Equation {_spoken_code(code)} is no longer available")
            document_matches = [
                index for index, item in enumerate(_document_items)
                if item.get("kind") == "equation" and item.get("label") == code
            ]
            if not document_matches:
                raise RuntimeError(f"Equation {_spoken_code(code)} is no longer tracked in this document")
            document_index = document_matches[-1]
            previous_item = _document_items[document_index]
            previous_state = {
                "kind": "equation",
                "latex": equation["latex"],
                "content": equation["latex"],
                "rendered": f"[equation image] — label {_spoken_code(code)}",
                "delete_count": previous_item["delete_count"],
                "saved_code": code,
                "document_index": document_index,
                "document_key": document_key,
            }
            user_prompt = (
                f"CURRENT_ITEM_TYPE: EQUATION\nCURRENT_ITEM:\n{equation['latex']}"
                f"\n\nEDIT_INSTRUCTION: {edit_instruction}"
            )
            updated_item = call_equation_model(EDIT_SCRIBE_SYSTEM_PROMPT, user_prompt)
            match = re.match(r"(?is)^TYPE:\s*(EQUATION|TEXT)\s*\n(.*)$", updated_item.strip())
            if not match or match.group(1).upper() != "EQUATION" or not match.group(2).strip():
                raise RuntimeError("The editor did not return an updated equation")
            new_latex = match.group(2).strip()
            preview_png = _render_fxeditor_png(new_latex)

            # Re-select after model/render work so the correct image remains targeted.
            _select_document_equation(code)
            _replace_selected_equation_png(preview_png)
            actions.key("ctrl-end")
            _update_saved_equation(code, new_latex, preview_png)
            _document_items[document_index]["content"] = new_latex
            _equation_history.append({
                "kind": "equation",
                "latex": new_latex,
                "content": new_latex,
                "rendered": f"[equation image] — label {_spoken_code(code)}",
                "delete_count": previous_item["delete_count"],
                "saved_code": code,
                "document_index": document_index,
                "document_key": document_key,
                "replaces_previous": True,
                "restore_state": previous_state,
            })
            _scribe_context.append(f"EDITED EQUATION {_spoken_code(code)}: {new_latex}")
            _scribe_context = _scribe_context[-100:]
            _persist_equation_state()
            show_hud(
                f"Updated equation {_spoken_code(code)}.",
                heard=edit_instruction,
                result=new_latex,
            )
        except Exception as e:
            print(f"[Equation Editor Labeled Edit Error] {e}")
            show_hud(f"Edit Error: {e}", heard=edit_instruction)
        finally:
            _pending_equation_code = None
            _pending_document_key = None
            _pending_equation_edit_confirmation = False

    def equation_edit_start():
        """Shows the current equation and waits for a longer spoken edit instruction."""
        if not _equation_history:
            show_hud("No scribed item from this session to edit.")
            return
        if _equation_history[-1].get("document_key") != _sync_document_items():
            show_hud("The latest scribed item belongs to a different document.")
            return
        last_state = _equation_history[-1]
        actions.mode.enable("user.equation_editing")
        show_hud(
            f"EDITING {last_state.get('saved_code') or 'last item'} — speak the change when ready.",
            heard=f"Current item: {last_state['rendered']}",
        )

    def equation_edit_complete(edit_instruction: str):
        """Applies the edit captured in the dedicated edit-listening state."""
        global _pending_equation_code
        actions.mode.disable("user.equation_editing")
        if _pending_equation_code:
            actions.user.equation_edit_by_label(_pending_equation_code, edit_instruction)
        else:
            actions.user.equation_edit_last(edit_instruction)

    def equation_edit_cancel():
        """Leaves the dedicated edit-listening state without changing the equation."""
        global _pending_equation_code, _pending_document_key
        global _pending_equation_edit_confirmation
        actions.mode.disable("user.equation_editing")
        _pending_equation_code = None
        _pending_document_key = None
        _pending_equation_edit_confirmation = False
        show_hud("Edit cancelled.")

    def equation_append_last(extra_math: str):
        """Appends spoken content to the last equation or prose item in place."""
        actions.user.equation_edit_last(f"append the following to the end of the current item: {extra_math}")

    def equation_revert():
        """Undoes the last item, restoring its old version when it was edited in place."""
        global _equation_history, _document_items, _scribe_context
        if not _equation_history:
            show_hud("There is no scribed item to undo.")
            return

        current_state = _equation_history[-1]
        if current_state.get("document_key") != _sync_document_items():
            show_hud("The latest scribed item belongs to a different document.")
            return
        replaces_previous = current_state.get("replaces_previous", False)
        previous_state = (
            current_state.get("restore_state") or _equation_history[-2]
            if replaces_previous
            else None
        )
        previous_kind = previous_state.get("kind", "equation") if previous_state else None
        previous_content = (
            previous_state.get("content", previous_state.get("latex", ""))
            if previous_state
            else ""
        )
        previous_png = (
            _render_fxeditor_png(previous_content)
            if previous_kind == "equation"
            else None
        )
        if current_state.get("restore_state") and previous_kind == "equation":
            code = current_state.get("saved_code")
            _select_document_equation(code)
            _replace_selected_equation_png(previous_png)
            actions.key("ctrl-end")
        elif previous_kind == "text":
            _delete_previous_item_in_document(current_state["delete_count"])
            actions.insert(previous_content)
            actions.key("enter")
        else:
            _delete_previous_item_in_document(current_state["delete_count"])
            if previous_kind == "equation":
                _paste_equation_png(previous_png)
        if previous_kind == "equation" and previous_state and previous_state.get("saved_code"):
            _update_saved_equation(previous_state["saved_code"], previous_content, previous_png)
        _equation_history.pop()
        document_index = current_state.get("document_index", len(_document_items) - 1)
        if previous_state:
            _document_items[document_index] = {
                "kind": previous_kind,
                "content": previous_content,
                "label": previous_state.get("saved_code"),
                "delete_count": previous_state["delete_count"],
            }
        elif document_index == len(_document_items) - 1:
            _document_items.pop()
        if previous_state:
            result = f"Restored: {previous_state['rendered']}"
        else:
            result = "Removed the last scribed item."
        _scribe_context.append(f"UNDO: {result}")
        _scribe_context = _scribe_context[-100:]
        _persist_equation_state()
        show_hud("Undo complete.", result=result)

    def math_paste_saved_equation(code: str):
        """Pastes a previously saved equation by its HUD code."""
        equation = _saved_equations.get(code)
        if not equation:
            show_hud(f"Saved equation '{code}' was not found.")
            return
        latex_eq = equation["latex"]
        try:
            show_hud(f"Pasting saved equation {code}...", heard=f"{code}: {latex_eq}")
            _paste_and_record(latex_eq, f"Copy of {code}")
            show_hud(f"Pasted a copy as {_spoken_code(_equation_history[-1]['saved_code'])}.", heard=latex_eq)
        except Exception as e:
            print(f"[Equation Editor Saved Equation Error] {e}")
            show_hud(f"Could not paste {code}: {e}", heard=f"{code}: {latex_eq}")

    def math_paste_all_equations():
        """Pastes one copy of every equation saved at the start of this request."""
        equations = [(code, item["latex"]) for code, item in _saved_equations.items()]
        if not equations:
            show_hud("There are no saved equations to paste.")
            return
        for index, (code, latex_eq) in enumerate(equations, start=1):
            try:
                _paste_and_record(latex_eq, f"Paste all: {code}")
            except Exception as e:
                print(f"[Equation Editor Paste All Error] {e}")
                show_hud(
                    f"Pasted {index - 1} of {len(equations)} equations; stopped at {code}.",
                    result=str(e),
                )
                return
        show_hud(f"Pasted all {len(equations)} saved equations.")

    def math_show_saved_equations():
        """Opens the labeled Equation Editor window."""
        global _saved_equations_visible
        _saved_equations_visible = True
        show_hud("Opening Equation Editor and refreshing saved equations...")
        try:
            _refresh_active_document_state()
        except Exception as e:
            print(f"[Equation Editor Open Error] {e}")
            show_hud("Equation Editor opened, but saved equations could not be refreshed.", result=str(e))
            return
        show_hud("Equation Editor open. Say 'edit' and a code, check the selected equation, then confirm to speak a change.")

    def math_scribe_context_clear():
        """Clears this session's dictation context without changing the document."""
        global _scribe_context
        _scribe_context = []
        _persist_equation_state()
        show_hud("Equation context cleared. The document was not changed.")

    def math_recording_start():
        """Starts or reopens continuous math recording without losing dictation."""
        _begin_math_recording()

    def math_recording_new():
        """Starts a fresh equation segment, writing any current segment first."""
        global _math_buffer
        chunks = _math_buffer[:] if _recording_active else []
        if not _recording_active:
            _begin_math_recording()
        else:
            _math_buffer = []
            show_hud("New equation started.", heard="(waiting for speech)")
        # Keep recording enabled while the previous segment is processed so
        # restarting does not leave the speech mode disabled on error.
        if chunks:
            try:
                _make_equation_batch(chunks)
            except Exception as e:
                print(f"[Equation Editor Batch Error] {e}")
                show_hud(f"Batch Error: {e}")

    def math_recording_append(spoken_text: str):
        """Compatibility action; the speech listener already captured this phrase."""
        _recording_append_action(spoken_text)

    def math_recording_scratch_last():
        """Removes the most recent spoken chunk while still inside recording mode."""
        global _math_buffer
        if _math_buffer:
            removed = _math_buffer.pop()
            current_full = " ".join(_math_buffer) if _math_buffer else "(empty)"
            show_hud(f"Removed '{removed}'", heard=current_full)
        else:
            show_hud("Buffer is already empty", heard="(waiting...)")

    def math_recording_finish():
        """Finishes recording and writes the requested equations and prose."""
        global _math_buffer, _recording_active, _pending_recording_action_phrase
        _recording_active = False
        _pending_recording_action_phrase = None
        actions.mode.disable("user.math_recording")
        chunks = _math_buffer[:]
        _math_buffer = []
        if chunks:
            try:
                _make_equation_batch(chunks)
            except Exception as e:
                print(f"[Equation Editor Batch Error] {e}")
                show_hud(f"Batch Error: {e}")
        else:
            show_hud("No speech recorded. Recording stopped.")

    def math_recording_cancel():
        """Cancels math recording."""
        global _math_buffer, _recording_active, _pending_recording_action_phrase
        _math_buffer = []
        _recording_active = False
        _pending_recording_action_phrase = None
        actions.mode.disable("user.math_recording")
        show_hud("Math recording cancelled.")

    def math_hud_hide():
        """Hides the persistent Equation Editor status window."""
        _hide_equation_windows()
