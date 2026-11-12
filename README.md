# BarranquillaWare

> **Videojuego arcade estilo WarioWare ambientado en la cultura, arquitectura y Carnaval de Barranquilla (Curramba la Bella), Colombia.**
> Diseñado bajo una arquitectura desacoplada a 60 FPS, pipeline gráfico híbrido con OpenGL/ModernGL, soporte universal de mandos (Xbox, PlayStation, DirectInput) y un lienzo virtual nativo de 1920x1080.

---

## 🎮 Modos de Juego

### 1. Modo Historia (`ModoHistoriaScene` / `StoryMapScene`)
- **Overworld Panorámico Continuo ($3342 \times 1882\text{ px}$):**
  - Costuras de cuadrantes completamente reparadas y maquilladas con faroles de hierro vectoriales, asfalto suavizado y el icónico Guayacán Rosa florecido.
  - 6 Puntos de Interés (POIs) emblemáticos con sombras suaves de contacto, halos pulsantes y destellos dorados.
  - Trazado de rutas luminosas que se iluminan al completar cada nivel.
  - **Etapa Jefe Desbloqueable:** Al conquistar los 6 distritos, el centro de la ciudad desbloquea la **Gran Batalla de Flores**. Superar este desafío corona al jugador como **Rey Momo del Carnaval** con lluvia de confeti, fuegos artificiales y fanfarria.
  - Menú lateral desplegable (*Drawer Menu*) con guardado persistente en `settings.json`, cambio de clima dinámico (Día, Atardecer, Noche, Lluvia tropical) y retorno seguro.

### 2. Modo Arcade (`ArcadeModeScene`)
- **Frenesí de Microjuegos Infinitos:**
  - Cadena ininterrumpida de microjuegos seleccionados al azar.
  - Sistema de 4 Vidas representadas por coloridas máscaras de Marimonda.
  - Escalado progresivo de velocidad: $+15\%$ cada 4 rondas superadas.
  - **Hito de Jefe (Ronda 10):** Cada 10 rondas se activa la **Etapa Jefe (Batalla de Flores)**; vencerla restaura 1 vida de Marimonda.
  - Pantalla de Game Over con persistencia de récord histórico en `settings.json`.

### 3. Modo Libre (`FreePlayScene`)
- **Catálogo Interactivo 3x3:**
  - Práctica individual e ilimitada de los 8 microgames con tarjetas animadas, badges de completitud ("★ COMPLETADO") y botón de lanzamiento directo.
  - **Acceso Directo a la Etapa Jefe:** Tarjeta dorada inferior para desafiar la Batalla de Flores en cualquier momento.

---

## 🕹️ Distritos y Microjuegos

| Nivel | Distrito | Microjuego | Consigna | Mecánica |
|:---:|---|---|---|---|
| **01** | **Ecorreserva Mallorquín** | *¡Fotografía al Flamenco!* | `¡FOTOGRAFÍA!` | Mueve el visor réflex con el mouse/stick y dispara la cámara cuando el flamenco esté centrado. |
| **02** | **Campus Uninorte** | *Carrera al Aula de 6:30* | `¡LLEGA AL SALÓN!` | Corre a toda prisa mofando el botón de acción antes de que el docente cierre la puerta. |
| **03** | **Ventana al Mundo** | *¡Armoniza los Cristales!* | `¡ARMONIZA!` | Identifica el color primario faltante en el monumento y pulsa la tecla (1-4) o haz click. |
| **04** | **Gran Malecón del Río** | *¡Frena en la Cima!* | `¡FRENA EN LA CIMA!` | La rueda Luna del Río gira; frena la cabina VIP exactamente en el cuadrante superior verde. |
| **05** | **Estadio Metropolitano** | *El Penal del Tiburón* | `¡COBRA EL PENAL!` | Espera a que la retícula oscilante apunte al ángulo de la portería y remata al arco. |
| **06** | **Aeropuerto Cortissoz** | *¡Aterriza en la Pista!* | `¡ATERRIZA!` | Compensa el viento cruzado y alinea el avión de pasajeros comercial para el touchdown. |
| **07** | **Calle 84** | *¡La Fritanga de la 84!* | `¡VOLTEA LA AREPA!` | Voltea las arepas de huevo en el caldero hirviendo cuando estén doradas antes de que se quemen. |
| **08** | **La Troja** | *¡Salsa y Cumbia en La Troja!* | `¡MANTÉN EL EQUILIBRIO!` | Baila salsa brava contrarrestando la inclinación del vaso helado en la cabeza sin dejarlo caer. |
| **JEFE** | **Vía 40 (Carnaval)** | *¡La Gran Batalla de Flores!* | `¡BATALLA DE FLORES!` | **Multietapa (15s):** 1) Esquiva la maicena y espuma; 2) Repica la tambora al compás cumbiero; 3) Salta y atrapa la Corona Real. |

