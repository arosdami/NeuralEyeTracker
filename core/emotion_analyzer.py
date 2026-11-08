# core/emotion_analyzer.py
# Érzelmi reakció mérés pupilla dinamikából

import math
from collections import deque
from typing import List, Optional, Tuple


class EmotionAnalyzer:
    """
    Érzelmi / arousal reakció mérés.

    A pupilla átmérőjének változásából következtet:
      - Arousal (izgalmi szint)
      - Kognitív terhelés
      - Stressz válasz
    """

    def __init__(self, baseline_size: float = 1.0):
        self.baseline = baseline_size
        self.pupil_history: deque = deque(maxlen=300)
        self.blink_events: List[float] = []
        self.fixation_events: List[Tuple[float, float, float, float]] = []

    # ==========================================================
    def reset_baseline(self, baseline_size: float):
        self.baseline = baseline_size
        self.pupil_history.clear()
        self.blink_events.clear()
        self.fixation_events.clear()

    # ==========================================================
    def add_pupil_sample(self, size: float, timestamp: float):
        """Új pupilla minta hozzáadása."""
        self.pupil_history.append((timestamp, size))

    def add_blink(self, timestamp: float):
        """Pislogás esemény rögzítése."""
        self.blink_events.append(timestamp)

    def add_fixation(self, x: float, y: float, duration_ms: float,
                     timestamp: float):
        """Fixációs esemény rögzítése."""
        self.fixation_events.append((x, y, duration_ms, timestamp))

    # ==========================================================
    def get_arousal_index(self) -> float:
        """
        Arousal index: mennyivel tér el az aktuális pupilla
        a baseline-tól.

        0.0 = nincs reakció
        1.0 = 100%-os tágulás
        """
        if not self.pupil_history or self.baseline <= 0:
            return 0.0

        # Utolsó 30 minta átlaga
        recent = [s for _, s in list(self.pupil_history)[-30:]]
        if not recent:
            return 0.0

        mean_recent = sum(recent) / len(recent)
        return max(0.0, (mean_recent - self.baseline) / self.baseline)

    # ==========================================================
    def get_pupil_variability(self) -> float:
        """
        Pupilla fluktuáció: a szórás / átlag.
        Magas érték = stressz, PTSD.
        """
        if len(self.pupil_history) < 10:
            return 0.0

        values = [s for _, s in self.pupil_history]
        mean = sum(values) / len(values)
        if mean <= 0:
            return 0.0

        var = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(var)
        return std / mean

    # ==========================================================
    def get_blink_rate(self, window_s: float = 10.0,
                       current_time: float = None) -> float:
        """
        Pislogási ráta (pislogás / perc) az utolsó N másodpercben.
        Magas = szorongás.
        """
        if not self.blink_events:
            return 0.0

        now = current_time or self.blink_events[-1]
        cutoff = now - window_s
        recent = [t for t in self.blink_events if t >= cutoff]
        return len(recent) * (60.0 / window_s)

    # ==========================================================
    def get_stress_score(self) -> float:
        """
        Összetett stressz pontszám (0-1).

        Összetevők:
          - Arousal index (40%)
          - Pupilla variabilitás (30%)
          - Pislogási ráta (30%)
        """
        arousal = min(1.0, self.get_arousal_index())
        variability = min(1.0, self.get_pupil_variability() * 5)
        blink_rate = min(1.0, self.get_blink_rate() / 30.0)

        return 0.4 * arousal + 0.3 * variability + 0.3 * blink_rate

    # ==========================================================
    def get_fixation_stats(self) -> dict:
        """Fixációs statisztikák."""
        if not self.fixation_events:
            return {
                "count": 0,
                "mean_duration_ms": 0.0,
                "max_duration_ms": 0.0,
                "total_time_ms": 0.0,
            }

        durations = [d for _, _, d, _ in self.fixation_events]
        return {
            "count": len(durations),
            "mean_duration_ms": sum(durations) / len(durations),
            "max_duration_ms": max(durations),
            "total_time_ms": sum(durations),
        }