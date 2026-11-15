# Equation Editor commands
settings():
    speech.timeout = 1.200

# Edit the last equation or prose item in-place.
(edit | change | fix) last item:
    user.equation_edit_start()

(edit | change | fix) last item <user.math_phrase>:
    user.equation_edit_last(math_phrase)

(open | show) equation editor:
    user.math_show_saved_equations()

equation editor:
    user.math_show_saved_equations()

confirm equation edit:
    user.equation_edit_by_label_confirm()

(show | open) equations:
    user.math_show_saved_equations()

close equation editor:
    user.math_hud_hide()

# Append more math or text to the latest item in place.
append to last item <user.math_phrase>:
    user.equation_append_last(math_phrase)

(revert | undo) last item:
    user.equation_revert()

# Start recording, or finish the current segment and begin another one.
(start | begin) (equation | equations):
    user.math_recording_start()

(new | next) (equation | equations):
    user.math_recording_new()

(paste all | paste all equations):
    user.math_paste_all_equations()

# The status window wraps long dictation and can be hidden on request.
(hide | close) math (ui | window | status):
    user.math_hud_hide()

(show | open) saved equations:
    user.math_show_saved_equations()

clear equation memory:
    user.math_scribe_context_clear()
