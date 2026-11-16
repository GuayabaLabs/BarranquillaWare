"""Headless checks of CurramGram's route, seals, cases, door, and bot scripts."""
import os,sys,unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from microgames.curramgram.juego import CurramGramGo,PUNTOS,PUERTA_X,ALTURA_PERSONAJE_PX,PISO,ESTRELLAS_CURRAM

class VectorTeclas:
 def __init__(self,held):self.held=held
 def __getitem__(self,key):return key in self.held

class CurramGramBucleTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):pygame.init();pygame.display.set_mode((1,1))
 @classmethod
 def tearDownClass(cls):pass  # pygame se comparte con el resto de la suite
 def setUp(self):
  self.j=CurramGramGo();self.j.inicio=False
 def test_personajes_normalizados_y_piso(self):
  self.assertEqual(self.j.sprites['cami_idle'].get_height(),ALTURA_PERSONAJE_PX)
  for name in ('policia','hombre_gorra','turista_pasaporte','joven_llorando','senora_cava','bailarina_comparsa','tamborero'):
   self.assertEqual(self.j.sprites[name].get_height(),ALTURA_PERSONAJE_PX,name)
  self.assertAlmostEqual(PISO/1080,.71,delta=.001)
  self.assertAlmostEqual(self.j.sprites['cami_idle'].get_height()/1080,.162,delta=.001)
 def test_inicio_bloquea_reloj_y_espacio_comienza(self):
  j=CurramGramGo();j.update(1,VectorTeclas(set()),(0,0));self.assertEqual(j.tiempo,120)
  j.keydown(pygame.K_SPACE);self.assertFalse(j.inicio)
 def test_sellos_casos_y_bonos(self):
  j=self.j
  for s in j.sellos:
   j.x=s['x'];j.salto=.36 if s['y']<PISO-167 else 0;j._recoger_sellos()
  self.assertEqual(sum(s['recogido'] for s in j.sellos),25);self.assertEqual(j.puntos,125)
  j.x=PUNTOS[0];j._actualizar_interacciones(.8);self.assertEqual(j.casos[0],'Confirmó que era maizena')
  j.x=PUNTOS[1];j._actualizar_interacciones(.8);j.keydown(pygame.K_e);self.assertIn('Avisó',j.casos[1])
  j.revelados[2]=True;j.x=PUNTOS[2]+60;j._actualizar_interacciones(.01);self.assertIn('Pasó de largo',j.casos[2])
  j.x=PUNTOS[3];j._actualizar_interacciones(.8);self.assertEqual(j.casos[3],'Era hielo derramado')
  j.x=PUNTOS[4];j.revelados[4]=True;j._capturar_foto((int(PUNTOS[4]-j._camara()),600));j.keydown(pygame.K_p)
  self.assertIn('Foto pública',j.casos[4]);self.assertEqual(j.likes,120)
  self.assertEqual(j.tiempo,140)
 def test_mision_tamborero_persecucion_y_entrega(self):
  j=self.j;j.x=PUNTOS[5]-105;j.ocultando=True;j.en_escondite=True;j.amenaza=False
  j._capturar_foto((int(PUNTOS[5]-j._camara()),600))
  self.assertTrue(j.evidencia);self.assertEqual(j.persecucion,20)
  j.x=180;antes=j.tiempo;j.interactuar()
  self.assertFalse(j.evidencia);self.assertIn('entregada',j.casos[5]);self.assertGreaterEqual(j.tiempo,antes+10)
  j.reiniciar();j.inicio=False;j.x=PUNTOS[5];j._capturar_foto((int(PUNTOS[5]-j._camara()),600))
  self.assertFalse(j.final);self.assertIn('ERROR:',j.casos[5])
 def test_obstaculo_penaliza_y_bloquea_repeticion(self):
  j=self.j;j.carrito={'x':j.x,'hit':False};j.carrito_clock=10
  j.update(.05,VectorTeclas(set()),(0,0));self.assertAlmostEqual(j.tiempo,116.95)
  j.carrito={'x':j.x,'hit':False};j.update(.05,VectorTeclas(set()),(0,0));self.assertAlmostEqual(j.tiempo,116.9)
 def test_puerta_requiere_e_y_estrellas(self):
  j=self.j;j.x=PUERTA_X-100;j.puntos=400
  self.assertIsNone(j.final);j.interactuar()
  self.assertEqual(j.final,'LLEGASTE A GATE 7');self.assertEqual(j.estrellas,3)
 def test_bot_guionado_buen_final_con_margen(self):
  j=self.j
  for sello in j.sellos:
   j.x=sello['x'];j.salto=.36 if sello['y']<PISO-167 else 0;j._recoger_sellos()
  j.x=PUNTOS[0];j._actualizar_interacciones(.8)
  j.x=PUNTOS[1];j._actualizar_interacciones(.8);j.keydown(pygame.K_e)
  j.revelados[2]=True;j.x=PUNTOS[2]+60;j._actualizar_interacciones(.01)
  j.x=PUNTOS[3];j._actualizar_interacciones(.8)
  j.x=PUNTOS[4];j.revelados[4]=True;j._capturar_foto((int(PUNTOS[4]-j._camara()),600));j.publicar()
  j.x=PUNTOS[5]-105;j.ocultando=True;j.en_escondite=True;j.amenaza=False;j._capturar_foto((int(PUNTOS[5]-j._camara()),600))
  j.x=180;j.interactuar();j.x=PUERTA_X-100
  # Distancia recorrida en el guion: ida, regreso a Policía y puerta, a 320 px/s.
  distancia=(PUERTA_X-350)+2*(PUNTOS[5]-180)
  j.tiempo=max(0,120-distancia/320+34);j.puntos=495;j.interactuar()
  self.assertTrue(j.victoria);self.assertEqual(j.estrellas,3);self.assertGreaterEqual(j.tiempo,25)
 def test_bot_solo_caminar_y_bot_inactivo(self):
  j=self.j
  for _ in range(400):j.update(.05,VectorTeclas({pygame.K_d}),(0,0))
  estrellas=sum(j.puntos>=n for n in ESTRELLAS_CURRAM)
  self.assertLessEqual(estrellas,1);self.assertLess(j.puntos,250)
  idle=CurramGramGo();idle.inicio=False
  for _ in range(2400):
   if idle.final:break
   idle.update(.05,VectorTeclas(set()),(0,0))
  self.assertEqual(idle.final,'VUELO PERDIDO')

if __name__=='__main__':unittest.main()
