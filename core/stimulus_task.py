# core/stimulus_task.py
# Dinamikus kategóriák – mappából olvassa fel
# + Stroop-teszt támogatás (Millour et al. 2026 alapján)
# + VAS (észlelt stressz) támogatás
# + Robusztus protokoll-építő kis képszámhoz és üres mappákhoz

import os
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

from core.stroop_task import STROOP_COLORS, StroopTask


# ==========================================================
# TRIAL
# ==========================================================
@dataclass
class Trial:
    index: int
    category: str
    image_path: str
    image_id: str
    t_start: float = 0.0
    t_end: float = 0.0
    pupil_baseline: float = 0.0
    pupil_max: float = 0.0
    pupil_mean: float = 0.0
    pupil_median: float = 0.0
    pupil_min: float = 0.0
    pupil_std: float = 0.0
    pupil_samples: List[float] = field(default_factory=list)
    first_fixation_x: float = -1.0
    first_fixation_y: float = -1.0
    first_fixation_latency_ms: float = 0.0
    total_fixation_time_ms: float = 0.0
    detection_confidence: float = 0.0
    was_blinking: bool = False
    arousal_index: float = 0.0
    reaction_time_ms: float = 0.0

    # Stroop-specifikus
    is_stroop: bool = False
    stroop_word: str = ""
    stroop_color: str = ""
    stroop_congruent: bool = False
    stroop_correct: Optional[bool] = None
    stroop_response_ms: float = 0.0

    # VAS (észlelt stressz)
    vas_before: float = -1.0
    vas_after: float = -1.0


# ==========================================================
# EXPERIMENT RESULT
# ==========================================================
@dataclass
class ExperimentResult:
    subject_id: str = "unknown"
    subject_note: str = ""
    session_start: float = 0.0
    session_end: float = 0.0
    trials: List[Trial] = field(default_factory=list)
    baseline_pupil_size: float = 0.0
    mean_pupil_size: float = 0.0
    median_pupil_size: float = 0.0
    total_baseline_samples: int = 0
    total_blinks: int = 0
    arousal_by_category: Dict[str, float] = field(default_factory=dict)
    arousal_std_by_category: Dict[str, float] = field(default_factory=dict)
    fixation_time_by_category: Dict[str, float] = field(default_factory=dict)
    reaction_time_by_category: Dict[str, float] = field(default_factory=dict)
    negative_arousal: float = 0.0
    positive_arousal: float = 0.0
    emotional_balance: float = 0.0

    # VAS (észlelt stressz)
    vas_before: float = -1.0
    vas_after: float = -1.0
    vas_delta: float = 0.0

    # Stroop-eredmények
    stroop_accuracy: float = 0.0
    stroop_mean_rt_ms: float = 0.0
    stroop_congruent_rt_ms: float = 0.0
    stroop_incongruent_rt_ms: float = 0.0
    stroop_interference_ms: float = 0.0
    stroop_n_correct: int = 0
    stroop_n_total: int = 0


