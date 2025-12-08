# internetconnectiontestingapp

A lightweight monitoring service that periodically pings a target host, performs spot speed checks, and records samples and outage events in memory.

## Features
- Configurable ping interval and timeout with rolling uptime/failure counts.
- Outage detection triggered by consecutive ping failures; records start/end timestamps.
- Periodic speed sampling via HTTP download (and optional custom upload/download probes) with throughput calculations.
- Thread-safe in-memory `SessionRecorder` for ping, speed, and outage history snapshots.

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
