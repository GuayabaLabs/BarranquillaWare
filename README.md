# BarranquillaWare

Videojuego arcade estilo *WarioWare* ambientado en Barranquilla, enfocado en el uso responsable y consciente de las redes sociales.

---

## Requisitos

- **Python 3.10+**
- **Pygame** (y dependencias del proyecto)
- *(Opcional)* **Cámara web + MediaPipe** para microjuegos con detección de movimiento/gestos

## Instalación rápida

```powershell
# 1. Clonar el repositorio
git clone https://github.com/GuayabaLabs/BarranquillaWare.git
cd BarranquillaWare

# 2. (Opcional) Crear y activar entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar dependencias base
pip install pygame

# 4. (Opcional) Habilitar controles por cámara con MediaPipe
python -m pip install -r requirements-camera.txt
```

## Cómo ejecutar el juego

En Windows puedes iniciarlo directamente con el lanzador:

```powershell
.\JUGAR.bat
```

O desde la terminal con Python:

```powershell
python main.py
```

## Pruebas automatizadas

Para ejecutar la suite de pruebas en modo *headless* (sin abrir ventana ni audio):

```powershell
$env:SDL_VIDEODRIVER = "dummy"
$env:SDL_AUDIODRIVER = "dummy"
python -m pytest -q
```

## Estructura del proyecto

| Carpeta / Archivo | Descripción |
| :--- | :--- |
| `main.py` | Punto de entrada principal del juego. |
| `JUGAR.bat` | Lanzador rápido para Windows. |
| `core/` | Motor (`Engine`), máquina de estados, cámara, audio, assets y `BaseMicrogame`. |
| `scenes/` | Escenas principales: menú, selección de personaje, mapa historia, arcade y modo libre. |
| `microgames/` | Microjuegos independientes. |
| `ui/` | Componentes de interfaz reutilizables. |
| `effects/` | Partículas y efectos visuales. |
| `assets/` | Imágenes, fuentes y audio. |
| `tests/` | Pruebas automatizadas. |
| `tools/` | Utilidades de desarrollo y revisión. |

## Desarrollo de microjuegos

Los microjuegos nuevos deben heredar de `core.microgame.BaseMicrogame`, reutilizar el flujo de resultados existente y cargar recursos mediante las convenciones de `AssetManager` y `AudioManager`.
