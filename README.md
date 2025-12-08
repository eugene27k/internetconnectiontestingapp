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

## iOS data storage
The SwiftUI client saves session logs under the app sandbox's Application Support directory, namespaced by the bundle identifier and a `Sessions` subfolder (e.g., `Application Support/<bundle-id>/Sessions`). This keeps the data alongside other app support files and away from user-visible Documents storage.
