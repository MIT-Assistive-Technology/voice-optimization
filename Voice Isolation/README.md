# ABOUT
This guide walks you through setting up MetalVoice and BlackHole with Talon to acheive voice isolation.

# DEPENDENCIES
* **Mac with Apple Silicon** 
* **Homebrew** installed on your Mac.

# INSTALLATION INSTRUCTIONS
## Step 1: Install BlackHole 2ch (Virtual Audio Cable)
```bash
brew install blackhole-2ch
```

## Step 2: Install MetalVoice
1. Go to the [MetalVoice Releases Page](https://github.com/Ghostkwebb/MetalVoice/releases).
2. Download the latest `MetalVoice_<version>.zip` archive.
3. Extract the zip file and drag **`MetalVoice.app`** into your **Applications** folder.
4. **First Launch Security Notice:** Right-click `MetalVoice.app`, select **Open**, and confirm. *(If macOS blocks it, go to **System Settings > Privacy & Security** and click **Open Anyway**)*.

## Step 3: Configure the Audio Pipeline
Now, route your physical microphone through MetalVoice's AI filter and push the cleaned audio into BlackHole.

1. Launch **MetalVoice** from your Applications folder (look for the waveform icon in your menu bar).
2. Open settings/preferences and configure your audio devices:
   * **Input Device:** Set to your **Physical Microphone** (e.g., *MacBook Pro Microphone* or external desk mic).
   * **Output Device:** Set to **`BlackHole 2ch`**.
3. Toggle the AI noise suppression switch **ON**. 

## Step 4: Configure Talon
1. Open **Talon**.
2. Open your Talon audio settings (via the tray menu bar icon or your user config files).
3. Set your active microphone input device explicitly to **`BlackHole 2ch`**.