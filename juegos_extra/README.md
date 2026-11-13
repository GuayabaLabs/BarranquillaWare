# Juegos extra

Dos juegos independientes en Pygame. Desde la carpeta raíz del proyecto:

```powershell
python juegos_extra/emoji_catch.py
python juegos_extra/curramgram_go.py
```

No se importa el menú ni el gestor existente y no se requieren dependencias nuevas. Cada juego tiene su propio bloque `if __name__ == "__main__"`.

## Ventana y utilidades

- Lienzo virtual de **1920×1080**, salida inicial de **1280×720**, redimensionable y escalada manteniendo proporción; si sobra espacio quedan franjas del color de fondo.
- **F11** alterna pantalla completa. Ambos juegos apuntan a 60 FPS.
- `comun.py` contiene carga segura de recursos, fuentes, paneles, entrada, pausa y pantalla final. La función `leer_entrada()` concentra teclado y mouse.
- ESC abre **Continuar / Reiniciar / Salir**. Al terminar se muestra el resultado; **R** reinicia.
- Constantes de duración, dificultad, umbrales y velocidades están arriba de cada juego.

## Emoji Catch: Balance!

Partida de 120 segundos. La mano morada **solo** se mueve con **A/D** y recoge emojis negativos; la mano azul **solo** con **J/L** y recoge positivos. S, las flechas y las demás teclas no mueven las manos. Un error de mano resta salud y puntos; si un negativo escapa, golpea el feed y baja la salud. Se gana si queda salud y el balance final está dentro del umbral configurable; no hay límite de puntaje.

Incluye combos x2/x3, patrocinio de puntos dobles, vómito zigzagueante, enojados que aceleran, corazón roto separado, pulgar que gira, oleadas de haters/tendencia/troll, mega-hater de tres golpes, aviso de desbalance, partículas, vibración y cámara lenta en los últimos segundos.

## CurramGram Go!: Aterrizando en el Cortissoz

Recorre la terminal hacia Gate 7 antes de los 120 segundos:

- **A/D** o flechas izquierda/derecha: caminar.
- **S** o flecha abajo: esconderse/agacharse.
- **Espacio**: saltar el carrito.
- **E**: interactuar.
- **Mouse + clic izquierdo**: tomar foto con el visor.
- **P**: publicar la última foto.

La terminal se desplaza horizontalmente y muestra tres zonas, Policía, puesto de fritos, pasajeros, comparsa, Gate 7, carrito móvil y las seis situaciones del reporte. Las fotos de lejos muestran el señuelo; al acercarse se revela el contexto. Para entregar evidencia real, fotografía al tamborero escondido y usa E junto a Policía. Apuntar durante más de un segundo a una persona vulnerable activa el aviso de privacidad. Al llegar a Gate 7 o acabar el tiempo aparece el perfil con la decisión y aprendizaje de cada escena.

## Arte y audio reutilizados

Las hojas adjuntas se guardaron dentro de este paquete para mantener todos los cambios aislados. Sus versiones originales están en `assets/hojas/`; las variantes limpiadas y los recortes están también bajo `assets/`. Los archivos del proyecto original se leen desde sus rutas relativas y no se alteran.

| Juego | Recursos originales del proyecto | Recursos de las hojas adjuntas | Dibujado porque no había sprite equivalente |
|---|---|---|---|
| Emoji Catch | `assets/fondo_concentracion_microjuego.png`; `assets/fonts/Impact.ttf` y `ArialBold.ttf`; música `assets/7am_ancpg_ost_main_menu.ogg`; golpe `assets/char_audio_0_microjuego_puño.ogg`; marco/botones de `assets/recuadro_menu_pausa.png` y `assets/boton_*_menu_pausa.png` | Título, tarjetas, tubos laterales, guantes morado/azul y los doce tipos de emoji en `juegos_extra/assets/emoji/` | Balanza, relleno animado de los tubos, chispas, grietas, partículas, aura de combo y paneles de HUD dinámicos |
| CurramGram Go | Fuentes `assets/fonts/Impact.ttf` y `ArialBold.ttf`; música `assets/7am_ancpg_ost_main_menu.ogg`; sonido `assets/char_audio_1_microjuego_puño.ogg`; marco y botones de pausa del proyecto | Cami, policía, comparsa, trabajador del carrito, grupo vendedor/letrero, tamborero, viajero, turista, pasajeros, joven, señora de la cava, globos, zonas, cabeceras, Gate y teclas desde `juegos_extra/assets/curramgram/` | Interior del terminal (ventanales, pista, aviones, columnas, palmeras, mostradores, bancas y baldosas), sombras, movimiento/idle, visor, cursor de privacidad, alertas dinámicas y cuadros de texto |

