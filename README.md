# BarranquillaWare

Videojuego arcade tipo WarioWare ambientado en Barranquilla. Su tema es el uso consciente de las redes sociales.

## Ejecutar

```powershell
python main.py
```

Para habilitar los controles por cámara con MediaPipe, instala la versión compatible de Protocol Buffers:

```powershell
python -m pip install -r requirements-camera.txt
```

Pruebas sin ventana:

```powershell
$env:SDL_VIDEODRIVER = "dummy"
$env:SDL_AUDIODRIVER = "dummy"
python -m pytest -q
```

## Estructura

- `main.py`: punto de entrada.
- `core/`: motor, estados, cámara, audio, assets, configuración y microjuego base.
- `scenes/`: menú, selección de personaje, mapa, arcade y modo libre.
- `microgames/`: microjuegos individuales.
- `ui/`: componentes de interfaz.
- `effects/`: partículas y efectos visuales.
- `assets/`: imágenes, fuentes y audio.
- `tests/`: pruebas automatizadas.
- `tools/`: ejecutores y herramientas de desarrollo.
- `Project-TBD/`: versión anterior y material histórico.

## Reglas rápidas

Los microjuegos nuevos deben heredar de `core.microgame.BaseMicrogame`, reutilizar el flujo de resultados existente y cargar recursos mediante las convenciones del proyecto.

## Auditoría rápida

```powershell
powershell -ExecutionPolicy Bypass -File tools/review_project.ps1
```

La auditoría muestra el estado, módulos, imports, rutas externas sospechosas, assets y una prueba de importación.
