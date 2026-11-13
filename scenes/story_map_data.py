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

# Progresión de los 4 Niveles Principales del Modo Historia
STORY_CAMPAIGN_ORDER = ["uninorte", "buenavista", "metropolitano", "aeropuerto"]
STORY_SECRET_POIS = ["malecon"]
STORY_PLAYABLE_POIS = STORY_CAMPAIGN_ORDER + STORY_SECRET_POIS

# Secuencia de desafíos encadenados por cada Nivel de la Historia
STORY_LEVEL_STAGES: Dict[str, list] = {
    "uninorte": [
        {
            "id": "uninorte_sprint",
            "title": "RONDA 1: CARRERA AL AULA A-203",
            "cls": UninorteSprintMicrogame
        },
        {
            "id": "uninorte_concentrate",
            "title": "RONDA 2: ¡CONCÉNTRATE EN LA BIBLIOTECA!",
            "cls": UninorteConcentrateMicrogame
        }
    ],
    "buenavista": [
        {
            "id": "buenavista_trend",
            "title": "EL TREND EN BUENAVISTA",
            "cls": BuenavistaTrendMicrogame
        }
    ],
    "metropolitano": [
        {
            "id": "metropolitano_moderacion",
            "title": "¡MODERA LA BARRA BRAVA!",
            "cls": MetropolitanoModeracionMicrogame
        }
    ],
    "aeropuerto": [
        {
            "id": "punch_alert",
            "title": "¡DESPACHA EL SPAM ANTES DE DESPEGAR!",
            "cls": PunchAlertMicrogame
        }
    ]
}

# Guion completo de Diálogos Cozy con la Paloma Guía de Curramba (Revisión Tarea 005)
PALOMA_STORY_DIALOGS: Dict[str, Dict[str, Any]] = {
    "welcome": {
        "speaker": "PALOMA DE CURRAMBA",
        "pages": [
            [
                "¡Cucu-rrucú! ¡Ajá mi llave, qué alegría verte llegar a Barranquilla con esta brisa sabrosa!",
                "Por ahí andan todos pegados a la pantallita y con el acelere a mil por hora, ¿verdad?",
                "Ven conmigo: vamos a recorrer juntos nuestros 4 rincones favoritos sin estrés ni pantallas."
            ],
            [
                "Primero pasaremos por Uninorte, luego el C.C. Buenavista, el Metropolitano y el Cortissoz.",
                "Acércate a cada parada, respira hondo y charlamos antes de jugar. ¡Ponte las pilas!"
            ]
        ],
        "voice_clip_prefix": "paloma_welcome"
    },
    "uninorte": {
        "level_badge": "NIVEL 1 DE 4 • CAMPUS UNINORTE",
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
                "vale más que mil mensajes urgentes. ¡Vamos volando hacia el Buenavista!"
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
    "buenavista": {
        "level_badge": "NIVEL 2 DE 4 • C.C. BUENAVISTA",
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
        "level_badge": "NIVEL 3 DE 4 • ESTADIO METROPOLITANO",
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
                "¡Última escala: volemos con rumbo al Aeropuerto Ernesto Cortissoz!"
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
        "level_badge": "NIVEL 4 DE 4 • AEROPUERTO CORTISSOZ",
        "speaker": "PALOMA DE CURRAMBA",
        "pre_pages": [
            [
                "¡Última escala en la pista del Aeropuerto Ernesto Cortissoz!",
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
                "¡Pista limpia, cielo despejado y corazón en paz! Completaste todo el recorrido.",
                "Barranquilla brilla mucho más bonita cuando despegas los ojos de la pantalla",
                "para sentir su calor, su música y su gente real. ¡Eres orgullo de Curramba!"
            ]
        ],
        "post_lose_pages": [
            [
                "¡Erda, se nos colaron demasiadas ventanas emergentes antes de abordar!",
                "Cierra ese ruido, respira fresco y despejemos la pista juntos otra vez."
            ]
        ],
        "voice_clip_prefix": "paloma_aeropuerto"
    }
}
