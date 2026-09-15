"""Spike del análisis del patrón de recorrido (2026-09-14). NO es parte de Clipify: parte cada entregable en TOMAS y arma una hoja de contacto.

No es parte de Clipify ni del programa final -- es el andamio para la prueba
de si un modelo reconoce los cuartos de Bruno. Vive en el scratchpad a
proposito.
"""
import subprocess, sys, os, re, glob, json
from PIL import Image, ImageDraw, ImageFont

SALIDA = sys.argv[1]
UMBRAL = 0.25          # sensibilidad del detector de cortes
MIN_TOMA = 0.35        # segundos: por debajo de esto no es una toma, es un parpadeo
ANCHO_CELDA = 260      # px del lado corto de cada cuadro en la hoja
COLUMNAS = 5

def duracion(v):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","csv=p=0",v],capture_output=True,text=True).stdout.strip())

def cortes(v):
    r = subprocess.run(["ffmpeg","-i",v,"-filter:v",
        f"select='gt(scene,{UMBRAL})',showinfo","-f","null","-"],
        capture_output=True,text=True)
    return [float(m) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)]

def tomas(v):
    d = duracion(v)
    puntos = [0.0] + [t for t in cortes(v) if 0.2 < t < d-0.2] + [d]
    out = []
    for a,b in zip(puntos, puntos[1:]):
        if b-a >= MIN_TOMA:
            out.append((a,b))
        elif out:                      # toma muy corta: se pega a la anterior
            out[-1] = (out[-1][0], b)
    return out

def cuadro(v, t, destino):
    subprocess.run(["ffmpeg","-y","-ss",str(t),"-i",v,"-frames:v","1",
        "-vf",f"scale='if(gt(iw,ih),-2,{ANCHO_CELDA})':'if(gt(iw,ih),{ANCHO_CELDA},-2)'",
        destino], capture_output=True)

def fuente(px):
    for r in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc"]:
        if os.path.exists(r):
            try: return ImageFont.truetype(r, px)
            except Exception: pass
    return ImageFont.load_default()

def hoja(video, nombre):
    ts = tomas(video)
    tmp = os.path.join(SALIDA, "_tmp"); os.makedirs(tmp, exist_ok=True)
    imgs = []
    for i,(a,b) in enumerate(ts):
        p = os.path.join(tmp, f"{i:03d}.jpg")
        cuadro(video, a + (b-a)/2, p)
        if os.path.exists(p): imgs.append((i,a,b,Image.open(p).convert("RGB")))
    if not imgs: return None
    cw = max(im.width for *_,im in imgs)
    ch = max(im.height for *_,im in imgs)
    barra = 30
    filas = (len(imgs)+COLUMNAS-1)//COLUMNAS
    hoja = Image.new("RGB",(COLUMNAS*cw, filas*(ch+barra)), (17,17,17))
    dib = ImageDraw.Draw(hoja); f = fuente(19)
    for k,(i,a,b,im) in enumerate(imgs):
        x = (k%COLUMNAS)*cw; y = (k//COLUMNAS)*(ch+barra)
        hoja.paste(im,(x + (cw-im.width)//2, y+barra))
        dib.text((x+6,y+5), f"{i+1}  {a:.1f}-{b:.1f}s  ({b-a:.1f})",
                 fill=(255,209,102), font=f)
    ruta = os.path.join(SALIDA, nombre + ".jpg")
    hoja.save(ruta, quality=72, optimize=True)
    for *_,im in imgs: im.close()
    return ruta, [(i+1,round(a,2),round(b,2),round(b-a,2)) for i,a,b,_ in imgs]

resumen = {}
for v in sorted(glob.glob(os.path.expanduser("~/Movies/patron-2026/*.mp4"))):
    nombre = os.path.splitext(os.path.basename(v))[0]
    r = hoja(v, nombre)
    if r:
        ruta, lista = r
        resumen[nombre] = lista
        print(f"{nombre[:40]:40} {len(lista):3d} tomas  -> {os.path.basename(ruta)}")
json.dump(resumen, open(os.path.join(SALIDA,"tomas.json"),"w"), indent=1, ensure_ascii=False)
