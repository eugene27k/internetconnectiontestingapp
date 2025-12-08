import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from subprocess import CalledProcessError, run
from typing import Callable, List, Optional


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
        consecutive_failure_threshold: int = 3,
        recorder: Optional[SessionRecorder] = None,
        ping_probe: Optional[Callable[[str, float], float]] = None,
        downloader: Optional[Callable[[str, int, float], SpeedSample]] = None,
    ) -> None:
        self.target = target
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.speed_interval = speed_interval
        self.speed_blob_url = speed_blob_url
        self.speed_blob_bytes = speed_blob_bytes
        self.consecutive_failure_threshold = max(1, consecutive_failure_threshold)
        self.recorder = recorder or SessionRecorder()
        self.ping_probe = ping_probe or default_ping_probe
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

    def start(self) -> None:
        if self._ping_thread and self._ping_thread.is_alive():
            return
        self._stop_event.clear()
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
