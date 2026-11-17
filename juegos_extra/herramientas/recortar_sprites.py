"""Limpia las hojas planas, recorta atlas y crea contactos para revisión."""
from __future__ import annotations
import json
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / 'assets'


def key_background(rgb: np.ndarray) -> tuple[np.ndarray, int]:
    """Flood-fill solo los tonos acromáticos conectados al borde del cuadriculado."""
    h, w, _ = rgb.shape
    # Los sprites tienen líneas oscuras y colores propios; el tablero es gris neutro.
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    luma = rgb.mean(axis=2)
    candidato = (chroma <= 11) & (luma >= 112) & (luma <= 225)
    alpha_zero = np.zeros((h, w), dtype=bool)
    pila: list[int] = []
    for x in range(w):
        if candidato[0, x]: alpha_zero[0, x] = True; pila.append(x)
        i = (h - 1) * w + x
        if candidato[h - 1, x] and not alpha_zero[h - 1, x]: alpha_zero[h - 1, x] = True; pila.append(i)
    for y in range(h):
        i = y * w
        if candidato[y, 0] and not alpha_zero[y, 0]: alpha_zero[y, 0] = True; pila.append(i)
        i = y * w + (w - 1)
        if candidato[y, w - 1] and not alpha_zero[y, w - 1]: alpha_zero[y, w - 1] = True; pila.append(i)
    # Vecindad 4: protege superficies grises/blancas rodeadas por el contorno de cada sprite.
    flat = alpha_zero.ravel(); cand = candidato.ravel()
    while pila:
        i = pila.pop(); y, x = divmod(i, w)
        if y and cand[i-w] and not flat[i-w]: flat[i-w] = True; pila.append(i-w)
        if y+1 < h and cand[i+w] and not flat[i+w]: flat[i+w] = True; pila.append(i+w)
        if x and cand[i-1] and not flat[i-1]: flat[i-1] = True; pila.append(i-1)
        if x+1 < w and cand[i+1] and not flat[i+1]: flat[i+1] = True; pila.append(i+1)
    return alpha_zero, int((candidato & ~alpha_zero).sum())


