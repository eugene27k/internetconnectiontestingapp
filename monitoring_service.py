import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from subprocess import CalledProcessError, run
from typing import Callable, Dict, List, Optional, Protocol


@dataclass
class PingSample:
    timestamp: datetime
    target: str
    latency_ms: Optional[float]
    success: bool
    timeout: bool
    error: Optional[str] = None


@dataclass
class SpeedSample:
    timestamp: datetime
    direction: str  # "download" or "upload"
    size_bytes: int
    duration_seconds: float
    throughput_mbps: float
    error: Optional[str] = None


@dataclass
class OutageEvent:
    start: datetime
    end: Optional[datetime] = None
    failure_count: int = 0


def serialize_ping(sample: PingSample) -> Dict[str, object]:
    return {
        "timestamp": sample.timestamp.isoformat(),
        "target": sample.target,
        "latency_ms": sample.latency_ms,
        "success": sample.success,
        "timeout": sample.timeout,
        "error": sample.error,
    }


def serialize_speed(sample: SpeedSample) -> Dict[str, object]:
    return {
        "timestamp": sample.timestamp.isoformat(),
        "direction": sample.direction,
        "size_bytes": sample.size_bytes,
        "duration_seconds": sample.duration_seconds,
        "throughput_mbps": sample.throughput_mbps,
        "error": sample.error,
    }


def serialize_outage(outage: OutageEvent) -> Dict[str, object]:
    return {
        "start": outage.start.isoformat(),
        "end": outage.end.isoformat() if outage.end else None,
        "failure_count": outage.failure_count,
    }


class PlatformAdapter(Protocol):
    """Abstraction over platform-specific behaviors.

    Implementations encapsulate OS-specific details such as ping invocation and
    the storage location for persisted monitoring sessions. This allows swapping
    macOS defaults for Windows equivalents without changing the monitoring loop
    or data model.
    """

    def ping(self, target: str, timeout: float) -> Optional[float]:
        ...

    def sessions_directory(self) -> Path:
        ...


class MacPlatformAdapter:
    """Default adapter tailored for macOS systems."""

    def ping(self, target: str, timeout: float) -> Optional[float]:
        return default_ping_probe(target, timeout)

    def sessions_directory(self) -> Path:
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "internetconnectiontestingapp"
            / "sessions"
        )


class WindowsPlatformAdapter:
    """Default adapter tailored for Windows systems."""

    def ping(self, target: str, timeout: float) -> Optional[float]:
        return windows_ping_probe(target, timeout)

    def sessions_directory(self) -> Path:
        base_dir = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
        return Path(base_dir) / "internetconnectiontestingapp" / "sessions"


def default_platform_adapter() -> PlatformAdapter:
    if sys.platform.startswith("win"):
        return WindowsPlatformAdapter()
    return MacPlatformAdapter()


@dataclass
class SessionSummary:
    session_id: str
    start: datetime
    end: datetime
    duration_seconds: float
    uptime_ratio: float
    interruption_count: int
    interruption_durations: List[float]
    average_ping_ms: Optional[float]
    min_ping_ms: Optional[float]
    max_ping_ms: Optional[float]
    total_pings: int
    successful_pings: int
    failed_pings: int
    pings: List[PingSample]
    speed_samples: List[SpeedSample]
    outages: List[OutageEvent]

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.session_id,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "duration_seconds": self.duration_seconds,
            "uptime_ratio": self.uptime_ratio,
            "interruption_count": self.interruption_count,
            "interruption_durations": self.interruption_durations,
            "average_ping_ms": self.average_ping_ms,
            "min_ping_ms": self.min_ping_ms,
            "max_ping_ms": self.max_ping_ms,
            "total_pings": self.total_pings,
            "successful_pings": self.successful_pings,
            "failed_pings": self.failed_pings,
            "pings": [serialize_ping(p) for p in self.pings],
            "speed_samples": [serialize_speed(s) for s in self.speed_samples],
            "outages": [serialize_outage(o) for o in self.outages],
        }


