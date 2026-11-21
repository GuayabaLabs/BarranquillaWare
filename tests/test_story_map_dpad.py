"""Las flechas del mapa siguen la dirección real de las calles y todo el mapa sigue siendo alcanzable."""
import math
import os
import unittest
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from core.settings import SettingsManager
from scenes.story_map.scene import StoryMapScene

FLECHAS = {"derecha": (1.0, 0.0), "izquierda": (-1.0, 0.0), "arriba": (0.0, -1.0), "abajo": (0.0, 1.0)}
DIAGONALES = {"der-arr": (1.0, -1.0), "der-aba": (1.0, 1.0), "izq-arr": (-1.0, -1.0), "izq-aba": (-1.0, 1.0)}


class TestStoryMapDpad(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        SettingsManager.get_instance().reset_story_progress()
        cls.scene = StoryMapScene(character_id="shakira")
        cls.nodes, _, cls.node_map, cls.adj, _ = cls.scene._get_street_graph()

    def _mover(self, nid, vec):
        s = self.scene
        s.player_node_id, s.player_is_moving = nid, False
        destino = s._pick_dpad_neighbor(vec)
        s.player_is_moving = False
        return destino

    def test_ninguna_flecha_toma_una_calle_desviada(self):
        for n in self.nodes:
            for nombre, vec in {**FLECHAS, **DIAGONALES}.items():
                destino = self._mover(n["id"], vec)
                if destino is None:
                    continue
                dx, dy = self.scene._edge_screen_direction(n["id"], destino)
                m = math.hypot(*vec)
                angulo = math.degrees(math.acos(max(-1.0, min(1.0, (dx * vec[0] + dy * vec[1]) / m))))
                limite = 45 if nombre in ("derecha", "izquierda") else 68 if nombre in ("arriba", "abajo") else 45
                self.assertLessEqual(angulo, limite + 0.5, f"nodo {n['id']} {nombre} -> {destino} ({angulo:.0f}°)")
                # Nunca la peor opción: si hay una calle mejor alineada, se toma esa.
                for otro in self.adj[n["id"]]:
                    ox, oy = self.scene._edge_screen_direction(n["id"], otro)
                    self.assertLessEqual(ox * vec[0] + oy * vec[1], dx * vec[0] + dy * vec[1] + 1e-6)

    def test_derecha_nunca_baja_ni_sube_en_vertical(self):
        for n in self.nodes:
            for vec in (FLECHAS["derecha"], FLECHAS["izquierda"]):
                destino = self._mover(n["id"], vec)
                if destino is not None:
                    dx, dy = self.scene._edge_screen_direction(n["id"], destino)
                    self.assertGreater(abs(dx), abs(dy), f"nodo {n['id']}: horizontal se fue en vertical")

    def test_todo_el_mapa_alcanzable_con_flechas(self):
        inicio = self.nodes[0]["id"]
        visto, cola = {inicio}, deque([inicio])
        while cola:
            nid = cola.popleft()
            for vec in list(FLECHAS.values()) + list(DIAGONALES.values()):
                destino = self._mover(nid, vec)
                if destino is not None and destino not in visto:
                    visto.add(destino)
                    cola.append(destino)
        # Los nodos sin ninguna calle (sueltos en los datos del mapa) no cuentan.
        faltan = {n["id"] for n in self.nodes if self.adj[n["id"]]} - visto
        self.assertFalse(faltan, f"Nodos inalcanzables con flechas: {sorted(faltan)}")

    def test_tecla_con_otra_sostenida_toma_diagonal(self):
        from core import input_state

        s = self.scene
        input_state.clear()
        input_state.VIRTUAL_KEYS.add(pygame.K_DOWN)
        try:
            for n in self.nodes:
                diagonal = self._mover(n["id"], DIAGONALES["der-aba"])
                if diagonal is None:
                    continue
                s.player_node_id, s.player_is_moving = n["id"], False
                s.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT, "mod": 0, "unicode": ""}))
                self.assertTrue(s.player_is_moving)
                self.assertEqual(s.player_path_edges[0]["to"], diagonal)
                s.player_is_moving, s.player_path_edges = False, []
                break
        finally:
            input_state.clear()


if __name__ == "__main__":
    unittest.main()
