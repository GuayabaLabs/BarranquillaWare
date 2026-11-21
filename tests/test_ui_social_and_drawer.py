import os

# Ejecución headless de Pygame para testing sin ventana física
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1920, 1080))

from ui.social_hud import SocialHUD
from ui.side_drawer import SideNavDrawer
from scenes.story_map import StoryMapScene

def test_social_hud():
    print("[TEST] 1. Inicializando SocialHUD con texturas oficiales...")
    hud = SocialHUD(1920, 1080)
    assert len(hud.pills) == 3, f"Esperadas 3 pills, obtenidas: {len(hud.pills)}"
    assert "seguidores" in hud.pills
    assert "likes" in hud.pills
    assert "logros" in hud.pills

    # Validar que los números están desactivados por defecto
    for k, pill in hud.pills.items():
        assert pill.value_text is None, f"La pill {k} no debe tener número por defecto"
        assert pill.width == 258 and pill.height == 86, f"Dimensiones incorrectas: {pill.width}x{pill.height}"

    # Validar render sobre superficie
    test_surf = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    hud.update(0.016)
    hud.render(test_surf)
    print("  -> SocialHUD con texturas oficiales renderizado exitosamente.")

    # Validar asignación futura de métrica
    hud.set_metric("seguidores", "12.5K")
    assert hud.pills["seguidores"].value_text == "12.5K"
    hud.render(test_surf)
    print("  -> Asignación de métrica dinámica verificada.")

def test_side_drawer():
    print("[TEST] 2. Inicializando SideNavDrawer a escala de referencia...")
    selected_nav = []
    drawer = SideNavDrawer(1920, 1080, on_nav_selected=lambda item_id: selected_nav.append(item_id))

    # Estado inicial: colapsado
    assert not drawer.is_open, "El drawer debe iniciar cerrado"
    assert drawer.anim_t == 0.0, "anim_t inicial debe ser 0.0"

    # Verificar que el botón de pestaña exterior está en el borde visible
    tab_rect = drawer._get_tab_rect()
    print(f"  -> Tab Rect colapsado: {tab_rect}")
    assert tab_rect.right > 0, f"La pestaña colapsada debe asomarse en pantalla, actual: {tab_rect}"

    # Simular clic en la pestaña
    click_pos = (max(5, tab_rect.centerx), tab_rect.centery)
    event_down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": click_pos})
    consumed = drawer.handle_event(event_down)
    assert consumed, "El evento de clic en pestaña debe ser consumido"

    event_up = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": click_pos})
    consumed_up = drawer.handle_event(event_up)
    assert consumed_up, "El evento de soltar en pestaña debe ser consumido"
    assert drawer.is_open, "El drawer debe abrirse tras el clic en la pestaña"

    # Simular varios frames de animación
    for _ in range(30):
        drawer.update(0.016)
    assert drawer.anim_t > 0.95, f"El drawer debe expandirse suavemente, anim_t={drawer.anim_t}"
    assert drawer.is_blocking(), "El drawer debe bloquear la interacción del mapa mientras está abierto"

    # Simular clic en un item interno ('mensajes')
    item_rect = drawer._get_item_screen_rect(drawer.nav_items[1])  # Index 1 = mensajes
    drawer.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": item_rect.center}))
    drawer.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": item_rect.center}))
    assert "mensajes" in selected_nav, f"Callback de mensajes no fue disparado: {selected_nav}"
    assert drawer.active_tab == "mensajes"

    # Simular clic fuera del panel (x=1000) para auto-cerrar
    click_outside = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (1000, 500)})
    consumed_out = drawer.handle_event(click_outside)
    assert consumed_out, "Clic fuera debe ser consumido"
    assert not drawer.is_open, "El drawer debe colapsarse al hacer clic fuera"

    # Simular retorno a colapsado
    for _ in range(40):
        drawer.update(0.016)
    assert drawer.anim_t == 0.0 or drawer.anim_t < 0.01, f"anim_t debe volver a 0.0, actual: {drawer.anim_t}"

    # Renderizado
    test_surf = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    drawer.render(test_surf)
    print("  -> SideNavDrawer ciclo de apertura, interacción y cierre verificado.")

def test_story_map_integration():
    print("[TEST] 3. Verificando integración completa en StoryMapScene...")
    scene = StoryMapScene(character_id="paloma")
    assert hasattr(scene, "social_hud"), "StoryMapScene debe contener social_hud"
    assert hasattr(scene, "side_drawer"), "StoryMapScene debe contener side_drawer"

    # Tick y render
    test_surf = pygame.Surface((1920, 1080))
    scene.update(0.016)
    scene.render(test_surf)

    # Probar que el drawer consume el evento a nivel de escena
    tab_rect = scene.side_drawer._get_tab_rect()
    click_pos = (max(5, tab_rect.centerx), tab_rect.centery)
    down_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": click_pos})
    scene.handle_event(down_ev)
    assert scene.side_drawer.tab_pressed, "scene.handle_event debió enviar evento a side_drawer"

    up_ev = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": click_pos})
    scene.handle_event(up_ev)
    assert scene.side_drawer.is_open, "El drawer debe abrirse a través de la escena"

    # Un update de la escena
    scene.update(0.05)
    assert scene.side_drawer.is_blocking(), "El drawer debe bloquear el arrastre del mapa en la escena"

    print("  -> Integración en StoryMapScene validada con éxito.")

