# core/report_generator.py
# Riport generátor – TXT (emberi olvasás) + JSON (Analyze fül) + CSV (táblázat)

import os
import json
import csv
from datetime import datetime
from typing import Optional, Any, Dict, List

from core.stimulus_task import ExperimentResult
from config.paths import REPORTS_DIR


class ReportGenerator:

    def __init__(self, output_dir: str = str(REPORTS_DIR)):
        self.output_dir = str(output_dir)
        os.makedirs(output_dir, exist_ok=True)

    # ==========================================================
    # FŐ BELÉPÉSI PONT – TXT + JSON + CSV
    # ==========================================================
    def save_report(self, result: ExperimentResult,
                    filename: Optional[str] = None) -> str:
        """
        Elmenti a riportot:
          - TXT  (emberi olvasásra)
          - JSON (Analyze fülhöz, gépi feldolgozáshoz)
        Visszatérés: a JSON fájl útvonala (ezt használja az Analyze).
        """
        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = f"report_{result.subject_id}_{ts}"
        else:
            base = os.path.splitext(filename)[0]

        # TXT
        try:
            txt_path = os.path.join(self.output_dir, f"{base}.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(self.generate_text_report(result))
        except Exception as e:
            print(f"[REPORTER] TXT hiba: {e}")

        # JSON
        json_path = os.path.join(self.output_dir, f"{base}.json")
        try:
            data = self._build_json(result)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[REPORTER] JSON hiba: {e}")

        return json_path

    # ==========================================================
    # TXT – EMBERI OLVASÁSRA
    # ==========================================================
    def generate_text_report(self, result: ExperimentResult) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("PUPILLOMETRIAI INGERKÍSÉRLET – KLINIKAI RIPORT")
        lines.append("=" * 70)
        lines.append("")

        lines.append(f"Alany azonosító: {result.subject_id}")
        if getattr(result, "subject_note", ""):
            lines.append(f"Megjegyzés: {result.subject_note}")
        lines.append(f"Vizsgálat kezdete: {self._fmt_time(result.session_start)}")
        lines.append(f"Vizsgálat vége:   {self._fmt_time(result.session_end)}")
        lines.append(
            f"Vizsgálat időtartama: "
            f"{(result.session_end - result.session_start):.1f} s"
        )
        lines.append(f"Próbák száma: {len(result.trials)}")
        lines.append("")

        lines.append("-" * 70)
        lines.append("1. PUPILLA ALAPADATOK")
        lines.append("-" * 70)
        lines.append(f"Baseline pupilla méret: {result.baseline_pupil_size:.3f}")
        lines.append(f"Átlagos pupilla méret: {result.mean_pupil_size:.3f}")
        lines.append(f"Összes pislogás:       {result.total_blinks}")
        lines.append("")

        lines.append("-" * 70)
        lines.append("2. AROUSAL REAKCIÓ KATEGÓRIÁNKÉNT")
        lines.append("-" * 70)
        lines.append("Kategória       | Arousal  | Szórás  | Fixáció(ms) | Reakció(ms)")
        lines.append("-" * 70)

        for cat in sorted(getattr(result, "arousal_by_category", {}).keys()):
            arousal = result.arousal_by_category.get(cat, 0.0)
            std = getattr(result, "arousal_std_by_category", {}).get(cat, 0.0)
            fixation = getattr(result, "fixation_time_by_category", {}).get(cat, 0.0)
            reaction = getattr(result, "reaction_time_by_category", {}).get(cat, 0.0)
            lines.append(
                f"{cat:15s} | {arousal:+8.4f} | {std:7.4f} | "
                f"{fixation:11.0f} | {reaction:10.0f}"
            )
        lines.append("")

        # Érzelmi markerek
        arousal_cats = getattr(result, "arousal_by_category", {})
        if ("neutral" in arousal_cats
                and "positive" in arousal_cats
                and "negative" in arousal_cats):
            lines.append("-" * 70)
            lines.append("3. ÉRZELMI REAKCIÓ MARKEREK")
            lines.append("-" * 70)
            lines.append(f"Negatív arousal:   {getattr(result, 'negative_arousal', 0.0):+.4f}")
            lines.append(f"Pozitív arousal:   {getattr(result, 'positive_arousal', 0.0):+.4f}")
            lines.append(f"Érzelmi egyensúly: {getattr(result, 'emotional_balance', 0.0):+.4f}")
            lines.append("")
            lines.append("Értelmezés:")
            lines.append("  Negatív arousal > +0.05   → stressz-érzékenység")
            lines.append("  Pozitív arousal < -0.03   → anhedonia")
            lines.append("  Érzelmi egyensúly > +0.10 → negatív torzítás")
            lines.append("")

            lines.append("-" * 70)
            lines.append("4. KLINIKAI ÉRTELMEZÉS")
            lines.append("-" * 70)
            lines.append(self._interpret(result))
            lines.append("")

        lines.append("=" * 70)
        lines.append(
            "MEGJEGYZÉS: Automatikus kiértékelés. Klinikai diagnózis "
            "csak szakorvosi értékelés alapján állítható fel."
        )
        lines.append("=" * 70)
        return "\n".join(lines)

    # ==========================================================
    # KLINIKAI ÉRTELMEZÉS (változatlan)
    # ==========================================================
    def _interpret(self, result: ExperimentResult) -> str:
        lines = []
        neg = getattr(result, "negative_arousal", 0.0)
        pos = getattr(result, "positive_arousal", 0.0)
        bal = getattr(result, "emotional_balance", 0.0)

        if neg > 0.10:
            lines.append(
                "FOKOZOTT NEGATÍV REAKCIÓ: a pupilla jelentősen "
                "tágul negatív ingerekre."
            )
            lines.append("  → stressz-érzékenység, szorongás, depresszió.")
        elif neg > 0.03:
            lines.append("Enyhe negatív reakció (normál tartomány felső határa).")
        else:
            lines.append("Negatív reakció normál tartományban.")

        if pos < -0.03:
            lines.append(
                "CSÖKKENT POZITÍV VÁLASZ: a pupilla nem tágul "
                "pozitív ingerekre."
            )
            lines.append("  → anhedonia (örömképesség csökkenése), depresszió.")
        elif pos > 0.05:
            lines.append("Jó pozitív válasz.")
        else:
            lines.append("Pozitív válasz normál tartományban.")

        if bal > 0.10:
            lines.append(
                "NEGATÍV IRÁNYÚ ÉRZELMI TORZÍTÁS: a negatív ingerek "
                "jóval erősebb reakciót váltanak ki."
            )
        elif bal < -0.10:
            lines.append("Pozitív irányú érzelmi torzítás.")
        else:
            lines.append("Kiegyensúlyozott érzelmi reakció.")

        return "\n".join(lines)

    # ==========================================================
    # JSON – ANALYZE FÜL SZÁMÁRA
    # ==========================================================
    def _build_json(self, result: ExperimentResult) -> Dict[str, Any]:
        trials_json: List[Dict[str, Any]] = []
        for t in getattr(result, "trials", []) or []:
            trials_json.append({
                "index": int(getattr(t, "index", 0)),
                "category": str(getattr(t, "category", "")),
                "image": self._basename(getattr(t, "image_path", "")),
                "image_id": str(getattr(t, "image_id", "")),
                "is_stroop": bool(getattr(t, "is_stroop", False)),

                # Pupilla metrikák
                "pupil_baseline": self._f(getattr(t, "pupil_baseline", None)),
                "pupil_mean": self._f(getattr(t, "pupil_mean", None)),
                "pupil_median": self._f(getattr(t, "pupil_median", None)),
                "pupil_max": self._f(getattr(t, "pupil_max", None)),
                "pupil_min": self._f(getattr(t, "pupil_min", None)),
                "pupil_std": self._f(getattr(t, "pupil_std", None)),

                # Figyelmi metrikák
                "reaction_time_ms": self._f(getattr(t, "reaction_time_ms", None)),
                "total_fixation_time_ms": self._f(getattr(t, "total_fixation_time_ms", None)),
                "first_fixation_x": self._f(getattr(t, "first_fixation_x", None)),
                "first_fixation_y": self._f(getattr(t, "first_fixation_y", None)),
                "first_fixation_latency_ms": self._f(getattr(t, "first_fixation_latency_ms", None)),

                # Arousal
                "arousal_index": self._f(getattr(t, "arousal_index", None)),

                # Stroop
                "stroop_word": getattr(t, "stroop_word", None),
                "stroop_color": getattr(t, "stroop_color", None),
                "stroop_correct": getattr(t, "stroop_correct", None),
                "stroop_response_ms": self._f(getattr(t, "stroop_response_ms", None)),

                # Időbélyegek
                "t_start": self._f(getattr(t, "t_start", None)),
                "t_end": self._f(getattr(t, "t_end", None)),
            })

        return {
            "schema_version": 2,
            "generated_at": datetime.now().isoformat(),
            "subject_id": str(getattr(result, "subject_id", "")),
            "subject_note": str(getattr(result, "subject_note", "")),
            "mode": str(getattr(result, "mode", "images")),
            "session_start": self._f(getattr(result, "session_start", None)),
            "session_end": self._f(getattr(result, "session_end", None)),
            "baseline_pupil": self._f(getattr(result, "baseline_pupil_size", None)),
            "mean_pupil": self._f(getattr(result, "mean_pupil_size", None)),
            "total_blinks": int(getattr(result, "total_blinks", 0) or 0),
            "vas_before": self._f(getattr(result, "vas_before", -1.0)),
            "vas_after": self._f(getattr(result, "vas_after", -1.0)),

            # Kategória-szintű összesítők (a TXT-vel konzisztensen)
            "arousal_by_category": self._f_dict(getattr(result, "arousal_by_category", {})),
            "arousal_std_by_category": self._f_dict(getattr(result, "arousal_std_by_category", {})),
            "fixation_time_by_category": self._f_dict(getattr(result, "fixation_time_by_category", {})),
            "reaction_time_by_category": self._f_dict(getattr(result, "reaction_time_by_category", {})),

            # Érzelmi markerek
            "negative_arousal": self._f(getattr(result, "negative_arousal", None)),
            "positive_arousal": self._f(getattr(result, "positive_arousal", None)),
            "emotional_balance": self._f(getattr(result, "emotional_balance", None)),

            # Próbánkénti részletes adatok
            "trials": trials_json,
        }

    # ==========================================================
    # CSV – MÁSODLAGOS (táblázat)
    # ==========================================================
    def save_csv(self, result: ExperimentResult,
                 filename: Optional[str] = None) -> str:
        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data_{result.subject_id}_{ts}.csv"
        path = os.path.join(self.output_dir, filename)

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow([
                    "trial_index", "category", "image_id", "image",
                    "is_stroop", "arousal_index",
                    "pupil_baseline", "pupil_mean", "pupil_median",
                    "pupil_max", "pupil_min", "pupil_std",
                    "reaction_time_ms", "total_fixation_time_ms",
                    "first_fixation_x", "first_fixation_y",
                    "first_fixation_latency_ms",
                    "stroop_word", "stroop_color",
                    "stroop_correct", "stroop_response_ms",
                ])
                for t in getattr(result, "trials", []) or []:
                    w.writerow([
                        getattr(t, "index", ""),
                        getattr(t, "category", ""),
                        getattr(t, "image_id", ""),
                        self._basename(getattr(t, "image_path", "")),
                        getattr(t, "is_stroop", False),
                        self._safe(getattr(t, "arousal_index", "")),
                        self._safe(getattr(t, "pupil_baseline", "")),
                        self._safe(getattr(t, "pupil_mean", "")),
                        self._safe(getattr(t, "pupil_median", "")),
                        self._safe(getattr(t, "pupil_max", "")),
                        self._safe(getattr(t, "pupil_min", "")),
                        self._safe(getattr(t, "pupil_std", "")),
                        self._safe(getattr(t, "reaction_time_ms", "")),
                        self._safe(getattr(t, "total_fixation_time_ms", "")),
                        self._safe(getattr(t, "first_fixation_x", "")),
                        self._safe(getattr(t, "first_fixation_y", "")),
                        self._safe(getattr(t, "first_fixation_latency_ms", "")),
                        getattr(t, "stroop_word", ""),
                        getattr(t, "stroop_color", ""),
                        getattr(t, "stroop_correct", ""),
                        self._safe(getattr(t, "stroop_response_ms", "")),
                    ])
        except Exception as e:
            print(f"[REPORTER] CSV hiba: {e}")
        return path

    # ==========================================================
    # SEGÉDEK
    # ==========================================================
    @staticmethod
    def _fmt_time(t: float) -> str:
        if not t or t <= 0:
            return "N/A"
        return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _basename(p) -> str:
        if not p:
            return ""
        try:
            return os.path.basename(str(p))
        except Exception:
            return ""

    @staticmethod
    def _f(v):
        """Biztonságos float konverzió – None vagy NaN esetén None."""
        if v is None:
            return None
        try:
            fv = float(v)
            # NaN / inf ellenőrzés
            if fv != fv or fv in (float("inf"), float("-inf")):
                return None
            return fv
        except Exception:
            return None

    @staticmethod
    def _safe(v):
        if v is None or v == "":
            return ""
        try:
            return float(v)
        except Exception:
            return str(v)

    def _f_dict(self, d) -> Dict[str, float]:
        out = {}
        if not isinstance(d, dict):
            return out
        for k, v in d.items():
            fv = self._f(v)
            if fv is not None:
                out[str(k)] = fv
        return out