import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
from core.engine import Engine

def test_gamepad_engine():
    engine = Engine(enable_gl=False)
    assert hasattr(engine, "_translate_joystick_event")

    # Botón 0 -> K_SPACE
    evt = pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0})
    trans = engine._translate_joystick_event(evt)
    assert len(trans) == 1 and trans[0].key == pygame.K_SPACE

    # Botón 1 -> K_ESCAPE
    evt_b = pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 1})
    trans_b = engine._translate_joystick_event(evt_b)
    assert len(trans_b) == 1 and trans_b[0].key == pygame.K_ESCAPE

    # D-Pad Arriba -> K_UP
    evt_hat = pygame.event.Event(pygame.JOYHATMOTION, {"value": (0, 1)})
    trans_hat = engine._translate_joystick_event(evt_hat)
    assert len(trans_hat) == 1 and trans_hat[0].key == pygame.K_UP

    # Stick izquierdo a la derecha -> K_RIGHT
    evt_axis = pygame.event.Event(pygame.JOYAXISMOTION, {"axis": 0, "value": 0.8})
    trans_axis = engine._translate_joystick_event(evt_axis)
    assert len(trans_axis) == 1 and trans_axis[0].key == pygame.K_RIGHT

    print("[OK] Universal Gamepad Mapping verificado exitosamente.")

if __name__ == "__main__":
    test_gamepad_engine()
