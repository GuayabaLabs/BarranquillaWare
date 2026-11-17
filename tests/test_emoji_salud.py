"""Casual/weak/perfect/inactive player checks for mental-health pacing."""
import os, random, sys, unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from microgames.emojis.juego import EmojiCatch, SALUD_INICIAL, SALUD_ESCAPE_MEGA, ANIMO_DURACION

class SaludEmojiTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  pygame.init();pygame.display.set_mode((1,1))
 @classmethod
 def tearDownClass(cls):pass  # pygame se comparte con el resto de la suite
 def setUp(self):self.j=EmojiCatch()
 def _partida_bot(self,seed,precision):
  rng=random.Random(seed);j=EmojiCatch();j.tiempo=120;j.elapsed=0
  # Targets arrive every 0.65 s; the bot reacts in 0.35 s and has time to cross its lane.
  for n in range(180):
   if j.final:break
   if rng.random()<precision:
    j._puntos_captura(0,{"kind":"emoji_enojado_naranja","x":400,"y":900,"mega":False})
   else:
    j._cambiar_salud(-5);j.combo=0
   j.elapsed+=.65;j.tiempo=max(0,120-j.elapsed)
  if j.salud>0:
   j.final="BALANCE LOGRADO";j.victoria=True;j.estrellas=1+int(j.salud>=60)+int(j.salud>=85)
  return j
 def test_empieza_en_50_y_premia_racha(self):
  j=self.j;self.assertEqual(j.salud,SALUD_INICIAL)
  def hit():j._puntos_captura(0,{"kind":"emoji_enojado_naranja","x":400,"y":900,"mega":False})
  hit();self.assertEqual(j.salud,53)
  j.combo=4;hit();self.assertEqual(j.salud,57) # combo 5: +3 base +1
  j.combo=9;hit();self.assertEqual(j.salud,63) # combo 10: +3 +1 +2
 def test_escape_de_cualquier_lado_y_derrota_inmediata(self):
  j=self.j
  for kind,expected in (("emoji_corazon",45),("emoji_triste",40)):
   j.items=[{"kind":kind,"x":400,"y":1040,"speed":1,"mega":False,"angle":0,"base_x":400,"t":0,"phase":0}]
   j.update(.01,set());self.assertEqual(j.salud,expected)
  j.items=[{"kind":"emoji_enojado_rojo","x":400,"y":1040,"speed":1,"mega":True,"angle":0,"base_x":400,"t":0,"phase":0}]
  j.update(.01,set());self.assertEqual(j.salud,30)
  j.salud=5;j._cambiar_salud(-5)
  self.assertEqual(j.final,"SALUD MENTAL AGOTADA");self.assertFalse(j.victoria)
 def test_animo_tope_activa_multiplicador_con_enfriamiento(self):
  j=self.j;j.salud=97;j._cambiar_salud(3)
  self.assertEqual(j.salud,100);self.assertEqual(j.animo_activo,ANIMO_DURACION)
  j._cambiar_salud(-5);j._cambiar_salud(5)
  self.assertEqual(j.animo_activo,ANIMO_DURACION) # cooldown prevents repeated trigger
 def test_calibracion_bots_repeticiones_10(self):
  casual=[self._partida_bot(i,.75) for i in range(10)]
  weak=[self._partida_bot(100+i,.45) for i in range(10)]
  self.assertGreaterEqual(sum(j.victoria and j.estrellas>=2 for j in casual),9)
  self.assertGreaterEqual(sum(not j.victoria for j in weak),7)
  perfecto=self._partida_bot(999,1.0);self.assertEqual(perfecto.estrellas,3)
 def test_inactivo_pierde_por_escapes(self):
  j=self.j;pygame.event.pump();keys=pygame.key.get_pressed();n=0
  random.seed(42)
  while j.tiempo>0 and not j.final and n<3000:
   j.update(.05,keys);n+=1
  self.assertEqual(j.final,"SALUD MENTAL AGOTADA")

if __name__=='__main__':unittest.main()
