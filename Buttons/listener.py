"""
offline commands

Listens with vosk. When it hears one of your phrases, it finds the button
with the matching name (its aria-label usually) and clicks it.

"""
import json, os, queue, subprocess, sys, threading, time

# ===================== EDIT YOUR COMMANDS HERE =====================
# "phrase you say": ["buttons to search for", "more buttons if wanted"]
# Use a list to give several possible names for the same button; it clicks
# the first one it finds, e.g. ["Dictate", "Start dictation"].
# Phrases: lowercase, english words. ignore caps for names
COMMANDS = {
    "synchronized dolphin":        ["Dictate", "Start dictation"],
    "equation finished dictating": ["Stop dictating", "Stop recording"],
    # more phrases:        ["more buttons"],
}
# ===================================================================

MODEL_FOLDER = "vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
FULL_SEARCH_LIMIT = 10.0   # seconds for the whole-window search
APPS_TO_CHECK = ["com.google.Chrome"]   # add "com.apple.Safari" to also use Safari, or other browsers if you want

CLICKABLE_ROLES = {"AXButton", "AXLink"}
# don't look at these
SKIP_ROLES = {"AXStaticText", "AXImage", "AXToolbar", "AXTabGroup", "AXMenuBar"}

from ApplicationServices import (
    AXIsProcessTrusted, AXIsProcessTrustedWithOptions,
    AXUIElementCreateApplication, AXUIElementCreateSystemWide,
    AXUIElementCopyAttributeValue, AXUIElementSetAttributeValue,
    AXUIElementPerformAction, AXUIElementGetPid, AXValueGetValue,
)
from AppKit import NSRunningApplication
from Quartz import (
    CGEventCreate, CGEventCreateMouseEvent, CGEventGetLocation, CGEventPost,
    kCGHIDEventTap, kCGEventMouseMoved, kCGEventLeftMouseDown, kCGEventLeftMouseUp,
    kCGMouseButtonLeft,
)

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------- macOS accessibility helpers ----------

def ax(el, attr):
    """Read one accessibility attribute, or None."""
    if el is None:
        return None
    try:
        err, val = AXUIElementCopyAttributeValue(el, attr, None)
    except Exception:
        return None
    return val if err == 0 else None


def candidate_apps():
    """The app you're looking at first, then Chrome."""
    pids = []
    front = ax(AXUIElementCreateSystemWide(), "AXFocusedApplication")
    if front is not None:
        err, pid = AXUIElementGetPid(front, None)
        if err == 0:
            pids.append(pid)
    for bundle_id in APPS_TO_CHECK:
        for app in NSRunningApplication.runningApplicationsWithBundleIdentifier_(bundle_id):
            pid = app.processIdentifier()
            if pid not in pids:
                pids.append(pid)
    return [(pid, AXUIElementCreateApplication(pid)) for pid in pids]


_woken = set()
def wake_up(pid, app_el):
    """Ask Chrome to share the web page's buttons with macOS.
    Returns True the first time for this app."""
    for attr in ("AXManualAccessibility", "AXEnhancedUserInterface"):
        try:
            AXUIElementSetAttributeValue(app_el, attr, True)
        except Exception:
            pass
    if pid in _woken:
        return False
    _woken.add(pid)
    return True


def geometry(el):
    """(x, y, width, height) of an element on screen, or None if hidden."""
    pos, size = ax(el, "AXPosition"), ax(el, "AXSize")
    if pos is None or size is None:
        return None
    try:
        ok1, p = AXValueGetValue(pos, 1, None)    
        ok2, sz = AXValueGetValue(size, 2, None) 
    except Exception:
        return None
    if not (ok1 and ok2) or sz.width < 1 or sz.height < 1:
        return None
    return p.x, p.y, sz.width, sz.height


def real_click(btn, app_el):
    """Bring the app forward, click the middle of the button with the real mouse,
    then put the cursor back."""
    g = geometry(btn)
    if g is None:
        return AXUIElementPerformAction(btn, "AXPress") == 0
    try:
        AXUIElementSetAttributeValue(app_el, "AXFrontmost", True)
    except Exception:
        pass
    time.sleep(0.15)
    x, y = g[0] + g[2] / 2, g[1] + g[3] / 2
    old = CGEventGetLocation(CGEventCreate(None))
    for kind in (kCGEventMouseMoved, kCGEventLeftMouseDown, kCGEventLeftMouseUp):
        CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, kind, (x, y), kCGMouseButtonLeft))
        time.sleep(0.04)
    CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, kCGEventMouseMoved, old, kCGMouseButtonLeft))
    return True


def names_of(el):
    names = []
    for attr in ("AXDescription", "AXTitle"):
        v = ax(el, attr)
        if v:
            names.append(str(v).strip().lower())
    return names


