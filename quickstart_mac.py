"""One-command Mac quickstart for the monitoring service.

This script starts the monitor with reasonable defaults for home connections,
lets it run for a short window, then prints where session JSON is saved.
"""

import time

from monitoring_service import MonitoringService


def main() -> None:
    monitor = MonitoringService(
        target="1.1.1.1",  # Cloudflare DNS is an always-on target
        ping_interval=1.0,
        ping_timeout=1.0,
        speed_interval=30.0,
        speed_blob_url="https://speed.cloudflare.com/__down?bytes=524288",
    )

    print("Starting monitor. Press Ctrl+C to stop early.\n")
    monitor.start()
    try:
        time.sleep(45)
    except KeyboardInterrupt:
        print("\nStopping early...")
    finally:
        monitor.stop()

    snapshot = monitor.recorder.snapshot()
    ping_count = len(snapshot["pings"])
    speed_count = len(snapshot["speeds"])
    outage_count = len(snapshot["outages"])

    sessions_dir = monitor.platform.sessions_directory()
    print(
        f"Finished. Pings: {ping_count}, speed samples: {speed_count}, outages: {outage_count}.\n"
        f"Session JSON saved under: {sessions_dir}\n"
        "Open the newest .json file there to inspect the run."
    )


if __name__ == "__main__":
    main()
