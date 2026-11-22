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

# Progresión de los 5 Niveles Principales del Modo Historia
STORY_CAMPAIGN_ORDER = ["uninorte", "ventana", "buenavista", "metropolitano", "aleta"]
STORY_SECRET_POIS = ["malecon"]
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
    "aeropuerto": [],
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
        "preview_asset": "fondo_box_microjuego.png",
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
                "¡Llegamos al C.C. Buenavista! Huele a tarde de helado, amigos y música bacana.",
                "En la plaza todos están grabando el trend viral de bachata para ganar likes,",
                "pero ojo: bailamos por gozárnosla, ¡no para que un algoritmo nos diga cuánto valemos!"
            ],
            [
                "Suena 'Imitadora': sigue el ritmo de las notas con las teclas D, F, J y K.",
                "Diviértete al compás sin dejar que la presión social te robe la sonrisa."
            ]
        ],
        "post_win_pages": [
            [
                "¡Qué sabrosura! Bailaste con el corazón ligero y gozaste de principio a fin.",
                "Las redes son para compartir sonrisas, no para medir tu valor en corazoncitos.",
                "¡Ahora despleguemos las alas hacia el calor del Estadio Metropolitano!"
            ]
        ],
        "post_lose_pages": [
            [
                "¡Casi, casi! Entre tanta coreografía y flashes es normal perder el compás.",
                "Sacúdete las plumas sin pena y volvamos a tirarnos ese paso en Buenavista."
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
                "¡Llegamos a la pista del Aeropuerto Ernesto Cortissoz!",
                "Antes de despegar, el celular quiere llenarte la maleta de cadenas falsas, spam",
                "y un montón de urgencias ficticias que solo te cargan de angustia.",
            ],
            [
                "Dale un buen golpe al spam y a las fake news para viajar con la mente despejada.",
                "¡Limpia la pantalla y preparemos el vuelo triunfal por toda Curramba!"
            ]
        ],
        "post_win_pages": [
            [
                "¡Pista limpia, cielo despejado y corazón en paz! Despachaste todo el spam.",
                "Antes de despedirnos nos falta una parada bien sabrosa:",
                "¡vamos a la Aleta del Tiburón a comernos una arepa de huevo!"
            ]
        ],
        "post_lose_pages": [
            [
                "¡Erda, se nos colaron demasiadas ventanas emergentes antes de abordar!",
                "Cierra ese ruido, respira fresco y despejemos la pista juntos otra vez."
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