class SessionRecorder:
    """Simple in-memory recorder for samples and events."""

    def __init__(self) -> None:
        self.pings: List[PingSample] = []
        self.speeds: List[SpeedSample] = []
        self.outages: List[OutageEvent] = []
        self._lock = threading.Lock()

    def record_ping(self, sample: PingSample) -> None:
        with self._lock:
            self.pings.append(sample)

    def record_speed(self, sample: SpeedSample) -> None:
        with self._lock:
            self.speeds.append(sample)

    def record_outage(self, outage: OutageEvent) -> None:
        with self._lock:
            self.outages.append(outage)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "pings": list(self.pings),
                "speeds": list(self.speeds),
                "outages": list(self.outages),
            }


class MonitoringService:
    """Monitors connectivity by periodically pinging and performing speed checks."""

    def __init__(
        self,
        target: str,
        ping_interval: float = 2.0,
        ping_timeout: float = 1.0,
        speed_interval: float = 60.0,
        speed_blob_url: Optional[str] = None,
        speed_blob_bytes: int = 512 * 1024,
        speed_test_duration: Optional[float] = None,
        consecutive_failure_threshold: int = 3,
        recorder: Optional[SessionRecorder] = None,
        ping_probe: Optional[Callable[[str, float], float]] = None,
        downloader: Optional[Callable[[str, int, float], SpeedSample]] = None,
        platform: Optional[PlatformAdapter] = None,
    ) -> None:
        self.target = target
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.speed_interval = speed_interval
        self.speed_blob_url = speed_blob_url
        self.speed_blob_bytes = speed_blob_bytes
        self.speed_test_duration = speed_test_duration
        self.consecutive_failure_threshold = max(1, consecutive_failure_threshold)
        self.recorder = recorder or SessionRecorder()
        self.platform = platform or default_platform_adapter()
        self.ping_probe = ping_probe or self.platform.ping
        self.downloader = downloader or default_downloader

        self._stop_event = threading.Event()
        self._ping_thread: Optional[threading.Thread] = None
        self._speed_thread: Optional[threading.Thread] = None

        self.total_pings = 0
        self.success_pings = 0
        self.failed_pings = 0
        self._consecutive_failures = 0
        self._current_outage: Optional[OutageEvent] = None
        self._failure_streak_start: Optional[datetime] = None
        self.session_started_at: Optional[datetime] = None

    def start(self) -> None:
        if self._ping_thread and self._ping_thread.is_alive():
            return
        self._stop_event.clear()
        if self.session_started_at is None:
            self.session_started_at = datetime.utcnow()
        self._ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
        self._speed_thread = threading.Thread(target=self._speed_loop, daemon=True)
        self._ping_thread.start()
        self._speed_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._ping_thread:
            self._ping_thread.join()
        if self._speed_thread:
            self._speed_thread.join()
        self._close_active_outage()
        self._persist_session()

    def _ping_loop(self) -> None:
        while not self._stop_event.is_set():
            loop_start = time.monotonic()
            sample_time = datetime.utcnow()
            success = False
            timeout = False
            latency_ms: Optional[float] = None
            error: Optional[str] = None
            try:
                latency_ms = self.ping_probe(self.target, self.ping_timeout)
                success = latency_ms is not None
            except TimeoutError:
                timeout = True
                success = False
                error = "timeout"
            except Exception as exc:  # pragma: no cover - defensive logging
                success = False
                error = str(exc)

            self.total_pings += 1
            if success:
                self.success_pings += 1
                self._consecutive_failures = 0
                self._failure_streak_start = None
                if self._current_outage:
                    self._current_outage.end = sample_time
                    self.recorder.record_outage(self._current_outage)
                    self._current_outage = None
            else:
                self.failed_pings += 1
                self._consecutive_failures += 1
                if self._failure_streak_start is None:
                    self._failure_streak_start = sample_time
                if (
                    not self._current_outage
                    and self._consecutive_failures >= self.consecutive_failure_threshold
                ):
                    outage_start = self._failure_streak_start or sample_time
                    self._current_outage = OutageEvent(
                        start=outage_start,
                        failure_count=self._consecutive_failures,
                    )
                elif self._current_outage:
                    self._current_outage.failure_count = self._consecutive_failures

            self.recorder.record_ping(
                PingSample(
                    timestamp=sample_time,
                    target=self.target,
                    latency_ms=latency_ms,
                    success=success,
                    timeout=timeout,
                    error=error,
                )
            )

            elapsed = time.monotonic() - loop_start
            sleep_for = max(self.ping_interval - elapsed, 0.01)
            self._stop_event.wait(sleep_for)

    def _speed_loop(self) -> None:
        # run an initial speed check
        self._run_speed_sample()
        while not self._stop_event.wait(self.speed_interval):
            self._run_speed_sample()

    def _run_speed_sample(self) -> None:
        if not self.speed_blob_url:
            return
        sample_time = datetime.utcnow()
        try:
            if self.speed_test_duration and self.speed_test_duration > 0:
                speed_sample = continuous_downloader(
                    self.speed_blob_url,
                    self.speed_test_duration,
                    self.ping_timeout,
                )
            else:
                speed_sample = self.downloader(self.speed_blob_url, self.speed_blob_bytes, self.ping_timeout)
        except Exception as exc:  # pragma: no cover - defensive logging
            speed_sample = SpeedSample(
                timestamp=sample_time,
                direction="download",
                size_bytes=self.speed_blob_bytes,
                duration_seconds=0.0,
                throughput_mbps=0.0,
                error=str(exc),
            )
        else:
            speed_sample.timestamp = sample_time
        self.recorder.record_speed(speed_sample)

    def _close_active_outage(self) -> None:
        if self._current_outage:
            self._current_outage.end = datetime.utcnow()
            self.recorder.record_outage(self._current_outage)
            self._current_outage = None

    def _persist_session(self) -> None:
        if not self.session_started_at:
            return

        end_time = datetime.utcnow()
        snapshot = self.recorder.snapshot()
        pings: List[PingSample] = snapshot["pings"]
        speeds: List[SpeedSample] = snapshot["speeds"]
        outages: List[OutageEvent] = snapshot["outages"]

        successful_latencies = [p.latency_ms for p in pings if p.success and p.latency_ms is not None]
        average_ping = sum(successful_latencies) / len(successful_latencies) if successful_latencies else None
        min_ping = min(successful_latencies) if successful_latencies else None
        max_ping = max(successful_latencies) if successful_latencies else None

        duration_seconds = max((end_time - self.session_started_at).total_seconds(), 0.0)
        uptime_ratio = (self.success_pings / self.total_pings) if self.total_pings else 0.0
        interruption_durations: List[float] = []
        for outage in outages:
            if outage.end:
                interruption_durations.append((outage.end - outage.start).total_seconds())

        session = SessionSummary(
            session_id=self._session_id(),
            start=self.session_started_at,
            end=end_time,
            duration_seconds=duration_seconds,
            uptime_ratio=uptime_ratio,
            interruption_count=len(outages),
            interruption_durations=interruption_durations,
            average_ping_ms=average_ping,
            min_ping_ms=min_ping,
            max_ping_ms=max_ping,
            total_pings=self.total_pings,
            successful_pings=self.success_pings,
            failed_pings=self.failed_pings,
            pings=pings,
            speed_samples=speeds,
            outages=outages,
        )

        sessions_dir = self._sessions_directory()
        sessions_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": session.to_dict(),
            "summary_text": self._format_summary_text(session),
        }
        session_file = sessions_dir / f"{session.session_id}.json"
        session_file.write_text(json.dumps(payload, indent=2))
        self._update_index(session, session_file)

    def _sessions_directory(self) -> Path:
        """Return the platform-specific storage directory for session files."""

        return self.platform.sessions_directory()

    def _session_id(self) -> str:
        started = self.session_started_at or datetime.utcnow()
        return started.strftime("%Y%m%dT%H%M%SZ")

    def _update_index(self, session: SessionSummary, session_file: Path) -> None:
        index_file = session_file.parent / "index.json"
        index: Dict[str, Dict[str, object]] = {}
        if index_file.exists():
            try:
                index = json.loads(index_file.read_text())
            except json.JSONDecodeError:
                index = {}
        index[session.session_id] = {
            "file": session_file.name,
            "start": session.start.isoformat(),
            "end": session.end.isoformat(),
            "duration_seconds": session.duration_seconds,
            "uptime_ratio": session.uptime_ratio,
        }
        index_file.write_text(json.dumps(index, indent=2))

    @staticmethod
    def _format_summary_text(session: SessionSummary) -> str:
        uptime_percent = round(session.uptime_ratio * 100, 2)
        total_downtime = round(sum(session.interruption_durations), 2) if session.interruption_durations else 0.0
        lines = [
            f"Session {session.session_id}",
            f"Start: {session.start.isoformat()}",
            f"End: {session.end.isoformat()}",
            f"Duration: {session.duration_seconds:.2f}s",
            f"Uptime: {uptime_percent}% ({session.successful_pings}/{session.total_pings} successful pings)",
            f"Downtime events: {session.interruption_count} (total {total_downtime}s)",
            "Ping latency (ms): "
            + (
                f"avg {session.average_ping_ms:.2f}, min {session.min_ping_ms:.2f}, max {session.max_ping_ms:.2f}"
                if session.average_ping_ms is not None
                else "no successful pings"
            ),
            f"Speed samples: {len(session.speed_samples)}",
        ]
        return "\n".join(lines)