def test_drawer_tabs_and_sections():
    """Valida la navegación entre todas las pestañas del menú desplegable izquierdo."""
    print("[TEST] 4. Verificando pestañas Mensajes, Misiones, Perfil y Logros...")
    scene = StoryMapScene(character_id="westcol")
    drawer = scene.side_drawer
    drawer.is_open = True
    drawer.anim_t = 1.0

    os.makedirs("artifacts", exist_ok=True)
    test_surf = pygame.Surface((1920, 1080), pygame.SRCALPHA)

    # 1. Probar pestaña Mensajes
    scene._on_side_nav_selected("mensajes")
    assert drawer.seccionActual == "mensajes"
    drawer.render(test_surf)
    pygame.image.save(test_surf, "artifacts/verify_drawer_mensajes.png")

    # Cerrar sección con botón X
    close_r = drawer.rectBotonCerrar(drawer._get_panel_x())
    ev_down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": close_r.center})
    consumed = drawer.handle_event(ev_down)
    assert consumed is True
    assert drawer.seccionActual == "botones"

    # 2. Probar pestaña Misiones
    scene._on_side_nav_selected("misiones")
    assert drawer.seccionActual == "misiones"
    test_surf.fill((0, 0, 0, 0))
    drawer.render(test_surf)
    pygame.image.save(test_surf, "artifacts/verify_drawer_misiones.png")

    ev_down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": close_r.center})
    drawer.handle_event(ev_down)
    assert drawer.seccionActual == "botones"

    # 3. Probar pestaña Perfil
    scene._on_side_nav_selected("perfil")
    assert drawer.seccionActual == "perfil"
    test_surf.fill((0, 0, 0, 0))
    drawer.render(test_surf)
    pygame.image.save(test_surf, "artifacts/verify_drawer_perfil.png")

    ev_down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": close_r.center})
    drawer.handle_event(ev_down)
    assert drawer.seccionActual == "botones"

    # 4. Probar pestaña Logros
    scene._on_side_nav_selected("logros")
    assert drawer.seccionActual == "trofeos"
    test_surf.fill((0, 0, 0, 0))
    drawer.render(test_surf)
    pygame.image.save(test_surf, "artifacts/verify_drawer_trofeos.png")

    ev_down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": close_r.center})
    drawer.handle_event(ev_down)
    assert drawer.seccionActual == "botones"

    print("  -> Todas las secciones del Drawer validadas y capturadas en artifacts/.")

if __name__ == "__main__":
    test_social_hud()
    test_side_drawer()
    test_story_map_integration()
    test_drawer_tabs_and_sections()
    print("\n[ÉXITO] Todas las pruebas empíricas pasaron satisfactoriamente.")


def test_profile_and_missions_include_fritanga():
    from scenes.story_map_data import STORY_CAMPAIGN_ORDER
    scene = StoryMapScene(character_id="westcol")
    assert scene.side_drawer.perfil_data["niveles"].endswith(f"/{len(STORY_CAMPAIGN_ORDER)}")
    assert "aleta" in {mission["id"] for mission in scene.side_drawer.misiones}


def test_drawer_missions_messages_state_and_main_menu_logros():
    """Verifica rectificación de misiones, badge de mensajes sin leer y logros reales en MainMenu."""
    from core.settings import SettingsManager
    from core.audio_manager import AudioManager
    from scenes.main_menu import MainMenuScene

    settings = SettingsManager.get_instance()
    settings.reset_story_progress()
    audio = AudioManager.get_instance()
    try:
        scene = StoryMapScene(character_id="westcol")
        missions = {m["id"]: m["completada"] for m in scene.side_drawer.misiones}
        assert len(missions) == 6
        assert all(not done for done in missions.values()), f"En partida nueva ninguna misión debe iniciar completada: {missions}"
        assert scene.side_drawer.show_notification_badge is True

        # Renderizar pestañas con 6 ítems sin errores de superficie
        scene.side_drawer.is_open = True
        scene.side_drawer.anim_t = 1.0
        surf = pygame.Surface((1920, 1080), pygame.SRCALPHA)
        scene._on_side_nav_selected("misiones")
        scene.side_drawer.render(surf)
        scene._on_side_nav_selected("mensajes")
        scene.side_drawer.render(surf)

        # Despejar Uninorte (2 rondas) actualiza misión, mensaje y trofeo real en MainMenu
        scene.active_poi = "uninorte"
        scene.current_level_stage_idx = 0
        scene._on_microgame_complete(True)
        scene._on_microgame_complete(True)
        audio.stop_voice(fade_ms=0)

        missions_after = {m["id"]: m["completada"] for m in scene.side_drawer.misiones}
        assert missions_after["uninorte"] is True
        assert missions_after["buenavista"] is False
        msg_map = {m["remitente"]: m["leido"] for m in scene.side_drawer.mensajes}
        assert msg_map["Alerta Digital Uninorte"] is True
        assert "Aleta del Tiburón" in msg_map

        menu = MainMenuScene(1920, 1080)
        lines = menu._build_logros_lines()
        assert any("1 / 4" in line for line in lines), f"MainMenu logros debe mostrar trofeos del mapa: {lines}"
    finally:
        audio.stop_voice(fade_ms=0)
        settings.reset_story_progress()


