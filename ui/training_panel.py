# ui/training_panel.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QProgressBar, QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, QTimer


class TrainingPanel(QWidget):
    """Neurális háló állapotát és tanítási paramétereit mutató panel."""

    def __init__(self, tracker):
        super().__init__()
        self.tracker = tracker
        self.setObjectName("trainingPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # ---- CÍM ----
        title = QLabel("Neurális háló állapota")
        title.setObjectName("sliderLabel")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: 700; font-size: 12px;")
        layout.addWidget(title)

        # ---- ELVÁLASZTÓ ----
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # ---- STÁTUSZ INDIKÁTOR ----
        self.status_label = QLabel("NINCS ADAT")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #ff4444; padding: 6px;")
        layout.addWidget(self.status_label)

        # ---- INFORMÁCIÓS SZÖVEG ----
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(100)
        self.info_text.setMinimumHeight(80)
        self.info_text.setObjectName("infoText")
        self.info_text.setStyleSheet("font-size: 11px; background: #0d1530; border: 1px solid #1e3050;")
        layout.addWidget(self.info_text)

        # ---- TANÍTÁSI PROGRESS ----
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(10)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #1e3050;
                background: #0d1530;
                border-radius: 0px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a8aff, stop:1 #4dd0e1);
            }
        """)
        layout.addWidget(self.progress_bar)

        # ---- METRIKÁK ----
        metrics_group = QGroupBox("Metrikák")
        metrics_group.setObjectName("panelGroup")
        metrics_layout = QVBoxLayout()
        metrics_layout.setSpacing(3)

        self.sample_label = QLabel("Minták: 0")
        self.sample_label.setObjectName("hintLabel")
        metrics_layout.addWidget(self.sample_label)

        self.r2_label = QLabel("R²: -")
        self.r2_label.setObjectName("hintLabel")
        metrics_layout.addWidget(self.r2_label)

        self.layers_label = QLabel("Rétegek: -")
        self.layers_label.setObjectName("hintLabel")
        metrics_layout.addWidget(self.layers_label)

        self.iter_label = QLabel("Iterációk: -")
        self.iter_label.setObjectName("hintLabel")
        metrics_layout.addWidget(self.iter_label)

        self.lr_label = QLabel("Tanulási ráta: -")
        self.lr_label.setObjectName("hintLabel")
        metrics_layout.addWidget(self.lr_label)

        self.features_label = QLabel("Jellemzők: -")
        self.features_label.setObjectName("hintLabel")
        metrics_layout.addWidget(self.features_label)

        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)

        # ---- GOMBOK ----
        btn_row = QHBoxLayout()

        self.refresh_btn = QPushButton("Frissítés")
        self.refresh_btn.setObjectName("secondary")
        self.refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(self.refresh_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("danger")
        self.reset_btn.clicked.connect(self._reset_model)
        btn_row.addWidget(self.reset_btn)
        layout.addLayout(btn_row)

        layout.addStretch()

        # ---- AUTO FRISSÍTÉS ----
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)

        # ---- KEZDETI FRISSÍTÉS ----
        self.refresh()

    def refresh(self):
        """Frissíti a neurális háló állapotát."""
        model = self.tracker.neural_model
        sample_count = model.sample_count
        is_trained = model.is_trained

        self.sample_label.setText(f"Minták: {sample_count}")

        if is_trained:
            info = model.get_model_info()

            # Státusz
            self.status_label.setText("KALIBRÁLVA")
            self.status_label.setStyleSheet(
                "font-size: 14px; font-weight: 700; color: #00ff88; padding: 6px;"
            )

            # Metrikák
            self.r2_label.setText(f"R²: {info['train_score']:.4f}")
            self.r2_label.setStyleSheet("color: #00ff88; font-weight: 600;")
            self.layers_label.setText(f"Rétegek: {info['layers']}")
            self.iter_label.setText(f"Iterációk: {info['iterations']}")
            self.lr_label.setText(f"Tanulási ráta: {info['learning_rate']:.4f}")
            self.features_label.setText(f"Jellemzők: {info['feature_count']}")

            # Progress
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(True)

            # Info szöveg
            info_text = (
                f"Állapot: KALIBRÁLVA\n"
                f"Tanítóminták: {info['samples']}\n"
                f"R² pontosság: {info['train_score']:.4f}\n"
                f"Rejtett rétegek: {info['layers']}\n"
                f"Tanítási iterációk: {info['iterations']}\n"
                f"Tanulási ráta: {info['learning_rate']:.4f}\n"
                f"Jellemzők száma: {info['feature_count']}"
            )
            self.info_text.setText(info_text)

        else:
            # Státusz
            if sample_count > 0:
                self.status_label.setText("TANULÓ MÓD")
                self.status_label.setStyleSheet(
                    "font-size: 14px; font-weight: 700; color: #ffcc00; padding: 6px;"
                )
            else:
                self.status_label.setText("NINCS ADAT")
                self.status_label.setStyleSheet(
                    "font-size: 14px; font-weight: 700; color: #ff4444; padding: 6px;"
                )

            # Metrikák
            self.r2_label.setText("R²: -")
            self.r2_label.setStyleSheet("color: #ff4444; font-weight: 600;")
            self.layers_label.setText("Rétegek: -")
            self.iter_label.setText("Iterációk: -")
            self.lr_label.setText("Tanulási ráta: -")
            self.features_label.setText("Jellemzők: -")

            # Progress
            if sample_count > 0:
                progress = min(100, int(sample_count / 20 * 100))
                self.progress_bar.setValue(progress)
                self.progress_bar.setVisible(True)
            else:
                self.progress_bar.setValue(0)
                self.progress_bar.setVisible(False)

            # Info szöveg
            if sample_count > 0:
                info_text = (
                    f"Állapot: TANULÓ MÓD\n"
                    f"Gyűjtött minták: {sample_count}\n"
                    f"Minimum szükséges: 20\n"
                    f"Hiányzik: {max(0, 20 - sample_count)} minta\n\n"
                    f"Indítsd el a kalibrációt a Kalibráció fülön,\n"
                    f"vagy kattints a Stimulus ablakban!"
                )
            else:
                info_text = (
                    "Állapot: NINCS ADAT\n\n"
                    "A neurális háló még nem kapott tanítómintát.\n\n"
                    "1. Indítsd el a követést (Indítás gomb)\n"
                    "2. Nyisd meg a Kalibrációt (jobb oldali panel)\n"
                    "3. Kövesd a képernyőn megjelenő pontokat"
                )

            self.info_text.setText(info_text)

    def _reset_model(self):
        """Neurális háló resetelése."""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Reset",
            "Biztosan törlöd a neurális háló összes tanítómintáját?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.tracker.neural_model.reset()
            self.refresh()