# ABOUT
This guide walks you through setting up Ollama and the custom equation editor (In its early stages).

# INSTALLATION INSTRUCTIONS
## Step 1: Install unicodeit in talon folder
```bash
~/.talon/.venv/bin/pip install unicodeit

~/.talon/.venv/bin/python -m pip show unicodeit
```

## Step 2: Install Ollama and Qwen 3
1. Go to the [Ollama Download Page](https://ollama.com/download/mac).
2. Download the Ollama installer manually then set up the app
3. Open up the terminal and type
    ```
    Ollama pull qwen3
    ```
4. This will install Qwen3 for Ollama

## Step 3: Set up the scripts

1. Download the Scripts from the questions folder
2. Make a new folder in ~/.talon/user
   * Call the folder something like, math_equations
3. Drag all the scripts into the folder 

## Step 4: Test
1. Make sure everything is saved
2. Have Talon up and running
3. Say "Start Equation" and a window should appear. 