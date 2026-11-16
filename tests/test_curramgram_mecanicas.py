"""Unit tests for the six citizen interactions in CurramGram Go."""
import os,sys,unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from microgames.curramgram.juego import CurramGramGo,PUNTOS

class MecanicasCurramGramTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):pygame.init();pygame.display.set_mode((1,1))
 @classmethod
 def tearDownClass(cls):pass  # pygame se comparte con el resto de la suite
 def setUp(self):self.j=CurramGramGo();self.j.inicio=False
 def foto(self,i):self.j.x=PUNTOS[i];self.j._capturar_foto((int(PUNTOS[i]-self.j._camara()),600))
 def test_confirmaciones_automaticas_y_aviso(self):
  j=self.j;j.x=PUNTOS[0];j._actualizar_interacciones(.8);self.assertIn('maizena',j.casos[0])
  j.x=PUNTOS[1];j._actualizar_interacciones(.8);j.keydown(pygame.K_e);self.assertIn('Avisó',j.casos[1])
  j.x=PUNTOS[3];j._actualizar_interacciones(.8);self.assertIn('hielo',j.casos[3])
 def test_respetar_privacidad_y_penalizar_foto(self):
  j=self.j;j.revelados[2]=True;j.x=PUNTOS[2]+60;j._actualizar_interacciones(.01);self.assertIn('Pasó de largo',j.casos[2])
  j.reiniciar();j.inicio=False;j.x=PUNTOS[2];self.foto(2)
  self.assertIn('ERROR:',j.casos[2]);self.assertEqual(j.puntos,0)
 def test_comparsa_publicacion_segura(self):
  j=self.j;j.revelados[4]=True;self.foto(4);j.publicar()
  self.assertIn('Foto pública',j.casos[4]);self.assertEqual(j.likes,120);self.assertGreater(j.puntos,0)
 def test_mision_discreta_seguida_de_entrega(self):
  j=self.j;j.x=PUNTOS[5]-105;j.ocultando=True;j.en_escondite=True;j.amenaza=False;self.foto(5)
  self.assertTrue(j.evidencia);j.x=180;j.interactuar()
  self.assertFalse(j.evidencia);self.assertIn('entregada',j.casos[5])
  j.reiniciar();j.inicio=False;j.x=PUNTOS[5];self.foto(5)
  self.assertIsNone(j.final);self.assertIn('ERROR:',j.casos[5])

if __name__=='__main__':unittest.main()
