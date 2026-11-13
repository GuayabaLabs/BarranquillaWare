# Integración de primeras tareas

## Resumen

Integra las mejoras de la rama `cuatroPrimerasTareas` con la estructura actual de `main` y corrige el flujo de salida de Coaster y de los menús de pausa.

## Cambios incluidos

### Música de fondo

- Añade siete pistas MP3 en `assets/` y las asigna a los minijuegos correspondientes.
- Mantiene la música del minijuego durante los intersticios del modo Arcade.
- Añade un control de volumen relativo por pista a `AudioManager` para que `PunchAlert` suene más bajo sin modificar el volumen global.
- Traslada las asignaciones de música a las rutas actuales de `punch_alert` y `uninorte_concentrate`, que fueron reorganizadas en `main`.

### Coaster y navegación

- Hace que el botón final **Volver al mapa** de Coaster se identifique explícitamente al terminar el último nivel.
- Evita confundir la acción **Repetir** con la salida al mapa.
- Separa las acciones de la pausa de los minijuegos: **Volver al mapa** regresa al mapa y **Salir al menú** abre el menú principal.
- Conecta la salida desde la pausa y desde el mapa con la escena del menú principal, conservando el guardado del progreso.
- Ajusta el panel de pausa para mostrar ambas acciones.

### Ventana e instrucciones del proyecto

- Conserva los cambios pendientes de manejo de ventana en `core/engine.py`.
- Incluye la guía del proyecto en `AGENTS.md`, una skill de revisión y el script `tools/review_project.ps1`.
- Reduce el README para describir el proyecto de forma breve.

## Archivos principales

- `core/audio_manager.py`
- `core/microgame_pause.py`
- `core/engine.py`
- `microgames/coaster_launcher.py`
- `scenes/main_menu.py`
- `scenes/mode_select.py`
- `scenes/story_map/scene.py`
- `scenes/arcade_mode.py`
- `assets/*.mp3` (siete pistas)

## Verificación

- La auditoría `tools/review_project.ps1` completó la revisión e importación principal.
- Los módulos de navegación y pausa importaron correctamente.
- `git diff --check` no reportó errores de formato; solo mostró avisos de conversión de finales de línea de Git.
- No se ejecutó `pytest`.

## Pendiente para publicar

- Confirmar que las licencias de las pistas permiten distribuirlas con el juego.
- Crear la rama `integracion_primeratarea`, publicar el pull request hacia `main` y fusionarlo. Estas acciones aún no se realizaron porque este entorno no permite escribir en `.git` y la sesión de GitHub CLI tiene un token inválido.
