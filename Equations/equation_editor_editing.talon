mode: user.equation_editing
-
settings():
    # Allow a comfortable pause before and during a detailed correction.
    speech.timeout = 3.000

# Let the user open the editor while the edit dictation catchall is active.
(open | show) equation editor:
    user.math_show_saved_equations()

open editor:
    user.math_show_saved_equations()

cancel edit:
    user.equation_edit_cancel()

<user.math_phrase>:
    user.equation_edit_complete(math_phrase)
