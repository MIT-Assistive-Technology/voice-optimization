# C:\Users\kaemy\AppData\Roaming\talon\user\qwen_equation.py
import json
import re
import urllib.request
import urllib.error
from talon import Context, Module, actions, clip, cron, imgui

try:
    import unicodeit
    HAS_UNICODEIT = True
except ImportError:
    HAS_UNICODEIT = False

mod = Module()
ctx = Context()

mod.mode("math_recording", desc="Continuous recording mode for math equations")
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
    # Helpful editing keywords
    "replace": "replace", "with": "with", "change": "change", "remove": "remove",
    "delete": "delete", "numerator": "numerator", "denominator": "denominator",
    "exponent": "exponent", "upper bound": "upper bound", "lower bound": "lower bound",
    "left side": "left side", "right side": "right side", "term": "term",
}

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3"

# Recording buffer state
_math_buffer = []
_math_output_mode = "normal"

# Equation history state for in-place editing & undo
# Each entry is a dict: {"latex": str, "rendered": str, "mode": str}
_equation_history = []

# HUD state
_hud_status = ""
_hud_heard = ""
_hud_result = ""
_hud_job = None

@imgui.open(y=0)
def math_hud(gui: imgui.GUI):
    gui.text(f"Qwen3 Math: {_hud_status}")
    if _hud_heard:
        gui.text(f"Heard: {_hud_heard}")
    if _hud_result:
        gui.text(f"Output: {_hud_result}")

def show_hud(status: str, heard: str = "", result: str = "", auto_hide_sec: int = 5):
    global _hud_status, _hud_heard, _hud_result, _hud_job
    _hud_status = status
    _hud_heard = heard
    _hud_result = result
    math_hud.show()
    if _hud_job:
        cron.cancel(_hud_job)
        _hud_job = None
    if auto_hide_sec > 0:
        _hud_job = cron.after(f"{auto_hide_sec}s", math_hud.hide)

LATEX_SYSTEM_PROMPT = (
    "/no_think\n"
    "You are an expert speech-to-LaTeX translator. The input comes from a speech-to-text "
    "engine that frequently mishears math homophones (e.g. 'ex' for 'x', 'why' for 'y', "
    "'to' or 'too' for '2', 'for' for '4', 'pie' for 'pi', 'sign' for 'sin', 'the ex' for 'dx', "
    "'are' for 'r', 'see' for 'c', 'dee ex' for 'dx').\n"
    "Rules:\n"
    "1. Infer the intended mathematical equation from the phonetic transcript and output ONLY valid LaTeX code.\n"
    "2. Do NOT wrap in markdown code blocks, backticks, or dollar signs ($).\n"
    "3. Do NOT include any explanations.\n"
    "Examples:\n"
    "User: ex squared plus why squared equals are squared\n"
    "Assistant: x^2 + y^2 = r^2\n"
    "User: integral from zero to infinity of e to the negative ex squared dee ex\n"
    "Assistant: \\int_{0}^{\\infty} e^{-x^2} dx"
)

