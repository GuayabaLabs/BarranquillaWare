"""Reproducción de animaciones editables por JSON."""
import json
from pathlib import Path

class Animacion:
    def __init__(self, archivo):
        self.defs=json.loads(Path(archivo).read_text(encoding='utf-8'))
        self.nombre=None;self.t=0.0
    def seleccionar(self,nombre):
        if nombre!=self.nombre:self.nombre=nombre;self.t=0.0
    def cuadro(self,dt=0.0):
        d=self.defs[self.nombre];frames=d['frames'];dur=float(d['duracion'])
        self.t+=max(0,dt)
        n=int(self.t/max(.001,dur))
        if d.get('loop',True):n%=len(frames)
        else:n=min(n,len(frames)-1)
        return frames[n]
    def terminada(self):
        d=self.defs[self.nombre]
        return not d.get('loop',True) and self.t>=float(d['duracion'])*len(d['frames'])
