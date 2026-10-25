# C:\Users\kaemy\AppData\Roaming\talon\user\qwen_equation.talon
settings():
    speech.timeout = 1.200

# Create a new equation
make equation <user.math_phrase>:
    user.qwen_make_equation(math_phrase, "normal")

make an equation <user.math_phrase>:
    user.qwen_make_equation(math_phrase, "normal")

make latex <user.math_phrase>:
    user.qwen_make_equation(math_phrase, "latex")

# Edit the last equation you just made in-place
(change | edit | fix) equation <user.math_phrase>:
    user.qwen_edit_last_equation(math_phrase)

# Append more math to the end of the last equation in-place
append equation <user.math_phrase>:
    user.qwen_append_last_equation(math_phrase)

# Undo the last edit and restore the prior version of the equation
(revert | u*[m]ndo) equation:
    user.qwen_revert_equation()

# Edit any older equation that you currently have highlighted with your mouse/keyboard
(change | edit) selected equation <user.math_phrase>:
    user.qwen_edit_selected_equation(math_phrase, "normal")

(change | edit) selected latex <user.math_phrase>:
    user.qwen_edit_selected_equation(math_phrase, "latex")

# Start multi-pause continuous recording mode
start equation:
    user.math_recording_start("normal")

start latex:
    user.math_recording_start("latex")