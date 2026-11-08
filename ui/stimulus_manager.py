# ui/stimulus_manager.py
# Professzionális ingerkategória-kezelő widget
# - Kategóriák létrehozása, átnevezése, törlése (drag & drop sorrend)
# - Képek feltöltése, törlése, sorrendezése (drag & drop)
# - Megjelenítési idő, ismétlés, véletlen sorrend, aktív állapot
# - JSON mentés/betöltés: stimuli/categories.json

import os
import json
import shutil
import time
from typing import List, Dict, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QGroupBox, QFrame,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
    QFileDialog, QMessageBox, QAbstractItemView, QSplitter,
    QScrollArea, QSizePolicy, QSlider, QInputDialog
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon, QColor, QFont, QImage

from config.settings import PALETTE

# Támogatott kép kiterjesztések
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")


# ============================================================
# KATEGÓRIA MODELL
# ============================================================
class StimulusCategory:
    def __init__(self, name: str, path: str = ""):
        self.name: str = name
        self.path: str = path                      # stimuli/<name>
        self.images: List[str] = []                # relatív fájlnevek
        self.display_time: float = 3.0             # másodperc
        self.repetitions: int = 1                  # hányszor
        self.random_order: bool = True
        self.active: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "images": list(self.images),
            "display_time": float(self.display_time),
            "repetitions": int(self.repetitions),
            "random_order": bool(self.random_order),
            "active": bool(self.active),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StimulusCategory":
        c = cls(d.get("name", "Névtelen"), d.get("path", ""))
        c.images = list(d.get("images", []))
        c.display_time = float(d.get("display_time", 3.0))
        c.repetitions = int(d.get("repetitions", 1))
        c.random_order = bool(d.get("random_order", True))
        c.active = bool(d.get("active", True))
        return c


# ============================================================
# KATEGÓRIA-LISTA ELEM (drag & drop)
# ============================================================
class CategoryListWidget(QListWidget):
    order_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setIconSize(QSize(48, 48))

    def dropEvent(self, event):
        super().dropEvent(event)
        self.order_changed.emit()


