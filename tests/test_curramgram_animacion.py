"""Animation JSON sequences and stable Cami foot anchors."""
import json,unittest
from pathlib import Path
from microgames.curramgram.animacion import Animacion
from microgames.curramgram.juego import CurramGramGo

ROOT=Path(__file__).resolve().parents[1]  # raíz del proyecto
class AnimacionCamiTest(unittest.TestCase):
 def setUp(self):self.anim=Animacion(ROOT/'assets/curramgram/animaciones.json')
 def test_walking_cycle_order(self):
  self.anim.seleccionar('walk');names=[self.anim.cuadro(0)]+[self.anim.cuadro(.09) for _ in range(5)]
  self.assertEqual(names,['cami_walk_1','cami_walk_2','cami_walk_3','cami_walk_4','cami_walk_5','cami_walk_1'])
 def test_squat_stand_photo_and_stumble_sequences(self):
  self.anim.seleccionar('agachar')
  self.assertEqual([self.anim.cuadro(0),self.anim.cuadro(.06),self.anim.cuadro(.06)],['cami_agachar_1','cami_agachar_2','cami_cuclillas'])
  self.anim.seleccionar('levantarse')
  self.assertEqual([self.anim.cuadro(0),self.anim.cuadro(.06),self.anim.cuadro(.06)],['cami_agachar_2','cami_agachar_1','cami_regreso'])
  self.anim.seleccionar('foto_pie');self.assertEqual(self.anim.cuadro(0),'cami_walk_4')
  self.anim.seleccionar('foto_agachada')
  self.assertEqual([self.anim.cuadro(0),self.anim.cuadro(.15)],['cami_arrodillada','cami_foto_agachada'])
  self.anim.seleccionar('empujon');self.assertEqual(self.anim.cuadro(0),'cami_agachar_1')
 def test_anchor_is_at_lowest_foot_and_characters_share_height(self):
  raw=json.loads((ROOT/'assets/curramgram/anclajes_cami.json').read_text(encoding='utf-8'))
  for name,data in raw.items():
   from PIL import Image
   with Image.open(ROOT/'assets/curramgram'/f'{name}.png') as img:
    self.assertEqual(data['anchor'][1],img.height-1,name)
  juego=CurramGramGo()
  idle=juego.animacion.defs['idle']['frames'][0]
  self.assertEqual(juego.sprites[idle].get_height(),175)
  if not juego.acuarela:
   self.assertTrue(all(juego.sprites[n].get_height()==175 for n in ('policia','hombre_gorra','turista_pasaporte','joven_llorando','senora_cava','bailarina_comparsa','tamborero')))
  else:
   # Arte acuarela: todos los cuadros de la animación existen y apoyan los pies en el piso (ancla abajo al centro).
   for frames in (d['frames'] for d in juego.animacion.defs.values()):
    for f in frames:
     self.assertIn(f,juego.sprites,f)

if __name__=='__main__':unittest.main()
