# Pedidos de arte y audio: CurramGram Go! y Emoji Catch

Todo lo que falta para que los dos minijuegos queden a la altura de los demás. **El código ya está listo
para recibirlo**: basta con guardar cada archivo con el nombre exacto en la carpeta indicada y el juego lo
usa solo (mientras falte, se ve el respaldo actual hecho por código).

## Estado

- ✅ **CurramGram, arte recibido e integrado**: pared, piso, visor, círculo, 6 botones, sello, logo, 6 props,
  8 personajes y 8 poses de Cami (originales en `artifacts/arte_recibido/`). Se importaron con
  `python tools/importar_arte_curramgram.py artifacts/arte_recibido` (quita el fondo blanco, separa las hojas y
  descarta las etiquetas). Para cambiar una imagen: reemplazar el archivo numerado y volver a correr el comando.
- ✅ **Emoji Catch, arte recibido e integrado**: balanza, 8 manos (se usan abierta y puño) y 12 emojis
  (dos nuevos: estrellas y ángel). Importados con `python tools/importar_arte_emoji.py artifacts/arte_recibido`.
- ✅ **Audio recibido e integrado**: música de los dos juegos y los 11 efectos. Los efectos largos se recortan al
  cargar (silencio inicial y duración máxima con desvanecido); los archivos originales en `assets/` no cambian.
  Duraciones máximas en `SFX` de `microgames/curramgram_go.py` y `microgames/emoji_catch.py`.
- Sin pedidos pendientes. La voz de la Paloma sigue siendo opcional (hoy suena su arrullo).
- Notas del arte recibido: Cami no tiene pose "agachada tomando foto" ni "empujón"; se reutiliza la pose agachada.
  La hoja de Cami tiene los cuadros de caminar más pequeños que "quieta"; el código los iguala por altura.

## Reglas para generar las imágenes

- Estilo: **acuarela pintada a mano**, colores cálidos del Caribe, contorno marrón oscuro suave
  (como `assets/Interfaz/bannerUbicacion.jpg` o los edificios del mapa).
