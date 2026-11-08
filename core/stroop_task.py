# Stroop-teszt – kognitív stressz indukció.

import random
from typing import List, Tuple


STROOP_COLORS = {
    "piros": (255, 0, 0),
    "zöld": (0, 255, 0),
    "kék": (0, 0, 255),
    "sárga": (255, 255, 0),
}


class StroopTask:
    """
    Stroop-teszt generátor.
    - Kongruens: a szó jelentése == a betű színe
    - Inkongruens: a szó jelentése != a betű színe
    """

    COLORS = STROOP_COLORS

    def __init__(self, n_trials: int = 180, congruent_ratio: float = 0.5):
        self.n_trials = n_trials
        self.congruent_ratio = congruent_ratio
        self.trials: List[Tuple[str, str, bool]] = []
        self._generate()

    def _generate(self):
        n_congruent = int(self.n_trials * self.congruent_ratio)
        n_incongruent = self.n_trials - n_congruent

        for _ in range(n_congruent):
            word = random.choice(list(self.COLORS.keys()))
            self.trials.append((word, word, True))

        for _ in range(n_incongruent):
            word = random.choice(list(self.COLORS.keys()))
            color_options = [c for c in self.COLORS.keys() if c != word]
            color = random.choice(color_options)
            self.trials.append((word, color, False))

        random.shuffle(self.trials)

    def get_color_bgr(self, color_name: str):
        return self.COLORS.get(color_name, (255, 255, 255))