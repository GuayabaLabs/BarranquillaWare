import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from microgames.fritanga_84 import Fritanga84Microgame
from microgames.troja_baile import TrojaBaileMicrogame

def test_folcloricos_microgames():
    print("Iniciando pruebas de los 2 nuevos microjuegos folclóricos...")

    # 1. Test Fritanga de la 84
    tuto = Fritanga84Microgame(character_id="westcol")
    tuto.phase = tuto.PHASE_PLAY
    tuto.update(0.05)
    assert tuto.tutorial is not None
    tiempoAntes = tuto.time_left
    tuto.update(1.0)
    assert tuto.time_left == tiempoAntes
    tuto.render_game(pygame.Surface((1920, 1080)))
    for _ in range(len(tuto.pasosTutorial())):
        tuto.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    assert tuto.tutorial is None

    frit = Fritanga84Microgame(character_id="westcol")
    frit.tutorialPendiente = False
    assert frit.time_limit == 75.0
    assert len(frit.arepas) == 3
    frit.phase = frit.PHASE_PLAY
    frit.update_game(0.4)

    arepa = frit.arepas[0]
    arepa["coccion"] = 0.7
    frit.tocarArepa(arepa)
    assert arepa["lado"] == 2
    arepa["volteo"] = 0.0
    arepa["coccion"] = 0.7
    frit.tocarArepa(arepa)
    frit.update_game(1.0)
    assert frit.arepasListas == 1

    frit.cliente = {"cual": 0, "estado": "esperando", "tiempo": 0.0, "paciencia": 10.0}
    frit.teclaServir = True
    for _ in range(20):
        frit.update_game(0.05)
    frit.teclaServir = False
    frit.update_game(0.05)
    assert frit.vasoLleno() is True
    assert frit.estadoVaso == "listo"
    assert frit.patillazosServidos == 0
    frit.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=frit.cajaVasoQuieto().center))
    assert frit.estadoVaso == "arrastrando"
    destino = frit.cajaCliente().center
    frit.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=destino, rel=(0, 0), buttons=(1, 0, 0)))
    frit.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=destino))
    assert frit.patillazosServidos == 1

    regado = Fritanga84Microgame(character_id="westcol")
    regado.tutorialPendiente = False
    regado.phase = regado.PHASE_PLAY
    regado.teclaServir = True
    for _ in range(40):
        regado.actualizarVaso(0.05)
    assert regado.estadoVaso == "regandose"
    assert regado.vasoAplastado is False
    assert regado.fallos == 1

    furioso = Fritanga84Microgame(character_id="westcol")
    furioso.tutorialPendiente = False
    furioso.phase = furioso.PHASE_PLAY
    furioso.rabia = 0.8
    furioso.teclaServir = True
    for _ in range(10):
        furioso.actualizarVaso(0.05)
    assert furioso.estadoVaso == "regandose"
    assert furioso.vasoAplastado is True

    frit.time_left = 0.01
    frit.update(0.05)
    assert frit.secuencia == "victoria"
    frit.update(3.0)
    assert frit.is_won is True
    assert frit.is_finished is True

    surf1 = pygame.Surface((1920, 1080))
    frit.render_game(surf1)

    trol = Fritanga84Microgame(character_id="westcol")
    trol.tutorialPendiente = False
    trol.phase = trol.PHASE_PLAY
    for arepa in trol.arepas:
        arepa["velocidad"] = 0.0
    trol.tiempoJugado = 10.0
    trol.update(0.05)
    assert trol.trol["estado"] == "aviso"
    tiempoAntes = trol.time_left
    trol.update(0.5)
    assert trol.time_left == tiempoAntes
    rabiaAntes = trol.rabia
    trol.elegirOpcion(0)
    assert trol.rabia > rabiaAntes
    assert trol.respuestas == 1
    for _ in range(int(90 / 0.05)):
        if trol.trol["estado"] == "aviso":
            trol.elegirOpcion(0)
        if trol.reflexion:
            trol.cerrarReflexion()
        trol.update(0.05)
    assert trol.is_finished is True
    assert trol.is_won is False
    assert trol.ensenanzaFinal["pierde"] == trol.ensenanzaRabia
    assert trol.manoQuemada is True
    assert trol.lineasFinales()[-1] == trol.fraseRedes

    calma = Fritanga84Microgame(character_id="westcol")
    calma.tutorialPendiente = False
    calma.phase = calma.PHASE_PLAY
    calma.tiempoJugado = 10.0
    calma.update(0.05)
    calma.elegirOpcion(1)
    assert calma.trol["estado"] == "nada"
    assert calma.respuestas == 0
    assert calma.rabia < 0.1
    calma.update(0.05)
    assert calma.reflexion is not None
    tiempoAntes = calma.time_left
    calma.update(0.5)
    assert calma.time_left == tiempoAntes
    calma.cerrarReflexion()
    calma.tiempoJugado = 32.0
    calma.finTrol = -100.0
    calma.update(0.05)
    assert calma.trol["estado"] == "aviso"
    calma.elegirOpcion(1)
    for _ in range(int(3 / 0.05)):
        calma.update(0.05)
    assert calma.reflexion is None
    print("[OK] Fritanga de la 84 (Arepa de Huevo) probado y verificado.")

    # 2. Test La Troja
    troja = TrojaBaileMicrogame(character_id="shakira")
    assert troja.time_limit == 4.0
    troja.phase = troja.PHASE_PLAY
    troja.time_left = 0.04
    troja.update_game(0.05)
    assert troja.is_won is True
    assert troja.is_finished is True

    surf2 = pygame.Surface((1920, 1080))
    troja.render_game(surf2)
    print("[OK] La Troja (Equilibrio Salsero) probado y verificado.")

    print("TODAS LAS PRUEBAS FOLCLÓRICAS PASARON SATISFACTORIAMENTE (EXIT 0).")

if __name__ == "__main__":
    test_folcloricos_microgames()
