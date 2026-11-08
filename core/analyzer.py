# core/analyzer.py
# Statisztikai elemző: metrikák számítása a kiválasztott riportokból

import numpy as np
from typing import List, Dict, Optional, Callable, Tuple
from core.report_loader import ReportRecord


# Metrika-definíciók (név → mező + címke)
METRICS = {
    "pupil_mean": {
        "label": "Pupilla átmérő (átlag)",
        "unit": "",
        "field": "pupil_mean",
        "color": "#0e8cf0",
    },
    "pupil_max": {
        "label": "Pupilla átmérő (maximum)",
        "unit": "",
        "field": "pupil_max",
        "color": "#ef4a5a",
    },
    "reaction_time_ms": {
        "label": "Reakcióidő",
        "unit": "ms",
        "field": "reaction_time_ms",
        "color": "#4ec976",
    },
    "total_fixation_time_ms": {
        "label": "Fixációs idő összesen",
        "unit": "ms",
        "field": "total_fixation_time_ms",
        "color": "#f0a838",
    },
    "first_fixation_latency_ms": {
        "label": "Első fixáció látencia",
        "unit": "ms",
        "field": "first_fixation_latency_ms",
        "color": "#a06cf0",
    },
    "pupil_std": {
        "label": "Pupilla szórás",
        "unit": "",
        "field": "pupil_std",
        "color": "#20c4d8",
    },
    "stroop_response_ms": {
        "label": "Stroop reakcióidő",
        "unit": "ms",
        "field": "stroop_response_ms",
        "color": "#ef4a8c",
    },
}


class Analyzer:
    """
    A kiválasztott riportokból kinyeri és csoportosítja a metrikákat.

    Kimeneti struktúra:
    {
      "metric": "pupil_mean",
      "metric_label": "Pupilla átmérő (átlag)",
      "unit": "",
      "groups": [
        {
           "name": "Dog",
           "values": [1.12, 1.18, 1.09, ...],
           "mean": 1.13,
           "median": 1.12,
           "std": 0.05,
           "min": 1.05, "max": 1.22,
           "n": 42,
        },
        ...
      ]
    }
    """

    def __init__(self, reports: List[ReportRecord]):
        self.reports = reports

    # ------------------------------------------------------------
    # Metrika-kinyerés
    # ------------------------------------------------------------
    def collect(self,
                metric_key: str,
                group_by: str = "category",
                category_filter: Optional[List[str]] = None) -> dict:
        """
        metric_key:    METRICS egyik kulcsa (pl. "pupil_mean")
        group_by:      "category" | "subject" | "trial_index" | "all"
        category_filter: csak ezeket a kategóriákat tartalmazza (None = mind)
        """
        if metric_key not in METRICS:
            return self._empty_result(metric_key)

        field = METRICS[metric_key]["field"]
        groups: Dict[str, List[float]] = {}

        for rep in self.reports:
            for t in rep.trials:
                val = t.get(field)
                if val is None:
                    continue
                try:
                    val = float(val)
                except Exception:
                    continue
                if not np.isfinite(val):
                    continue

                cat = t.get("category", "?")
                if category_filter and cat not in category_filter:
                    continue

                # Csoport-kulcs
                if group_by == "category":
                    key = cat
                elif group_by == "subject":
                    key = rep.subject_id
                elif group_by == "trial_index":
                    key = f"Trial {t.get('index', 0)}"
                elif group_by == "session":
                    key = rep.date_str
                else:
                    key = "Összes"

                groups.setdefault(key, []).append(val)

        # Rendezés: kategóriánál ABC, indexnél szám, egyébként ABC
        if group_by == "trial_index":
            def sort_key(k):
                try:
                    return int(k.split()[1])
                except Exception:
                    return 0
            sorted_keys = sorted(groups.keys(), key=sort_key)
        else:
            sorted_keys = sorted(groups.keys())

        group_list = []
        for k in sorted_keys:
            vals = np.array(groups[k], dtype=float)
            if len(vals) == 0:
                continue
            group_list.append({
                "name": k,
                "values": vals.tolist(),
                "mean": float(np.mean(vals)),
                "median": float(np.median(vals)),
                "std": float(np.std(vals)),
                "min": float(np.min(vals)),
                "max": float(np.max(vals)),
                "n": int(len(vals)),
            })

        return {
            "metric": metric_key,
            "metric_label": METRICS[metric_key]["label"],
            "unit": METRICS[metric_key]["unit"],
            "color": METRICS[metric_key]["color"],
            "group_by": group_by,
            "groups": group_list,
        }

    # ------------------------------------------------------------
    # Összehasonlító statisztika (t-próba két csoportra)
    # ------------------------------------------------------------
    def compare_two_groups(self, metric_key: str, cat_a: str, cat_b: str) -> Optional[dict]:
        """Független kétmintás t-próba a két kategória között."""
        data = self.collect(metric_key, group_by="category")
        groups = {g["name"]: np.array(g["values"]) for g in data["groups"]}
        if cat_a not in groups or cat_b not in groups:
            return None
        a = groups[cat_a]
        b = groups[cat_b]
        if len(a) < 2 or len(b) < 2:
            return None
        try:
            from scipy import stats
            t, p = stats.ttest_ind(a, b, equal_var=False)
        except ImportError:
            # Fallback: csak leíró statisztika
            return {
                "cat_a": cat_a,
                "cat_b": cat_b,
                "mean_a": float(np.mean(a)),
                "mean_b": float(np.mean(b)),
                "diff": float(np.mean(a) - np.mean(b)),
                "p_value": None,
            }
        return {
            "cat_a": cat_a,
            "cat_b": cat_b,
            "mean_a": float(np.mean(a)),
            "mean_b": float(np.mean(b)),
            "diff": float(np.mean(a) - np.mean(b)),
            "t": float(t),
            "p_value": float(p),
        }

    # ------------------------------------------------------------
    # Idősor (pupilla lefolyása)
    # ------------------------------------------------------------
    def time_series(self, metric_key: str = "pupil_mean",
                    category: Optional[str] = None) -> dict:
        """A kiválasztott metrika próbák szerinti sorozata (egy riportra szűkítve)."""
        if not self.reports:
            return {"x": [], "y": [], "label": ""}

        rep = self.reports[0]
        x, y = [], []
        for t in rep.trials:
            if category and t.get("category") != category:
                continue
            val = t.get(METRICS.get(metric_key, {}).get("field", ""))
            if val is None:
                continue
            x.append(t.get("index", 0))
            y.append(float(val))
        return {
            "x": x,
            "y": y,
            "label": METRICS.get(metric_key, {}).get("label", ""),
            "subject": rep.subject_id,
        }

    # ------------------------------------------------------------
    # Összes kategória listája (szűrőhöz)
    # ------------------------------------------------------------
    def all_categories(self) -> List[str]:
        cats = set()
        for r in self.reports:
            for c in r.categories:
                if c:
                    cats.add(c)
        return sorted(cats)

    def all_subjects(self) -> List[str]:
        return sorted(set(r.subject_id for r in self.reports))

    # ------------------------------------------------------------
    def _empty_result(self, metric_key: str) -> dict:
        return {
            "metric": metric_key,
            "metric_label": METRICS.get(metric_key, {}).get("label", metric_key),
            "unit": "",
            "color": "#0e8cf0",
            "group_by": "category",
            "groups": [],
        }