def clickables_in(root, deadline, max_nodes=100000):
    """Yield (element, names) for buttons and links under root, bottom of the page first."""
    stack, seen = [root], 0
    while stack and seen < max_nodes and time.time() < deadline:
        el = stack.pop()
        seen += 1
        role = ax(el, "AXRole")
        if role in CLICKABLE_ROLES:
            yield el, names_of(el)
            continue
        if role in SKIP_ROLES:
            continue
        kids = ax(el, "AXChildren")
        if kids:
            stack.extend(kids)


def search_app(app_el, wanted):
    def matches(el, names):
        return any(n in wanted for n in names) and geometry(el) is not None

    #1) fast: search outward from whatever has keyboard focus
    el = ax(app_el, "AXFocusedUIElement")
    for level in range(12):
        el = ax(el, "AXParent")
        if el is None or ax(el, "AXRole") in ("AXWebArea", "AXWindow"):
            break
        if level < 1:
            continue
        for btn, names in clickables_in(el, time.time() + 1.0, max_nodes=800):
            if matches(btn, names):
                return btn

    #2) Search the whole front window.
    window = ax(app_el, "AXFocusedWindow")
    if window is not None:
        for btn, names in clickables_in(window, time.time() + FULL_SEARCH_LIMIT):
            if matches(btn, names):
                return btn
    return None


def find_button(labels):
    """Returns (button, app) or (None, None)."""
    wanted = {l.strip().lower() for l in labels}
    for attempt in range(2):
        just_woke = False
        for pid, app_el in candidate_apps():
            just_woke |= wake_up(pid, app_el)
            btn = search_app(app_el, wanted)
            if btn is not None:
                return btn, app_el
        if not just_woke:
            break
        time.sleep(2.5)   # first time only: give chrome time to look through buttons
    return None, None


def sound(name):
    subprocess.Popen(["afplay", f"/System/Library/Sounds/{name}.aiff"])


_busy = threading.Lock()
def press(labels):
    if not _busy.acquire(blocking=False):
        return
    try:
        t0 = time.time()
        btn, app_el = find_button(labels)
        took = time.time() - t0
        if btn is not None and real_click(btn, app_el):
            print(f"  -> clicked {labels[0]} ({took:.1f}s)")
            sound("Tink")
        else:
            print(f"  -> couldn't find {' / '.join(labels)} ({took:.1f}s)")
            sound("Basso")
    finally:
        _busy.release()


def ensure_accessibility():
    if AXIsProcessTrusted():
        return
    AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True})
    print("macOS needs to let Terminal press buttons for you:")
    print("  System Settings > Privacy & Security > Accessibility > turn on Terminal")
    print("Waiting for permission...")
    for _ in range(180):
        time.sleep(1)
        if AXIsProcessTrusted():
            print("Got it.\n")
            return
    sys.exit("Still no permission. Turn it on, then run again.")


# ---------- listening ----------

def main():
    import sounddevice as sd
    from vosk import Model, KaldiRecognizer, SetLogLevel

    ensure_accessibility()

    model_path = os.path.join(HERE, MODEL_FOLDER)
    if not os.path.isdir(model_path):
        sys.exit(f"Speech model not found at {model_path}")

    # Normalise: phrase -> list of button names. Longest phrases are checked first.
    commands = {p.lower().strip(): ([b] if isinstance(b, str) else list(b))
                for p, b in COMMANDS.items()}
    phrases = sorted(commands, key=len, reverse=True)

    SetLogLevel(-1)
    model = Model(model_path)

    find_word = getattr(model, "vosk_model_find_word", None) or getattr(model, "find_word", None)
    unknown = {w for p in phrases for w in p.split() if find_word and find_word(w) == -1}
    if unknown:
        print(f"Warning: the model doesn't know these words, so they'll never match: {', '.join(unknown)}\n")

    # Only listen for your phrases; everything else becomes nothing.
    rec = KaldiRecognizer(model, SAMPLE_RATE, json.dumps(phrases + ["[unk]"]))

    audio = queue.Queue()
    def on_audio(indata, frames, t, status):
        audio.put(bytes(indata))

    last_fire = 0.0
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4000,
                           dtype="int16", channels=1, callback=on_audio):
        print("Listening. Ctrl+C to quit.")
        for p in phrases:
            print(f"  '{p}'  ->  {' / '.join(commands[p])}")
        print()
        while True:
            if not rec.AcceptWaveform(audio.get()):
                continue
            text = json.loads(rec.Result()).get("text", "")
            if not text or text == "[unk]":
                continue
            phrase = next((p for p in phrases if p in text), None)
            if phrase and time.time() - last_fire > 1.5:
                last_fire = time.time()
                print(f"heard '{text}'")
                threading.Thread(target=press, args=(commands[phrase],), daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")