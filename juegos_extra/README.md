# Juegos extra

Dos juegos Pygame aislados. Ejecución desde la raíz:

```powershell
python juegos_extra/emoji_catch.py
python juegos_extra/curramgram_go.py
```

## Recursos y controles compartidos

El lienzo de juego es 1920×1080 y se presenta en una ventana redimensionable. F11 alterna pantalla completa; ESC abre pausa; R reinicia desde el resultado. Los recursos requeridos se validan al arrancar. Si una imagen, sprite, fuente o archivo de datos falta o no se puede leer, el juego lanza `ErrorRecursos` con la ruta intentada. Solo `JUEGOS_EXTRA_TOLERANTE=1` permite omitir una imagen, y siempre imprime un `WARNING` con el recurso omitido.

## Emoji Catch

La mano morada usa A/D en el lado izquierdo y atrapa negativos; la mano azul usa J/L en el lado derecho y atrapa positivos. Cada partida dura 120 segundos. La salud mental inicia en 50%, aumenta al atrapar y baja si un emoji escapa; llegar a 0% termina la partida. Al alcanzar 100%, los puntos se duplican durante 8 segundos y vuelve a activarse después de un enfriamiento de 20 segundos. Las estrellas finales dependen de la salud: 1 por ganar, 2 desde 60% y 3 desde 85%. Las barras laterales muestran negatividad y positividad; no cambian la salud.

## CurramGram Go

Pulsa ESPACIO para empezar. Camina con A/D, salta con ESPACIO, escóndete con S, avisa con E, toma fotos con clic y publica con P. Junta 25 sellos, resuelve seis situaciones y aborda en la puerta 7 con E. Cada sello da 5 puntos. Las situaciones bien resueltas dan puntos y 4 segundos; entregar evidencia del tamborero a Policía da 80 puntos y 10 segundos. Las marcas de estrellas son 150, 250 y 350 puntos. Un carrito anunciado con `¡SALTA!` quita 3 segundos si tropiezas; el jugador parpadea y queda invulnerable durante 1,5 segundos.

Cami y los NPC se preescalan una sola vez a 175 px de altura (16,2% de 1080 px). `assets/curramgram/animaciones.json` define los ciclos y `animacion.py` los reproduce. El archivo `assets/curramgram/anclajes_cami.json` conserva el anclaje al pie de los 12 cuadros.

## Arte y capturas

Las hojas y los recortes viven bajo `assets/`. Las capturas headless de juego, pausa y final están en `_capturas/`; los renders de referencia 1920×1080 se guardan reducidos a 1600×900 para inspección visual segura.

Regenerar capturas:

```powershell
python juegos_extra/herramientas/capturar_juegos.py
```

Ejecutar las verificaciones y bots:

```powershell
$env:SDL_VIDEODRIVER = "dummy"
$env:SDL_AUDIODRIVER = "dummy"
python -m unittest juegos_extra.tests.test_emoji_salud juegos_extra.tests.test_controles_emoji juegos_extra.tests.test_curramgram_mecanicas juegos_extra.tests.test_curramgram_bucle juegos_extra.tests.test_animacion_cami juegos_extra.tests.test_assets_y_pixeles -v
```
