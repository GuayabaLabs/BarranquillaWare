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

# Guion completo de Diálogos Cozy con la Paloma Guía de Curramba
PALOMA_STORY_DIALOGS: Dict[str, Dict[str, Any]] = {
    "welcome": {
        "speaker": "PALOMA DE CURRAMBA",
        "pages": [
            [
                "¡Cucu-rrucú! Qué alegría verte volar por Barranquilla con esta brisa suave.",
                "A veces la ciudad y las pantallas giran demasiado rápido, ¿verdad?",
                "Ven conmigo: recorramos juntos nuestros 4 rincones favoritos sin prisa."
            ],
            [
                "Nuestra primera parada nos espera bajo las acacias del Campus Uninorte.",
                "Luego pasearemos por C.C. Buenavista, el Estadio Metropolitano y el Aeropuerto.",
                "Acércate a cada parada y charlamos antes de empezar. ¡Disfruta el paseo!"
            ]
        ]
    },
    "uninorte": {
        "level_badge": "NIVEL 1 DE 4 • CAMPUS UNINORTE",
        "speaker": "PALOMA DE CURRAMBA",
        "pre_pages": [
            [
                "¡Mira qué fresca está la sombra de los robles aquí en Uninorte!",
                "Pero entre el afán de llegar al salón y el zumbido del celular, cuesta respirar.",
                "Primero crucemos el pasillo sin mirar la pantalla para llegar a tiempo a clase."
            ],
            [
                "Y apenas entremos a la biblioteca, ayudemos a despejar las nubes de ruido digital.",
                "Regálale un ratito de calma a tu mente. ¿Listo para vivir el campus de verdad?"
            ]
        ],
        "inter_stage_pages": [
            [
                "¡Llegaste al salón con la frente en alto y mirando el camino, así se hace!",
                "Ahora entremos en silencio a la biblioteca: espanta las notificaciones flotantes",
                "para que nada interrumpa la paz de estudiar concentrado. ¡Tú puedes!"
            ]
        ],
        "post_win_pages": [
            [
                "¡Qué paz se siente cuando uno suelta el teléfono y habita el presente!",
                "En Uninorte aprendimos que caminar mirando el cielo y regalarle silencio",
                "a nuestra mente vale más que mil mensajes urgentes. ¡Vamos hacia Buenavista!"
            ]
        ],
        "post_lose_pages": [
            [
                "Ay, el ruido digital nos ganó por un poquito, ¡pero no pasa nada!",
                "Respira hondo como la brisa del norte y volvamos a intentarlo con calma."
            ]
        ]
    },
    "buenavista": {
        "level_badge": "NIVEL 2 DE 4 • C.C. BUENAVISTA",
        "speaker": "PALOMA DE CURRAMBA",
        "pre_pages": [
            [
                "¡Llegamos al C.C. Buenavista! Huele a tarde de amigos y música alegre.",
                "En el pasillo central todos están grabando el trend viral de bachata,",
                "pero recuerda: bailamos por pura alegría, ¡sin obsesionarnos con los likes!"
            ],
            [
                "Suena 'Imitadora' en la plaza central: sigue el ritmo con D, F, J y K",
                "y diviértete bailando el trend sin dejar que la presión social te quite el aire."
            ]
        ],
        "post_win_pages": [
            [
                "¡Bailaste con el corazón ligero y disfrutaste el ritmo de principio a fin!",
                "Los trends y las redes son para compartir sonrisas, no para medir cuánto vales",
                "por un corazón en pantalla. ¡Volemos ahora hacia el Estadio Metropolitano!"
            ]
        ],
        "post_lose_pages": [
            [
                "¡Casi, casi! Entre tantas luces y tendencias es fácil perder el compás.",
                "Sacúdete las plumas sin presión y volvamos a disfrutar Buenavista."
            ]
        ]
    },
    "metropolitano": {
        "level_badge": "NIVEL 3 DE 4 • ESTADIO METROPOLITANO",
        "speaker": "PALOMA DE CURRAMBA",
        "pre_pages": [
            [
                "¡Siente cómo late el Roberto Meléndez! La casa de nuestra pasión currambera.",
                "El fútbol y las redes se parecen: son hermosos cuando celebramos con respeto,",
                "pero se nublan cuando alguien confunde pasión con agresión."
            ],
            [
                "Usa las flechas y ESPACIO en la pantalla gigante para moderar a los tóxicos",
                "y cuidar a los hinchas alegres. ¡Que en esta tribuna solo reine la empatía!"
            ]
        ],
        "post_win_pages": [
            [
                "¡Golazo por la convivencia! La tribuna brilla cuando nos tratamos con cariño.",
                "Detrás de cada pantalla y de cada camiseta hay una persona sintiendo como tú.",
                "¡Ahora sí, despleguemos las alas hacia el Aeropuerto Ernesto Cortissoz!"
            ]
        ],
        "post_lose_pages": [
            [
                "Se nos alborotó un poquito la tribuna, ¡pero el partido aún no termina!",
                "Tomemos aire fresco y volvamos a cuidar la alegría del Metropolitano."
            ]
        ]
    },
    "aeropuerto": {
        "level_badge": "NIVEL 4 DE 4 • AEROPUERTO CORTISSOZ",
        "speaker": "PALOMA DE CURRAMBA",
        "pre_pages": [
            [
                "¡Última parada en la pista del Aeropuerto Ernesto Cortissoz!",
                "Antes de despegar hacia nuevas aventuras, el teléfono intenta llenarte",
                "la maleta de spam, falsas alarmas y urgencias que no necesitas llevar."
            ],
            [
                "Despacha esas ventanas molestas con buen pulso para viajar liviano de mente.",
                "¡Despejemos el cielo para el gran vuelo final por Curramba!"
            ]
        ],
        "post_win_pages": [
            [
                "¡Cielo despejado y corazón en calma! Has completado todo nuestro recorrido.",
                "Barranquilla brilla distinto cuando levantas la mirada de la pantalla",
                "para sentir su brisa, su música y su gente. ¡Eres orgullo de Curramba!"
            ]
        ],
        "post_lose_pages": [
            [
                "¡Uy, demasiadas ventanas emergentes antes del abordaje!",
                "Respira tranquilo, cierra ese ruido y volvamos a despejar la pista."
            ]
        ]
    }
}
