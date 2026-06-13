"""
Power Monitor for Jarvis Voice Engine
Watches AC/battery state and triggers STT device switching automatically.
"""

import threading
import logging
import psutil

logger = logging.getLogger("PowerMonitor")

# Model fallback ladder: if a model fails on CPU, try the next smaller one
MODEL_FALLBACK_LADDER = [
    "large-v3",
    "medium.en",
    "small.en",
    "base.en",
    "tiny.en",
]


def get_power_state():
    """Returns (plugged_in: bool, battery_percent: int|None)"""
    battery = psutil.sensors_battery()
    if battery is None:
        # Desktop PC — always treat as plugged in
        return True, None
    return battery.power_plugged, int(battery.percent)


def get_optimal_device(plugged_in):
    """Pick CUDA when plugged in, CPU when on battery."""
    import torch
    if plugged_in and torch.cuda.is_available():
        return "cuda"
    return "cpu"


def get_compute_type(device):
    """Pick the best compute type for the given device."""
    if device == "cuda":
        return "float16"
    return "int8"


def find_fallback_model(current_model, device):
    """
    Try to find the best model that actually loads on the given device.
    Returns (model_name, compute_type) or None if nothing works.
    """
    import faster_whisper

    # Build candidate list: start from current model's tier and go smaller
    try:
        start_idx = MODEL_FALLBACK_LADDER.index(current_model)
    except ValueError:
        start_idx = 0  # Unknown model, start from the top

    compute = get_compute_type(device)

    for model_name in MODEL_FALLBACK_LADDER[start_idx:]:
        try:
            logger.info(f"[PowerMonitor] Probing model '{model_name}' on {device}/{compute}...")
            _test = faster_whisper.WhisperModel(model_name, device=device, compute_type=compute)
            del _test
            logger.info(f"[PowerMonitor] ✓ Model '{model_name}' loaded successfully on {device}.")
            return model_name, compute
        except Exception as e:
            logger.warning(f"[PowerMonitor] ✗ Model '{model_name}' failed on {device}/{compute}: {e}")
            continue

    # Absolute last resort: tiny.en on CPU with float32
    try:
        logger.info("[PowerMonitor] Last resort: tiny.en on CPU/float32...")
        _test = faster_whisper.WhisperModel("tiny.en", device="cpu", compute_type="float32")
        del _test
        return "tiny.en", "float32"
    except Exception:
        return None


class PowerMonitor:
    """
    Background thread that polls battery state every N seconds.
    When a change is detected (plugged in <-> battery), it calls the
    provided callback to hot-swap the STT model.
    """

    def __init__(self, on_power_change_callback, poll_interval=15):
        """
        Args:
            on_power_change_callback: async-safe callable(device, model, compute_type)
                                      called when power state changes.
            poll_interval: seconds between checks.
        """
        self.callback = on_power_change_callback
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread = None

        # Snapshot the initial state
        plugged, percent = get_power_state()
        self.last_plugged = plugged
        logger.info(
            f"[PowerMonitor] Initialized — plugged_in={plugged}, "
            f"battery={'N/A (desktop)' if percent is None else f'{percent}%'}"
        )

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="PowerMonitor")
        self._thread.start()
        logger.info("[PowerMonitor] Background polling started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[PowerMonitor] Stopped.")

    def _poll_loop(self):
        while not self._stop_event.is_set():
            self._stop_event.wait(self.poll_interval)
            if self._stop_event.is_set():
                break

            plugged, percent = get_power_state()

            if plugged != self.last_plugged:
                old_state = "AC" if self.last_plugged else "Battery"
                new_state = "AC" if plugged else "Battery"
                logger.info(
                    f"[PowerMonitor] ⚡ Power changed: {old_state} → {new_state} "
                    f"(battery={'N/A' if percent is None else f'{percent}%'})"
                )
                self.last_plugged = plugged

                new_device = get_optimal_device(plugged)
                new_compute = get_compute_type(new_device)
                logger.info(f"[PowerMonitor] Requesting STT switch → device={new_device}, compute={new_compute}")

                try:
                    self.callback(new_device, new_compute)
                except Exception as e:
                    logger.error(f"[PowerMonitor] Callback failed: {e}")
