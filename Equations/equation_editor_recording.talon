# Equation Editor recording commands
mode: user.math_recording
-
settings():
    # Leave time for multiword editor commands while recording is active.
    speech.timeout = 1.200

# Explicit command in this mode so the dictation catchall cannot absorb it.
(open | show) equation editor:
    user.math_show_saved_equations()

open editor:
    user.math_show_saved_equations()

(done | finish | end) equation:
    user.math_recording_finish()

cancel equation:
    user.math_recording_cancel()

# Undo the last spoken chunk while dictating
(scratch | undo) chunk:
    user.math_recording_scratch_last()

<user.math_phrase>:
    user.math_recording_append(math_phrase)
