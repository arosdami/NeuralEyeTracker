# core/neural_model.py - PONTOS, TANULÉKONY
# - Relatív pozíció a baseline-hoz (kis mozgás is nagy jel)
# - Nagyobb háló (256-128-64-32)
# - Baseline rögzítés az első N mintából
# - Kevesebb hiszterézis (3)

import os
import pickle
import warnings
from typing import Optional, Dict, Tuple, List

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)

from config.settings import (
    AZIMUTH_RANGE, ELEVATION_RANGE, MIN_TRAINING_SAMPLES
)


class NeuralGazeModel:
    """
    Tekintet-előrejelző modell - RELATÍV pozícióval.

    Kulcs újdonság: a modell a **pupilla pozícióját a baseline-hoz képest**
    használja (delta), nem a nyers pozíciót. Ez azt jelenti, hogy a kis
    pupilla-mozgás is **nagy jelet** ad a hálónak.

    A baseline az első 10-15 tanítómintából számolódik.
    """

    FEATURE_NAMES = [
        "dx_norm", "dy_norm",           # ← relatív pozíció!
        "abs_norm_x", "abs_norm_y",     # ← abszolút pozíció is (kiegészítés)
        "major_norm", "minor_norm", "angle_norm",
        "area_norm", "aspect_ratio",
        "darkness_norm", "iris_contrast",
        "velocity_x", "velocity_y",
    ]
    FEATURE_COUNT = 13

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            config = {}

        # Nagyobb háló a nemlineáris leképezéshez
        hidden_layers = config.get("hidden_layers", (256, 128, 64, 32))
        learning_rate = config.get("learning_rate", 0.0008)
        max_iter = config.get("max_iter", 1500)

        self.model = MLPRegressor(
            hidden_layer_sizes=hidden_layers,
            activation="relu",
            solver="adam",
            learning_rate="adaptive",
            learning_rate_init=learning_rate,
            max_iter=max_iter,
            warm_start=False,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=30,
            alpha=1e-4,
            batch_size="auto",
            shuffle=True,
            tol=1e-7,
            verbose=False,
        )

        # StandardScaler jobb a kis értékek kiemelésére
        self.scaler = StandardScaler()

        self.is_trained: bool = False
        self.training_data_X: List[np.ndarray] = []
        self.training_data_Y: List[List[float]] = []

        # ---- BASELINE - a kiindulási pupilla pozíció ----
        self._baseline_x: Optional[float] = None  # normalizált
        self._baseline_y: Optional[float] = None
        self._baseline_samples: List[Tuple[float, float]] = []
        self.BASELINE_COUNT: int = 10  # ennyi mintából számoljuk a baseline-t

        # Feature state
        self._prev_pos: Optional[Tuple[float, float]] = None
        self._prev_vel: Tuple[float, float] = (0.0, 0.0)

        # Predikciós hiszterézis (kevesebb = gyorsabb)
        self._pred_history: List[Tuple[float, float]] = []
        self._pred_history_maxlen: int = 3

        # Metaadatok
        self.train_score: float = 0.0
        self.train_samples: int = 0

        self.azimuth_range = AZIMUTH_RANGE
        self.elevation_range = ELEVATION_RANGE

    # ==================================================================
    # BASELINE KEZELÉS
    # ==================================================================
    def _update_baseline(self, norm_x: float, norm_y: float):
        """Az első N mintából számolja a baseline-t."""
        if self._baseline_x is not None:
            return  # már megvan

        self._baseline_samples.append((norm_x, norm_y))

        if len(self._baseline_samples) >= self.BASELINE_COUNT:
            # Medián a baseline (robusztus)
            xs = [s[0] for s in self._baseline_samples]
            ys = [s[1] for s in self._baseline_samples]
            self._baseline_x = float(np.median(xs))
            self._baseline_y = float(np.median(ys))

    # ==================================================================
    # JELLEMZŐKINYERÉS
    # ==================================================================
    def extract_features(
        self, raw_data: dict, update_state: bool = False
    ) -> np.ndarray:
        """
        13 jellemző:
          - dx_norm, dy_norm: a baseline-hoz képesti eltérés (FŐ JELLEMZŐ!)
          - abs_norm_x, abs_norm_y: abszolút pozíció (kiegészítés)
          - méret jellemzők
          - mozgás jellemzők
        """
        cx = float(raw_data.get("cx", 320.0))
        cy = float(raw_data.get("cy", 240.0))
        frame_w = max(float(raw_data.get("frame_w", 640.0)), 1.0)
        frame_h = max(float(raw_data.get("frame_h", 480.0)), 1.0)

        major = float(raw_data.get("ellipse_major", 20.0))
        minor = float(raw_data.get("ellipse_minor", 18.0))
        angle = float(raw_data.get("ellipse_angle", 0.0))
        area = float(raw_data.get("pupil_area", 300.0))

        darkness = float(raw_data.get("inner_darkness", 30.0))
        iris_contrast = float(raw_data.get("iris_contrast", 0.5))

        # Abszolút pozíció a kép közepéhez képest
        abs_norm_x = float(np.clip(
            (cx - frame_w / 2.0) / (frame_w / 2.0), -1.0, 1.0
        ))
        abs_norm_y = float(np.clip(
            (cy - frame_h / 2.0) / (frame_h / 2.0), -1.0, 1.0
        ))

        # Baseline frissítés (csak tanításkor)
        if update_state:
            self._update_baseline(abs_norm_x, abs_norm_y)

        # Relatív pozíció a baseline-hoz képest
        if self._baseline_x is not None and self._baseline_y is not None:
            dx_norm = abs_norm_x - self._baseline_x
            dy_norm = abs_norm_y - self._baseline_y
        else:
            # Ha még nincs baseline, használjuk az abszolút értéket
            dx_norm = abs_norm_x
            dy_norm = abs_norm_y

        # Skálázás: a kis eltéréseket felnagyítjuk (10x)
        # Ez azért kell, mert a pupilla alig mozdul a képen
        dx_norm = float(np.clip(dx_norm * 10.0, -1.0, 1.0))
        dy_norm = float(np.clip(dy_norm * 10.0, -1.0, 1.0))

        major_norm = float(np.clip(major / 80.0, 0.05, 2.0))
        minor_norm = float(np.clip(minor / 80.0, 0.05, 2.0))
        angle_norm = float((angle % 180.0) / 180.0)
        area_norm = float(np.clip(area / 800.0, 0.05, 5.0))
        aspect = float(np.clip(minor / max(major, 0.01), 0.1, 1.0))
        darkness_norm = float(np.clip(darkness / 255.0, 0.0, 1.0))
        iris_contrast_norm = float(np.clip(iris_contrast, 0.0, 1.0))

        # Sebesség / gyorsulás
        if self._prev_pos is not None:
            vx = dx_norm - self._prev_pos[0]
            vy = dy_norm - self._prev_pos[1]
        else:
            vx = vy = 0.0

        vx = float(np.clip(vx, -1.0, 1.0))
        vy = float(np.clip(vy, -1.0, 1.0))

        if update_state:
            self._prev_pos = (dx_norm, dy_norm)
            self._prev_vel = (vx, vy)

        features = np.array([
            dx_norm, dy_norm,
            abs_norm_x, abs_norm_y,
            major_norm, minor_norm, angle_norm,
            area_norm, aspect,
            darkness_norm, iris_contrast_norm,
            vx, vy,
        ], dtype=np.float64)

        if np.any(np.isnan(features)) or np.any(np.isinf(features)):
            features = np.zeros(self.FEATURE_COUNT, dtype=np.float64)

        return features

    # ==================================================================
    # TANÍTÁS
    # ==================================================================
    def add_training_sample(
        self, raw_data: dict, gaze_target: Tuple[float, float]
    ):
        feat = self.extract_features(raw_data, update_state=True)

        az = float(np.clip(
            gaze_target[0], self.azimuth_range[0], self.azimuth_range[1]
        ))
        el = float(np.clip(
            gaze_target[1], self.elevation_range[0], self.elevation_range[1]
        ))

        self.training_data_X.append(feat)
        self.training_data_Y.append([az, el])

    def train(self, callback=None) -> Dict:
        n = len(self.training_data_X)
        if n < MIN_TRAINING_SAMPLES:
            return {
                "error": f"Nincs elég tanítóadat (min {MIN_TRAINING_SAMPLES}, jelenleg {n})",
                "samples": n,
            }

        try:
            if callback:
                callback(10, "Adatok előkészítése...")

            X = np.array(self.training_data_X, dtype=np.float64)
            Y = np.array(self.training_data_Y, dtype=np.float64)

            X, Y = self._filter_outliers(X, Y)

            if len(X) < MIN_TRAINING_SAMPLES:
                return {
                    "error": f"Outlier szűrés után túl kevés minta ({len(X)})",
                    "samples": len(X),
                }

            # StandardScaler - jobb a kis értékek kiemelésére
            X_scaled = self.scaler.fit_transform(X)

            if callback:
                callback(30, "Modell tanítása...")

            self.model.fit(X_scaled, Y)
            self.is_trained = True
            self.train_samples = len(X)
            self.train_score = float(self.model.score(X_scaled, Y))

            if callback:
                callback(100, "Kész")

            return {
                "samples": len(X),
                "score": self.train_score,
                "layers": str(self.model.hidden_layer_sizes),
                "iters": int(self.model.n_iter_),
                "outliers_removed": n - len(X),
            }

        except Exception as e:
            return {"error": f"Tanítási hiba: {e}"}

    def _filter_outliers(
        self, X: np.ndarray, Y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """IQR-alapú outlier szűrés."""
        if len(X) < 10:
            return X, Y

        try:
            # Csak az első 2 feature-re (dx_norm, dy_norm)
            q1 = np.percentile(X[:, 0:2], 5, axis=0)
            q3 = np.percentile(X[:, 0:2], 95, axis=0)
            iqr = q3 - q1

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            mask = np.all(
                (X[:, 0:2] >= lower) & (X[:, 0:2] <= upper), axis=1
            )

            if mask.sum() < len(X) * 0.7:
                return X, Y

            return X[mask], Y[mask]
        except Exception:
            return X, Y

    # ==================================================================
    # PREDIKCIÓ
    # ==================================================================
    def predict(self, raw_data: dict) -> Tuple[float, float]:
        if not self.is_trained:
            return (0.0, 0.0)

        try:
            feat = self.extract_features(
                raw_data, update_state=False
            ).reshape(1, -1)

            feat_scaled = self.scaler.transform(feat)
            pred = self.model.predict(feat_scaled)[0]

            az = float(np.clip(
                pred[0], self.azimuth_range[0], self.azimuth_range[1]
            ))
            el = float(np.clip(
                pred[1], self.elevation_range[0], self.elevation_range[1]
            ))

            # Enyhe simítás (3 ablak)
            self._pred_history.append((az, el))
            if len(self._pred_history) > self._pred_history_maxlen:
                self._pred_history.pop(0)

            if len(self._pred_history) >= 2:
                # Súlyozott átlag (a legutóbbi érték súlya nagyobb)
                weights = list(range(1, len(self._pred_history) + 1))
                total_w = sum(weights)
                az = sum(
                    p[0] * w for p, w in zip(self._pred_history, weights)
                ) / total_w
                el = sum(
                    p[1] * w for p, w in zip(self._pred_history, weights)
                ) / total_w

            return (az, el)

        except Exception:
            return (0.0, 0.0)

    # ==================================================================
    # MENTÉS / BETÖLTÉS
    # ==================================================================
    def save(self, path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            tmp = path + ".tmp"

            data = {
                "model": self.model,
                "scaler": self.scaler,
                "is_trained": self.is_trained,
                "training_data_X": self.training_data_X,
                "training_data_Y": self.training_data_Y,
                "train_score": self.train_score,
                "train_samples": self.train_samples,
                "baseline_x": self._baseline_x,
                "baseline_y": self._baseline_y,
            }

            with open(tmp, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

            if os.path.exists(path):
                os.remove(path)
            os.rename(tmp, path)
            return True

        except Exception as e:
            print(f"[NEURAL_MODEL] Mentési hiba: {e}")
            return False

    def load(self, path: str) -> bool:
        if not os.path.exists(path):
            return False

        try:
            with open(path, "rb") as f:
                data = pickle.load(f)

            self.model = data.get("model", self.model)
            self.scaler = data.get("scaler", self.scaler)
            self.is_trained = bool(data.get("is_trained", False))
            self.training_data_X = data.get("training_data_X", [])
            self.training_data_Y = data.get("training_data_Y", [])
            self.train_score = float(data.get("train_score", 0.0))
            self.train_samples = int(data.get("train_samples", 0))

            # Baseline visszaállítása
            self._baseline_x = data.get("baseline_x", None)
            self._baseline_y = data.get("baseline_y", None)
            self._baseline_samples = []

            self._pred_history.clear()
            self._prev_pos = None
            self._prev_vel = (0.0, 0.0)

            return True

        except Exception as e:
            print(f"[NEURAL_MODEL] Betöltési hiba: {e}")
            return False

    # ==================================================================
    # SEGÉD
    # ==================================================================
    @property
    def sample_count(self) -> int:
        return len(self.training_data_X)

    def get_model_info(self) -> Dict:
        return {
            "trained": self.is_trained,
            "samples": self.train_samples,
            "train_score": float(self.train_score),
            "layers": str(self.model.hidden_layer_sizes),
            "iterations": int(getattr(self.model, "n_iter_", 0) or 0),
            "learning_rate": float(self.model.learning_rate_init),
            "feature_count": self.FEATURE_COUNT,
            "has_baseline": self._baseline_x is not None,
        }

    def reset(self):
        self.is_trained = False
        self.training_data_X = []
        self.training_data_Y = []
        self._prev_pos = None
        self._prev_vel = (0.0, 0.0)
        self._pred_history = []
        self.train_score = 0.0
        self.train_samples = 0
        self.scaler = StandardScaler()
        self._baseline_x = None
        self._baseline_y = None
        self._baseline_samples = []