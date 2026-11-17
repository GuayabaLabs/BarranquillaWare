"""El controlador libera recursos y permite reintentar después de fallos, sin cámara real."""
from types import SimpleNamespace

import numpy as np

from core import camera_gestures as camera_module


def test_detector_failure_clears_active_state_and_releases_resources(monkeypatch):
    camera = camera_module.CameraGestureInput()
    camera.enabled = True
    camera.hand_detected = True
    closed = []
    released = []
    class FakeHands:
        def process(self, frame):
            raise AttributeError("SymbolDatabase has no GetPrototype")
        def close(self):
            closed.append(True)
    cap = SimpleNamespace(isOpened=lambda: True,
                          read=lambda: (True, np.zeros((4, 4, 3), dtype=np.uint8)),
                          release=lambda: released.append(True))
    cv = SimpleNamespace(VideoCapture=lambda index: cap, flip=lambda frame, axis: frame,
                         cvtColor=lambda frame, mode: frame, COLOR_BGR2RGB=1)
    mp = SimpleNamespace(solutions=SimpleNamespace(hands=SimpleNamespace(Hands=lambda **kw: FakeHands())))
    monkeypatch.setattr(camera_module, "cv2", cv)
    monkeypatch.setattr(camera_module, "mp", mp)
    camera._run()
    assert "GetPrototype" in camera.error
    assert not camera.enabled
    assert not camera.hand_detected
    assert closed == [True]
    assert released == [True]


def test_unavailable_device_clears_active_state(monkeypatch):
    camera = camera_module.CameraGestureInput()
    camera.enabled = True
    released = []
    cap = SimpleNamespace(isOpened=lambda: False, release=lambda: released.append(True))
    monkeypatch.setattr(camera_module, "cv2", SimpleNamespace(VideoCapture=lambda index: cap))
    camera._run()
    assert not camera.enabled
    assert not camera.available
    assert "abrir" in camera.error
    assert released == [True]
