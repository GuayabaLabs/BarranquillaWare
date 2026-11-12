import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from scenes.story_map import StoryMapScene

def test_branching_and_midpoints_suite():
    print("Iniciando suite de verificación: Ramificaciones de red vial, Nodos Medios y Circuitos...")
    with open("config/map_poi_layout.json", "r", encoding="utf-8") as f:
        original_layout_backup = f.read()

    try:
        scene = StoryMapScene(character_id="westcol")
        dev = scene.dev_tool
        dev.enabled = True
        dev.mode = "paths"

        # Limpiar red para prueba
        dev.nodes.clear()
        dev.edges.clear()
        dev.selected_node_id = -1
        dev.selected_edge_idx = -1

        # 1. Crear Nodo 1 (id 0) en (500, 200)
        c1 = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (500, 200)})
        dev.handle_event(c1, (0, 0))
        up1 = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (500, 200)})
        dev.handle_event(up1, (0, 0))
        assert len(dev.nodes) == 1, "Fallo al crear nodo 0"
        assert len(dev.edges) == 0, "No debería haber aristas aún"

        # 2. Crear Nodo 2 (id 1) en (800, 200) conectado al Nodo 1
        c2 = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (800, 200)})
        dev.handle_event(c2, (0, 0))
        up2 = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (800, 200)})
        dev.handle_event(up2, (0, 0))
        assert len(dev.nodes) == 2, "Fallo al crear nodo 1"
        assert len(dev.edges) == 1, "Fallo al conectar arista 0 -> 1"
        assert dev.edges[0]["from"] == 0 and dev.edges[0]["to"] == 1
        print("[OK] Primer tramo vial creado: Nodo #1 -> Nodo #2")

        # 3. RAMIFICACIÓN: Seleccionar Nodo 1 (id 0) como origen y sacar una nueva rama hacia (500, 500)
        dev.selected_node_id = 0  # Seleccionar Nodo 1
        c3 = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (500, 500)})
        dev.handle_event(c3, (0, 0))
        up3 = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (500, 500)})
        dev.handle_event(up3, (0, 0))
        assert len(dev.nodes) == 3, "Fallo al crear nodo 2"
        assert len(dev.edges) == 2, "Fallo al crear arista de ramificación"
        # Verificar que la arista 1 nace de 0 hacia 2
        branch_edge = dev.edges[1]
        assert (branch_edge["from"] == 0 and branch_edge["to"] == 2) or (branch_edge["from"] == 2 and branch_edge["to"] == 0)
        print(f"[OK] Ramificación exitosa: Nodo #1 ahora bifurca hacia Nodo #2 y hacia Nodo #3 (from={branch_edge['from']}, to={branch_edge['to']})")

        # 4. SUBDIVISIÓN CON NODO MEDIO (Tecla I o botón):
        # Seleccionar arista 0 -> 1 (entre (500, 200) y (800, 200))
        dev.selected_edge_idx = 0
        dev.selected_node_id = -1
        evt_i = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_i, "mod": 0})
        dev.handle_event(evt_i, (0, 0))

        # Debe haberse creado un nodo medio en (650, 200) y dividido la arista en 2
        assert len(dev.nodes) == 4, f"Se esperaban 4 nodos tras subdivisión, hay {len(dev.nodes)}"
        mid_node = dev.nodes[-1]
        assert mid_node["x"] == 650 and mid_node["y"] == 200, f"Posición incorrecta de nodo medio: ({mid_node['x']}, {mid_node['y']})"
        assert len(dev.edges) == 3, f"Se esperaban 3 aristas tras subdivisión, hay {len(dev.edges)}"
        print(f"[OK] Subdivisión Bézier de Casteljau: nuevo nodo medio #{mid_node['id'] + 1} insertado en ({mid_node['x']}, {mid_node['y']})")

        # 5. CONECTAR DOS NODOS EXISTENTES (Shift + Click):
        # Seleccionar Nodo 2 (id 1 en (800, 200))
        dev.selected_node_id = 1
        # Shift + Click sobre Nodo 3 (id 2 en (500, 500))
        pygame.key.set_mods(pygame.KMOD_SHIFT)
        c_shift = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (500, 500)})
        dev.handle_event(c_shift, (0, 0))
        up_shift = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (500, 500)})
        dev.handle_event(up_shift, (0, 0))
        pygame.key.set_mods(0)

        assert len(dev.edges) == 4, "Debe haber 4 aristas tras cerrar circuito"
        print("[OK] Conexión entre nodos existentes verificada (Circuito de calles cerrado).")

        # 6. Renderizar en el mapa mundial
        scene._on_devtool_layout_changed()
        test_surf = pygame.Surface((1920, 1080))
        scene.render(test_surf)
        print("[OK] Renderizado del grafo completo de calles sobre world_map sin errores.")

        # 7. Guardar y verificar persistencia en JSON
        save_ok = dev.save_layout()
        assert save_ok is True, "Fallo al guardar red en layout"
        reloaded = dev.load_layout()
        assert len(reloaded["street_network"]["nodes"]) == 4, "Fallo al recargar nodos"
        assert len(reloaded["street_network"]["edges"]) == 4, "Fallo al recargar aristas"
        print("[OK] Persistencia de red vial (street_network) verificada.")

    finally:
        with open("config/map_poi_layout.json", "w", encoding="utf-8") as f:
            f.write(original_layout_backup)

    print("\nTODAS LAS PRUEBAS DE RAMIFICACIÓN Y NODOS MEDIOS PASARON EXITOSAMENTE (EXIT 0).")

if __name__ == "__main__":
    test_branching_and_midpoints_suite()
