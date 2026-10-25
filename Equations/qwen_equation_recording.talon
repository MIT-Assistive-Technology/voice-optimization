# C:\Users\kaemy\AppData\Roaming\talon\user\qwen_equation_recording.talon
mode: user.math_recording
-
settings():
    speech.timeout = 1.500

(done | finish | end) equation:
    user.math_recording_finish()

cancel equation:
    user.math_recording_cancel()

# Undo the last spoken chunk while still dictating a long equation
(scratch | undo) chunk:
    user.math_recording_scratch_last()

<user.math_phrase>:
    user.math_recording_append(math_phrase)