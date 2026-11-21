<div align="center">

# 🌴 BarranquillaWare

**Videojuego arcade estilo *WarioWare* ambientado en Barranquilla, enfocado en el uso responsable y consciente de las redes sociales.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Pygame](https://img.shields.io/badge/Pygame-2.x-00C853?style=for-the-badge&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Estado-En%20Desarrollo-FF9800?style=for-the-badge)

</div>

---

## 🎮 Descripción

**BarranquillaWare** combina el ritmo frenético de los microjuegos clásicos tipo *WarioWare* con escenarios, humor y situaciones cotidianas de Barranquilla para reflexionar sobre privacidad, desinformación, algoritmos y convivencia digital.

### Modos de juego
- **Modo Historia:** Recorre el mapa interactivo de la ciudad y supera desafíos temáticos.
- **Modo Arcade:** Ráfagas continuas de microjuegos con dificultad creciente.
- **Modo Libre:** Selecciona y practica cualquier microjuego desbloqueado.

---

## ⚙️ Requisitos e Instalación

- **Python 3.10+**
- **Pygame**
- *(Opcional)* **Cámara web + MediaPipe** para microjuegos con detección de movimiento/gestos

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

---

## 🚀 Cómo ejecutar el juego

En Windows puedes iniciarlo directamente con el lanzador:

```powershell
.\JUGAR.bat
```

O desde la terminal con Python:

```powershell
python main.py
```

---

## 🧪 Pruebas automatizadas

Para ejecutar la suite de pruebas en modo *headless* (sin abrir ventana ni audio):

```powershell
$env:SDL_VIDEODRIVER = "dummy"
$env:SDL_AUDIODRIVER = "dummy"
python -m pytest -q
```

---

## 📁 Estructura del proyecto

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

---

## 👥 Equipo — GuayabaLabs

| Integrante | GitHub |
| :--- | :--- |
| **César Antonio Berrío Remolina** | [@Remolinac](https://github.com/Remolinac) |
| **Samuel Elías Ortega Rodríguez** | [@Seor1601](https://github.com/Seor1601) |
| **Daniel Alejandro Rincón Navarro** | [@WosDan](https://github.com/WosDan) |
| **Salma Valeria Romero Robles** | [@Salma-rro](https://github.com/Salma-rro) |