def componentes(alpha: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    """Busca componentes 8-conectados sobre el canal alfa y devuelve sus cajas."""
    mask = alpha > 8
    h, w = mask.shape
    visited = np.zeros((h, w), dtype=bool)
    boxes = []
    for y, x in zip(*np.nonzero(mask)):
        if visited[y, x]: continue
        pila = [(int(y), int(x))]; visited[y, x] = True
        minx=maxx=int(x); miny=maxy=int(y); count=0
        while pila:
            cy,cx=pila.pop();count+=1
            minx=min(minx,cx);maxx=max(maxx,cx);miny=min(miny,cy);maxy=max(maxy,cy)
            for ny in range(max(0,cy-1),min(h,cy+2)):
                for nx in range(max(0,cx-1),min(w,cx+2)):
                    if mask[ny,nx] and not visited[ny,nx]:visited[ny,nx]=True;pila.append((ny,nx))
        boxes.append((minx,miny,maxx+1,maxy+1,count))
    return boxes


def componer_contacto(sprites: list[tuple[str, Image.Image]], out: Path) -> None:
    columnas=4; celda_w=240; celda_h=205; filas=(len(sprites)+columnas-1)//columnas
    fondo=Image.new('RGB',(columnas*celda_w,filas*celda_h),(244,231,218));d=ImageDraw.Draw(fondo)
    try:font=ImageFont.truetype('arial.ttf',15)
    except OSError:font=ImageFont.load_default()
    for i,(nombre,img) in enumerate(sprites):
        x=(i%columnas)*celda_w;y=(i//columnas)*celda_h
        # Fondo fucsia suave para que salten a la vista restos del cuadriculado o halos grises.
        d.rounded_rectangle((x+8,y+8,x+celda_w-8,y+celda_h-8),radius=10,fill=(241,201,222),outline=(87,60,79),width=2)
        maxw,maxh=celda_w-28,celda_h-55;factor=min(maxw/max(1,img.width),maxh/max(1,img.height),3.0)
        size=(max(1,int(img.width*factor)),max(1,int(img.height*factor)))
        thumb=img.resize(size,Image.Resampling.LANCZOS)
        fondo.paste(thumb,(x+(celda_w-size[0])//2,y+14+(maxh-size[1])//2),thumb)
        d.text((x+14,y+celda_h-32),nombre,fill=(40,33,44),font=font)
    fondo.save(out)


def procesar(atlas_path: Path, grupo: str) -> None:
    atlas=json.loads(atlas_path.read_text(encoding='utf-8-sig'))
    source=ROOT/atlas['source']
    original=Image.open(source).convert('RGB')
    rgb=np.asarray(original,dtype=np.uint8)
    transparent,interiores=key_background(rgb)
    rgba=np.dstack((rgb,np.where(transparent,0,255).astype(np.uint8)))
    limpia=Image.fromarray(rgba,'RGBA')
    limpia.save(ROOT/'assets'/'hojas'/f'hoja_{grupo}_limpia.png')
    comps=componentes(rgba[:,:,3])
    outdir=ROOT/'assets'/grupo;outdir.mkdir(parents=True,exist_ok=True)
    contactos=[];metadata={}
    permitidos={f"{nombre}.png" for nombre in atlas['items']}|{f"_contacto_{grupo}.png"}
    for antiguo in outdir.glob('*.png'):
        if antiguo.name not in permitidos: antiguo.unlink()
    for nombre,item in atlas['items'].items():
        x,y,w,h=item['box'];raw=limpia.crop((x,y,x+w,y+h))
        # Comprueba los componentes encontrados y mantiene el grupo manual señalado en el atlas.
        intersectan=[c for c in comps if c[0]<x+w and c[2]>x and c[1]<y+h and c[3]>y]
        # Limpia restos neutros del cuadriculado dentro de sprites coloridos; conserva blancos (>224) y tintas oscuras (<108).
        if item.get('remove_neutral_checker'):
            px=np.asarray(raw.convert('RGBA')).copy()
            rgb_crop=px[:,:,:3].astype(np.int16)
            chroma=rgb_crop.max(axis=2)-rgb_crop.min(axis=2)
            luma=rgb_crop.mean(axis=2)
            restos=(chroma<=15)&(luma>=108)&(luma<=224)
            px[:,:,3][restos]=0
            raw=Image.fromarray(px,'RGBA')
        # En los personajes aislados se elimina ruido suelto, conservando el componente alfa principal.
        if item.get('component_policy') == 'dominant':
            local_alpha=np.asarray(raw.getchannel('A'))
            local_comps=componentes(local_alpha)
            if local_comps:
                principal=max(local_comps,key=lambda c:c[-1])
                px0,py0,px1,py1,_=principal
                limpia_alpha=raw.getchannel('A')
                mascara=np.zeros_like(local_alpha,dtype=np.uint8)
                mascara[py0:py1,px0:px1]=local_alpha[py0:py1,px0:px1]
                # El mayor grupo (cuerpo/ropa/equipo conectado) queda, motas y vecinos no.
                raw.putalpha(Image.fromarray(mascara,'L'))
        bbox=raw.getchannel('A').getbbox()
        if bbox:
            sprite=raw.crop(bbox)
            ax=max(0,min(sprite.width,int(item['anchor'][0]-(bbox[0]))))
            ay=max(0,min(sprite.height,int(item['anchor'][1]-(bbox[1]))))
        else:
            sprite=raw;ax,ay=item['anchor']
        sprite.save(outdir/f'{nombre}.png')
        metadata[nombre]={'anchor':[ax,ay],'box':item['box'],'components_in_box':len(intersectan),'groups':item.get('groups',False)}
        contactos.append((nombre,sprite))
    # Ambos atlas guardan sus anclajes en un manifiesto común en assets/.
    ruta_anclajes=ROOT/'assets'/'anclajes.json'
    anclajes=json.loads(ruta_anclajes.read_text(encoding='utf-8')) if ruta_anclajes.exists() else {}
    anclajes[grupo]=metadata
    ruta_anclajes.write_text(json.dumps(anclajes,ensure_ascii=False,indent=2),encoding='utf-8')
    componer_contacto(contactos,outdir/f'_contacto_{grupo}.png')
    print(f'{grupo}: {len(comps)} componentes alfa; {len(atlas["items"])} recortes; {interiores} píxeles neutros protegidos dentro de contornos.')
    sin=[n for n,v in metadata.items() if v['components_in_box']==0]
    if sin: print('  cajas sin componentes:',', '.join(sin))

if __name__=='__main__':
    procesar(ATLAS/'atlas_emoji.json','emoji')
    procesar(ATLAS/'atlas_curramgram.json','curramgram')


