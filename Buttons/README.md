# Voice Trigger

## ABOUT

This is meant to click buttons for you in chrome, based on specific phrases that you say. Currently, it's a python script that you run in your terminal, though in the future, it may be devleoped further.

General overview:

1. **Listening:** [Vosk](https://alphacephei.com/vosk/) listens to your microphone and recognizes the phrases that you input (more on that in a bit). Everything else said is ignored, the script runs in the background and can be stopped at any point. Recognition runs entirely on your Mac, so no audio leaves your computer. As a side note, sometimes vosk will recognize similar phrases, so make sure to make phrases unique
2. **Finding the button:** when it hears a phrase, it uses macOS's accessibility system (the same one screen readers use) to find the matching button in your browser (usually by aria-label, which is what you should look for to inpu)
3. **Clicking:** it brings browser (whatever you configure) to the front, clicks the button with a real mouse click, and puts your cursor back where it was. You'll hear distinctive sounds for both working and not working (like a 'ting!' if work, and more like 'bonk' if no)

Phrases and buttons are set in the `COMMANDS` table at the top of `listener.py`:

```python
COMMANDS = {
    "PHRASE TO SAY":        ["BUTTONS TO SEARCH FOR", "OTHER BUTTON TO SEARCH FOR"],
}
```

Here, "PHRASE TO SAY" is the phrase you say to activate, and the list is a list of button names (essentially aria-labels) that will be searched for. Usually, these aria-labels correspond to hovering over a button. If this doesn't work, though, use inspect element and cmd + f the words you see on hover, then look for the aria-label in that particular element

**Requirements:** a Mac and some browser

## DEPENDENCIES

**Python 3.9 or newer.** On a Mac this comes with Apple's developer tools, which macOS offers to install the first time you run `python3`.

**Python libraries**, installed with pip:

| Library | What it's used for |
| --- | --- |
| `vosk` | Offline speech recognition of your phrases |
| `sounddevice` | Reading audio from the microphone |
| `pyobjc-framework-ApplicationServices` | Finding buttons through macOS accessibility (also provides `AppKit`, used to find Chrome) |
| `pyobjc-framework-Quartz` | Performing mouse click |

**Speech model:** `vosk-model-small-en-us-0.15` (about 40 MB), placed in the same folder as `listener.py`.

**macOS permissions** for Terminal (or whichever app you run the script from):

- **Accessibility**, so it can find and click buttons
- **Microphone**, so it can hear you

The script also uses Python's standard library (`json`, `os`, `queue`, `subprocess`, `sys`, `threading`, `time`) and macOS's built-in `afplay` for the sounds.

## INSTALLATION INSTRUCTIONS

### One-time setup

1. **Folder setup**
   - Create a `voice-trigger` folder inside Downloads (or wherever you choose, though KEEP IN MIND, if you put it somewhere else, change the `cd` path below to match).
   - Add `listener.py` to the folder, either by:
     - downloading from this GitHub and moving it into `voice-trigger`, **or**
     - creating a file named `listener.py` and pasting listener.py into this file
   - Open **Terminal** and run the following commands to go to the folder and download the speech model (about 40 MB):
```
     cd ~/Downloads/voice-trigger
     curl -L -o model.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
     unzip model.zip && rm model.zip
```
   - The folder should now look like this. DO NOT rename the model folder:
```
     voice-trigger/
       listener.py
       vosk-model-small-en-us-0.15/
```

2. **Open Terminal** & navigate to folder (if not already there), if in downloads like above, should be something like the following, otherwise route path accordingly:
   ```
   cd ~/Downloads/voice-trigger
   ```

3. **Create a virtual environment and install the libraries:**
Note: This is just so that it isn't installed on your overall mac environment, won't affect anything else
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install vosk sounddevice pyobjc-framework-ApplicationServices pyobjc-framework-Quartz
   ```
   If a window asks to install developer tools, click **Install**, wait for it to finish, then run these commands again.

4. **Set your commands** Open `listener.py` in a text editor and edit the `COMMANDS` table near the top. Ensure phrases are lowercase, and end in commas to preserve structure

5. **Run it and grant permissions:**
   ```
   python listener.py
   ```
   - When prompted, go to **System Settings → Privacy & Security → Accessibility** and turn on **Terminal**. The script waits until you do.
   - Click **Allow** when Terminal asks to use the microphone.

### Every time

1. Start the listener:
   ```
   cd ~/Downloads/voice-trigger
   source .venv/bin/activate
   python listener.py
   ```
   Terminal lists every phrase and the button it clicks.
2. Open ChatGPT (or your page) in Chrome and click into the page once.
3. Say a phrase, then pause briefly.
4. Press **Ctrl+C** in Terminal to quit.

### Finding a button's name

Right-click the button in Chrome, choose **Inspect**, and look for `aria-label="..."` on the highlighted `<button>`. Put that text in the `COMMANDS` table. It must be a button or link that's visible on screen.

### Troubleshooting

| Problem | Fix |
| --- | --- |
| `No module named ...` | The environment isn't active. Run `source .venv/bin/activate`, and use `python`, not `python3`. |
| "Couldn't find" (bonk sound) | Check the button's name with Inspect and that it's visible. The first try after opening Chrome can miss while Chrome builds its button list, so try once more. |
| "The model doesn't know these words" | Change that phrase to more common words. |
| Phrase not detected | Pause briefly after speaking, and check that your mic is the system default input. |
| Your stop phrase appears in the dictated text | ChatGPT hears it too; delete it before sending. |

**Privacy note:** the Accessibility permission lets Terminal control your computer. You can turn it off in the same settings when you're not using Voice Trigger.