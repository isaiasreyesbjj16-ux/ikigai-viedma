"""Genera las marcas de agua del logo para el fondo de la app.

El logo original (static/icons/logo.png) es RGB con fondo blanco opaco: si se
usa tal cual sobre el fondo oscuro de la app se veria un cuadro blanco. Acá se
convierte en un PNG con canal alfa: los trazos se vuelven claros/oscuros segun el
tema y el blanco de fondo queda totalmente transparente, con una opacidad baja
(~14%) para que se vea sin tapar nada.
"""
from PIL import Image

SRC = 'static/icons/logo.png'
OUT_DARK = 'static/icons/logo-fondo-oscuro.png'   # para el tema oscuro
OUT_LIGHT = 'static/icons/logo-fondo-claro.png'   # para el tema claro
ANCHO = 620
K = 0.20          # opacidad maxima de la marca de agua


def es_rojo(r, g, b):
    return r > 110 and r - g > 55 and r - b > 55


def construir(oscuro):
    im = Image.open(SRC).convert('RGB')
    w, h = im.size
    px = im.load()
    out = Image.new('RGBA', (w, h))
    opx = out.load()
    tinta = (245, 235, 238) if oscuro else (42, 26, 30)
    rojo = (255, 90, 77) if oscuro else (208, 36, 36)
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if es_rojo(r, g, b):
                a = int(min(255, (255 - min(r, g, b)) * K))
                c = rojo
            else:
                # solo el negro/gris del trazo; el blanco de fondo queda alfa 0
                d = 255 - min(r, g, b)
                if d < 12:
                    continue
                a = int(min(255, d * K))
                c = tinta
            if a > 0:
                opx[x, y] = (c[0], c[1], c[2], a)
    out = out.resize((ANCHO, int(ANCHO * h / w)), Image.LANCZOS)
    return out


for oscuro, destino in ((True, OUT_DARK), (False, OUT_LIGHT)):
    img = construir(oscuro)
    # PNG con paleta: la marca de agua solo tiene 2 tintas + alfa, asi que
    # cuantizar deja el archivo ~5 veces mas liviano sin que se note.
    img = img.quantize(colors=48, method=Image.FASTOCTREE)
    img.save(destino, 'PNG', optimize=True)
    ex = img.convert('RGBA').getextrema()
    print('%s -> %s %s  alpha %s-%s' % (destino, img.size, img.mode, ex[3][0], ex[3][1]))