def test_mensajes_section_no_text_overlap_and_fits_panel():
    """Valida que título, subtítulo, remitente, asunto, cuerpo y pie en Mensajes no se solapen ni recorten."""
    scene = StoryMapScene(character_id="westcol")
    drawer = scene.side_drawer
    drawer.is_open = True
    drawer.anim_t = 1.0
    drawer.mostrarMensajes()
    surf = pygame.Surface((1920, 1080), pygame.SRCALPHA)

    base_msgs = list(drawer.mensajes)
    assert len(base_msgs) == 6

    for count in (6, 5, 3, 0):
        drawer.ponerMensajes(base_msgs[:count] if count else [])
        surf.fill((0, 0, 0, 0))
        drawer.render(surf)
        m = drawer.last_mensajes_layout_metrics
        assert len(m["cards"]) == (count if count else 6)

        assert m["titulo_ink"].bottom < m["sub_ink"].top, (
            f"count={count}: título solapa subtítulo ({m['titulo_ink']} vs {m['sub_ink']})"
        )
        assert m["sub_ink"].bottom < m["cards"][0]["card_rect"].top, (
            f"count={count}: subtítulo solapa primera tarjeta"
        )
        for idx, card in enumerate(m["cards"]):
            c_rect = card["card_rect"]
            assert card["rem_ink"].bottom < card["as_ink"].top, (
                f"count={count} card={idx}: remitente solapa asunto ({card['rem_ink']} vs {card['as_ink']})"
            )
            assert card["as_ink"].bottom < card["body_inks"][0].top, (
                f"count={count} card={idx}: asunto solapa cuerpo ({card['as_ink']} vs {card['body_inks'][0]})"
            )
            if len(card["body_inks"]) > 1:
                assert card["body_inks"][0].bottom < card["body_inks"][1].top, (
                    f"count={count} card={idx}: líneas de cuerpo se solapan ({card['body_inks']})"
                )
            assert card["rem_ink"].top >= 2
            assert card["rem_ink"].right <= c_rect.width - 8, (
                f"count={count} card={idx}: remitente desborda a la derecha ({card['rem_ink']} en w={c_rect.width})"
            )
            assert card["as_ink"].right <= c_rect.width - 8, (
                f"count={count} card={idx}: asunto desborda a la derecha ({card['as_ink']} en w={c_rect.width})"
            )
            assert card["body_inks"][-1].bottom <= c_rect.height - 2, (
                f"count={count} card={idx}: cuerpo toca borde inferior ({card['body_inks'][-1]} en h={c_rect.height})"
            )

        assert m["cards"][-1]["card_rect"].bottom < m["pie_ink"].top, (
            f"count={count}: última tarjeta solapa pie ({m['cards'][-1]['card_rect']} vs {m['pie_ink']})"
        )
        assert m["pie_ink"].bottom < m["panel_rect"].bottom - 20, (
            f"count={count}: pie demasiado cerca del borde inferior ({m['pie_ink']} vs {m['panel_rect']})"
        )

    # Caso extremo: remitentes y asuntos largos en 6 tarjetas compactas tampoco deben recortarse
    drawer.ponerMensajes([
        {
            "remitente": "Departamento de Bienestar Digital Uninorte",
            "asunto": "Alerta urgente sobre desinformación viral en redes locales",
            "cuerpo": "Texto largo de prueba para verificar ajuste de ancho sin desbordes ni solapamientos.",
            "leido": (i % 2 == 0),
        }
        for i in range(6)
    ])
    surf.fill((0, 0, 0, 0))
    drawer.render(surf)
    m_long = drawer.last_mensajes_layout_metrics
    for idx, card in enumerate(m_long["cards"]):
        c_rect = card["card_rect"]
        assert card["rem_ink"].right <= c_rect.width - 8, f"long card={idx} remitente desbordado: {card['rem_ink']}"
        assert card["as_ink"].right <= c_rect.width - 8, f"long card={idx} asunto desbordado: {card['as_ink']}"
        assert card["rem_ink"].bottom < card["as_ink"].top
        assert card["as_ink"].bottom < card["body_inks"][0].top