---

## ⌨️ Controles

| Acción | Teclado / Ratón | Mando / Gamepad (Xbox / PlayStation) |
|---|---|---|
| **Acción / Mashing / Salto** | `ESPACIO` / Click Izquierdo | `Botón A` / `Cruz` (Cross) |
| **Pausa / Menú / Volver** | `ESCAPE` | `Botón B` / `Start` / `Opciones` |
| **Confirmar Selección** | `ENTER` | `Botón X` / `Cuadrado` |
| **Movimiento / Navegación** | Flechas `← ↑ ↓ →` o `W A S D` | D-Pad o Stick Analógico Izquierdo |
| **Pantalla Completa** | `F11` | — |

---

## 🏗️ Arquitectura Técnica

- **Engine Principal ([`core/engine.py`](file:///c:/Users/danie/Desktop/BarranquillaWare/core/engine.py)):**
  - Gameloop desacoplado a 60 FPS con Delta Time clamped ($dt \le 0.08$).
  - Canvas nativo $1920 \times 1080$ renderizado mediante shaders GLSL de ModernGL (con fallback transparente a software SDL si no hay aceleración 3D).
  - Letterbox / Pillarbox automático al redimensionar ventanas.
- **Audio Procedural ([`core/audio_manager.py`](file:///c:/Users/danie/Desktop/BarranquillaWare/core/audio_manager.py)):**
  - Generación de formas de onda en tiempo real con `numpy` (tambor alegre cumbiero, silbato carnavalero, chimes de victoria y buzzers de fallo), garantizando cero latencia y cero dependencias de archivos externos faltantes.
- **Persistencia ([`core/settings.py`](file:///c:/Users/danie/Desktop/BarranquillaWare/core/settings.py)):**
  - Almacenamiento atómico en formato JSON de configuraciones de audio, pantalla completa, progreso del Modo Historia y high scores de Arcade.

---

## 📦 Compilación de Ejecutable Autónomo (Standalone .EXE)

Para empaquetar el juego completo en un ejecutable de Windows independiente:

```powershell
# 1. Crear carpeta portable en dist/BarranquillaWare
python build_standalone.py

# 2. Crear un único archivo .exe monolítico
python build_standalone.py --onefile
```

---

## 🧪 Pruebas Automatizadas

El proyecto incluye suites de pruebas automatizadas que ejecutan todos los subsistemas en modo *headless* (sin ventana física):

```powershell
python test_story_map_pois.py   # Valida Overworld, los 6 POIs y el Boss Stage
python test_arcade_mode.py      # Valida gameloop Arcade, escalado de velocidad y ronda 10
python test_free_play.py        # Valida catálogo 3x2 y tarjeta de jefe
python test_menu_verification.py # Valida menús, transiciones y audio continuo
python test_gamepad.py          # Valida traducción de mandos virtuales
python test_boss_stage.py       # Valida las 3 fases del Boss Stage
```
