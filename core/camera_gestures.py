"""Entrada opcional de gestos MediaPipe, aislada del motor y de los minijuegos.

La cámara nunca es requisito para arrancar: cuando faltan dependencias, cámara o
permisos, el adaptador queda inactivo y el juego conserva sus controles normales.
"""
from __future__ import annotations

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
        self.hands_xy: list = []  # Todas las manos detectadas (máx. 2), en coordenadas normalizadas espejadas
        self.hand_detected = False
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

    def start(self) -> bool:
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

    def keep_alive(self, retry_interval: float = 2.0) -> None:
        """Reintenta abrir la cámara si falló, con pausa para evitar bucles rápidos."""
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

    def get_hands(self) -> list:
        """Posiciones (x, y) normalizadas de hasta dos manos; la primera es la mano principal."""
        with self._lock:
            return list(self.hands_xy)

    def _run(self) -> None:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.error = "No se pudo abrir la cámara"
            self.available = False
            self.enabled = False
            cap.release()
            return
        try:
            hands = mp.solutions.hands.Hands(
                static_image_mode=False, max_num_hands=2,
                min_detection_confidence=0.6, min_tracking_confidence=0.55
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
                hands_xy = []
                if result.multi_hand_landmarks:
                    detected = True
                    hands_xy = [(h.landmark[9].x, h.landmark[9].y) for h in result.multi_hand_landmarks[:2]]
                    # Gestos y puntero siguen usando solo la mano principal (la primera).
                    lm = result.multi_hand_landmarks[0].landmark
                    # Seguimiento focal en la punta del dedo índice (LM 8) para que el lápiz apunte donde apunta el dedo
                    hand_x, hand_y = lm[8].x, lm[8].y

                    # Detección de pellizco (distancia euclidiana entre punta de pulgar LM 4 y punta de índice LM 8)
                    dist_pinch = ((lm[8].x - lm[4].x) ** 2 + (lm[8].y - lm[4].y) ** 2) ** 0.5
                    pinch = dist_pinch < 0.075

                    # Clasificación robusta: no depende de la altura absoluta de la cámara.
                    # Los cuatro dedos extendidos representan palma abierta.
                    for i, (tip, pip) in enumerate(((8, 6), (12, 10), (16, 14), (20, 18))):
                        extended_fingers[i] = lm[tip].y < lm[pip].y - 0.012
                        piano_fingers[i] = lm[tip].y > lm[pip].y + 0.012
                    raised = sum(extended_fingers) >= 4
                    fist = sum(piano_fingers) >= 3
                with self._lock:
                    moving_up = self._previous_hand_y - hand_y > 0.035
                    self.hand_detected = detected
                    self.hand_x, self.hand_y = hand_x, hand_y
                    self.hands_xy = hands_xy
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
                time.sleep(0.01)
            hands.close()
        except Exception as exc:
            self.error = f"Error de MediaPipe: {exc}"
            self.available = False
        finally:
            cap.release()
