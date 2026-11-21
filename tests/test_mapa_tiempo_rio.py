"""Paso del tiempo, faroles nocturnos, río animado y CurramGram en el aeropuerto del mapa."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame

from core.settings import SettingsManager
from core.state_machine import StateMachine
from scenes.story_map.ciclo_dia import CicloDia, DURACION_DIA_SEG, HORAS_POR_NIVEL
from scenes.story_map.faroles import Faroles, cargar_faroles


class TestCicloDia(unittest.TestCase):
    def test_tiempo_pasa_solo_y_rapido(self):
        c = CicloDia(10.0)
        for _ in range(60):
            c.update(1.0)
        self.assertAlmostEqual(c.hora, 10.0 + 60 * 24.0 / DURACION_DIA_SEG, places=3)
        self.assertLessEqual(DURACION_DIA_SEG, 600)  # un día entero en pocos minutos

    def test_adelanto_por_nivel_es_animado(self):
        c = CicloDia(14.0)
        c.adelantar()
        c.update(0.1)
        self.assertTrue(14.0 < c.hora < 14.0 + HORAS_POR_NIVEL)  # no salta de golpe
        for _ in range(60):
            c.update(0.1)
        self.assertGreaterEqual(c.hora, 14.0 + HORAS_POR_NIVEL - 0.01)

    def test_anochece_y_amanece(self):
        oscuridad = {h: CicloDia(h).oscuridad() for h in (3, 6, 12, 17.3, 18.4, 19.4, 22)}
        self.assertEqual(oscuridad[12], 0.0)
        self.assertEqual(oscuridad[22], 1.0)
        self.assertLess(oscuridad[17.3], oscuridad[18.4])
        self.assertLess(oscuridad[18.4], oscuridad[19.4])
        self.assertLess(oscuridad[19.4], oscuridad[22])
        self.assertGreater(oscuridad[3], oscuridad[6])
        self.assertEqual(CicloDia(12).fase(), "day")
        self.assertEqual(CicloDia(18.4).fase(), "sunset")
        self.assertEqual(CicloDia(23).fase(), "night")

    def test_tinte_oscurece_de_noche_y_no_toca_el_dia(self):
        s = pygame.Surface((40, 40))
        s.fill((200, 200, 200))
        CicloDia(12.0).aplicar_tinte(s)
        self.assertEqual(tuple(s.get_at((5, 5)))[:3], (200, 200, 200))
        CicloDia(23.0).aplicar_tinte(s)
        r, g, b = tuple(s.get_at((5, 5)))[:3]
        self.assertLess(r, 80)
        self.assertGreater(b, r)  # noche azulada


class TestFaroles(unittest.TestCase):
    def test_posiciones_cargadas(self):
        puntos = cargar_faroles()
        self.assertGreaterEqual(len(puntos), 20)
        for x, y, pie in puntos:
            self.assertGreater(pie, y)  # el pie del poste está debajo de la linterna

    def test_se_prenden_solo_de_noche(self):
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        f = Faroles()
        x, y, _ = f.puntos[0]
        for hora, encendido in ((12.0, False), (23.0, True)):
            c = CicloDia(hora)
            lm = c.mapa_luz((1920, 1080))
            antes = lm.get_at((960, 540))
            prendio = f.iluminar(lm, x - 960, y - 540, c.oscuridad(), 1.0)
            self.assertEqual(prendio, encendido, hora)
            if encendido:
                self.assertGreater(sum(lm.get_at((960, 560))[:3]), sum(antes[:3]))


class TestRio(unittest.TestCase):
    def test_rio_se_mueve_y_no_toca_nada_fuera_del_agua(self):
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        from scenes.story_map import StoryMapScene
        from scenes.story_map.rio import RioAnimado

        mapa = StoryMapScene(character_id="valdiri")
        mundo = mapa.world_map
        rio = RioAnimado(mundo)
        self.assertTrue(rio.activo)
        self.assertGreaterEqual(len(rio.olas), 20)
        cam = (1300, 0)
        base = pygame.Surface((1920, 1080))
        base.blit(mundo, (-cam[0], -cam[1]))
        cuadros = []
        for _ in range(2):
            for _ in range(30):
                rio.update(1 / 30)
            s = base.copy()
            rio.render(s, cam[0], cam[1], 1.0)
            cuadros.append(pygame.surfarray.array3d(s).astype(int))
        agua = rio.agua[cam[0]:cam[0] + 1920, cam[1]:cam[1] + 1080]
        fondo = pygame.surfarray.array3d(base).astype(int)
        for c in cuadros:
            cambio = np.abs(c - fondo).sum(axis=2) > 0
            self.assertEqual(int((cambio & ~agua).sum()), 0, "el río pintó fuera del agua")
            self.assertGreater(int((cambio & agua).sum()), 1000)
        self.assertGreater(int((np.abs(cuadros[0] - cuadros[1]).sum(axis=2) > 0).sum()), 500, "el agua no se movió")


class TestAeropuertoCurramGram(unittest.TestCase):
    def test_aeropuerto_lanza_curramgram_y_el_tiempo_avanza(self):
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        from microgames.curramgram_go import CurramGramGoMicrogame
        from scenes.story_map import StoryMapScene
        from scenes.story_map_data import STORY_PLAYABLE_POIS

        settings = SettingsManager.get_instance()
        settings.reset_story_progress()
        self.assertIn("aeropuerto", STORY_PLAYABLE_POIS)
        sm = StateMachine()
        mapa = StoryMapScene(character_id="valdiri")
        sm.change_state(mapa)
        mapa.active_poi, mapa.current_level_stage_idx = "aeropuerto", 0
        mapa.ciclo.hora = 12.0
        mapa._launch_microgame()
        juego = sm.current_state
        self.assertIsInstance(juego, CurramGramGoMicrogame)
        self.assertIsNone(juego.paloma_intro)  # en el mapa la Paloma habla antes del nivel, no se repite
        juego.on_complete_callback(True)
        progreso = settings.get_story_progress()
        self.assertIn("curramgram_go", progreso["completed_microgames"])
        self.assertAlmostEqual(progreso["hora_mapa"], 12.0 + HORAS_POR_NIVEL, places=2)
        for _ in range(120):
            mapa.update(1 / 60)  # el reloj corre aunque la Paloma esté felicitando
        self.assertGreaterEqual(mapa.ciclo.hora, 12.0 + HORAS_POR_NIVEL - 0.01)

    def test_render_a_todas_horas(self):
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        from scenes.story_map import StoryMapScene

        mapa = StoryMapScene(character_id="valdiri")
        s = pygame.Surface((1920, 1080))
        for hora in (0.0, 5.5, 6.5, 12.0, 17.5, 18.5, 19.5, 21.0):
            mapa.ciclo.hora = hora
            mapa.update(1 / 60)
            mapa.render(s)
        mapa.set_weather("rain")
        mapa.update(1 / 60)
        mapa.render(s)
        self.assertEqual(mapa.current_weather, "rain")


if __name__ == "__main__":
    unittest.main()
