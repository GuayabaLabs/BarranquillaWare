---
name: review-barranquillaware
description: Audita rápidamente el proyecto BarranquillaWare antes de modificarlo. Úsala para revisar qué existe, detectar rutas o assets rotos, comprobar la arquitectura Pygame, identificar pruebas problemáticas y resumir el estado real del juego.
---

# Revisar BarranquillaWare

Ejecuta `tools/review_project.ps1` desde la raíz y trata sus resultados como un inventario, no como autorización para modificar código.

Revisa siempre `git status --short`, distingue el código principal de `Project-TBD/` y abre el módulo y la prueba relacionada para cualquier problema concreto. Usa los drivers SDL dummy para pruebas Pygame sin ventana.

No corras la suite completa si detectas pruebas que escriben en rutas absolutas externas; ejecuta primero pruebas específicas. No actives cámara o MediaPipe para probar escenas que no los necesitan. No confundas nombres de assets con assets realmente cargados: comprueba las referencias desde el código.

Entrega un resumen con punto de entrada, subsistemas, microjuegos, assets o imports problemáticos, pruebas ejecutadas y siguiente acción recomendada. No edites durante una revisión salvo que el usuario lo pida.