def default_ping_probe(target: str, timeout: float) -> Optional[float]:
    """Send a single ping and return latency in milliseconds or None on failure."""
    try:
        completed = run(
            ["ping", "-n", "-c", "1", "-W", str(max(1, int(timeout))), target],
            capture_output=True,
            text=True,
            timeout=timeout + 0.5,
            check=False,
        )
    except CalledProcessError:
        return None
    except Exception:
        return None

    if completed.returncode != 0:
        return None

    match = re.search(r"time=([0-9.]+) ms", completed.stdout)
    if not match:
        return None
    return float(match.group(1))


def windows_ping_probe(target: str, timeout: float) -> Optional[float]:
    """Send a single ping on Windows and return latency in milliseconds or None."""
    timeout_ms = max(1, int(timeout * 1000))
    try:
        completed = run(
            ["ping", "-n", "1", "-w", str(timeout_ms), target],
            capture_output=True,
            text=True,
            timeout=timeout + 1.0,
            check=False,
        )
    except CalledProcessError:
        return None
    except Exception:
        return None

    if completed.returncode != 0:
        return None

    match = re.search(r"time[=<]\s*([0-9]+)ms", completed.stdout)
    if not match:
        return None
    return float(match.group(1))


def default_downloader(url: str, expected_bytes: int, timeout: float) -> SpeedSample:
    import urllib.request

    start = time.monotonic()
    with urllib.request.urlopen(url, timeout=timeout) as response:
        data = response.read(expected_bytes)
    duration = max(time.monotonic() - start, 1e-6)
    throughput_mbps = (len(data) * 8) / (duration * 1_000_000)
    return SpeedSample(
        timestamp=datetime.utcnow(),
        direction="download",
        size_bytes=len(data),
        duration_seconds=duration,
        throughput_mbps=throughput_mbps,
    )


def continuous_downloader(url: str, duration_seconds: float, timeout: float) -> SpeedSample:
    import urllib.request

    duration_seconds = max(duration_seconds, 0.1)
    start = time.monotonic()
    bytes_read = 0
    with urllib.request.urlopen(url, timeout=timeout) as response:
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            bytes_read += len(chunk)
            if time.monotonic() - start >= duration_seconds:
                break
    duration = max(time.monotonic() - start, 1e-6)
    throughput_mbps = (bytes_read * 8) / (duration * 1_000_000)
    return SpeedSample(
        timestamp=datetime.utcnow(),
        direction="download",
        size_bytes=bytes_read,
        duration_seconds=duration,
        throughput_mbps=throughput_mbps,
    )