- **Fondo blanco puro (#FFFFFF)**, sin sombras sobre el fondo ni marco. El código quita el blanco
  (`AssetManager.cargarSinFondo`). No pedir "fondo transparente": la IA lo dibuja como cuadros.
- **Una imagen por elemento**, centrado y completo, con margen blanco alrededor. Nada de escenas armadas.
- PNG, tamaño mínimo indicado (más grande también sirve; el código escala).
- Sin texto dentro de la imagen salvo que se pida (el texto lo pone el código con IndieFlower).

Plantilla de prompt que funciona:

> Ilustración en acuarela pintada a mano, estilo cuento infantil cálido, de [ELEMENTO], vista [frontal / 3/4],
> contorno marrón oscuro suave, colores vivos del Caribe, un solo objeto centrado, **fondo blanco puro liso**,
> sin texto, sin sombra en el fondo.

---

## CurramGram Go! (carpeta `assets/curramgram/`)

| Archivo | Tamaño mín. | Dónde se usa | Qué dibujar |
|---|---|---|---|
| `fondo_pared_terminal.png` | 1920×780 | Fondo superior del recorrido; se repite hacia los lados | Pared interior de terminal de aeropuerto con ventanales grandes que muestran la pista y un avión, techo cálido. **Que el borde izquierdo y el derecho empalmen** (para repetirse). |
| `fondo_piso_terminal.png` | 1920×320 | Piso donde camina Cami; se repite | Piso de baldosa terracota clara visto de frente, empalma a los lados. |
| `visor_camara.png` | 400×400 | Marco que sigue al puntero para tomar la foto | Visor de cámara: cuatro esquinas redondeadas tipo marco de enfoque y un punto/círculo al centro. Centro vacío (blanco). |
| `circulo_caso.png` | 300×300 | Círculos 1-6 de los casos (arriba a la derecha) y los iconos sobre cada persona | Un círculo/botón redondo acuarela **sin número**, color neutro claro (el código lo tiñe gris, verde o rojo y le pone el número). |
| `boton_caminar.png` | 600×200 | Barra inferior, botón A/D | Botón píldora crema con un icono de pies caminando a la izquierda. Sin texto. |
| `boton_saltar.png` | 600×200 | Barra inferior, botón Espacio | Igual, icono de persona saltando. |
| `boton_esconder.png` | 600×200 | Barra inferior, botón S | Igual, icono de persona agachada. |
| `boton_avisar.png` | 600×200 | Barra inferior, botón E | Igual, icono de megáfono o mano levantada. |
| `boton_foto.png` | 600×200 | Barra inferior, botón Foto | Igual, icono de cámara. |
| `boton_publicar.png` | 600×200 | Barra inferior, botón P | Igual, icono de corazón/compartir de red social. |

> Nota sobre los botones: si los generan **con** el icono y **sin** texto, el código escribe la tecla y el texto
> encima con IndieFlower. Si prefieren que el botón traiga el texto dibujado, avísenme y apago el texto del código.

**Opcionales** (mejoran mucho, pero el juego funciona sin ellos; avisen si los van a hacer para conectarlos):

| Archivo | Dónde se usa | Qué dibujar |
|---|---|---|
| `sello_pasaporte.png` (200×200) | Los 25 sellos que se recogen (hoy son cuadritos verdes) | Sello de pasaporte redondo acuarela verde con un avión. |
| `logo_curramgram.png` (900×260) | Título arriba a la izquierda (hoy es pixel art) | Logo "CurramGram Go!" acuarela (aquí **sí** con texto). |
| Props sueltos: `mostrador_checkin.png`, `puesto_butifarras.png`, `banca_espera.png`, `pilar_palmera.png`, `caseta_policia.png`, `puerta_7.png` | Decoración sobre el fondo | Cada uno por separado, vista frontal. |
| Personajes en acuarela | Cami, policía, viajero, turista, joven, señora, comparsa, tamborero, trabajador del carrito | Hoy son pixel art. Si se rehacen, cada personaje en su propio PNG de cuerpo entero, vista de lado, misma altura. Para Cami además: quieta, 5 cuadros caminando, agachada, saltando, tomando foto. |

## Emoji Catch (carpeta `assets/emoji_catch/`)

| Archivo | Tamaño mín. | Dónde se usa | Qué dibujar |
|---|---|---|---|
| `balanza.png` | 400×400 | Balanza arriba al centro (se inclina según negatividad/positividad) | Balanza de dos platos acuarela, plato izquierdo morado y derecho azul. |

**Opcionales**: volver a generar los emojis y las manos en acuarela con fondo blanco puro (los actuales son
recortes con halo; ya se limpian por código, pero con fondo blanco quedan perfectos). Mismos nombres que los
archivos actuales de `assets/emoji_catch/` (`emoji_corazon.png`, `mano_morada.png`, etc.).

---

## Audio (carpeta `assets/`)

Formato `.ogg` o `.mp3`. Música en bucle de 1-2 min; efectos cortos (menos de 1 s). Mientras falten,
suena audio reciclado de otros minijuegos (hay que escucharlo y confirmar que tenga sentido).

### CurramGram Go!

| Archivo sugerido | Momento | Hoy suena (reciclado) | Dónde se cambia |
|---|---|---|---|
| `curramgram_musica.ogg` | Música mientras se recorre el terminal | `contraRelojMusic.mp3` | `MUSIC_TRACK` en `microgames/curramgram_go.py` |
| `curramgram_sello.ogg` | Recoger un sello | golpe del juego del puño | `SFX_SELLO` en `microgames/curramgram/juego.py` |
| `curramgram_salto.ogg` | Saltar | salto general | `_play_event_sounds` en `microgames/curramgram_go.py` |
| `curramgram_tropiezo.ogg` | Chocar con maleta o carrito | fallo general | ídem |
| `curramgram_foto.ogg` | Tomar foto (obturador) | clic de menú | ídem |
| `curramgram_caso_bien.ogg` | Caso resuelto bien | tambora | ídem |
| `curramgram_caso_mal.ogg` | Caso resuelto mal (publicar algo privado, etc.) | derrota general | ídem |

### Emoji Catch

| Archivo sugerido | Momento | Hoy suena (reciclado) | Dónde se cambia |
|---|---|---|---|
| `emoji_musica.ogg` | Música de fondo (biblioteca, lo-fi tranquilo) | `concentracionMusic.mp3` | `MUSIC_TRACK` en `microgames/emoji_catch.py` |
| `emoji_bloqueo.ogg` | Bloquear un emoji negativo | golpe del juego del puño | `SFX_BLOQUEO` en `microgames/emojis/juego.py` |
| `emoji_positivo.ogg` | Atrapar un emoji positivo ("like") | acierto general | `_play_event_sounds` en `microgames/emoji_catch.py` |
| `emoji_escapa.ogg` | Se escapa un emoji (baja la salud) | fallo general | ídem |
| `emoji_animo.ogg` | "Ánimo a tope" (power-up) | silbato | ídem |
| `emoji_megahater.ogg` | Bloquear al Mega-Hater | tambora | ídem |

### Voz de la Paloma (opcional)

Si quieren voz en el diálogo de contexto: un clip por página, por ejemplo `paloma_curramgram_0.ogg` … `_3.ogg`
y `paloma_emoji_0.ogg` … `_2.ogg`. Hoy suena el arrullo de la paloma al abrir el diálogo.

---

## Juego Punch (Ventana al Mundo): tarjetas nuevas y villancico

✅ **Recibido e integrado**: la canción "Los peces en el río" y los 4 iconos acuarela.

El código ya está listo; mientras falten estos archivos se usan iconos dibujados por código y no cambia la música.

| Archivo | Dónde se usa | Qué es |
|---|---|---|
| `assets/Punch/villancico.mp3` (o `.ogg`) | Suena en lugar de la música del juego cuando la tarjeta "Villancico de fondo" cae en la publicación | Grabación de **"Los peces en el río"** (instrumental o cantado, 1-2 min, en bucle) |
| `assets/Punch/iconos/nieve.png` | Icono de la tarjeta "Filtro de nieve" | Copo de nieve acuarela |
| `assets/Punch/iconos/recuerdo.png` | Icono de la tarjeta "Filtro de foto antigua" | Foto vieja / polaroid sepia acuarela |
| `assets/Punch/iconos/hashtag.png` | Icono de la tarjeta "Hashtag navideño" | Símbolo # acuarela (con un toque navideño: rojo y verde) |
| `assets/Punch/iconos/abuela.png` | Icono de la tarjeta "Comentario de la abuela" | Abuelita sonriente con un globito de comentario y un corazón |

Iconos: mismo estilo que los de `assets/Punch/tarjetas.png` (acuarela suave, contorno marrón), **solo el icono,
sin la tarjeta y sin texto**, fondo blanco puro, cuadrado, 400×400 o más. El código lo pone dentro de la tarjeta
y escribe el texto con la fuente de las demás tarjetas.
