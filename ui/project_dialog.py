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
    QVBoxLayout,
)

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
        self.setMinimumWidth(560)
        self.setModal(True)
        self._build_ui()
        self._refresh_recent()

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel("Mérés előkészítése")
        title.setObjectName("dialogTitle")
        root.addWidget(title)
        subtitle = QLabel("Hozzon létre vagy nyisson meg egy projektet a folytatáshoz.")
        subtitle.setObjectName("dialogSubtitle")
        root.addWidget(subtitle)

        project_form = QFormLayout()
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("pl. Pupillometriai vizsgálat 2026")
        project_form.addRow("Projekt neve *", self.project_name)
        root.addLayout(project_form)

        actions = QHBoxLayout()
        for text, callback in (
            ("Új projekt", self._new_project),
            ("Projekt megnyitása", self._open_project),
            ("Munkamenet megnyitása", self._open_session),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            actions.addWidget(button)
        root.addLayout(actions)

        root.addWidget(QLabel("Legutóbbi projektek"))
        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self._open_recent)
        root.addWidget(self.recent_list)

        patient_form = QFormLayout()
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
        root.addLayout(patient_form)

        footer = QHBoxLayout()
        footer.addStretch()
        self.continue_button = QPushButton("Projekt megnyitása")
        self.continue_button.setProperty("class", "primary")
        self.continue_button.clicked.connect(self._continue)
        footer.addWidget(self.continue_button)
        root.addLayout(footer)

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