# ==========================================================
# STIMULUS TASK
# ==========================================================
class StimulusTask:
    """
    Ingerkísérlet – dinamikus kategóriákkal.
    A kategóriák a stimuli mappából olvasódnak fel.
    """

    def __init__(self, image_dir: str = "stimuli"):
        self.image_dir = image_dir
        self.trials: List[Trial] = []
        self.categories: Dict[str, List[str]] = {}
        self._load_images()

    def _load_images(self):
        """Minden alkategóriát felismer a stimuli mappában."""
        self.categories = {}

        if not os.path.isdir(self.image_dir):
            return

        for cat_name in sorted(os.listdir(self.image_dir)):
            cat_dir = os.path.join(self.image_dir, cat_name)
            if not os.path.isdir(cat_dir):
                continue

            files = []
            for fname in sorted(os.listdir(cat_dir)):
                if fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                    files.append(os.path.join(cat_dir, fname))

            self.categories[cat_name] = files

        for cat, files in self.categories.items():
            print(f"[STIMULUS] {cat}: {len(files)} kép")

    def reload(self):
        """Újratölti a kategóriákat."""
        self._load_images()

    def get_category_names(self) -> List[str]:
        return list(self.categories.keys())

    def get_category_count(self, cat: str) -> int:
        return len(self.categories.get(cat, []))

    def has_images(self, required: List[str] = None) -> bool:
        if not required:
            return any(len(files) > 0 for files in self.categories.values())
        for cat in required:
            if len(self.categories.get(cat, [])) == 0:
                return False
        return True

    def build_protocol(
        self,
        category_counts: Dict[str, int],
        randomize: bool = True,
    ) -> List[Trial]:
        """Kategória-számok alapján összeállítja a protokollt."""
        protocol: List[Trial] = []
        idx = 0

        def pick(cat: str, n: int) -> List[str]:
            if n <= 0:
                return []
            files = self.categories.get(cat, [])
            if not files:
                return []
            if len(files) >= n:
                return random.sample(files, n)
            return random.choices(files, k=n)

        # 1. Kiválogatjuk azokat a kategóriákat, amikben ténylegesen van képfájl
        valid_requested = [
            cat for cat, count in category_counts.items()
            if count > 0 and len(self.categories.get(cat, [])) > 0
        ]

        # Ha a felületről nem jött érvényes kérés, fallback: minden mappa, ahol van kép
        if not valid_requested:
            valid_requested = [
                cat for cat, files in self.categories.items() if len(files) > 0
            ]

        if not valid_requested:
            self.trials = []
            return []

        # 2. Baseline meghatározása
        first_cat = "neutral" if ("neutral" in valid_requested and len(self.categories.get("neutral", [])) > 0) else valid_requested[0]
        num_avail = len(self.categories.get(first_cat, []))
        baseline_count = min(3, max(1, num_avail))

        for path in pick(first_cat, baseline_count):
            protocol.append(Trial(
                index=idx,
                category=first_cat,
                image_path=path,
                image_id=os.path.basename(path),
            ))
            idx += 1

        # 3. Kevert ingerpróbák hozzáadása
        mixed = []
        for cat in valid_requested:
            # Ha szerepel a kértek közt, az ottani darabszámot vesszük, egyébként max a meglévő képek számát
            n = category_counts.get(cat, len(self.categories.get(cat, [])))
            n = min(n, len(self.categories.get(cat, [])))
            if n <= 0:
                n = 1
            for p in pick(cat, n):
                mixed.append((cat, p))

        if randomize:
            random.shuffle(mixed)

        for cat, path in mixed:
            protocol.append(Trial(
                index=idx,
                category=cat,
                image_path=path,
                image_id=os.path.basename(path),
            ))
            idx += 1

        self.trials = protocol
        return protocol

    def build_stroop_protocol(
        self,
        n_trials: int = 180,
        congruent_ratio: float = 0.5,
    ) -> List[Trial]:
        """Stroop-teszt protokoll összeállítása."""
        stroop = StroopTask(n_trials=n_trials, congruent_ratio=congruent_ratio)
        protocol: List[Trial] = []
        for i, (word, color, is_cong) in enumerate(stroop.trials):
            protocol.append(Trial(
                index=i,
                category="stroop",
                image_path="",
                image_id=f"stroop_{i:03d}",
                is_stroop=True,
                stroop_word=word,
                stroop_color=color,
                stroop_congruent=is_cong,
            ))
        self.trials = protocol
        return protocol

    def analyze(
        self,
        subject_id: str = "unknown",
        subject_note: str = "",
        session_start: float = 0.0,
        session_end: float = 0.0,
        baseline_pupil: float = 1.0,
        total_blinks: int = 0,
        vas_before: float = -1.0,
        vas_after: float = -1.0,
    ) -> ExperimentResult:
        result = ExperimentResult(
            subject_id=subject_id,
            subject_note=subject_note,
            session_start=session_start,
            session_end=session_end,
            trials=self.trials,
            baseline_pupil_size=baseline_pupil,
            total_blinks=total_blinks,
            vas_before=vas_before,
            vas_after=vas_after,
        )

        if vas_before >= 0 and vas_after >= 0:
            result.vas_delta = vas_after - vas_before

        if not self.trials:
            return result

        cat_arousal: Dict[str, List[float]] = {}
        cat_fixation: Dict[str, List[float]] = {}
        cat_reaction: Dict[str, List[float]] = {}
        all_pupil: List[float] = []

        stroop_correct_count = 0
        stroop_total = 0
        stroop_rts_cong: List[float] = []
        stroop_rts_incong: List[float] = []
        stroop_rts_all: List[float] = []

        for trial in self.trials:
            cat = trial.category

            ref_pupil = trial.pupil_median if trial.pupil_median > 0 else trial.pupil_mean
            if baseline_pupil > 0 and ref_pupil > 0:
                arousal = (ref_pupil - baseline_pupil) / baseline_pupil
                trial.arousal_index = float(arousal)
            else:
                trial.arousal_index = 0.0

            cat_arousal.setdefault(cat, []).append(trial.arousal_index)
            cat_fixation.setdefault(cat, []).append(trial.total_fixation_time_ms)
            cat_reaction.setdefault(cat, []).append(trial.reaction_time_ms)
            all_pupil.extend(trial.pupil_samples)

            if trial.is_stroop:
                stroop_total += 1
                if trial.stroop_correct is True:
                    stroop_correct_count += 1
                if trial.stroop_response_ms > 0:
                    stroop_rts_all.append(trial.stroop_response_ms)
                    if trial.stroop_congruent:
                        stroop_rts_cong.append(trial.stroop_response_ms)
                    else:
                        stroop_rts_incong.append(trial.stroop_response_ms)

        def safe_mean(lst):
            return sum(lst) / len(lst) if lst else 0.0

        def safe_std(lst):
            if len(lst) < 2:
                return 0.0
            m = safe_mean(lst)
            var = sum((x - m) ** 2 for x in lst) / (len(lst) - 1)
            return var ** 0.5

        def safe_median(lst):
            if not lst:
                return 0.0
            s = sorted(lst)
            n = len(s)
            if n % 2 == 0:
                return (s[n // 2 - 1] + s[n // 2]) / 2.0
            return float(s[n // 2])

        for cat, vals in cat_arousal.items():
            result.arousal_by_category[cat] = safe_mean(vals)
            result.arousal_std_by_category[cat] = safe_std(vals)
        for cat, vals in cat_fixation.items():
            result.fixation_time_by_category[cat] = safe_mean(vals)
        for cat, vals in cat_reaction.items():
            result.reaction_time_by_category[cat] = safe_mean(vals)

        result.mean_pupil_size = safe_mean(all_pupil)
        result.median_pupil_size = safe_median(all_pupil)

        neutral = result.arousal_by_category.get("neutral", 0.0)
        positive = result.arousal_by_category.get("positive", 0.0)
        negative = result.arousal_by_category.get("negative", 0.0)

        result.negative_arousal = negative - neutral
        result.positive_arousal = positive - neutral
        result.emotional_balance = negative - positive

        if stroop_total > 0:
            result.stroop_n_total = stroop_total
            result.stroop_n_correct = stroop_correct_count
            result.stroop_accuracy = stroop_correct_count / stroop_total
            result.stroop_mean_rt_ms = safe_mean(stroop_rts_all)
            result.stroop_congruent_rt_ms = safe_mean(stroop_rts_cong)
            result.stroop_incongruent_rt_ms = safe_mean(stroop_rts_incong)
            result.stroop_interference_ms = (
                result.stroop_incongruent_rt_ms
                - result.stroop_congruent_rt_ms
            )

        print("\n[ANALYZE] Arousal kategóriánként:")
        for cat, val in result.arousal_by_category.items():
            std = result.arousal_std_by_category.get(cat, 0.0)
            print(f"  {cat:15s}: {val:+.4f} ± {std:.4f}")
        print(f"[ANALYZE] Baseline pupilla: {baseline_pupil:.3f}")
        print(f"[ANALYZE] Átlag pupilla: {result.mean_pupil_size:.3f}")
        print(f"[ANALYZE] Medián pupilla: {result.median_pupil_size:.3f}")
        if stroop_total > 0:
            print(f"[ANALYZE] Stroop pontosság: {result.stroop_accuracy:.1%}")
            print(f"[ANALYZE] Stroop átlag RT: {result.stroop_mean_rt_ms:.0f} ms")
            print(f"[ANALYZE] Stroop interferencia: {result.stroop_interference_ms:+.0f} ms")
        if vas_before >= 0 and vas_after >= 0:
            print(f"[ANALYZE] VAS: {vas_before:.0f} → {vas_after:.0f} (Δ {result.vas_delta:+.0f})")

        return result