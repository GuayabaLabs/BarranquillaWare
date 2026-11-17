import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from microgames.batalla_flores_boss import BatallaFloresBossMicrogame

def test_boss_microgame():
    print("Iniciando verificación del Boss Stage: Batalla de Flores...")
    boss = BatallaFloresBossMicrogame(character_id="westcol")
    assert boss.time_limit == 15.0
    assert boss._get_current_boss_subphase() == 1

    # Fase 1: Probar proyectil y movimiento
    boss.time_left = 14.0
    boss.phase = boss.PHASE_PLAY
    boss.update_game(0.1)
    assert len(boss.confetti) == 80
    print("[OK] Fase 1 (Esquivar maicena) operativa.")

    # Simular paso a Fase 2 (Tambora)
    boss.time_left = 8.0
    assert boss._get_current_boss_subphase() == 2
    boss.update_game(0.5)
    # Simular golpe rítmico
    evt_hit = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE})
    boss.handle_game_event(evt_hit)
    print("[OK] Fase 2 (Repique de Tambora) operativa.")

    # Simular paso a Fase 3 (Atrapa Corona)
    boss.time_left = 3.0
    assert boss._get_current_boss_subphase() == 3
    boss.update_game(0.1)
    
    # Colocar la corona directamente en la zona de colisión de la cabeza del jugador
    p_head_rect = pygame.Rect(boss.player_x - 60, boss.player_y - 140 + boss.player_jump_y, 120, 90)
    boss.crown_x = float(p_head_rect.centerx)
    boss.crown_y = float(p_head_rect.centery)
    boss.update_game(0.016)
    
    assert boss.crown_caught is True
    assert boss.is_won is True
    assert boss.is_finished is True
    print("[OK] Fase 3 (Captura de Corona Real) victoria confirmada.")

    # Probar render
    surf = pygame.Surface((1920, 1080))
    boss.render_game(surf)
    out_png = os.path.join(os.path.dirname(__file__), "..", "artifacts", "render_boss_stage.png")
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    pygame.image.save(surf, out_png)
    print(f"[OK] Render de Boss Stage guardado en: {out_png}")

    print("PRUEBA DEL BOSS STAGE PASÓ CON ÉXITO (EXIT 0).")

if __name__ == "__main__":
    test_boss_microgame()
