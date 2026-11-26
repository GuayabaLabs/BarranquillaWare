"""Entrada opcional de gestos MediaPipe, aislada del motor y de los minijuegos.

La cámara nunca es requisito para arrancar: cuando faltan dependencias, cámara o
permisos, el adaptador queda inactivo y el juego conserva sus controles normales.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from typing import Optional

HAVE_CAMERA = False
CAMERA_IMPORT_ERROR = ""
try:
    import cv2
    import mediapipe as mp
    HAVE_CAMERA = True
except Exception as exc:
    cv2 = None
    mp = None
    CAMERA_IMPORT_ERROR = str(exc)


class CameraGestureInput:
    """Detector singleton mínimo y reutilizable de gestos y visión MediaPipe."""
    _instance: Optional['CameraGestureInput'] = None
    MIN_HAND_SCALE: float = 0.065
    RELATIVE_SCALE_RATIO: float = 0.55
    MAX_TRACK_JUMP: float = 0.30

    @classmethod
    def get_instance(cls) -> 'CameraGestureInput':
        if cls._instance is None:
            cls._instance = CameraGestureInput()
        return cls._instance

    def __init__(self) -> None:
        self.available = HAVE_CAMERA
        self.enabled = False
        self.suspended = False
        self.error = CAMERA_IMPORT_ERROR if not HAVE_CAMERA else ""
        self._last_start_attempt = 0.0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._finger_pressed = [False] * 4
        self._finger_just_pressed = [False] * 4
        self._previous = [False] * 4
        self._cooldowns = [0.0] * 4
        self.hand_x = 0.5
        self.hand_y = 0.5
        self.hand_detected = False
        self.pointing_direction: Optional[tuple[float, float]] = None
        self.pinch_active = False
        self._pinch_just_pressed = False
        self._previous_pinch = False
        self.hand_raised = False
        self.open_palm = False
        self._hand_raise_just_pressed = False
        self._fist_just_pressed = False
        self._punch_just_pressed = False
        self._previous_fist = False
        self._previous_raised = False
        self._previous_hand_y = 0.5
        self._tracked_palm: Optional[tuple[float, float]] = None
        self._tracked_lost_frames: int = 0
        self._hands: list[tuple[float, float]] = []

    def start(self) -> bool:
        from core.settings import SettingsManager
        if not SettingsManager.get_instance().get("camera_enabled", True):
            return False
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":
            return False
        self.suspended = False
        if self.enabled:
            return True
        if not HAVE_CAMERA:
            self.error = (
                f"No se pudo cargar MediaPipe/OpenCV: {CAMERA_IMPORT_ERROR}"
                if CAMERA_IMPORT_ERROR
                else "MediaPipe/OpenCV no están instalados"
            )
            return False
        if self._thread and self._thread.is_alive():
            return False
        self._last_start_attempt = time.monotonic()
        self.available = True
        self.error = ""
        self._stop.clear()
        self.enabled = True
        self._thread = threading.Thread(target=self._run, name="bw-mediapipe", daemon=True)
        self._thread.start()
        return True

    def set_enabled(self, enabled: bool) -> None:
        """Guarda la elección del usuario y la aplica a todos los juegos."""
        from core.settings import SettingsManager
        SettingsManager.get_instance().set("camera_enabled", bool(enabled))
        if enabled:
            self.resume()
        else:
            self.suspend()

    def keep_alive(self, retry_interval: float = 2.0) -> None:
        """Reintenta abrir la cámara si falló, con pausa para evitar bucles rápidos."""
        from core.settings import SettingsManager
        if not SettingsManager.get_instance().get("camera_enabled", True):
            return
        if self.suspended or not HAVE_CAMERA or self.enabled:
            return
        if time.monotonic() - self._last_start_attempt >= retry_interval:
            self.start()

    def suspend(self) -> None:
        """Pausa la webcam para un estado que necesita acceso exclusivo a ella."""
        self.suspended = True
        self.stop()

    def resume(self) -> bool:
        """Reanuda la webcam compartida después de un estado exclusivo."""
        self.suspended = False
        return self.start()

    def stop(self) -> None:
        self._stop.set()
        self.enabled = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.4)
        # No arrancar otro capturador mientras el anterior aún libera la webcam.
        if not self._thread or not self._thread.is_alive():
            self._thread = None
        with self._lock:
            self._finger_pressed = [False] * 4
            self._finger_just_pressed = [False] * 4
            self._previous = [False] * 4
            self._fist_just_pressed = False
            self._punch_just_pressed = False
            self._hand_raise_just_pressed = False
            self._previous_fist = False
            self._previous_raised = False
            self.open_palm = False
            self._tracked_palm = None
            self._tracked_lost_frames = 0
            self._hands = []

    def consume_finger(self, index: int) -> bool:
        if not 0 <= index < 4:
            return False
        with self._lock:
            result = self._finger_just_pressed[index]
            self._finger_just_pressed[index] = False
            return result

    def consume_fist(self) -> bool:
        """Devuelve un flanco de puño cerrado; sirve como acción única."""
        with self._lock:
            result = self._fist_just_pressed
            self._fist_just_pressed = False
            return result

    def consume_click(self) -> bool:
        """Consume solo el pellizco; el puño queda disponible para el minijuego."""
        with self._lock:
            result = self._pinch_just_pressed
            self._pinch_just_pressed = False
            return result

    def is_clicking(self) -> bool:
        with self._lock:
            return self.pinch_active or bool(self._previous_fist)

    def is_pinching(self) -> bool:
        """Pellizco sostenido, separado de los eventos de un fotograma."""
        with self._lock:
            return bool(self.enabled and self.hand_detected and self.pinch_active)

    def is_fist(self) -> bool:
        """Puño cerrado sostenido."""
        with self._lock:
            return bool(self.enabled and self.hand_detected and self._previous_fist)

    def is_open_palm(self) -> bool:
        """Palma abierta sostenida, excluyendo pellizco o puño."""
        with self._lock:
            return bool(
                self.enabled
                and self.hand_detected
                and self.open_palm
                and not self.pinch_active
                and not self._previous_fist
            )

    def is_hand_present(self) -> bool:
        with self._lock:
            return self.hand_detected

    def consume_hand_raise(self) -> bool:
        with self._lock:
            result = self._hand_raise_just_pressed
            self._hand_raise_just_pressed = False
            return result

    def consume_punch(self) -> bool:
        with self._lock:
            result = self._punch_just_pressed
            self._punch_just_pressed = False
            return result

    def get_position(self) -> tuple[float, float]:
        with self._lock:
            return self.hand_x, self.hand_y

    def get_hands(self) -> list[tuple[float, float]]:
        """Devuelve la lista de posiciones (x, y) normalizadas de hasta 2 manos."""
        with self._lock:
            return list(getattr(self, "_hands", []))

    def get_pointing_direction(self) -> Optional[tuple[float, float]]:
        """Dirección cardinal (dx, dy) al apuntar con los dedos arriba/abajo/izquierda/derecha."""
        with self._lock:
            return self.pointing_direction if (self.enabled and self.hand_detected) else None

    @staticmethod
    def _hand_scale(lm) -> float:
        """Estima el tamaño aparente de la mano (muñeca LM 0 a nudillo medio LM 9)."""
        return ((lm[0].x - lm[9].x) ** 2 + (lm[0].y - lm[9].y) ** 2) ** 0.5

    @classmethod
    def _filter_foreground_hands(
        cls,
        hand_landmarks_list: list,
        min_scale: Optional[float] = None,
        rel_ratio: Optional[float] = None,
    ) -> list:
        """Descarta manos lejanas o de fondo y conserva hasta 2 manos de primer plano."""
        if not hand_landmarks_list:
            return []
        min_sc = cls.MIN_HAND_SCALE if min_scale is None else min_scale
        ratio = cls.RELATIVE_SCALE_RATIO if rel_ratio is None else rel_ratio
        scaled = []
        for hand in hand_landmarks_list:
            scale = cls._hand_scale(hand.landmark)
            if scale >= min_sc:
                scaled.append((scale, hand))
        if not scaled:
            return []
        max_scale = max(scale for scale, _ in scaled)
        foreground = [
            (scale, hand)
            for scale, hand in scaled
            if scale >= max_scale * ratio
        ]
        foreground.sort(key=lambda item: item[0], reverse=True)
        return [hand for _, hand in foreground[:2]]

    @classmethod
    def _select_primary_hand(
        cls,
        foreground_hands: list,
        tracked_palm: Optional[tuple[float, float]],
        max_jump: Optional[float] = None,
    ):
        """Mantiene la mano principal en seguimiento para evitar saltos con una segunda mano."""
        if not foreground_hands:
            return None, None
        limit = cls.MAX_TRACK_JUMP if max_jump is None else max_jump
        if len(foreground_hands) == 1 or tracked_palm is None:
            chosen = foreground_hands[0]
            lm = chosen.landmark
            return chosen, (lm[9].x, lm[9].y)
        tx, ty = tracked_palm
        best = min(
            foreground_hands,
            key=lambda h: ((h.landmark[9].x - tx) ** 2 + (h.landmark[9].y - ty) ** 2) ** 0.5,
        )
        dist = ((best.landmark[9].x - tx) ** 2 + (best.landmark[9].y - ty) ** 2) ** 0.5
        chosen = best if dist <= limit else foreground_hands[0]
        lm = chosen.landmark
        return chosen, (lm[9].x, lm[9].y)

    @staticmethod
    def _detect_pointing_direction(lm) -> Optional[tuple[float, float]]:
        """Detecta hacia qué dirección cardinal apunta el índice (con anular y meñique plegados)."""
        def dist(a, b):
            return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5

        wrist = lm[0]
        index_ext = dist(lm[8], wrist) > dist(lm[6], wrist) * 1.18
        ring_folded = dist(lm[16], wrist) < dist(lm[14], wrist) * 1.14
        pinky_folded = dist(lm[20], wrist) < dist(lm[18], wrist) * 1.14
        if not (index_ext and ring_folded and pinky_folded):
            return None
        vx = lm[8].x - lm[5].x
        vy = lm[8].y - lm[5].y
        if max(abs(vx), abs(vy)) < 0.055:
            return None
        if max(abs(vx), abs(vy)) < min(abs(vx), abs(vy)) * 1.4:
            return None
        if abs(vx) >= abs(vy):
            return (1.0, 0.0) if vx > 0 else (-1.0, 0.0)
        return (0.0, 1.0) if vy > 0 else (0.0, -1.0)

    def _run(self) -> None:
        cap = None
        if sys.platform.startswith("win") and hasattr(cv2, "CAP_DSHOW"):
            try:
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap.release()
                    cap = None
            except TypeError:
                cap = None
        if cap is None:
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.error = "No se pudo abrir la cámara"
            self.available = False
            self.enabled = False
            cap.release()
            return
        if hasattr(cap, "set"):
            for prop_name, value in (
                ("CAP_PROP_FRAME_WIDTH", 640),
                ("CAP_PROP_FRAME_HEIGHT", 480),
                ("CAP_PROP_BUFFERSIZE", 1),
            ):
                prop = getattr(cv2, prop_name, None)
                if prop is not None:
                    try:
                        cap.set(prop, value)
                    except Exception:
                        pass
        hands = None
        try:
            hands = mp.solutions.hands.Hands(
                static_image_mode=False, max_num_hands=3,
                min_detection_confidence=0.65, min_tracking_confidence=0.60
            )
            last = time.monotonic()
            while self.enabled and not self._stop.is_set():
                ok, frame = cap.read()
                now = time.monotonic()
                dt = min(0.1, max(0.001, now - last))
                last = now
                if not ok:
                    time.sleep(0.03)
                    continue
                rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
                result = hands.process(rgb)
                # Señal de piano: cada dedo plegado equivale a pulsar su carril.
                piano_fingers = [False] * 4
                extended_fingers = [False] * 4
                hand_x, hand_y = 0.5, 0.5
                detected = False
                raised = False
                fist = False
                pinch = False
                pointing_dir = None
                hands_list: list[tuple[float, float]] = []
                foreground = self._filter_foreground_hands(result.multi_hand_landmarks) if result.multi_hand_landmarks else []
                if foreground:
                    detected = True
                    hands_list = [(h.landmark[9].x, h.landmark[9].y) for h in foreground]
                    primary_h, palm_pos = self._select_primary_hand(foreground, self._tracked_palm)
                    self._tracked_palm = palm_pos
                    self._tracked_lost_frames = 0
                    lm = primary_h.landmark
                    # Preferir la mano derecha (en imagen espejada) para apuntar direcciones en el mapa.
                    right_hand_lm = max(foreground, key=lambda h: h.landmark[9].x).landmark
                    pointing_dir = self._detect_pointing_direction(right_hand_lm)
                    # Seguimiento focal en la punta del dedo índice (LM 8) para que el lápiz apunte donde apunta el dedo
                    hand_x, hand_y = lm[8].x, lm[8].y

                    # Detección de pellizco con histéresis para evitar rebotes cerca del umbral
                    dist_pinch = ((lm[8].x - lm[4].x) ** 2 + (lm[8].y - lm[4].y) ** 2) ** 0.5
                    pinch = dist_pinch < (0.095 if self._previous_pinch else 0.068)

                    # Clasificación robusta: no depende de la altura absoluta de la cámara.
                    # Los cuatro dedos extendidos representan palma abierta.
                    for i, (tip, pip) in enumerate(((8, 6), (12, 10), (16, 14), (20, 18))):
                        extended_fingers[i] = lm[tip].y < lm[pip].y - 0.012
                        piano_fingers[i] = lm[tip].y > lm[pip].y + 0.012
                    raised = sum(extended_fingers) >= 4
                    fist = bool(piano_fingers[0] and sum(piano_fingers) >= 3)
                else:
                    self._tracked_lost_frames += 1
                    if self._tracked_lost_frames >= 8:
                        self._tracked_palm = None
                with self._lock:
                    moving_up = self._previous_hand_y - hand_y > 0.035
                    self.hand_detected = detected
                    self.hand_x, self.hand_y = hand_x, hand_y
                    self._hands = hands_list
                    self.pointing_direction = pointing_dir
                    self.hand_raised = raised
                    self.open_palm = raised
                    self.pinch_active = pinch
                    self._pinch_just_pressed = bool(pinch and not self._previous_pinch)
                    self._fist_just_pressed = bool(fist and not self._previous_fist)
                    self._punch_just_pressed = bool(fist and not self._previous_fist and moving_up)
                    self._hand_raise_just_pressed = bool(raised and not self._previous_raised)
                    self._previous_pinch = pinch
                    self._previous_fist = fist
                    self._previous_raised = raised
                    self._previous_hand_y = hand_y
                    for i, active in enumerate(piano_fingers):
                        self._cooldowns[i] = max(0.0, self._cooldowns[i] - dt)
                        self._finger_pressed[i] = piano_fingers[i]
                        self._finger_just_pressed[i] = bool(active and not self._previous[i] and self._cooldowns[i] <= 0.0)
                        if self._finger_just_pressed[i]:
                            self._cooldowns[i] = 0.22
                        self._previous[i] = piano_fingers[i]
                time.sleep(0.001)
        except Exception as exc:
            self.error = f"Error de MediaPipe: {exc}"
            self.available = False
            self.enabled = False
            with self._lock:
                self.hand_detected = False
        finally:
            if hands is not None and hasattr(hands, "close"):
                try:
                    hands.close()
                except Exception:
                    pass
            cap.release()