EDIT_LATEX_SYSTEM_PROMPT = (
    "/no_think\n"
    "You are an expert LaTeX equation editor. You will receive a CURRENT_EQUATION (in LaTeX "
    "or Unicode math) and a spoken EDIT_INSTRUCTION from a voice dictation user.\n"
    "Note that spoken instructions may contain speech-to-text homophones ('ex' for 'x', "
    "'why' for 'y', 'to' for '2', 'for' for '4', 'pie' for 'pi', 'sign' for 'sin').\n"
    "Rules:\n"
    "1. Apply the requested modification to CURRENT_EQUATION and output ONLY the updated valid LaTeX code.\n"
    "2. Keep all other parts of CURRENT_EQUATION intact.\n"
    "3. Do NOT wrap in markdown code blocks, backticks, or dollar signs ($).\n"
    "4. Do NOT include any explanations.\n"
    "Examples:\n"
    "User: CURRENT_EQUATION: x^2 + y^2 = r^2\nEDIT_INSTRUCTION: replace y squared with z cubed\n"
    "Assistant: x^2 + z^3 = r^2\n"
    "User: CURRENT_EQUATION: \\int_{0}^{\\infty} e^{-x^2} dx\nEDIT_INSTRUCTION: change the upper bound to pi\n"
    "Assistant: \\int_{0}^{\\pi} e^{-x^2} dx\n"
    "User: CURRENT_EQUATION: f(x) = \\sin(x)\nEDIT_INSTRUCTION: append plus cosine of two x\n"
    "Assistant: f(x) = \\sin(x) + \\cos(2x)"
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

def call_qwen3(system_prompt: str, user_text: str) -> str:
    """Calls local qwen3:4b via Ollama with thinking disabled for instant response."""
    body = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        "stream": False,
        "think": False,
        "keep_alive": "24h",
        "options": {
            "temperature": 0.0,
            "num_ctx": 2048
        }
    }

    req = urllib.request.Request(
        OLLAMA_CHAT_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError:
        # Fallback if the user's Ollama version doesn't accept top-level "think" key
        body.pop("think", None)
        req = urllib.request.Request(
            OLLAMA_CHAT_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

    content = data.get("message", {}).get("content", "").strip()
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    content = re.sub(r"^```(?:latex)?\n?|\n?```$", "", content).strip()
    return content.strip("$").strip()

def latex_to_normal_form(latex_str: str) -> str:
    cleaned = latex_str
    cleaned = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", cleaned)
    cleaned = re.sub(r"\\sqrt\{([^{}]+)\}", r"√(\1)", cleaned)
    cleaned = cleaned.replace(r"\left", "").replace(r"\right", "").replace(r"\,", " ")

    if HAS_UNICODEIT:
        return unicodeit.replace(cleaned)
    return cleaned

def _delete_previous_equation_in_document(char_count: int):
    """Deletes the previously pasted equation characters right before the cursor."""
    if char_count > 0:
        actions.key(f"backspace:{char_count}")
        actions.sleep("80ms")

def _paste_and_record(latex_eq: str, output_mode: str, heard_label: str):
    """Formats the LaTeX output, pastes it, and saves state to _equation_history."""
    global _equation_history
    if output_mode == "latex":
        final_output = latex_eq
    else:
        final_output = latex_to_normal_form(latex_eq)

    _equation_history.append({
        "latex": latex_eq,
        "rendered": final_output,
        "mode": output_mode
    })

    show_hud("Done!", heard=heard_label, result=final_output, auto_hide_sec=6)
    clip.set_text(final_output)
    actions.sleep("150ms")
    actions.key("ctrl-v")

@mod.action_class
class Actions:
    def qwen_make_equation(spoken_text: str, output_mode: str = "normal"):
        """Translates spoken math to LaTeX via Qwen3, then converts to target form."""
        global _equation_history
        try:
            _equation_history = []
            show_hud("Translating via Qwen3...", heard=spoken_text, auto_hide_sec=10)
            latex_eq = call_qwen3(LATEX_SYSTEM_PROMPT, spoken_text)
            _paste_and_record(latex_eq, output_mode, spoken_text)
        except Exception as e:
            print(f"[Qwen3 Math Error] {e}")
            show_hud(f"Error: {e}", heard=spoken_text, auto_hide_sec=8)

    def qwen_edit_last_equation(edit_instruction: str):
        """Edits the last generated equation in-place based on spoken instructions."""
        global _equation_history
        if not _equation_history:
            show_hud("No previous equation to edit! Highlight one and say 'change selected equation...'", auto_hide_sec=5)
            return

        last_state = _equation_history[-1]
        prev_latex = last_state["latex"]
        prev_rendered = last_state["rendered"]
        mode = last_state["mode"]

        try:
            show_hud(f"Editing: {prev_rendered}", heard=edit_instruction, auto_hide_sec=10)
            user_prompt = f"CURRENT_EQUATION: {prev_latex}\nEDIT_INSTRUCTION: {edit_instruction}"
            new_latex = call_qwen3(EDIT_LATEX_SYSTEM_PROMPT, user_prompt)

            _delete_previous_equation_in_document(len(prev_rendered))
            _paste_and_record(new_latex, mode, f"Edit: {edit_instruction}")
        except Exception as e:
            print(f"[Qwen3 Edit Error] {e}")
            show_hud(f"Edit Error: {e}", heard=edit_instruction, auto_hide_sec=8)

    def qwen_append_last_equation(extra_math: str):
        """Appends additional spoken math to the end of the last equation in-place."""
        actions.user.qwen_edit_last_equation(f"append the following to the end of the equation: {extra_math}")

    def qwen_edit_selected_equation(edit_instruction: str, output_mode: str = "normal"):
        """Copies whatever equation is highlighted on screen, edits it via Qwen3, and replaces it."""
        global _equation_history
        try:
            clip.set_text("")
            actions.key("ctrl-c")
            actions.sleep("150ms")
            selected_text = clip.text().strip()

            if not selected_text:
                show_hud("Nothing selected! Highlight an equation first.", auto_hide_sec=4)
                return

            show_hud(f"Editing selected: {selected_text}", heard=edit_instruction, auto_hide_sec=10)
            user_prompt = f"CURRENT_EQUATION: {selected_text}\nEDIT_INSTRUCTION: {edit_instruction}"
            new_latex = call_qwen3(EDIT_LATEX_SYSTEM_PROMPT, user_prompt)

            _equation_history = []
            _paste_and_record(new_latex, output_mode, f"Selected Edit: {edit_instruction}")
        except Exception as e:
            show_hud(f"Selected Edit Error: {e}", auto_hide_sec=6)

    def qwen_revert_equation():
        """Reverts the last equation edit and restores the previous version in place."""
        global _equation_history
        if len(_equation_history) < 2:
            show_hud("Nothing to revert (already at original equation).", auto_hide_sec=4)
            return

        current_state = _equation_history.pop()
        previous_state = _equation_history[-1]

        _delete_previous_equation_in_document(len(current_state["rendered"]))
        clip.set_text(previous_state["rendered"])
        actions.sleep("150ms")
        actions.key("ctrl-v")
        show_hud("Reverted to previous version!", result=previous_state["rendered"], auto_hide_sec=5)

    def math_recording_start(output_mode: str = "normal"):
        """Starts continuous math recording mode with an on-screen HUD."""
        global _math_buffer, _math_output_mode
        _math_buffer = []
        _math_output_mode = output_mode
        actions.mode.enable("user.math_recording")
        show_hud("RECORDING ('done equation' to finish, 'scratch chunk' to undo last phrase)", heard="(waiting...)", auto_hide_sec=0)

    def math_recording_append(spoken_text: str):
        """Appends a spoken chunk to the ongoing equation buffer."""
        global _math_buffer
        _math_buffer.append(spoken_text)
        current_full = " ".join(_math_buffer)
        show_hud("RECORDING ('done equation' to finish, 'scratch chunk' to undo)", heard=current_full, auto_hide_sec=0)

    def math_recording_scratch_last():
        """Removes the most recent spoken chunk while still inside recording mode."""
        global _math_buffer
        if _math_buffer:
            removed = _math_buffer.pop()
            current_full = " ".join(_math_buffer) if _math_buffer else "(empty)"
            show_hud(f"Removed '{removed}'", heard=current_full, auto_hide_sec=0)
        else:
            show_hud("Buffer is already empty", heard="(waiting...)", auto_hide_sec=0)

    def math_recording_finish():
        """Finishes recording, sends the combined buffer to Qwen3, and pastes the result."""
        global _math_buffer, _math_output_mode
        actions.mode.disable("user.math_recording")
        full_text = " ".join(_math_buffer).strip()
        _math_buffer = []
        if full_text:
            actions.user.qwen_make_equation(full_text, _math_output_mode)
        else:
            show_hud("Cancelled (No speech recorded)", auto_hide_sec=3)

    def math_recording_cancel():
        """Cancels math recording."""
        global _math_buffer
        _math_buffer = []
        actions.mode.disable("user.math_recording")
        show_hud("Math Recording Cancelled", auto_hide_sec=3)