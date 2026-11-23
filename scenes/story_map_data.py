"""
BarranquillaWare - Datos y Guion del Modo Historia
Constantes de campaña, progresión de niveles y diálogos de Paloma de Curramba.
"""
from typing import Dict, Any
from microgames.uninorte_sprint import UninorteSprintMicrogame
from microgames.uninorte_concentrate import UninorteConcentrateMicrogame
from microgames.buenavista_trend import BuenavistaTrendMicrogame
from microgames.metropolitano_moderacion import MetropolitanoModeracionMicrogame
from microgames.punch_alert import PunchAlertMicrogame
from microgames.fritanga_84 import Fritanga84Microgame
from microgames.curramgram_go import CurramGramGoMicrogame

# Progresión de los 5 Niveles Principales del Modo Historia
STORY_CAMPAIGN_ORDER = ["uninorte", "ventana", "buenavista", "metropolitano", "aleta"]
# Niveles extra jugables en el mapa (no cuentan para la campaña de 5 niveles)
STORY_SECRET_POIS = ["malecon", "aeropuerto"]
STORY_PLAYABLE_POIS = STORY_CAMPAIGN_ORDER + STORY_SECRET_POIS

# Secuencia de desafíos encadenados por cada Nivel de la Historia
STORY_LEVEL_STAGES: Dict[str, list] = {
    "uninorte": [
        {
            "id": "uninorte_sprint",
            "title": "RONDA 1: CARRERA AL AULA A-203",
            "cls": UninorteSprintMicrogame,
            "difficulty": 2,
        },
        {
            "id": "uninorte_concentrate",
            "title": "RONDA 2: ¡CONCÉNTRATE EN LA BIBLIOTECA!",
            "cls": UninorteConcentrateMicrogame,
            "difficulty": 2,
        }
    ],
    "ventana": [
        {
            "id": "punch_alert",
            "title": "EL POST DEL ARBOLITO",
            "cls": PunchAlertMicrogame,
            "difficulty": 4,
        }
    ],
    "buenavista": [
        {
            "id": "buenavista_trend",
            "title": "EL TREND EN BUENAVISTA",
            "cls": BuenavistaTrendMicrogame,
            "difficulty": 3,
        }
    ],
    "metropolitano": [
        {
            "id": "metropolitano_moderacion",
            "title": "¡MODERA LA BARRA BRAVA!",
            "cls": MetropolitanoModeracionMicrogame,
            "difficulty": 3,
        }
    ],
    "aeropuerto": [
        {
            "id": "curramgram_go",
            "title": "CURRAMGRAM GO! · LLEGA A LA PUERTA 7",
            "cls": CurramGramGoMicrogame,
            "difficulty": 4,
        }
    ],
    "aleta": [
        {
            "id": "fritanga_84",
            "title": "La fritanga de la Aleta",
            "cls": Fritanga84Microgame,
            "difficulty": 4,
        }
    ]
}

# Metadatos de previsualización (miniatura real, dificultad y etiqueta corta) para los 5 POIs jugables
STORY_LEVEL_PREVIEW_META: Dict[str, Dict[str, Any]] = {
    "uninorte": {
        "difficulty": 2,
        "max_difficulty": 5,
        "preview_asset": "fondo_minijuego_crossy.png",
        "crop_anchor": "top",
        "callout_title": "CAMPUS UNINORTE",
    },
    "ventana": {
        "difficulty": 4,
        "max_difficulty": 5,
        "preview_asset": "Punch/fondo_punch.png",
        "crop_anchor": "center",
        "callout_title": "VENTANA AL MUNDO",
    },
    "buenavista": {
        "difficulty": 3,
        "max_difficulty": 5,
        "preview_asset": "fondo_piano_tiles_microjuego.png",
        "crop_anchor": "center",
        "callout_title": "C.C. BUENAVISTA",
    },
    "metropolitano": {
        "difficulty": 3,
        "max_difficulty": 5,
        "preview_asset": "fondo_chat_estadio_microjuego.png",
        "crop_anchor": "center",
        "callout_title": "ESTADIO METROPOLITANO",
    },
    "aeropuerto": {
        "difficulty": 4,
        "max_difficulty": 5,
        "preview_asset": "curramgram/fondo_pared_terminal.png",
        "crop_anchor": "center",
        "callout_title": "AEROPUERTO CORTISSOZ",
    },
    "aleta": {
        "difficulty": 4,
        "max_difficulty": 5,
        "preview_asset": "Fritanga/fondoFritanga.png",
        "crop_anchor": "center",
        "callout_title": "ALETA DEL TIBURÓN",
    },
    "malecon": {
        "difficulty": 4,
        "max_difficulty": 5,
        "preview_asset": "coaster_game/fondos/nivel1.jpg",
        "crop_anchor": "center",
        "callout_title": "GRAN MALECÓN DEL RÍO",
    },
}

