# Revisión pendiente para el equipo

Cambios de la rama `CesarAvances` que **solo se verificaron con pruebas automáticas** (headless, cámara y mando simulados).
Nadie los ha probado aún con webcam, mando físico ni escuchando el audio. Si pueden, revisen estos puntos y anoten
qué pasa (juego, qué hicieron, qué esperaban, qué ocurrió).

Cómo correr el juego completo:

```powershell
python main.py
```

## 1. Mando físico

- [ ] Los botones se configuraron con distribución **Xbox** (A=0, B=1, X=2, Y=3, Start=7). Con un control de
      PlayStation o genérico pueden quedar cruzados y Start podría no pausar. Archivo: `core/engine.py`
      (`JOY_BUTTON_KEYS`) y `GAMEPAD_BUTTON_KEYS` en cada minijuego.
- [ ] El stick debe avanzar **un** botón/nodo por empujón (zona muerta 0.5, soltar < 0.3). Si se siente duro o
      sensible, ajustar `JOY_AXIS_DEADZONE` / `JOY_AXIS_RELEASE` en `core/engine.py`.
- [ ] Start/B abre la pausa en todos los minijuegos.

## 2. Cámara (MediaPipe)

- [ ] El lapicero se ve **encima** de los menús (antes quedaba tapado). Mantenerlo quieto 0.7 s hace clic; pellizcar también.
- [ ] En el **mapa** no hay clic por permanencia (para no caminar sin querer): se hace clic pellizcando.
      Palma abierta hacia un lado ~0.35 s = avanzar un nodo. Puño sobre el nodo amarillo = entrar al nivel.
      Depende de que MediaPipe reconozca bien la palma abierta; con poca luz puede fallar.
- [ ] Ahora la cámara sigue **hasta dos manos** (para Emoji Catch). Si se levantan ambas manos, los juegos que usan
      una sola (Trend, Punch, Concentración, Sprint, Moderación) podrían seguir la mano equivocada por momentos.
      También puede bajar un poco el rendimiento. Archivo: `core/camera_gestures.py` (`max_num_hands=2`).
- [ ] Pellizco y puño a veces se confunden (lo detecta el mismo módulo de antes).
- [ ] Minijuegos con control por gestos nuevo (puente genérico `CAMERA_ACTIONS` en `core/microgame.py`):
      Aterrizaje, Troja, Flores, Mallorquín (mano a un lado = flechas), Fritanga, Malecón, Penal, Flores, Mallorquín,
      Cine (puño/pellizco = acción) y Ventana al Mundo / Cine (doblar un dedo = teclas 1-4).
      Los umbrales son estimados (`CAMERA_DEADZONE = 0.12`); quizá haya que ajustarlos por juego.
- [ ] Uninorte Concentración: cada pellizco debe contar (antes el motor se lo "robaba").

## 3. Emoji Catch y CurramGram Go!

Ahora hay **una sola versión** de cada juego (se eliminó `juegos_extra/`):
`microgames/curramgram_go.py` + `microgames/curramgram/` y `microgames/emoji_catch.py` + `microgames/emojis/`.
Sprites en `assets/curramgram/` y `assets/emoji_catch/`. Arte y audio pendientes: `docs/pedidos_arte_audio_redes.md`.

Probarlos solos (desde la raíz):

```powershell
python microgames/curramgram_go.py
python microgames/emoji_catch.py
```

- [ ] Antes de jugar aparece la Paloma con el contexto de redes; Espacio/clic/A/pellizco avanza, Esc la salta.
- [ ] Interfaz acuarela con IndieFlower (avisos, barras, círculos, botones). Revisar que ningún texto se corte.
- [ ] Emojis sin halo blanco (se limpia el borde por código al cargar).
- [ ] La pausa en Modo Libre ahora tiene Reiniciar y Salir (antes solo Continuar y Opciones).

- [ ] **Audio propio** (música + 11 efectos): escuchar volumen y que cada efecto suene en su momento. Los efectos
      largos se recortan (p. ej. "caso mal" de 4 s queda en 1,6 s); si alguno se corta feo, subir su duración
      máxima en `SFX` (`microgames/curramgram_go.py`, `microgames/emoji_catch.py`).
- [ ] **Arte acuarela**: CurramGram (fondo, props, personajes, Cami) y Emoji Catch (balanza, manos, emojis).
      Revisar que los personajes estén asignados al caso correcto (viajero, turista, joven, señora, comparsa,
      tamborero = niño con tambor, trabajador con cava = carrito) y que las manos acuarela no se vean borrosas
      (vienen pequeñas, ~100 px, y se agrandan a 270 px).
- [ ] Emoji Catch con dos manos: si las manos se cruzan de lado pueden "saltar" entre morada y azul; con una sola mano
      visible, la otra mano del juego se queda quieta.
- [ ] CurramGram: el tiempo puede pasar de 120 s con bonos; la barra se queda llena hasta que baja de 120.

## 4. Arte del mapa

- [ ] `assets/metropolitano_mapa.png` y `assets/ventana_al_mundo_mapa.png` se retocaron por código (color, tinta,
      contorno) para parecerse al resto del mapa. Originales en `artifacts/poi_originales/`. Si no convence, se
      reajusta con `python tools/estilizar_poi.py assets/metropolitano_mapa.png --sat 2.0`.

## 5. Interfaz

- [ ] Modo Libre ahora tiene 10 tarjetas (5x2): textos más pequeños. La corona de la tarjeta del jefe se ve como un
      cuadro (era así antes).
- [ ] La navegación con teclado/mando por menús muestra un halo dorado en el botón enfocado.

## Problema preexistente

- `tests/test_boss_stage.py` guarda una imagen en una ruta de otro computador (`C:/Users/danie/...`). No falla, pero
  debería usar `artifacts/`.
