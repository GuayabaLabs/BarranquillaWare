"""Pruebas unitarias de filtrado multi-mano y sticky tracking en CameraGestureInput."""
from types import SimpleNamespace

from core.camera_gestures import CameraGestureInput


def _make_hand(palm_x: float, palm_y: float, scale: float):
    """Construye una mano sintética con LM 0 (muñeca) y LM 9 (centro de palma) separados por `scale`."""
    lm = [SimpleNamespace(x=palm_x, y=palm_y) for _ in range(21)]
    lm[0] = SimpleNamespace(x=palm_x, y=palm_y + scale)
    lm[9] = SimpleNamespace(x=palm_x, y=palm_y)
    lm[8] = SimpleNamespace(x=palm_x, y=max(0.0, palm_y - scale * 0.8))
    lm[4] = SimpleNamespace(x=palm_x - scale * 0.4, y=palm_y)
    return SimpleNamespace(landmark=lm)


def test_filter_foreground_discards_small_and_background_hands():
    main_hand = _make_hand(0.45, 0.50, 0.22)
    too_small = _make_hand(0.20, 0.40, 0.04)  # < MIN_HAND_SCALE (0.065)
    background_hand = _make_hand(0.80, 0.45, 0.10)  # >= 0.065 pero < 0.22 * 0.55 (0.121)
    second_fg = _make_hand(0.70, 0.52, 0.18)

    fg = CameraGestureInput._filter_foreground_hands([too_small, background_hand, second_fg, main_hand])
    assert fg == [main_hand, second_fg]

    # Si solo hay manos por debajo del mínimo absoluto, no se detecta ninguna
    assert CameraGestureInput._filter_foreground_hands([too_small]) == []


def test_filter_foreground_caps_at_two_largest_hands_when_three_present():
    h1 = _make_hand(0.25, 0.50, 0.17)
    h2 = _make_hand(0.50, 0.50, 0.24)
    h3 = _make_hand(0.75, 0.50, 0.20)
    h4 = _make_hand(0.90, 0.40, 0.14)

    fg = CameraGestureInput._filter_foreground_hands([h1, h2, h3, h4])
    assert fg == [h2, h3]


def test_select_primary_hand_keeps_tracked_palm_when_second_hand_enters():
    player_hand = _make_hand(0.32, 0.55, 0.20)
    intruder_larger = _make_hand(0.78, 0.48, 0.26)

    # Sin historial previo, gana la de mayor escala
    first, pos0 = CameraGestureInput._select_primary_hand([intruder_larger, player_hand], tracked_palm=None)
    assert first is intruder_larger
    assert pos0 == (0.78, 0.48)

    # Con historial cerca de la mano del jugador, mantiene la mano seguida aunque otra sea más grande
    tracked = (0.30, 0.54)
    chosen, pos1 = CameraGestureInput._select_primary_hand([intruder_larger, player_hand], tracked_palm=tracked)
    assert chosen is player_hand
    assert pos1 == (0.32, 0.55)

    # Si ninguna mano está dentro de MAX_TRACK_JUMP, reengancha a la más grande
    far_a = _make_hand(0.82, 0.20, 0.25)
    far_b = _make_hand(0.75, 0.85, 0.19)
    reacquired, pos2 = CameraGestureInput._select_primary_hand([far_a, far_b], tracked_palm=(0.15, 0.50))
    assert reacquired is far_a
    assert pos2 == (0.82, 0.20)
