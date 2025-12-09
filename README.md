# internetconnectiontestingapp

A lightweight monitoring service that periodically pings a target host, performs spot speed checks, and records samples and outage events in memory.

## SwiftUI companion app

`SwiftUIApp` holds a minimal iOS SwiftUI client with:
- Start/stop controls for running a local monitoring session.
- Live stats for current ping, most recent speed sample, and interruption count.
- A Sessions tab that reads saved session JSON logs from the app's Application Support/Sessions folder, shows summaries, and surfaces the raw JSON payloads.
- Settings for host, ping/speed intervals, outage threshold, and a toggle to disable speed tests to conserve bandwidth.

## Features
- Configurable ping interval and timeout with rolling uptime/failure counts.
- Outage detection triggered by consecutive ping failures; records start/end timestamps.
- Periodic speed sampling via HTTP download (and optional custom upload/download probes) with throughput calculations.
- Thread-safe in-memory `SessionRecorder` for ping, speed, and outage history snapshots.
- Self-contained probes that rely on built-in HTTP requests rather than external CLI tools.

## Usage
Create and start the monitor by providing a ping target and an optional download URL for speed sampling:

```python
from monitoring_service import MonitoringService

monitor = MonitoringService(
    target="1.1.1.1",
    ping_interval=2.0,
    ping_timeout=1.0,
    speed_interval=60.0,
    speed_blob_url="https://speed.cloudflare.com/__down?bytes=524288",
)
monitor.start()

# ... let it run ...

monitor.stop()
print(monitor.recorder.snapshot())
```

The monitor runs background threads: a frequent ping loop (e.g., every 1–2 seconds) and a speed loop that performs a download check at startup and on a configurable cadence.

## macOS quickstart (no DMG installer)
If you are new to development, follow these steps on a Mac to get a working run:

1. **Install Xcode Command Line Tools** (gives you `git` and `python3`):
   ```bash
   xcode-select --install
   ```
2. **Download the repo**. In Terminal, pick a folder (e.g., `~/Projects`) and clone:
   ```bash
   git clone https://github.com/your-account/internetconnectiontestingapp.git
   cd internetconnectiontestingapp
   ```
   Alternatively, you can download the GitHub ZIP, unzip it, and `cd` into the unzipped folder.
3. **Run the one-command monitor** (saves logs to `~/Library/Application Support/internetconnectiontestingapp/sessions`):
   ```bash
   python3 quickstart_mac.py
   ```
   The script pings `1.1.1.1` once per second, runs a quick download probe every 30 seconds, and stops after ~45 seconds. Press **Ctrl+C** to stop early. When it ends, it prints the folder containing the newest session JSON file you can open.
4. **Rerun with different targets/intervals** by editing the values near the top of `quickstart_mac.py`.

## Build a double-clickable macOS app + DMG
If you want a simple downloadable app instead of running Python from Terminal, you can package the Tk-based wrapper (`mac_app_main.py`) into a signed-but-unsigned `.app` and `.dmg` with [PyInstaller](https://pyinstaller.org/). Run these commands on macOS:

1. Install Python 3 (via Xcode CLT or python.org) and install PyInstaller:
   ```bash
   python3 -m pip install --upgrade pip pyinstaller
   ```
2. From the repo root, build the `.app` and DMG:
   ```bash
   ./scripts/build_mac_app.sh
   ```
3. The script produces:
   - `dist/InternetConnectionTester.app` — a double-clickable app that starts/stops the monitor.
   - `dist/InternetConnectionTester.dmg` — a mountable image you can share or move to another Mac.
4. When you open the DMG and drag the app to `/Applications`, macOS may warn that it’s from an unidentified developer. Right-click the app, choose **Open**, and confirm to run it. Session logs are saved to `~/Library/Application Support/internetconnectiontestingapp/sessions`.

> Note: This build is not notarized. For distribution outside your machine/team, use your Apple Developer ID to sign and notarize the `.app` or the DMG.

### Using the SwiftUI app in Xcode (iOS simulator or device)
The `SwiftUIApp` folder contains the views, models, and services for an iOS client; there is no `.xcodeproj` included. To try it:
1. Open Xcode → *File > New > Project…* → choose **App (iOS)** → name it `InternetConnectionTestingApp`.
2. When the project opens, delete the default `ContentView.swift` and `AppNameApp.swift` files.
3. Drag the contents of `SwiftUIApp/` from Finder into the Xcode Project Navigator, making sure “Copy items if needed” is checked.
4. Select your simulator or plugged-in iPhone and press **Run**. The app will read/write session JSON under its sandbox Application Support `Sessions` folder.

## iOS data storage
The SwiftUI client saves session logs under the app sandbox's Application Support directory, namespaced by the bundle identifier and a `Sessions` subfolder (e.g., `Application Support/<bundle-id>/Sessions`). This keeps the data alongside other app support files and away from user-visible Documents storage.
