"""Genera una pagina minima que carga style.css + app.js y pinta la seccion de
Torneos con datos de ejemplo, para revisar el calendario, el ranking y el
medallero tal cual los ve el usuario."""
import json
import os
import sys
import tempfile
from datetime import date, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
os.environ['DB_MODE'] = 'sqlite'
tmpdir = tempfile.mkdtemp(prefix='ikigai_tor_')
os.environ['SQLITE_PATH'] = os.path.join(tmpdir, 'test.db')
sys.path.insert(0, BASE)

import app as A
A.app.config['DATABASE'] = os.environ['SQLITE_PATH']
A.app.config['TESTING'] = True
import dbadapter
dbadapter.DB_MODE = 'sqlite'
A.init_db()

hoy = date.today()
c = A.app.test_client()
c.post('/api/login', json={'username': 'admin', 'password': 'admin123'})

nombres = ['Ana Rodríguez', 'Leo Rodríguez', 'Sofía Gómez', 'Bruno Díaz', 'Carla Méndez', 'Diego Paz']
alumnos = []
for i, nom in enumerate(nombres):
    r = c.post('/api/alumnos', json={'nombre': nom, 'username': 'al_tor%d' % i, 'password': '1234',
                                     'categoria': ['adulto', 'juveniles', 'kids'][i % 3],
                                     'cinturon': ['blanco', 'azul', 'rojo', 'pardo'][i % 4],
                                     'nacimiento': '2015-%02d-15' % (i % 12 + 1)})
    if r.status_code == 200:
        js = r.get_json()
        aid = js.get('id') or (js.get('alumno') or {}).get('id') or (js.get('user') or {}).get('id')
        if aid:
            alumnos.append(aid)
print('alumnos creados:', len(alumnos))

torneos = [
    ('Copa Ciudad de Viedma', hoy + timedelta(days=25), 'Viedma', 'Gi', 'inscripcion'),
    ('Open de Patagonia', hoy + timedelta(days=70), 'Bariloche', 'NoGi', 'inscripcion'),
    ('Torneo Kids Invitational', hoy + timedelta(days=12), 'General Roca', 'Kids', 'inscripcion'),
    ('Copa Invierno', hoy - timedelta(days=35), 'Viedma', 'Gi', 'terminado'),
    ('Regional Pampeano', hoy - timedelta(days=90), 'Bahía Blanca', 'Gi', 'terminado'),
]
ids = []
for nom, f, ciu, tipo, est in torneos:
    r = c.post('/api/torneos', json={'nombre': nom, 'fecha': f.strftime('%Y-%m-%d'), 'ciudad': ciu,
                                     'tipo': tipo, 'estado': est})
    ids.append(r.get_json().get('id'))

for _t, tid, partes in [(0, ids[3], [(0, 'oro'), (1, 'plata'), (3, 'bronce'), (4, 'participacion')]),
                        (0, ids[4], [(0, 'oro'), (2, 'participacion')]),
                        (0, ids[1], [(5, 'participacion')])]:
    for ai, med in partes:
        if ai < len(alumnos):
            c.post('/api/torneos/%d/participantes' % tid,
                   json={'alumno_id': alumnos[ai], 'medalla': med})

datos = c.get('/api/torneos').get_json()
print('torneos:', len(datos['torneos']), '| ranking:', len(datos['ranking']),
      '| medallero:', json.dumps(datos['medallero']))

stub = """
  var DATOS = %s;
  async function api(path) {
    if (String(path).indexOf('/api/torneos') === 0) return DATOS;
    return { alumnos: [], profesores: [], avisos: [], pagos: [] };
  }
  function pintar() {
    var el = document.getElementById('sec-torneos');
    renderTorneos(el).then(function () { el.classList.add('active'); },
      function (e) { el.innerHTML = '<div class="card">ERROR: ' + e.message + '</div>'; });
  }
  window.addEventListener('load', function () {
    pintar();
    setTimeout(function () {
      var over = [];
      document.querySelectorAll('#sec-torneos *').forEach(function (el) {
        if (el.scrollWidth > el.clientWidth + 2 && getComputedStyle(el).overflowX === 'visible') {
          over.push(el.tagName + '.' + (el.className || '-') + ' sw=' + el.scrollWidth + ' cw=' + el.clientWidth);
        }
      });
      document.title = over.length ? 'OVERFLOW: ' + over.slice(0, 6).join(' || ') : 'sin overflow';
    }, 900);
  });
""" % json.dumps(datos, ensure_ascii=False)

html = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>prueba torneos</title>
<link rel="stylesheet" href="style.css?v=33">
</head>
<body class="dash-body">
<div class="content" style="padding-top:70px">
  <div id="sec-torneos" class="sec"></div>
</div>
<script>
window.USER = {"id":1,"role":"admin","nombre":"Isaias","username":"admin"};
window.DIAS = ['Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo'];
window.BELTS_ADULT = ['Blanco','Azul','Púrpura','Marrón','Negro'];
window.BELTS_KIDS = ['Blanco','Azul','Púrpura','Marrón','Negro'];
window.BELTS_JUV = ['Blanco','Azul','Púrpura','Marrón','Negro'];
window.CATEGORIAS = ['adulto','juveniles','kids'];
window.TIPOS_CLASE = ['Gi','NoGi','Kids','Juveniles','Abierto'];
window.METODOS = ['Efectivo','Transferencia'];
</script>
<script src="app.js"></script>
<script>%s</script>
</body></html>
""" % stub

open('static/_prueba_tor.html', 'w', encoding='utf-8').write(html)
print('ok: static/_prueba_tor.html')