Los NPC y emojis visibles salen de los sprites adjuntos. El fondo del aeropuerto no estaba entre los recursos originales, así que se construye en baja resolución y se escala con vecino más cercano, en lugar de reutilizar una ilustración exterior inadecuada. El chisme y los avisos dinámicos se componen con la tipografía y los colores de las piezas de la hoja. Si falta un recurso de disco, la carga devuelve `None` y el juego conserva un respaldo seguro.

## Preparación y recortes de las hojas

- `assets/hojas/hoja_emoji_catch.png` y `hoja_curramgram.png` se recibieron como RGB sin alfa: el tablero de transparencia estaba pintado. `herramientas/recortar_sprites.py` aplica flood-fill conectado desde los bordes, tolerancia de color y cajas manuales en `atlas_emoji.json`/`atlas_curramgram.json`.
- Las versiones `*_limpia.png` tienen transparencia y los recortes exportados incluyen anclajes en `assets/emoji/anclajes.json` y `assets/curramgram/anclajes.json`.
- Se generaron 21 recortes para Emoji Catch y 45 para CurramGram, con hojas de contacto revisadas: `assets/emoji/_contacto_emoji.png` y `assets/curramgram/_contacto_curramgram.png`. El vendedor y el letrero que se solapan se conservan como un solo grupo; los píxeles ocultos por el solape no se pueden recuperar del original.
- Las formas blancas/grises rodeadas por el contorno (guantes, pasabordo, cava) se conservaron durante la limpieza. Las barras de Emoji Catch llevan una máscara adicional en memoria para excluir el tablero residual y animar su relleno sin escribir sobre el sprite fuente.
- CurramGram se amplía con factores enteros y vecino más cercano; Emoji Catch usa suavizado moderado para emojis y guantes.

## Verificación

Prueba automática headless de teclas:

```powershell
$env:SDL_VIDEODRIVER = "dummy"
$env:SDL_AUDIODRIVER = "dummy"
python -m unittest juegos_extra.tests.test_controles_emoji juegos_extra.tests.test_curramgram_mecanicas -v
```

Para volver a generar las seis capturas headless (dos juegos × tres tamaños):

```powershell
python juegos_extra/herramientas/capturar_juegos.py
```

Las capturas quedan en `juegos_extra/_capturas/` con sufijos `1280x720`, `1366x768` y `1920x1080`.


## Cambios recientes en `juegos_extra/`

- `comun.py` dibuja pausa y finales en un panel oscuro propio; sus botones responden a teclado, hover y clic. `texto_con_contorno()` queda disponible para texto sobre escena.
- Emoji Catch ya ubica negativos a la izquierda y positivos a la derecha, limita cada mano a su mitad y ya no penaliza una supuesta mano equivocada. Su cronómetro, balance y salud siguen bajo ajuste.
- La hoja `assets/hojas/hoja_cami_animaciones.png` se recortó a 12 PNG, con anclajes al pie y contacto `assets/curramgram/_contacto_cami.png`. `assets/curramgram/animaciones.json` define ciclos editables y `animacion.py` los reproduce.
- La captura headless puede recrear escenas de juego, pausa y final a 1280×720 y 1920×1080. Los previews de 1920 se reducen a 1600 px de ancho para revisión.

La integración actual de Cami ya anima idle, caminar, agachada y salto. Aún falta conectar transiciones de agacharse/levantarse, fotos y empujón. El rediseño completo de CurramGram (tutorial contextual, investigación por proximidad, semáforo del tamborero, ruta más corta, bonus de tiempo y pruebas de bots) no está implementado. Los requisitos de bots para ambos juegos tampoco tienen resultados medidos en esta etapa.
