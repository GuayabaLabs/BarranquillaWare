# BarranquillaWare: instrucciones para agentes

## Objetivo

Mantener y ampliar un juego arcade estilo WarioWare sobre el uso responsable de redes sociales, ambientado en Barranquilla.

## Arquitectura real

- `main.py` inicia `core.engine.Engine` y `scenes.main_menu.MainMenuScene`.
- `core/` contiene la infraestructura compartida. No duplicar gameloops, carga de assets, audio ni transición de estados dentro de cada microjuego.
- `scenes/` contiene estados de alto nivel.
- `microgames/` contiene juegos independientes. La mayoría hereda de `BaseMicrogame`.
- `assets/` es la fuente de recursos.
- `tests/` valida comportamiento y render headless.
- `Project-TBD/` es histórico y queda fuera del flujo principal.

## Antes de editar

1. Revisar `git status --short`.
2. Ejecutar `tools/review_project.ps1`.
3. Leer el módulo objetivo y su prueba relacionada.
4. Confirmar si el cambio pertenece a la arquitectura actual o a `Project-TBD`.

## Reglas

- Mantener Pygame y la arquitectura orientada a objetos existente.
- Reutilizar `BaseState`, `BaseMicrogame`, `AssetManager`, `AudioManager` y `SettingsManager`.
- No hardcodear rutas absolutas del equipo del desarrollador.
- No guardar evidencias en carpetas externas; usar `artifacts/` si hace falta.
- Evitar iniciar cámara, MediaPipe, audio o hilos durante imports o pruebas que no los necesiten.
- Verificar dimensiones, transparencia y referencias antes de reemplazar assets.
- Preservar el estilo cozy acuarela y la resolución virtual 1920x1080 salvo indicación contraria.

## Verificación

```powershell
$env:SDL_VIDEODRIVER = "dummy"
$env:SDL_AUDIODRIVER = "dummy"
python -m pytest tests/test_nombre.py -q
python -m pytest -q
```

Si una prueba falla por una ruta de evidencia externa, corregir la prueba para usar una ruta local antes de atribuir el fallo al juego.

Preferir cambios pequeños y verificables. Informar archivos cambiados, pruebas ejecutadas y problemas preexistentes. No afirmar que una función existe solo porque aparece descrita en el README.
