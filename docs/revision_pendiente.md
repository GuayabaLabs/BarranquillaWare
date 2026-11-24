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

- [ ] Modo Libre muestra tarjetas con paginación limpia.
- [ ] La navegación con teclado/mando por menús muestra un halo dorado en el botón enfocado.
## 6. Tareas de fuegos, flechas del mapa y clic de botones

- [ ] **Fuegos artificiales**: cada fuego suena con un solo estallido justo al reventar (sin el silbido de subida).
      Revisar en el letrero de "¡Ganaste!" de cualquier minijuego, en el aviso de trofeo del mapa y en el resultado
      del Coaster. Deben oírse **por debajo** de la voz de SEOR ("¡Coronaste!"). Volúmenes en
      `effects/fuegos_sonido.py` (`VOLUMEN` y `VOLUMEN_CON_VOZ`).
- [ ] **Flechas en el mapa**: → y ← solo toman calles a ≤ 45° de la horizontal; ↑ y ↓ calles a ≤ 68°; dos flechas
      a la vez toman diagonales. Si una flecha no tiene calle hacia ese lado, Cami no se mueve (antes se iba
      por otra calle). Ángulos en `DPAD_MAX_ANGLE_*` de `scenes/story_map/scene.py`.
- [ ] **Clic de botones**: el juego ahora mide el tamaño real de la ventana (Windows) y abre una ventana que cabe en
      la pantalla. Probar en ventana normal, maximizada y F11 que el clic funcione sobre el botón (no debajo).
      Si `settings.json` tenía guardada una ventana de 1920x1080, al abrir se ajustará sola.

## 7. Tiempo en el mapa, río, faroles y aeropuerto

- [ ] **Paso del tiempo**: la píldora de arriba a la derecha muestra la hora (ej. `18:20 ATARDECER`). Un día dura
      6 minutos reales y **cada nivel completado adelanta 3 horas** (se ve anochecer mientras la Paloma felicita).
      La hora se guarda con la partida. Ajustes en `scenes/story_map/ciclo_dia.py` (`DURACION_DIA_SEG`,
      `HORAS_POR_NIVEL`, colores de cada franja en `FRANJAS`). Clic en la píldora sigue cambiando el clima
      (lleva el reloj a esa hora; la lluvia es aparte).
- [ ] **Faroles**: se prenden uno a uno al oscurecer (charco de luz en el piso + bombilla). Son los 23 faroles
      pintados en el mapa (`config/faroles_mapa.json`, generado con `python tools/detectar_faroles.py`).
      Si se mueve un farol del dibujo del mapa, hay que volver a correr ese comando.
- [ ] **Río animado**: olas copiadas de las pintadas en el mapa que avanzan con la corriente y destellos que
      titilan. Solo dibuja dentro del agua (prueba automática: 0 píxeles fuera). Revisar que se vea natural.
      Ajustes en `scenes/story_map/rio.py` (`FLUJO`, `DENSIDAD_OLAS`).
- [ ] **Rendimiento**: medido sin pantalla: 4-12 ms por cuadro (noche es lo más caro). Revisar en el PC real que
      el mapa vaya fluido de noche.
- [ ] **Aeropuerto**: ahora se juega CurramGram desde su nodo amarillo, con diálogo propio de la Paloma. Es un
      nivel extra (como el Malecón): no cambia el conteo de los 5 niveles de la campaña.

## 8. Lugares iluminados de noche y luces del aeropuerto

- [ ] De noche los lugares emblemáticos (estadio, Buenavista, Ventana, Uninorte, Malecón, Aleta, Mallorquín,
      aeropuerto) se ven iluminados con sus colores; las calles y zonas vacías siguen oscuras. Las estrellas
      y pines de los niveles dan luz a su alrededor. Ajustes en `scenes/story_map/luces_lugares.py`
      (`COLOR_EDIFICIO`, `INTENSIDAD_LUGAR`).
- [ ] Aeropuerto: luces rojas en los bordes de la pista que corren hacia la cabecera, barras rojas en ambas
      cabeceras y baliza que parpadea en la torre. De día se ven tenues. Si se mueve el aeropuerto en el mapa,
      las luces lo siguen; si se cambia su dibujo, ajustar `BORDE_A`, `BORDE_B`, `CABECERA_*` y `TORRE`.
- [ ] Rendimiento medido sin pantalla: unos 11 ms por cuadro de mediana, con picos de 20-30 ms durante el
      anochecer. Revisar en el PC real que no se note tironeo al caer la noche.

## 9. Música única y voz del heladero

- [ ] Punch: al caer la tarjeta del villancico se apaga la música del juego y suena solo "Los peces en el río";
      sigue sonando en el menú de pausa y nada vuelve a poner la música del Punch. (No se pudo reproducir el
      "dos canciones" en pruebas: se blindó para que cualquier música nueva apague la anterior.)
- [ ] Una sola canción en todo el juego: `AudioManager.play_bgm` apaga la anterior y también las canciones que un
      minijuego suene como efecto (p. ej. la del trol de la Fritanga). La canción del trol ahora sigue en la pausa.
- [ ] Heladero: el pregón "¡Heladooo!..." se oye cuando aparece la línea (falta el archivo de voz,
      `assets/voces/heladero_pregon.mp3`). La línea espera a que termine la voz antes de pasar.
