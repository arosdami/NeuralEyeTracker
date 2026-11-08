"""Compact project and patient setup dialog."""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)

from config.settings import PALETTE
from core.project_manager import (
    create_project,
    load_project,
    new_patient_id,
    recent_projects,
    save_project,
    validate_patient,
)


class ProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.project_path = ""
        self.setWindowTitle("Neural Eye Tracker | Projekt és páciens")
        self.setMinimumSize(680, 560)
        self.setModal(True)
        self._build_ui()
        self._refresh_recent()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        title = QLabel("Mérés előkészítése")
        title.setObjectName("dialogTitle")
        root.addWidget(title)
        subtitle = QLabel("Válasszon projektet, majd adja meg a vizsgálathoz szükséges páciensadatokat.")
        subtitle.setObjectName("dialogSubtitle")
        root.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("setupTabs")
        self.tabs.addTab(self._build_project_tab(), "Projekt")
        self.tabs.addTab(self._build_patient_tab(), "Páciens")
        root.addWidget(self.tabs, stretch=1)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 4, 0, 0)
        footer.addStretch()
        self.continue_button = QPushButton("Projekt megnyitása")
        self.continue_button.setObjectName("primaryButton")
        self.continue_button.clicked.connect(self._continue)
        footer.addWidget(self.continue_button)
        root.addLayout(footer)

        self.setStyleSheet(
            f"""
            QDialog {{
                background: {PALETTE['bg_primary']};
            }}
            QLabel#dialogTitle {{
                color: {PALETTE['text_primary']};
                font-size: 24px;
                font-weight: 700;
            }}
            QLabel#dialogSubtitle {{
                color: {PALETTE['text_secondary']};
                font-size: 12px;
                padding-bottom: 4px;
            }}
            QTabWidget#setupTabs::pane {{
                background: {PALETTE['bg_secondary']};
                border: 1px solid {PALETTE['border']};
                border-radius: 12px;
                top: -1px;
            }}
            QTabWidget#setupTabs QTabBar {{
                qproperty-drawBase: 0;
            }}
            QTabWidget#setupTabs QTabBar::tab {{
                background: transparent;
                color: {PALETTE['text_muted']};
                border: none;
                border-bottom: 2px solid transparent;
                padding: 11px 22px;
                margin-right: 8px;
                font-size: 13px;
                font-weight: 600;
            }}
            QTabWidget#setupTabs QTabBar::tab:hover {{
                color: {PALETTE['text_primary']};
            }}
            QTabWidget#setupTabs QTabBar::tab:selected {{
                color: {PALETTE['accent_primary']};
                border-bottom: 2px solid {PALETTE['accent_primary']};
            }}
            QFrame#setupCard {{
                background: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 10px;
            }}
            QLabel#sectionTitle {{
                color: {PALETTE['text_primary']};
                font-size: 14px;
                font-weight: 700;
            }}
            QLabel#sectionHint {{
                color: {PALETTE['text_secondary']};
                font-size: 11px;
            }}
            QLineEdit, QComboBox, QListWidget {{
                background: {PALETTE['bg_input']};
                color: {PALETTE['text_primary']};
                border: 1px solid {PALETTE['border_light']};
                border-radius: 7px;
                padding: 8px 10px;
                min-height: 18px;
            }}
            QLineEdit:focus, QComboBox:focus, QListWidget:focus {{
                border: 1px solid {PALETTE['accent_primary']};
            }}
            QListWidget {{
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 9px;
                border-radius: 5px;
            }}
            QListWidget::item:selected {{
                background: {PALETTE['accent_primary']};
                color: {PALETTE['text_inverse']};
            }}
            QPushButton {{
                background: {PALETTE['bg_elevated']};
                color: {PALETTE['text_primary']};
                border: 1px solid {PALETTE['border_light']};
                border-radius: 7px;
                padding: 9px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {PALETTE['accent_primary']};
                border-color: {PALETTE['accent_primary']};
            }}
            QPushButton#primaryButton {{
                background: {PALETTE['accent_primary']};
                border-color: {PALETTE['accent_primary']};
                padding: 10px 24px;
            }}
            QPushButton#primaryButton:hover {{
                background: {PALETTE['accent_hover']};
            }}
            """
        )

    def _build_project_tab(self):
        page = QVBoxLayout()
        page.setContentsMargins(22, 22, 22, 22)
        page.setSpacing(14)

        intro = QLabel("Projekt kiválasztása")
        intro.setObjectName("sectionTitle")
        page.addWidget(intro)
        hint = QLabel("Hozzon létre új projektet, nyisson meg egy meglévőt, vagy folytasson egy korábbi munkamenetet.")
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        page.addWidget(hint)

        project_form = QFormLayout()
        project_form.setSpacing(10)
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("pl. Pupillometriai vizsgálat 2026")
        project_form.addRow("Projekt neve *", self.project_name)
        page.addLayout(project_form)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        for text, callback in (
            ("Új projekt", self._new_project),
            ("Projekt megnyitása", self._open_project),
            ("Munkamenet megnyitása", self._open_session),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            actions.addWidget(button)
        page.addLayout(actions)

        recent_title = QLabel("Legutóbbi projektek")
        recent_title.setObjectName("sectionTitle")
        page.addWidget(recent_title)
        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(145)
        self.recent_list.itemDoubleClicked.connect(self._open_recent)
        page.addWidget(self.recent_list, stretch=1)
        return self._page_widget(page)

    def _build_patient_tab(self):
        page = QVBoxLayout()
        page.setContentsMargins(22, 22, 22, 22)
        page.setSpacing(14)

        intro = QLabel("Páciens adatai")
        intro.setObjectName("sectionTitle")
        page.addWidget(intro)
        hint = QLabel("A mérés csak az azonosító, név, TAJ-szám és vizsgálati cél megadása után indítható.")
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        page.addWidget(hint)

        patient_form = QFormLayout()
        patient_form.setSpacing(10)
        self.patient_id = QLineEdit()
        self.patient_id.setPlaceholderText("Üresen hagyva automatikusan generálódik")
        patient_form.addRow("Páciensazonosító", self.patient_id)
        self.patient_name = QLineEdit()
        patient_form.addRow("Páciens neve *", self.patient_name)
        self.taj = QLineEdit()
        self.taj.setPlaceholderText("9 számjegy")
        self.taj.setMaxLength(9)
        patient_form.addRow("TAJ-szám *", self.taj)
        self.diagnosis = QLineEdit()
        patient_form.addRow("Vizsgálati cél / diagnózis *", self.diagnosis)
        self.gender = QComboBox()
        self.gender.addItems(["Nincs megadva", "Nő", "Férfi", "Egyéb"])
        patient_form.addRow("Nem", self.gender)
        page.addLayout(patient_form)
        page.addStretch()
        return self._page_widget(page)

    @staticmethod
    def _page_widget(layout):
        from PyQt5.QtWidgets import QWidget

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _refresh_recent(self):
        self.recent_list.clear()
        for path in recent_projects():
            self.recent_list.addItem(Path(path).name)
            self.recent_list.item(self.recent_list.count() - 1).setData(Qt.UserRole, path)

    def _new_project(self):
        if not self.project_name.text().strip():
            self.project_name.setText("Új projekt")
        self._clear_patient()
        self.patient_id.setText(new_patient_id())
        self.patient_name.setFocus()

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Projekt megnyitása", "", "Neural Eye projekt (*.nep);;Minden fájl (*)"
        )
        if path:
            self._load(path)

    def _open_session(self):
        self._open_project()

    def _open_recent(self, item):
        self._load(item.data(Qt.UserRole))

    def _load(self, path: str):
        try:
            project = load_project(path)
        except (OSError, ValueError, TypeError) as error:
            QMessageBox.critical(self, "Projekt megnyitási hiba", str(error))
            return
        self.project = project
        self.project_path = path
        self.project_name.setText(project.get("name", ""))
        self._set_patient(project.get("patient", {}))
        self.continue_button.setText("Projekt megnyitása")

    def _continue(self):
        patient = {
            "patient_id": self.patient_id.text().strip() or new_patient_id(),
            "name": self.patient_name.text().strip(),
            "taj": self.taj.text().strip(),
            "diagnosis": self.diagnosis.text().strip(),
            "gender": self.gender.currentText(),
        }
        valid, message = validate_patient(patient)
        if not valid:
            QMessageBox.warning(self, "Hiányzó vagy hibás adat", message)
            return
        if self.project is None:
            self.project = create_project(self.project_name.text(), patient)
            path, _ = QFileDialog.getSaveFileName(
                self, "Projekt mentése", "", "Neural Eye projekt (*.nep)"
            )
            if not path:
                return
            if not path.lower().endswith(".nep"):
                path += ".nep"
            self.project_path = path
        else:
            self.project["patient"] = patient
            self.project["name"] = self.project_name.text().strip() or self.project["name"]
        save_project(self.project_path, self.project)
        self.accept()

    def _clear_patient(self):
        self.patient_name.clear()
        self.taj.clear()
        self.diagnosis.clear()
        self.gender.setCurrentIndex(0)

    def _set_patient(self, patient):
        self.patient_id.setText(patient.get("patient_id", ""))
        self.patient_name.setText(patient.get("name", ""))
        self.taj.setText(patient.get("taj", ""))
        self.diagnosis.setText(patient.get("diagnosis", ""))
        self.gender.setCurrentText(patient.get("gender", "Nincs megadva"))
