# Juegos extra de BarranquillaWare

Dos minijuegos independientes en Pygame. Se ejecutan desde la raíz del proyecto con `python juegos_extra/emoji_catch.py` o `python juegos_extra/curramgram_go.py`. No importan el menú ni el gestor original; comparten únicamente utilidades locales de `comun.py`. Requieren las librerías ya instaladas para el proyecto.

## Emoji Catch: Balance!

Duración: 120 segundos. La mano morada controlada con A/D recoge elementos negativos; la mano azul con J/L recoge los positivos. Un tipo equivocado resta salud mental y puntos; dejar caer un negativo también afecta la salud. Para ganar, termina el reloj con salud positiva y con las barras de negatividad/positividad separadas por no más de 24 puntos (configurable en `emoji_catch.py`). La dificultad crece con el tiempo. No hay tope de puntaje.

ESC abre la pausa; flechas arriba/abajo y Enter eligen Continuar, Reiniciar o Salir. La pantalla final muestra el resultado y R reinicia.

## CurramGram Go!: Aterrizando en el Cortissoz

Recorre la terminal con A/D o flechas y llega a Gate 7 antes de 120 segundos. S/flecha abajo activa sigilo; ESPACIO salta; E interactúa; mouse y clic toma una foto; P publica la última foto. ESC abre la pausa y R reinicia desde el reporte final. Los carritos descuentan cinco segundos si no saltas o te escondes.

Investiga las seis escenas: confirma que la bolsa blanca es harina sin acusar; fotografía al tamborero desde sigilo y vuelve a Policía; advierte a la turista del pasabordo con E; respeta al joven en la banca; verifica que el hielo de la cava se derramó; y comparte la comparsa en un evento público. Publicar datos privados o chismes penaliza ciudadanía. En la puerta o al terminar el tiempo aparece el perfil con el resultado de cada decisión.

## Recursos visuales y sonoros

Los recursos se cargan con rutas relativas desde `../assets/` y en modo solo lectura. Si falta una imagen o fuente, el juego sigue con sus recursos dibujados.

| Juego | Recursos existentes utilizados | Dibujado en Pygame por falta de alternativa en el proyecto |
|---|---|---|
| Emoji Catch | `fondo_concentracion_microjuego.png`, fuentes `Impact.ttf` y `ArialBold.ttf` | Emojis estilizados, manos enguantadas, barras laterales, destellos y grietas |
| CurramGram Go | `fondo_minijuego_crossy.png`, `westcol_chibi.png`, fuentes existentes | Interior del aeropuerto, policía, viajero, sospechoso, turistas, comparsa, mobiliario, Gate 7, cámara y avisos |

El Cortissoz disponible (`aeropuerto_ernesto_cortissoz_mapa.png`) es una ilustración para el mapa y no representa una terminal interior; el juego no la estira para fingir un escenario. Los spritesheets disponibles son de NPC de otro minijuego y no contienen variantes direccionales adecuadas para estas seis escenas, por lo que se dibujan siluetas propias. Tampoco hay sprites de guantes ni emojis. Se encontraron fuentes y sonidos ambientales, pero no un efecto dedicado de captura/bloqueo; no se toma prestado audio temático de otro minijuego.

## Resolución y controles compartidos

Ambos juegos abren a 1920×1080, 60 FPS. La entrada pasa por `leer_entrada()` para facilitar un reemplazo futuro por cámara/mano. Las constantes configurables están al inicio de cada archivo. `comun.py` centraliza carga segura de imágenes/fuentes, paneles, pausa y pantalla final.

Algunas escenas se resuelven de forma breve para no interrumpir el recorrido; los aprendizajes completos aparecen en el reporte final. El personaje jugable de CurramGram usa el chibi existente como retrato fijo porque el repositorio no incluye un sprite con direcciones.