# ============================================================
# KÉP-LISTA ELEM (drag & drop + törlés)
# ============================================================
class ImageListWidget(QListWidget):
    order_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setIconSize(QSize(96, 72))
        self.setViewMode(QListWidget.IconMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setSpacing(8)
        self.setMovement(QListWidget.Static)
        self.setUniformItemSizes(True)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.order_changed.emit()


# ============================================================
# FŐ WIDGET
# ============================================================
class StimulusManager(QWidget):
    """
    Professzionális ingerkategória-kezelő.
    Kezeli a stimuli/categories.json-t és a stimuli/<kategória>/ mappákat.
    """

    categories_changed = pyqtSignal()

    def __init__(self, stimuli_dir: str = "stimuli", parent=None):
        super().__init__(parent)
        self.stimuli_dir = stimuli_dir
        self.categories: List[StimulusCategory] = []
        self._current_index: int = -1
        self._loading = False

        os.makedirs(self.stimuli_dir, exist_ok=True)
        self._categories_json = os.path.join(self.stimuli_dir, "categories.json")

        self._build_ui()
        self._load_from_disk()

    # ==========================================================
    # UI ÉPÍTÉS
    # ==========================================================
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(14)

        # ---------- BAL: kategórialista ----------
        left = QVBoxLayout()
        left.setSpacing(8)

        cat_group = QGroupBox("INGERKATEGÓRIÁK")
        cat_layout = QVBoxLayout(cat_group)
        cat_layout.setContentsMargins(8, 14, 8, 8)
        cat_layout.setSpacing(6)

        self.cat_list = CategoryListWidget()
        self.cat_list.setMinimumWidth(240)
        self.cat_list.currentRowChanged.connect(self._on_category_selected)
        self.cat_list.order_changed.connect(self._on_category_order_changed)
        cat_layout.addWidget(self.cat_list, stretch=1)

        cat_btn_row = QHBoxLayout()
        cat_btn_row.setSpacing(6)

        self.btn_new_cat = QPushButton("Új kategória")
        self.btn_new_cat.clicked.connect(self._new_category)
        cat_btn_row.addWidget(self.btn_new_cat)

        self.btn_rename_cat = QPushButton("Átnevezés")
        self.btn_rename_cat.clicked.connect(self._rename_category)
        cat_btn_row.addWidget(self.btn_rename_cat)

        self.btn_delete_cat = QPushButton("Törlés")
        self.btn_delete_cat.setStyleSheet(
            f"color: {PALETTE.get('accent_danger', '#f85149')};"
        )
        self.btn_delete_cat.clicked.connect(self._delete_category)
        cat_btn_row.addWidget(self.btn_delete_cat)

        cat_layout.addLayout(cat_btn_row)

        # Mozgatás fel/le gombok
        move_row = QHBoxLayout()
        move_row.setSpacing(6)
        self.btn_up = QPushButton("Fel")
        self.btn_up.clicked.connect(lambda: self._move_category(-1))
        move_row.addWidget(self.btn_up)
        self.btn_down = QPushButton("Le")
        self.btn_down.clicked.connect(lambda: self._move_category(1))
        move_row.addWidget(self.btn_down)
        cat_layout.addLayout(move_row)

        left.addWidget(cat_group, stretch=1)

        left_wrap = QWidget()
        left_wrap.setLayout(left)
        left_wrap.setFixedWidth(280)
        root.addWidget(left_wrap)

        # ---------- JOBB: kategória részletei ----------
        right = QVBoxLayout()
        right.setSpacing(10)

        # Fejléc
        self.lbl_cat_title = QLabel("Válassz kategóriát")
        self.lbl_cat_title.setStyleSheet(
            f"color: {PALETTE.get('accent_primary', '#007acc')}; "
            f"font-size: 14px; font-weight: 700;"
        )
        right.addWidget(self.lbl_cat_title)

        # Beállítások
        settings_group = QGroupBox("KATEGÓRIA BEÁLLÍTÁSOK")
        settings_layout = QGridLayout(settings_group)
        settings_layout.setContentsMargins(10, 16, 10, 10)
        settings_layout.setSpacing(8)

        # Aktív
        self.cb_active = QCheckBox("Aktív (bekerül a protokollba)")
        self.cb_active.stateChanged.connect(self._on_settings_changed)
        settings_layout.addWidget(self.cb_active, 0, 0, 1, 4)

        # Megjelenítési idő
        lbl_time = QLabel("Megjelenítési idő:")
        settings_layout.addWidget(lbl_time, 1, 0)

        self.slider_time = QSlider(Qt.Horizontal)
        self.slider_time.setRange(5, 300)  # 0.5 .. 30.0 s (tizedmásodperc)
        self.slider_time.setValue(30)
        self.slider_time.valueChanged.connect(self._on_time_slider)
        settings_layout.addWidget(self.slider_time, 1, 1, 1, 2)

        self.spin_time = QDoubleSpinBox()
        self.spin_time.setRange(0.5, 30.0)
        self.spin_time.setSingleStep(0.1)
        self.spin_time.setDecimals(1)
        self.spin_time.setSuffix(" s")
        self.spin_time.setValue(3.0)
        self.spin_time.valueChanged.connect(self._on_time_spin)
        settings_layout.addWidget(self.spin_time, 1, 3)

        # Ismétlések
        lbl_rep = QLabel("Ismétlések:")
        settings_layout.addWidget(lbl_rep, 2, 0)

        self.spin_rep = QSpinBox()
        self.spin_rep.setRange(1, 20)
        self.spin_rep.setValue(1)
        self.spin_rep.setSuffix(" x")
        self.spin_rep.valueChanged.connect(self._on_settings_changed)
        settings_layout.addWidget(self.spin_rep, 2, 1)

        # Véletlen sorrend
        self.cb_random = QCheckBox("Véletlen sorrend")
        self.cb_random.setChecked(True)
        self.cb_random.stateChanged.connect(self._on_settings_changed)
        settings_layout.addWidget(self.cb_random, 2, 2, 1, 2)

        right.addWidget(settings_group)

        # Képek
        img_group = QGroupBox("KÉPEK")
        img_layout = QVBoxLayout(img_group)
        img_layout.setContentsMargins(10, 16, 10, 10)
        img_layout.setSpacing(8)

        # Gombok
        img_btn_row = QHBoxLayout()
        img_btn_row.setSpacing(6)

        self.btn_add_images = QPushButton("Képek hozzáadása...")
        self.btn_add_images.clicked.connect(self._add_images)
        img_btn_row.addWidget(self.btn_add_images)

        self.btn_add_folder = QPushButton("Mappa hozzáadása...")
        self.btn_add_folder.clicked.connect(self._add_folder)
        img_btn_row.addWidget(self.btn_add_folder)

        self.btn_remove_image = QPushButton("Kijelölt törlése")
        self.btn_remove_image.setStyleSheet(
            f"color: {PALETTE.get('accent_danger', '#f85149')};"
        )
        self.btn_remove_image.clicked.connect(self._remove_selected_images)
        img_btn_row.addWidget(self.btn_remove_image)

        self.btn_clear_images = QPushButton("Összes törlése")
        self.btn_clear_images.clicked.connect(self._clear_images)
        img_btn_row.addWidget(self.btn_clear_images)

        img_btn_row.addStretch()

        self.lbl_img_count = QLabel("0 kép")
        self.lbl_img_count.setStyleSheet(
            f"color: {PALETTE.get('text_secondary', '#a0a0a8')}; "
            f"font-weight: 600;"
        )
        img_btn_row.addWidget(self.lbl_img_count)

        img_layout.addLayout(img_btn_row)

        # Képlista
        self.img_list = ImageListWidget()
        self.img_list.order_changed.connect(self._on_image_order_changed)
        self.img_list.itemDoubleClicked.connect(self._preview_image)
        img_layout.addWidget(self.img_list, stretch=1)

        right.addWidget(img_group, stretch=1)

        # Összesítő
        summary_group = QGroupBox("ÖSSZESÍTŐ")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setContentsMargins(10, 16, 10, 10)

        self.lbl_summary = QLabel("-")
        self.lbl_summary.setStyleSheet(
            f"color: {PALETTE.get('text_primary', '#e1e1e6')}; "
            f"font-size: 12px; font-family: 'Consolas', monospace;"
        )
        summary_layout.addWidget(self.lbl_summary)
        summary_layout.addStretch()
        right.addWidget(summary_group)

        # Alsó gombok
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        self.btn_save = QPushButton("Mentés")
        self.btn_save.clicked.connect(self.save_to_disk)
        bottom_row.addWidget(self.btn_save)

        self.btn_reload = QPushButton("Újratöltés")
        self.btn_reload.clicked.connect(self._load_from_disk)
        bottom_row.addWidget(self.btn_reload)

        bottom_row.addStretch()
        right.addLayout(bottom_row)

        right_wrap = QWidget()
        right_wrap.setLayout(right)
        root.addWidget(right_wrap, stretch=1)

        # Kezdeti állapot
        self._set_editor_enabled(False)

    # ==========================================================
    # UI ÁLLAPOT
    # ==========================================================
    def _set_editor_enabled(self, enabled: bool):
        for w in (
            self.cb_active, self.slider_time, self.spin_time,
            self.spin_rep, self.cb_random,
            self.btn_add_images, self.btn_add_folder,
            self.btn_remove_image, self.btn_clear_images,
            self.img_list,
        ):
            w.setEnabled(enabled)

    # ==========================================================
    # DISK I/O
    # ==========================================================
    def _load_from_disk(self):
        self._loading = True
        self.categories.clear()

        if os.path.isfile(self._categories_json):
            try:
                with open(self._categories_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data.get("categories", []):
                    cat = StimulusCategory.from_dict(item)
                    # Ha a path üres, származtassuk a névből
                    if not cat.path:
                        cat.path = os.path.join(self.stimuli_dir, cat.name)
                    # Képek szinkronizálása a mappával
                    cat.images = self._sync_images(cat)
                    self.categories.append(cat)
            except Exception as e:
                print(f"[STIM] JSON hiba: {e}")

        # Ha nincs JSON, de vannak mappák, felismerjük őket
        if not self.categories:
            self._discover_folders()

        self._loading = False
        self._refresh_cat_list()
        self._update_summary()

    def save_to_disk(self):
        try:
            data = {
                "categories": [c.to_dict() for c in self.categories]
            }
            with open(self._categories_json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.categories_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Nem sikerült menteni:\n{e}")

    def _discover_folders(self):
        """Ha nincs categories.json, a stimuli/ alkönyvtáraiból építünk kategóriákat."""
        for entry in sorted(os.listdir(self.stimuli_dir)):
            full = os.path.join(self.stimuli_dir, entry)
            if os.path.isdir(full):
                cat = StimulusCategory(entry, full)
                cat.images = self._sync_images(cat)
                self.categories.append(cat)

    def _sync_images(self, cat: StimulusCategory) -> List[str]:
        """A mappában lévő képek listázása (a mentett sorrend megtartásával)."""
        if not cat.path or not os.path.isdir(cat.path):
            return list(cat.images)

        on_disk = {
            f for f in os.listdir(cat.path)
            if f.lower().endswith(IMAGE_EXTS)
        }
        # A mentett sorrendből csak azok, amik még léteznek
        ordered = [img for img in cat.images if img in on_disk]
        # Új fájlok hozzáfűzése a végére
        for f in sorted(on_disk):
            if f not in ordered:
                ordered.append(f)
        return ordered

    # ==========================================================
    # KATEGÓRIA-LISTA
    # ==========================================================
    def _refresh_cat_list(self):
        prev_row = self.cat_list.currentRow()
        self.cat_list.blockSignals(True)
        self.cat_list.clear()
        for cat in self.categories:
            item = QListWidgetItem(cat.name)
            # Aktív állapot szürkítés
            if not cat.active:
                item.setForeground(QColor(PALETTE.get('text_muted', '#6e6e76')))
            # Képszám
            item.setToolTip(
                f"{cat.name}\n{len(cat.images)} kép\n"
                f"Idő: {cat.display_time:.1f} s × {cat.repetitions}"
            )
            self.cat_list.addItem(item)
        self.cat_list.blockSignals(False)

        if 0 <= prev_row < self.cat_list.count():
            self.cat_list.setCurrentRow(prev_row)
        elif self.cat_list.count() > 0:
            self.cat_list.setCurrentRow(0)

    def _on_category_selected(self, row: int):
        if row < 0 or row >= len(self.categories):
            self._current_index = -1
            self.lbl_cat_title.setText("Válassz kategóriát")
            self._set_editor_enabled(False)
            return
        self._current_index = row
        self._load_category_to_editor()

    def _on_category_order_changed(self):
        """Drag & drop után újraépítjük a kategória-sorrendet a listanézetből."""
        new_order: List[StimulusCategory] = []
        for i in range(self.cat_list.count()):
            item = self.cat_list.item(i)
            # Név alapján keressük a kategóriát
            name = item.text()
            for cat in self.categories:
                if cat.name == name and cat not in new_order:
                    new_order.append(cat)
                    break
        if len(new_order) == len(self.categories):
            self.categories = new_order
            self.save_to_disk()

    def _move_category(self, direction: int):
        row = self.cat_list.currentRow()
        new_row = row + direction
        if 0 <= row < len(self.categories) and 0 <= new_row < len(self.categories):
            self.categories[row], self.categories[new_row] = \
                self.categories[new_row], self.categories[row]
            self._refresh_cat_list()
            self.cat_list.setCurrentRow(new_row)
            self.save_to_disk()

    # ==========================================================
    # KATEGÓRIA MŰVELETEK
    # ==========================================================
    def _new_category(self):
        name, ok = QInputDialog.getText(
            self, "Új kategória", "Kategória neve:"
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        if any(c.name == name for c in self.categories):
            QMessageBox.warning(self, "Figyelem", f"Már létezik ilyen kategória: {name}")
            return

        path = os.path.join(self.stimuli_dir, name)
        os.makedirs(path, exist_ok=True)

        cat = StimulusCategory(name, path)
        self.categories.append(cat)
        self._refresh_cat_list()
        self.cat_list.setCurrentRow(len(self.categories) - 1)
        self.save_to_disk()

    def _rename_category(self):
        if self._current_index < 0:
            return
        cat = self.categories[self._current_index]
        new_name, ok = QInputDialog.getText(
            self, "Átnevezés", "Új név:", text=cat.name
        )
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        if new_name == cat.name:
            return
        if any(c.name == new_name for c in self.categories):
            QMessageBox.warning(self, "Figyelem", f"Már létezik: {new_name}")
            return

        old_path = cat.path
        new_path = os.path.join(self.stimuli_dir, new_name)

        # Mappa átnevezése
        try:
            if os.path.isdir(old_path) and not os.path.exists(new_path):
                os.rename(old_path, new_path)
        except Exception as e:
            QMessageBox.warning(self, "Figyelem", f"Mappa átnevezése nem sikerült:\n{e}")

        cat.name = new_name
        cat.path = new_path
        self._refresh_cat_list()
        self._load_category_to_editor()
        self.save_to_disk()

    def _delete_category(self):
        if self._current_index < 0:
            return
        cat = self.categories[self._current_index]
        ans = QMessageBox.question(
            self, "Törlés",
            f"Biztosan törlöd a(z) '{cat.name}' kategóriát?\n"
            f"A mappa és a benne lévő képek is törlődnek!",
            QMessageBox.Yes | QMessageBox.No
        )
        if ans != QMessageBox.Yes:
            return

        try:
            if os.path.isdir(cat.path):
                shutil.rmtree(cat.path)
        except Exception as e:
            print(f"[STIM] Mappa törlés hiba: {e}")

        del self.categories[self._current_index]
        self._refresh_cat_list()
        self.save_to_disk()

    # ==========================================================
    # KATEGÓRIA BETÖLTÉS AZ EDITORBA
    # ==========================================================
    def _load_category_to_editor(self):
        if self._current_index < 0 or self._current_index >= len(self.categories):
            return
        cat = self.categories[self._current_index]
        self._loading = True

        self.lbl_cat_title.setText(f"Kategória: {cat.name}")
        self.cb_active.setChecked(cat.active)
        self.slider_time.setValue(int(cat.display_time * 10))
        self.spin_time.setValue(cat.display_time)
        self.spin_rep.setValue(cat.repetitions)
        self.cb_random.setChecked(cat.random_order)

        self._refresh_image_list()
        self._set_editor_enabled(True)
        self._loading = False

    # ==========================================================
    # KÉP-LISTA
    # ==========================================================
    def _refresh_image_list(self):
        self.img_list.clear()
        if self._current_index < 0:
            self.lbl_img_count.setText("0 kép")
            return
        cat = self.categories[self._current_index]
        for img in cat.images:
            full = os.path.join(cat.path, img)
            if not os.path.isfile(full):
                continue
            item = QListWidgetItem()
            item.setText(img)
            pm = QPixmap(full)
            if not pm.isNull():
                icon = QIcon(pm.scaled(96, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                item.setIcon(icon)
            item.setToolTip(full)
            item.setData(Qt.UserRole, img)
            self.img_list.addItem(item)
        self.lbl_img_count.setText(f"{len(cat.images)} kép")

    def _on_image_order_changed(self):
        if self._loading or self._current_index < 0:
            return
        cat = self.categories[self._current_index]
        new_imgs: List[str] = []
        for i in range(self.img_list.count()):
            item = self.img_list.item(i)
            new_imgs.append(item.data(Qt.UserRole))
        cat.images = new_imgs
        self.save_to_disk()

    # ==========================================================
    # KÉPEK HOZZÁADÁSA / TÖRLÉSE
    # ==========================================================
    def _add_images(self):
        if self._current_index < 0:
            return
        cat = self.categories[self._current_index]
        files, _ = QFileDialog.getOpenFileNames(
            self, "Képek kiválasztása", "",
            "Képek (*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff)"
        )
        if not files:
            return
        self._import_images(files)

    def _add_folder(self):
        if self._current_index < 0:
            return
        folder = QFileDialog.getExistingDirectory(self, "Mappa kiválasztása")
        if not folder:
            return
        files = []
        for fname in sorted(os.listdir(folder)):
            if fname.lower().endswith(IMAGE_EXTS):
                files.append(os.path.join(folder, fname))
        if not files:
            QMessageBox.information(self, "Info", "A mappában nincs támogatott kép.")
            return
        self._import_images(files)

    def _import_images(self, files: List[str]):
        cat = self.categories[self._current_index]
        os.makedirs(cat.path, exist_ok=True)

        added = 0
        for src in files:
            fname = os.path.basename(src)
            dst = os.path.join(cat.path, fname)

            # Ha már van ilyen nevű fájl, prefixet adunk
            base, ext = os.path.splitext(fname)
            counter = 1
            while os.path.exists(dst):
                fname = f"{base}_{counter}{ext}"
                dst = os.path.join(cat.path, fname)
                counter += 1

            try:
                shutil.copy2(src, dst)
                if fname not in cat.images:
                    cat.images.append(fname)
                added += 1
            except Exception as e:
                print(f"[STIM] Másolási hiba ({src}): {e}")

        self._refresh_image_list()
        self._refresh_cat_list()
        self._update_summary()
        self.save_to_disk()
        if added:
            QMessageBox.information(self, "Siker", f"{added} kép hozzáadva.")

    def _remove_selected_images(self):
        if self._current_index < 0:
            return
        sel = self.img_list.selectedItems()
        if not sel:
            return
        cat = self.categories[self._current_index]

        ans = QMessageBox.question(
            self, "Törlés",
            f"Biztosan törlöd a kijelölt {len(sel)} képet?\n(A fájlok is törlődnek!)",
            QMessageBox.Yes | QMessageBox.No
        )
        if ans != QMessageBox.Yes:
            return

        to_remove = [it.data(Qt.UserRole) for it in sel]
        for fname in to_remove:
            full = os.path.join(cat.path, fname)
            try:
                if os.path.isfile(full):
                    os.remove(full)
            except Exception as e:
                print(f"[STIM] Törlési hiba ({fname}): {e}")
            if fname in cat.images:
                cat.images.remove(fname)

        self._refresh_image_list()
        self._refresh_cat_list()
        self._update_summary()
        self.save_to_disk()

    def _clear_images(self):
        if self._current_index < 0:
            return
        cat = self.categories[self._current_index]
        if not cat.images:
            return
        ans = QMessageBox.question(
            self, "Törlés",
            f"Biztosan törlöd az ÖSSZES képet a(z) '{cat.name}' kategóriából?\n"
            f"A fájlok is törlődnek!",
            QMessageBox.Yes | QMessageBox.No
        )
        if ans != QMessageBox.Yes:
            return

        for fname in list(cat.images):
            full = os.path.join(cat.path, fname)
            try:
                if os.path.isfile(full):
                    os.remove(full)
            except Exception as e:
                print(f"[STIM] Törlési hiba ({fname}): {e}")
        cat.images.clear()

        self._refresh_image_list()
        self._refresh_cat_list()
        self._update_summary()
        self.save_to_disk()

    def _preview_image(self, item: QListWidgetItem):
        if self._current_index < 0:
            return
        cat = self.categories[self._current_index]
        fname = item.data(Qt.UserRole)
        full = os.path.join(cat.path, fname)
        if not os.path.isfile(full):
            return

        # Egyszerű előnézet dialógusban
        from PyQt5.QtWidgets import QDialog, QVBoxLayout as VBox
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Előnézet: {fname}")
        v = VBox(dlg)
        lbl = QLabel()
        pm = QPixmap(full)
        screen = self.screen().availableGeometry() if self.screen() else None
        max_w = 1200
        max_h = 800
        if pm.width() > max_w or pm.height() > max_h:
            pm = pm.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        lbl.setPixmap(pm)
        v.addWidget(lbl)
        dlg.exec_()

    # ==========================================================
    # BEÁLLÍTÁSOK
    # ==========================================================
    def _on_time_slider(self, value: int):
        if self._loading:
            return
        val = value / 10.0
        self._loading = True
        self.spin_time.setValue(val)
        self._loading = False
        self._apply_settings(display_time=val)

    def _on_time_spin(self, value: float):
        if self._loading:
            return
        self._loading = True
        self.slider_time.setValue(int(value * 10))
        self._loading = False
        self._apply_settings(display_time=value)

    def _on_settings_changed(self):
        if self._loading:
            return
        self._apply_settings()

    def _apply_settings(self, display_time: Optional[float] = None):
        if self._current_index < 0:
            return
        cat = self.categories[self._current_index]
        cat.active = self.cb_active.isChecked()
        cat.display_time = float(self.spin_time.value() if display_time is None else display_time)
        cat.repetitions = int(self.spin_rep.value())
        cat.random_order = self.cb_random.isChecked()

        # Listaelem frissítése
        item = self.cat_list.item(self._current_index)
        if item:
            item.setText(cat.name)
            if not cat.active:
                item.setForeground(QColor(PALETTE.get('text_muted', '#6e6e76')))
            else:
                item.setForeground(QColor(PALETTE.get('text_primary', '#e1e1e6')))
            item.setToolTip(
                f"{cat.name}\n{len(cat.images)} kép\n"
                f"Idő: {cat.display_time:.1f} s × {cat.repetitions}"
            )

        self._update_summary()
        self.save_to_disk()

    # ==========================================================
    # ÖSSZESÍTŐ
    # ==========================================================
    def _update_summary(self):
        total_cats = len(self.categories)
        active_cats = sum(1 for c in self.categories if c.active)
        total_imgs = sum(len(c.images) for c in self.categories if c.active)

        total_trials = 0
        total_time = 0.0
        for c in self.categories:
            if not c.active:
                continue
            n = len(c.images) * c.repetitions
            total_trials += n
            # fixáció 1s + kép megjelenítés
            total_time += n * (c.display_time + 1.0)

        mins = int(total_time // 60)
        secs = int(total_time % 60)

        self.lbl_summary.setText(
            f"Kategóriák: {active_cats}/{total_cats} aktív  |  "
            f"Képek: {total_imgs}  |  "
            f"Próbák: {total_trials}  |  "
            f"Becsült idő: {mins:02d}:{secs:02d}"
        )

    # ==========================================================
    # PUBLIKUS API – a MainWindow használhatja
    # ==========================================================
    def get_active_categories(self) -> Dict[str, int]:
        """Visszaadja a {kategória_név: próbaszám} szótárt az aktív kategóriákból."""
        result = {}
        for c in self.categories:
            if c.active and c.images:
                result[c.name] = len(c.images) * c.repetitions
        return result

    def get_category_metadata(self) -> Dict[str, dict]:
        """Visszaadja a kategóriák teljes metaadatát (idő, sorrend, stb.)."""
        meta = {}
        for c in self.categories:
            meta[c.name] = {
                "path": c.path,
                "images": list(c.images),
                "display_time": c.display_time,
                "repetitions": c.repetitions,
                "random_order": c.random_order,
                "active": c.active,
            }
        return meta