# Guion completo de Diálogos Cozy con la Paloma Guía de Curramba (Revisión Tarea 005)
PALOMA_STORY_DIALOGS: Dict[str, Dict[str, Any]] = {
    "welcome": {
        "speaker": "PALOMA DE CURRAMBA",
        "pages": [
            [
                "¡Cucu-rrucú! ¡Ajá mi llave, qué alegría verte llegar a Barranquilla con esta brisa sabrosa!",
                "Por ahí andan todos pegados a la pantallita y con el acelere a mil por hora, ¿verdad?",
                "Ven conmigo: vamos a recorrer juntos nuestros 5 rincones favoritos sin estrés ni pantallas."
            ],
            [
                "Primero pasaremos por Uninorte, luego la Ventana al Mundo, el C.C. Buenavista y el Metropolitano,",
                "y cerramos con broche de oro en la Aleta del Tiburón.",
                "Acércate a cada parada, respira hondo y charlamos antes de jugar. ¡Ponte las pilas!"
            ]
        ],
        "voice_clip_prefix": "paloma_welcome"
    },
    "uninorte": {
        "level_badge": "NIVEL 1 DE 5 • CAMPUS UNINORTE",
        "speaker": "PALOMA DE CURRAMBA",
        "pre_pages": [
            [
                "¡Mira qué sombra tan fresca nos regalan los robles aquí en Uninorte!",
                "Pero entre el afán de llegar a clase y el zumbido del celular, nadie mira al frente.",
                "Primero crucemos el pasillo sin mirar la pantalla para no tropezar con la gente."
            ],
            [
                "Y apenas entremos a la biblioteca, despejemos las alertas para poder estudiar concentrados.",
                "Regálale un ratito de silencio a la cabeza, mi vale. ¿Listo para vivir el campus de verdad?"
            ]
        ],
        "inter_stage_pages": [
            [
                "¡Erda, llegaste al salón con la frente en alto y sin tropezar, así se hace!",
                "Ahora entremos a la biblioteca: espanta las notificaciones de TikTok y WhatsApp",
                "para que nada interrumpa la paz de estudiar concentrado. ¡Dale con todo!"
            ]
        ],
        "post_win_pages": [
            [
                "¡Qué alivio se siente cuando uno suelta el teléfono y habita el presente!",
                "En Uninorte aprendimos que caminar mirando el cielo y regalarle calma a la mente",
                "vale más que mil mensajes urgentes. ¡Vamos volando hacia la Ventana al Mundo!"
            ]
        ],
        "post_lose_pages": [
            [
                "¡Ay mi hermano, el ruido digital nos ganó por un pelito, pero no pasa nada!",
                "Respira hondo como la brisa del río y volvamos a intentarlo con calma."
            ]
        ],
        "voice_clip_prefix": "paloma_uninorte"
    },
    "ventana": {
        "level_badge": "NIVEL 2 DE 5 • VENTANA AL MUNDO",
        "speaker": "PALOMA DE CURRAMBA",
        "pre_pages": [
            [
                "¡Llegamos a la Ventana al Mundo! Mira ese arbolito cambiando de colores, qué belleza.",
                "Toda la familia vino a tomarse la foto, y el celular ya está sugiriendo qué más ponerle al post.",
                "Ojo, mi llave: hay cosas que es mejor no contarle a medio mundo."
            ],
            [
                "Cuando una idea caiga en tu zona, sácala con un puño: ESPACIO o cerrando la mano.",
                "Lo que dejes pasar se va pa' tu publicación. ¡Deja pasar solo lo bonito!"
            ]
        ],
        "post_win_pages": [
            [
                "¡Qué post tan lindo! Salió el arbolito, la familia y nada más.",
                "Los recuerdos se comparten, pero dónde vives y lo que tienes se quedan contigo.",
                "¡Sigamos volando hacia el C.C. Buenavista!"
            ]
        ],
        "post_lose_pages": [
            [
                "¡Erda, se nos colaron datos de más en esa publicación!",
                "Respira, bórrala y vuelve a armarla con calma: el recuerdo sí, tu vida entera no."
            ]
        ],
        "voice_clip_prefix": "paloma_ventana"
    },
    "buenavista": {
        "level_badge": "NIVEL 3 DE 5 • C.C. BUENAVISTA",
        "speaker": "PALOMA DE CURRAMBA",
        "pre_pages": [
            [
                "¡C.C. Buenavista! Huele a raspado y salsa costeña.",
                "En la plaza todos graban el trend pa' cazar likes,",
                "¡pero aquí bailamos pa' gozar, no por un algoritmo!"
            ],
            [
                "Suena 'En Barranquilla Me Quedo': usa D, F, J y K.",
                "Disfruta el ritmo sabroso sin dejar que la presión te gane."
            ]
        ],
        "post_win_pages": [
            [
                "¡Cipote sabor, mi llave! Bailaste con el alma alegre.",
                "Un raspado frío y una buena salsa valen más que mil likes.",
                "¡Ahora despleguemos alas hacia el Estadio Metropolitano!"
            ]
        ],
        "post_lose_pages": [
            [
                "¡Ombe, casi coronas! Ese golpe salsero estuvo bravo.",
                "Sacude las plumas sin pena y volvamos a tirar ese paso."
            ]
        ],
        "voice_clip_prefix": "paloma_buenavista"
    },
    "metropolitano": {
        "level_badge": "NIVEL 4 DE 5 • ESTADIO METROPOLITANO",
        "speaker": "PALOMA DE CURRAMBA",
        "pre_pages": [
            [
                "¡Siente cómo ruge el 'Coloso de la Ciudadela'! La casa de la fiesta currambera.",
                "El fútbol y las redes se parecen: son una belleza cuando celebramos con respeto,",
                "pero se amargan cuando la gente confunde la pasión con tirar veneno y toxicidad."
            ],
            [
                "Controla la pantalla gigante del estadio con las FLECHAS y modera los comentarios agresivos.",
                "¡Que en esta tribuna del Junior solo reine la alegría, el respeto y la buena vibra!"
            ]
        ],
        "post_win_pages": [
            [
                "¡Golazo por la convivencia, mi vale! La tribuna y el chat brillan cuando hay respeto.",
                "Detrás de cada usuario y cada camiseta hay un ser humano sintiendo como tú.",
                "¡Próxima escala: volemos a la Aleta del Tiburón a comernos una arepa de huevo!"
            ]
        ],
        "post_lose_pages": [
            [
                "¡Se nos alborotó la hinchada por un segundo, pero el partido no se acaba aquí!",
                "Tomemos agua fría, mantengamos la calma y volvamos a cuidar el Metropolitano."
            ]
        ],
        "voice_clip_prefix": "paloma_metropolitano"
    },
    "aeropuerto": {
        "level_badge": "AEROPUERTO CORTISSOZ",
        "speaker": "PALOMA DE CURRAMBA",
        "pre_pages": [
            [
                "¡Ajá, llegamos al Aeropuerto Ernesto Cortissoz!",
                "Cami es creadora de contenido y tiene que llegar a la puerta 7",
                "antes de su vuelo, junta sellos por el camino y no pierdas el tiempo.",
            ],
            [
                "En la terminal verá cosas que parecen virales: un chisme, un accidente,",
                "una foto privada... ¡Ojo! No todo lo que se ve merece un post.",
                "Confirma, protege los datos de los demás y, si algo está mal, avísale a la Policía.",
            ]
        ],
        "post_win_pages": [
            [
                "¡Abordaste a tiempo y sin exponer a nadie! Así se usan las redes.",
                "Verificar antes de publicar y respetar la privacidad ajena",
                "también es ser buen ciudadano en Curramba."
            ]
        ],
        "post_lose_pages": [
            [
                "¡Erda, se nos fue el vuelo entre chismes y fotos!",
                "Recuerda: primero confirma y respeta, después publica.",
                "Respira y volvamos a intentarlo por la terminal."
            ]
        ],
        "voice_clip_prefix": "paloma_aeropuerto"
    },
    "aleta": {
        "level_badge": "NIVEL 5 DE 5 • ALETA DEL TIBURÓN",
        "speaker": "PALOMA DE CURRAMBA",
        "pre_pages": [
            [
                "¡Llegamos a la Aleta del Tiburón! Huele a arepa de huevo recién hecha.",
                "Hoy atiendes el puesto de fritos y lo transmites en vivo para toda Curramba.",
                "Pero ojo: en el chat se mete un trol que dice barbaridades para que te piques."
            ],
            [
                "Voltea las arepas con clic o espacio cuando estén doradas, y luego sácalas.",
                "Mantén P o el clic en el botellón para llenar el vaso de patillazo,",
                "y arrástralo hasta el cliente. ¡Y no le pares bolas al trol!"
            ]
        ],
        "post_win_pages": [
            [
                "¡Erda, qué arepas tan bien hechas! Y el trol se fue aburrido sin tu rabia.",
                "Hay cuentas que viven de hacerte enojar: si no les respondes, no ganan nada.",
                "¡Completaste todo el recorrido! Barranquilla está orgullosa de ti, mi llave."
            ]
        ],
        "post_lose_pages": [
            [
                "¡Ay, mi llave, ese trol te sacó la piedra y se nos quemó la arepa!",
                "Respira la brisa, cuenta hasta diez y volvamos a prender el caldero con calma."
            ]
        ],
        "voice_clip_prefix": "paloma_aleta"
    },
    "malecon": {
        "level_badge": "GRAN MALECÓN DEL RÍO - MODO COASTER",
        "speaker": "PALOMA DE CURRAMBA",
        "pre_pages": [
            [
                "¡Llegamos al Gran Malecón, frente a la brisa del Magdalena!",
                "Aquí cambiamos el scroll automático por lápiz, papel y creatividad con tus propias manos."
            ],
            [
                "Traza una montaña rusa firme frente al río y recoge las estrellas doradas,",
                "demostrando que crear con tus manos vale mucho más que mirar una pantalla."
            ]
        ],
        "post_win_pages": [
            [
                "¡Qué trazo tan bacano, llave! La brisa del río y esa vía hecha a mano",
                "valen mil veces más que cualquier feed infinito. ¡Sigue creando en el mundo real!"
            ]
        ],
        "post_lose_pages": [
            [
                "¡Uy, esa pendiente nos sacudió duro! Pero en el papel siempre se puede borrar",
                "y volver a diseñar con calma lejos de las pantallas. ¡Inténtalo otra vez!"
            ]
        ],
        "voice_clip_prefix": "paloma_malecon"
    }
}

# Trofeos escondidos en el mapa y minijuegos (Tarea 002)
trofeosMapa: list = [
    {
        "id": "vueltaVentana",
        "nombre": "La vuelta al mundo",
        "monumento": "ventana",
        "descripcion": "Le diste la vuelta a la glorieta de la Ventana al Mundo",
    },
    {
        "id": "vueltaAleta",
        "nombre": "Tiburón de glorieta",
        "monumento": "aleta",
        "descripcion": "Le diste la vuelta a la glorieta de la Aleta del Tiburón",
    },
    {
        "id": "charlaPaloma",
        "nombre": "¡Aja, Curramba!",
        "monumento": None,
        "descripcion": "Charlaste con la sabia Paloma mensajera de la ciudad",
    },
    {
        "id": "despejarUninorte",
        "nombre": "Cerebro Desconectado",
        "monumento": None,
        "descripcion": "Superaste el reto de concentración en la biblioteca de Uninorte",
    },
]

# Distancia máxima entre un nodo y el monumento para contar como parte de su glorieta
radioGlorieta: int = 200
