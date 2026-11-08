# ui/eye_widget.py
# 3D Szemmodell és Tekintet-Orientációs Modul (Clinical & Lab Edition)
# Illeszkedik a Tobii Pro Lab letisztult sötétszürke mérőfelületéhez

import math
import numpy as np
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPolygonF
)
from OpenGL.GL import *
from OpenGL.GLU import *

from config.settings import PALETTE


class EyeGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 220)
        self.setMouseTracking(True)

        # ---- Virtuális laboratóriumi kamera ----
        self.camera_dist = 3.8
        self.cam_rx = -6.0
        self.cam_ry = 0.0

        # ---- Szem orientáció (Kinematika) ----
        self.pitch = 0.0
        self.yaw = 0.0
        self.target_pitch = 0.0
        self.target_yaw = 0.0

        # ---- Pupilla állapota ----
        self.pupil_size = 1.0
        self.target_pupil = 1.0
        self.raw_pupil = 1.0
        self.confidence = 0.0

        # ---- Szűrők és predikció ----
        self._prev_target_pitch = 0.0
        self._prev_target_yaw = 0.0
        self._vel_pitch = 0.0
        self._vel_yaw = 0.0

        self.EYE_SMOOTH_SLOW = 0.08
        self.EYE_SMOOTH_FAST = 0.28
        self.EYE_FAST_THRESHOLD = 1.2

        self.PUPIL_SMOOTH = 0.06
        self.PUPIL_DEADZONE = 0.015
        self.PUPIL_HISTORY_LEN = 10
        self._pupil_history = []
        self.PREDICT_WEIGHT = 0.15

        self._last_mouse = None

        # ---- Geometriai felbontások ----
        self.SPHERE_LAT = 64
        self.SPHERE_LON = 64
        self.IRIS_SEG = 120
        self.IRIS_RADIUS = 0.45

        self._build_geometry()

        # ~60 FPS frissítési frekvencia
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._smooth_update)
        self.anim_timer.start(16)

    # -----------------------------------------------------------------
    # Geometria előkészítése
    # -----------------------------------------------------------------
    def _build_geometry(self):
        lat, lon = self.SPHERE_LAT, self.SPHERE_LON
        self._sphere_verts = []
        for i in range(lat + 1):
            la = math.pi * (-0.5 + i / lat)
            z = math.sin(la)
            zr = math.cos(la)
            row = []
            for j in range(lon + 1):
                lo = 2 * math.pi * j / lon
                row.append((math.cos(lo) * zr, math.sin(lo) * zr, z))
            self._sphere_verts.append(row)

    # -----------------------------------------------------------------
    # OpenGL Inicializáció
    # -----------------------------------------------------------------
    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        # Háttér: Tobii mély antracitszürke (#1e1e20)
        glClearColor(0.118, 0.118, 0.125, 1.0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(36, w / max(h, 1), 0.05, 100.0)
        glMatrixMode(GL_MODELVIEW)

    # -----------------------------------------------------------------
    # Rajzolási ciklus
    # -----------------------------------------------------------------
    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -self.camera_dist)
        glRotatef(self.cam_rx, 1, 0, 0)
        glRotatef(self.cam_ry, 0, 1, 0)

        self._setup_lights()

        glPushMatrix()
        glRotatef(self.yaw, 0, 1, 0)
        glRotatef(-self.pitch, 1, 0, 0)

        self._draw_sclera()
        self._draw_iris()
        self._draw_pupil()

        glPopMatrix()

        # Letisztult 2D orvosi telemetria fedvények
        self._draw_telemetry_overlay()
        self._draw_gaze_polar_overlay()

    # -----------------------------------------------------------------
    # Világítás: Természetes laboratóriumi fényviszonyok
    # -----------------------------------------------------------------
    def _setup_lights(self):
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        glLightfv(GL_LIGHT0, GL_POSITION, [2.5, 3.0, 4.0, 0.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.25, 0.25, 0.28, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  [0.75, 0.78, 0.82, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.60, 0.60, 0.65, 1.0])

        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.5, 0.5, 0.55, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 64.0)

    # -----------------------------------------------------------------
    # Szemfehérje (Sclera): Finom anatómiai árnyékolás
    # -----------------------------------------------------------------
    def _draw_sclera(self):
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        lat, lon = self.SPHERE_LAT, self.SPHERE_LON
        step = 4

        # Diszkrét szürke-fehér rácsozat
        for i in range(0, lat, step):
            for j in range(0, lon, step):
                glColor4f(0.55, 0.58, 0.62, 0.22)
                glBegin(GL_LINES)
                if i + step <= lat:
                    glVertex3fv(self._sphere_verts[i][j])
                    glVertex3fv(self._sphere_verts[i + step][j])
                if j + step <= lon:
                    glVertex3fv(self._sphere_verts[i][j])
                    glVertex3fv(self._sphere_verts[i][j + step])
                glEnd()

    # -----------------------------------------------------------------
    # Írisz: Orvosi kobaltkék struktúra
    # -----------------------------------------------------------------
    def _draw_iris(self):
        glDisable(GL_LIGHTING)
        ir = self.IRIS_RADIUS

        # Külső orvosi határoló gyűrű (Tobii kék)
        glLineWidth(1.6)
        glColor4f(0.18, 0.55, 0.94, 0.85)
        iz2 = math.sqrt(max(0.0, 1.0 - ir * ir))
        glBegin(GL_LINE_LOOP)
        for i in range(self.IRIS_SEG):
            a = 2 * math.pi * i / self.IRIS_SEG
            glVertex3f(math.cos(a) * ir, math.sin(a) * ir, iz2)
        glEnd()

        # Írisz kitöltés
        glEnable(GL_BLEND)
        glColor4f(0.08, 0.24, 0.42, 0.40)
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(0, 0, iz2)
        for i in range(self.IRIS_SEG + 1):
            a = 2 * math.pi * i / self.IRIS_SEG
            glVertex3f(math.cos(a) * ir, math.sin(a) * ir, iz2)
        glEnd()

        # Belső rostok
        glLineWidth(1.0)
        glColor4f(0.20, 0.65, 1.00, 0.25)
        glBegin(GL_LINES)
        for i in range(0, self.IRIS_SEG, 3):
            a = 2 * math.pi * i / self.IRIS_SEG
            r_in = ir * 0.35
            glVertex3f(math.cos(a) * r_in, math.sin(a) * r_in, iz2)
            glVertex3f(math.cos(a) * ir, math.sin(a) * ir, iz2)
        glEnd()

    # -----------------------------------------------------------------
    # Pupilla szegmens
    # -----------------------------------------------------------------
    def _draw_pupil(self):
        glDisable(GL_LIGHTING)
        glDisable(GL_BLEND)

        ir = self.IRIS_RADIUS
        pr = 0.14 * self.pupil_size
        pr = float(np.clip(pr, 0.05, ir * 0.85))
        pz = math.sqrt(max(0.0, 1.0 - pr * pr))
        seg = 64

        # Mélyfekete pupillatest
        glColor3f(0.02, 0.02, 0.03)
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(0, 0, pz)
        for i in range(seg + 1):
            a = 2 * math.pi * i / seg
            glVertex3f(math.cos(a) * pr, math.sin(a) * pr, pz)
        glEnd()

        # Finom élkontúr
        glLineWidth(1.2)
        glColor3f(0.12, 0.15, 0.18)
        glBegin(GL_LINE_LOOP)
        for i in range(seg):
            a = 2 * math.pi * i / seg
            glVertex3f(math.cos(a) * pr, math.sin(a) * pr, pz)
        glEnd()

    # -----------------------------------------------------------------
    # 2D OVERLAY: Bal felső numerikus telemetria kártya
    # -----------------------------------------------------------------
    def _draw_telemetry_overlay(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        px, py, pw, ph = 10, 10, 145, 78

        # Visszafogott, szürke kártyaháttér
        painter.setPen(QPen(QColor(PALETTE['border']), 1))
        painter.setBrush(QColor(34, 34, 37, 210))
        painter.drawRect(px, py, pw, ph)

        painter.setPen(QColor(PALETTE['text_muted']))
        painter.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
        painter.drawText(px + 8, py + 15, "TELEMETRIA CSATORNA")

        painter.setFont(QFont("Consolas", 8))
        y = py + 32
        lh = 14

        painter.setPen(QColor(PALETTE['text_secondary']))
        painter.drawText(px + 8, y, "Nyers méret:")
        painter.setPen(QColor(PALETTE['text_primary']))
        painter.drawText(px + 90, y, f"{self.raw_pupil:.2f}")

        y += lh
        painter.setPen(QColor(PALETTE['text_secondary']))
        painter.drawText(px + 8, y, "Simított:")
        painter.setPen(QColor(PALETTE['accent_primary']))
        painter.drawText(px + 90, y, f"{self.pupil_size:.2f}")

        y += lh
        painter.setPen(QColor(PALETTE['text_secondary']))
        painter.drawText(px + 8, y, "Stabilitás:")
        conf_color = QColor(PALETTE['accent_success']) if self.confidence > 0.4 else QColor(PALETTE['accent_warning'])
        painter.setPen(conf_color)
        painter.drawText(px + 90, y, f"{self.confidence * 100:.0f}%")

        painter.end()

    # -----------------------------------------------------------------
    # 2D OVERLAY: Jobb felső poláris szögmérő (Tekintetvektor)
    # -----------------------------------------------------------------
    def _draw_gaze_polar_overlay(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pw, ph = 120, 120
        px = self.width() - pw - 10
        py = 10

        # Háttérlap
        painter.setPen(QPen(QColor(PALETTE['border']), 1))
        painter.setBrush(QColor(34, 34, 37, 210))
        painter.drawRect(px, py, pw, ph)

        painter.setPen(QColor(PALETTE['text_muted']))
        painter.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
        painter.drawText(px + 8, py + 15, "TEKINTET VEKTOR")

        cx = px + pw // 2
        cy = py + 56
        r = 30

        # Koordinátakereszt és koncentrikus körök
        painter.setPen(QPen(QColor(PALETTE['border_light']), 1, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        painter.drawEllipse(cx - r // 2, cy - r // 2, r, r)

        painter.drawLine(cx - r - 2, cy, cx + r + 2, cy)
        painter.drawLine(cx, cy - r - 2, cx, cy + r + 2)

        # Normált vektorvektor rajzolása
        max_yaw, max_pitch = 40.0, 30.0
        yaw_n = float(np.clip(self.yaw / max_yaw, -1.0, 1.0))
        pitch_n = float(np.clip(self.pitch / max_pitch, -1.0, 1.0))

        dx = yaw_n * r
        dy = -pitch_n * r

        # Tekintetvektor iránya és pontja
        painter.setPen(QPen(QColor(PALETTE['accent_primary']), 1.8))
        painter.drawLine(int(cx), int(cy), int(cx + dx), int(cy + dy))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(PALETTE['accent_primary'])))
        painter.drawEllipse(QPointF(cx + dx, cy + dy), 3, 3)

        # Numerikus értékek lent
        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QColor(PALETTE['text_secondary']))
        coord_str = f"Y:{self.yaw:+4.1f}° P:{self.pitch:+4.1f}°"
        painter.drawText(px + 10, py + ph - 8, coord_str)

        painter.end()

    # -----------------------------------------------------------------
    # Mozgásinterpoláció és szűrés
    # -----------------------------------------------------------------
    def _smooth_update(self):
        d_pitch = self.target_pitch - self.pitch
        speed_p = abs(d_pitch)
        alpha_p = self.EYE_SMOOTH_FAST if speed_p > self.EYE_FAST_THRESHOLD else self.EYE_SMOOTH_SLOW
        self.pitch += d_pitch * alpha_p

        d_yaw = self.target_yaw - self.yaw
        speed_y = abs(d_yaw)
        alpha_y = self.EYE_SMOOTH_FAST if speed_y > self.EYE_FAST_THRESHOLD else self.EYE_SMOOTH_SLOW
        self.yaw += d_yaw * alpha_y

        d_pupil = self.target_pupil - self.pupil_size
        if abs(d_pupil) > self.PUPIL_DEADZONE:
            self.pupil_size += d_pupil * self.PUPIL_SMOOTH

        self.pupil_size = max(0.4, min(2.4, self.pupil_size))
        self.update()

    # -----------------------------------------------------------------
    # Adatfogadás a trackertől
    # -----------------------------------------------------------------
    def set_eye_pose(self, pitch, yaw, pupil_size, confidence):
        new_pitch = float(pitch)
        new_yaw = float(yaw)

        vel_pitch = new_pitch - self._prev_target_pitch
        vel_yaw = new_yaw - self._prev_target_yaw

        self._vel_pitch = self._vel_pitch * 0.7 + vel_pitch * 0.3
        self._vel_yaw = self._vel_yaw * 0.7 + vel_yaw * 0.3

        self.target_pitch = new_pitch + self._vel_pitch * self.PREDICT_WEIGHT
        self.target_yaw = new_yaw + self._vel_yaw * self.PREDICT_WEIGHT

        self._prev_target_pitch = new_pitch
        self._prev_target_yaw = new_yaw

        new_pupil = float(pupil_size)
        self.raw_pupil = new_pupil

        self._pupil_history.append(new_pupil)
        if len(self._pupil_history) > self.PUPIL_HISTORY_LEN:
            self._pupil_history.pop(0)

        # Medián szűrés a kiugró minták kizárására
        if len(self._pupil_history) >= 3:
            self.target_pupil = float(np.median(self._pupil_history))
        else:
            self.target_pupil = new_pupil

        self.confidence = float(confidence)

    def set_eye_style(self, style):
        # A stílusváltás kompatibilitási célból meghagyva
        pass

    # -----------------------------------------------------------------
    # Egérmozgások kezelése (Kameranézet igazítása)
    # -----------------------------------------------------------------
    def mousePressEvent(self, e):
        self._last_mouse = e.pos()

    def mouseMoveEvent(self, e):
        if self._last_mouse and e.buttons():
            dx = e.x() - self._last_mouse.x()
            dy = e.y() - self._last_mouse.y()
            if e.buttons() & Qt.LeftButton:
                self.cam_ry += dx * 0.35
                self.cam_rx += dy * 0.35
            elif e.buttons() & Qt.RightButton:
                self.camera_dist = max(1.5, min(5.5, self.camera_dist + dy * 0.01))
            self._last_mouse = e.pos()
            self.update()

    def wheelEvent(self, e):
        self.camera_dist = max(1.5, min(5.5, self.camera_dist - e.angleDelta().y() / 800))
        self.update()