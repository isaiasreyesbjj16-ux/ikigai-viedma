import re

t = open('static/_prueba_dash.html', encoding='utf-8').read()
t = re.sub(r'<html lang="es">', '<html lang="es" data-theme="light">', t, count=1)
open('static/_prueba_dash_light.html', 'w', encoding='utf-8').write(t)
print('ok light:', 'data-theme' in t)