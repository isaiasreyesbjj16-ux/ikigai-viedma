# -*- coding: utf-8 -*-
"""Suite de pruebas locales de la app IKIGAI (SQLite, base temporal).

Uso:  py test_ikigai.py

No toca la base real: crea una base SQLite temporal.
"""
import os, sys, json, tempfile, base64
from datetime import date, datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
os.environ['DB_MODE'] = 'sqlite'
tmpdir = tempfile.mkdtemp(prefix='ikigai_test_')
os.environ['SQLITE_PATH'] = os.path.join(tmpdir, 'test.db')
sys.path.insert(0, BASE)

import app as A
A.app.config['DATABASE'] = os.environ['SQLITE_PATH']
A.app.config['TESTING'] = True
A._ultimo_aviso[0] = 9999999999  # no disparar avisos periodicos durante el test

import dbadapter
dbadapter.DB_MODE = 'sqlite'
A.init_db()

PASS, FAIL = [], []


def check(nombre, cond, extra=''):
    (PASS if cond else FAIL).append(nombre)
    print(('  OK  ' if cond else '  FALLA ') + nombre + ('' if cond else '   -> %s' % extra))


def hoy_academy():
    """Espeja _hoy_academy(): UTC con offset -3 (Argentina)."""
    return datetime.now(timezone.utc) + timedelta(hours=-3)


def login(cli, usuario, clave='1234'):
    return cli.post('/api/login', json={'username': usuario, 'password': clave})


def nuevo_alumno(cli, n, **extra):
    body = {'role': 'alumno', 'nacimiento': '1995-05-05', 'username': 'alu%d' % n,
            'password': '1234', 'nombre': 'Alumno Prueba %d' % n, 'categoria': 'adulto',
            'cuota_mensual': 1000, 'acepto_tyc': True}
    body.update(extra)
    return cli.post('/api/register', json=body)


c = A.app.test_client()
PNG = 'data:image/png;base64,' + base64.b64encode(bytes.fromhex(
    '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a494441'
    '54789c6360000002000100' + '05fe02fe' + '0000000049454e44ae426082')).decode()

# ===========================================================================
print('== LOGIN ==')
r = login(c, 'admin', 'admin123')
check('admin puede entrar', r.status_code == 200 and r.get_json().get('ok'), 'r=%s' % r.status_code)
r = login(c, 'admin', 'claveIncorrecta')
check('clave incorrecta -> 401', r.status_code == 401, 'r=%s' % r.status_code)
login(c, 'admin', 'admin123')

# ===========================================================================
print('== ALUMNOS ==')
alu = []
for i in range(3):
    r = nuevo_alumno(c, i)
    ok = r.status_code == 200
    if ok:
        alu.append(r.get_json().get('user', {}).get('id'))
    check('registrar alumno %d' % i, ok, 'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:120]))
    login(c, 'admin', 'admin123')
r = c.get('/api/alumnos')
check('listado de alumnos devuelve 3', r.status_code == 200 and len(r.get_json()['alumnos']) >= 3,
      'n=%s' % len(r.get_json().get('alumnos', [])))

# ===========================================================================
print('== HORARIOS ==')
r = c.post('/api/horarios', json={'dia': 0, 'hora': '18:00', 'tipo': 'Gi', 'nivel': 'Todos'})
check('crear horario', r.status_code == 200, 'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:120]))
r = c.post('/api/horarios', json={'dia': 2, 'hora': '19:30', 'tipo': 'Gi', 'nivel': 'Adultos', 'profesor_id': 1})
check('crear horario con profesor', r.status_code == 200, 'r=%s' % r.status_code)
hs = c.get('/api/horarios').get_json()['horarios']
check('horarios listados con dia/nombre', len(hs) >= 2 and hs[0].get('dia_nombre'), 'n=%s' % len(hs))

# ===========================================================================
print('== PAGOS ==')
mes_ant = hoy_academy().month - 1 or 12
r = c.post('/api/pagos', json={'alumno_id': alu[0], 'monto': 1000, 'mes': mes_ant, 'anio': hoy_academy().year,
                               'metodo': 'Efectivo', 'nota': 'pago simple'})
check('registrar pago simple', r.status_code == 200 and r.get_json().get('ok'),
      'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:120]))
pagos = c.get('/api/pagos').get_json()['pagos']
check('el pago figura en el listado', any(p['alumno_id'] == alu[0] for p in pagos), 'pagos=%s' % len(pagos))

# ===========================================================================
print('== FAMILIA (alta + pago completo) ==')
r = c.post('/api/familias', json={'nombre': 'Familia Prueba', 'titular_id': alu[0]})
check('crear grupo familiar', r.status_code == 200 and r.get_json().get('id'),
      'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:120]))
fam_id = r.get_json().get('id')
for uid, rel in ((alu[1], 'Pareja'), (alu[2], 'Hijo/a')):
    r = c.post('/api/familias/%d/miembros' % fam_id, json={'user_id': uid, 'relacion': rel})
    check('agregar %s al grupo' % rel, r.status_code == 200, 'r=%s' % r.status_code)
fam = c.get('/api/familias').get_json()['familias'][0]
miembros = fam['miembros']
check('el grupo tiene 3 miembros', len(miembros) == 3, 'n=%s' % len(miembros))
check('los 3 con descuento familiar', all(m['descuento'] > 0 and m['cuota_final'] < m['cuota'] for m in miembros),
      json.dumps([(m['nombre'], m['cuota'], m['descuento'], m['cuota_final']) for m in miembros]))
total_esp = sum(m['cuota_final'] for m in miembros)
mes_f = hoy_academy().month
r = c.post('/api/pagos/familia', json={'titular_id': alu[0], 'mes': mes_f, 'anio': hoy_academy().year,
                                       'metodo': 'Transferencia', 'aplicar_cargo': False})
jf = r.get_json(silent=True) or {}
check('pagar familia completa (3 pagos)', r.status_code == 200 and jf.get('cantidad') == 3,
      'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:150]))
check('total = suma de cuotas descontadas', r.status_code == 200 and jf.get('total') == total_esp,
      'total=%s esperado=%s' % (jf.get('total'), total_esp))
pagos_f = [p for p in c.get('/api/pagos').get_json()['pagos'] if p['mes'] == mes_f]
check('3 pagos del mes en el listado', len(pagos_f) == 3, 'n=%s' % len(pagos_f))
r = c.post('/api/pagos/familia', json={'titular_id': alu[0], 'mes': mes_f, 'anio': hoy_academy().year})
check('repetir el pago no duplica', r.status_code == 200 and (r.get_json() or {}).get('cantidad') == 0,
      'r=%s' % r.get_data(as_text=True)[:120])
# alumno ve su familia
cf = A.app.test_client()
login(cf, 'alu0')
mf = cf.get('/api/mi_familia')
check('el titular ve su familia', mf.status_code == 200 and (mf.get_json() or {}).get('familia'), 'r=%s' % mf.status_code)
# el alumno NO registra pagos: manda el comprobante y queda pendiente
# (para el mes siguiente: en el actual el admin ya lo registró en el mostrador)
mes_t = mes_f % 12 + 1
anio_t = hoy_academy().year + (1 if mes_f == 12 else 0)
COMP = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
r = cf.post('/api/avisar_pago_familia', json={'comprobante': COMP, 'mes': mes_t, 'anio': anio_t})
jav = r.get_json(silent=True) or {}
check('el titular manda el comprobante familiar (3 avisos pendientes)',
      r.status_code == 200 and jav.get('cantidad') == 3, 'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:150]))
pend = [a for a in c.get('/api/avisos_pago').get_json()['avisos']
        if a['estado'] == 'pendiente' and 'familiar' in (a['nota'] or '').lower()]
check('los 3 avisos quedan pendientes con el comprobante',
      len(pend) == 3 and all(a['comprobante'] == COMP for a in pend), 'n=%d' % len(pend))
check('cada aviso pide el total descontado de la familia', jav.get('total') == total_esp,
      'total=%s esperado=%s' % (jav.get('total'), total_esp))
r = cf.post('/api/avisar_pago_familia', json={'comprobante': COMP})
check('reavisar el mismo mes no duplica avisos -> 400', r.status_code == 400, 'r=%s' % r.status_code)
r = cf.post('/api/avisar_pago_familia', json={'comprobante': 'no-es-comprobante'})
check('sin comprobante válido no se genera nada -> 400', r.status_code == 400, 'r=%s' % r.status_code)
r = cf.post('/api/pagos/familia', json={'titular_id': alu[0], 'mes': mes_t, 'anio': anio_t})
check('el alumno no puede registrar el pago directamente -> 403', r.status_code == 403,
      'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:100]))
# un alumno que NO es titular no puede mandar el comprobante familiar
cf2 = A.app.test_client()
login(cf2, 'alu1')
r = cf2.post('/api/avisar_pago_familia', json={'comprobante': COMP})
check('un alumno no titular no puede mandar el comprobante familiar -> 403',
      r.status_code == 403, 'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:100]))
# el profesor tampoco
r = A.app.test_client()
c.post('/api/profesores', json={'nombre': 'Profe Prueba', 'username': 'profe1', 'password': '1234'})
login(r, 'profe1', '1234')
r = r.post('/api/avisar_pago_familia', json={'comprobante': COMP})
check('el profesor no puede mandar el comprobante familiar -> 403',
      r.status_code == 403, 'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:100]))
# el admin sigue registrando pagos de familia en el mostrador
mes_t = mes_f % 12 + 1
anio_t = hoy_academy().year + (1 if mes_f == 12 else 0)
r = c.post('/api/pagos/familia', json={'titular_id': alu[0], 'mes': mes_t, 'anio': anio_t})
check('el admin puede registrar la familia en el mostrador', r.status_code == 200,
      'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:150]))

# ===========================================================================
print('== BECA ==')
r = c.post('/api/alumnos/%d/beca' % alu[2], json={})
check('admin da beca', r.status_code == 200 and r.get_json().get('beca') == 1, 'r=%s' % r.status_code)
alu_b = next(a for a in c.get('/api/alumnos').get_json()['alumnos'] if a['id'] == alu[2])
check('becado: cuota en 0 y estado becado', alu_b['cuota']['estado'] == 'becado' and alu_b['cuota']['cuota'] == 0,
      json.dumps(alu_b['cuota']))
deud = c.get('/api/deudores').get_json().get('deudores', [])
check('becado no figura en deudores', alu[2] not in [d['id'] for d in deud], 'deudores=%s' % [d['id'] for d in deud])
r = c.post('/api/notify_deuda', json={'alumno_id': alu[2]})
check('notify_deuda no avisa al becado', r.status_code == 200 and r.get_json().get('avisados') == 0,
      'r=%s' % r.get_data(as_text=True)[:120])
r = c.post('/api/alumnos/%d/beca' % alu[2], json={})
check('se le quita la beca', r.status_code == 200 and r.get_json().get('beca') == 0, 'r=%s' % r.status_code)

# ===========================================================================
print('== NOTIFICAR A TODOS / MENSAJE GENERAL ==')
r = c.post('/api/notify_deuda', json={})
check('notificar a todos responde ok', r.status_code == 200 and r.get_json().get('ok'),
      'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:120]))
r = c.post('/api/mensajes/broadcast', json={'texto': 'HOY A ENTRENAR'})
jb = r.get_json(silent=True) or {}
check('mensaje general enviado', r.status_code == 200 and jb.get('ok') and jb.get('enviados') == jb.get('destinatarios'),
      'r=%s %s' % (r.status_code, json.dumps(jb)))
r = c.post('/api/mensajes/broadcast', json={'texto': ''})
check('mensaje vacio -> 400', r.status_code == 400, 'r=%s' % r.status_code)
ca = A.app.test_client()
r = nuevo_alumno(ca, 9)
cperm = A.app.test_client()
login(cperm, 'alu9')
r = cperm.post('/api/mensajes/broadcast', json={'texto': 'hola'})
check('alumno no puede mandar mensaje general -> 403', r.status_code == 403, 'r=%s' % r.status_code)
r = cperm.post('/api/notify_deuda', json={})
check('alumno no puede notificar a todos -> 403', r.status_code == 403, 'r=%s' % r.status_code)

# ===========================================================================
print('== CUMPLEANOS ==')
mes_hoy = hoy_academy().month
with A.app.app_context():
    db = A.get_db()
    db.execute('UPDATE users SET nacimiento=? WHERE id=?', ('%04d-%02d-10' % (2001, mes_hoy), alu[0]))
    db.execute('UPDATE users SET nacimiento=? WHERE id=?', ('15/%02d/%04d' % (mes_hoy, 2002), alu[1]))
    db.commit()
cum = c.get('/api/cumpleanios').get_json()
nombres = [x['nombre'] for x in cum['cumpleanios']]
check('cumpleanios: muestra todos los del mes (formatos variados)',
      alu[0] and 'Alumno Prueba 0' in nombres and 'Alumno Prueba 1' in nombres, json.dumps(nombres))

# ===========================================================================
print('== MURO CON FOTOS ==')
r = c.post('/api/muro', json={'texto': 'Buen entreno', 'fotos': [PNG]})
check('publicar en el muro con foto', r.status_code == 200, 'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:120]))
posts = c.get('/api/muro').get_json().get('posts', c.get('/api/muro').get_json().get('muro', []))
con_foto = [p for p in posts if p.get('fotos')]
check('la foto queda en la publicacion', len(con_foto) == 1, 'n=%s' % len(con_foto))

# ===========================================================================
print('== PAGINA DE PRESENTACION ==')
r = c.get('/presentacion')
hp = r.get_data(as_text=True)
check('presentacion responde 200 (publica)', r.status_code == 200, 'r=%s' % r.status_code)
check('presentacion: nombre de la academia', 'CIENCIA Y ARTE DEL CONOCIMIENTO' in hp.upper()
      and 'JIU JITSU VIEDMA' in hp.upper(), 'len=%s' % len(hp))
check('presentacion: link de instagram', 'instagram.com' in hp, 'no esta el link')
check('presentacion: horarios cargados', '19:30' in hp and '18:00' in hp, 'faltan horarios')
profes = c.get('/api/profesores').get_json().get('profesores', [])
if profes:
    check('presentacion: aparece el profe', profes[0]['nombre'] in hp, 'nombre=%s' % profes[0]['nombre'])
c2anon = A.app.test_client()
check('presentacion se ve sin loguearse', c2anon.get('/presentacion').status_code == 200, 'r=%s' % c2anon.get('/presentacion').status_code)

# ===========================================================================
print('== TORNEOS (calendario + ranking + medallero) ==')
hoy = hoy_academy()
f_pasado = (hoy - timedelta(days=40)).strftime('%Y-%m-%d')
f_futuro = (hoy + timedelta(days=40)).strftime('%Y-%m-%d')
COMP = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
r = c.post('/api/torneos', json={'nombre': 'Copa Ciudad', 'fecha': f_pasado,
                                 'ciudad': 'Viedma', 'tipo': 'Gi'})
check('admin carga un torneo', r.status_code == 200 and r.get_json().get('id'),
      'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:120]))
tid1 = r.get_json().get('id')
r = c.post('/api/torneos', json={'nombre': 'Open de Patagonia', 'fecha': f_futuro, 'tipo': 'NoGi'})
tid2 = r.get_json().get('id')
r = c.post('/api/torneos', json={'nombre': ''})
check('torneo sin nombre se rechaza -> 400', r.status_code == 400, 'r=%s' % r.status_code)
r = c.post('/api/torneos', json={'nombre': 'X', 'fecha': f_futuro})
tid3 = r.get_json().get('id')
# resultados: alu[0] oro, alu[1] plata; alu[0] repite en el segundo torneo
r = c.post('/api/torneos/%d/participantes' % tid1, json={'alumno_id': alu[0], 'posicion': 1})
check('cargar participant con puesto 1 = oro', r.status_code == 200 and r.get_json().get('medalla') == 'oro',
      'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:120]))
c.post('/api/torneos/%d/participantes' % tid1, json={'alumno_id': alu[1], 'medalla': 'plata'})
c.post('/api/torneos/%d/participantes' % tid1, json={'alumno_id': alu[2]})
r = c.post('/api/torneos/%d/participantes' % tid1, json={'alumno_id': alu[0], 'medalla': 'oro'})
check('no duplica el mismo alumno en un torneo', r.status_code == 200 and r.get_json().get('nuevo') is False,
      'r=%s' % r.get_data(as_text=True)[:120])
c.post('/api/torneos/%d/participantes' % tid3, json={'alumno_id': alu[0], 'medalla': 'bronce'})
c.post('/api/torneos/%d/participantes' % tid2, json={'alumno_id': alu[0]})
tj = c.get('/api/torneos').get_json()
check('el calendario lista los 3 torneos', len(tj['torneos']) == 3, 'n=%s' % len(tj['torneos']))
prox = [t for t in tj['torneos'] if t['fecha'] >= hoy.strftime('%Y-%m-%d')]
check('los futuros van primero para el calendario', len(prox) == 2, 'n=%s' % len(prox))
rk = {x['id']: x for x in tj['ranking']}
check('el titular de mas torneos queda 1º en el ranking',
      rk.get(alu[0], {}).get('puesto') == 1 and rk[alu[0]]['participaciones'] == 3,
      'rk=%s' % rk.get(alu[0]))
check('el ranking cuenta oro, plata y bronce del 1º',
      rk[alu[0]]['oro'] == 1 and rk[alu[0]]['bronce'] == 1 and rk[alu[0]]['participo'] == 1,
      json.dumps(rk.get(alu[0], {})))
check('medallero de la academia cuenta todo',
      tj['medallero']['oro'] == 1 and tj['medallero']['plata'] == 1 and tj['medallero']['bronce'] == 1
      and tj['medallero']['total'] == 3, json.dumps(tj['medallero']))
check('el detalle del torneo trae los 3 competidores',
      len([t for t in tj['torneos'] if t['id'] == tid1][0]['participantes_detalle']) == 3)
# el alumno ve el calendario y puede saber si compitio
r = cf.get('/api/torneos')
tj2 = r.get_json()
check('el alumno tambien ve los torneos', r.status_code == 200 and len(tj2['torneos']) == 3, 'r=%s' % r.status_code)
check('al alumno le aparece marcado en que torneo compitio',
      all(t['participo'] is True for t in tj2['torneos'] if t['id'] == tid1))
r = cf.post('/api/torneos/%d/participantes' % tid2, json={'alumno_id': alu[1], 'medalla': 'oro'})
check('alumno NO puede cargar resultados de otro -> 403', r.status_code == 403, 'r=%s' % r.status_code)
r = cf.post('/api/torneos', json={'nombre': 'Torneo del alumno', 'fecha': f_futuro})
check('el alumno puede sumar un torneo al calendario',
      r.status_code == 200 and r.get_json().get('id'), 'r=%s %s' % (r.status_code, r.get_data(as_text=True)[:100]))
tid4 = r.get_json().get('id')
r = cf.put('/api/torneos/%d' % tid4, json={'nombre': 'NoAllowed'})
check('pero NO puede editar ni borrar -> 403/404',
      cf.put('/api/torneos/%d' % tid4, json={'nombre': 'NoAllowed'}).status_code == 403
      and cf.delete('/api/torneos/%d' % tid4).status_code == 403, 'r=%s' % r.status_code)
# editar y borrar
c.put('/api/torneos/%d' % tid2, json={'nombre': 'Open Patagonia', 'estado': 'cerrado'})
t2 = [t for t in c.get('/api/torneos').get_json()['torneos'] if t['id'] == tid2][0]
check('editar torneo (nombre y estado)', t2['nombre'] == 'Open Patagonia' and t2['estado'] == 'cerrado',
      json.dumps(t2)[:150])
antes = sum(len(t['participantes_detalle']) for t in c.get('/api/torneos').get_json()['torneos'])
check('antes de borrar habia 5 participaciones cargadas', antes == 5, 'n=%s' % antes)
r = c.delete('/api/torneos/%d' % tid2)
check('admin borra un torneo', r.status_code == 200, 'r=%s' % r.status_code)
check('el torneo borrado ya no esta', len(c.get('/api/torneos').get_json()['torneos']) == 3,
      'n=%s' % len(c.get('/api/torneos').get_json()['torneos']))
despues = sum(len(t['participantes_detalle']) for t in c.get('/api/torneos').get_json()['torneos'])
check('al borrar el torneo se van sus participantes', despues == antes - 1,
      'antes=%s despues=%s' % (antes, despues))

# ===========================================================================
print('== TORNEOS: COMO LES FUE (posts de cualquiera) ==')
FOTO = ('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')
r = cf.post('/api/torneos/%d/posts' % tid1,
            json={'texto': 'Mi primer torneo, me re bien', 'estrellas': 5, 'medalla': 'oro'})
jp = r.get_json(silent=True) or {}
check('el alumno cuenta como le fue', r.status_code == 200 and jp.get('ok'), 'r=%s' % r.status_code)
check('si marco medalla queda anotado como participante', jp.get('anotado') is True, json.dumps(jp))
r = A.app.test_client()
c.post('/api/profesores', json={'nombre': 'Profe Post', 'username': 'profepost', 'password': '1234'})
login(r, 'profepost', '1234')
prof = r
r = r.post('/api/torneos/%d/posts' % tid1, json={'texto': 'Gran labor del grupo', 'estrellas': 4})
check('el profesor tambien puede contar como le fue', r.status_code == 200, 'r=%s' % r.status_code)
r = prof.post('/api/torneos/%d/posts' % tid1, json={'texto': ''})
check('post vacio se rechaza -> 400', r.status_code == 400, 'r=%s' % r.status_code)
r = prof.post('/api/torneos/999999/posts', json={'texto': 'hola'})
check('post en torneo inexistente -> 404', r.status_code == 404, 'r=%s' % r.status_code)
r = prof.post('/api/torneos/%d/posts' % tid1, json={'texto': 'foto mala', 'foto': 'data:text/html,<script>x</script>'})
check('foto que no es imagen se rechaza -> 400', r.status_code == 400, 'r=%s' % r.status_code)
post_ok = c.post('/api/torneos/%d/posts' % tid1,
                 json={'texto': 'con foto', 'foto': FOTO}).get_json()
tposts = [t for t in c.get('/api/torneos').get_json()['torneos'] if t['id'] == tid1][0]['posts']
check('los posts quedan listados en el torneo', len(tposts) == 3, 'n=%s' % len(tposts))
check('el post guarda la foto y las estrellas',
      any(p['imagen'] == FOTO for p in tposts) and any(p['estrellas'] == 5 for p in tposts),
      json.dumps([(p['id'], bool(p['imagen']), p['estrellas']) for p in tposts]))
r = prof.delete('/api/torneos/posts/%d' % post_ok['id'])
check('el profesor NO puede borrar el post de otro -> 403', r.status_code == 403, 'r=%s' % r.status_code)
r = c.delete('/api/torneos/posts/%d' % post_ok['id'])
check('el admin puede borrar cualquier post', r.status_code == 200, 'r=%s' % r.status_code)
r = cf.delete('/api/torneos/posts/%d' % jp['id'])
check('cada uno borra el suyo', r.status_code == 200, 'r=%s' % r.status_code)
# la medalla del post cuenta en el medallero
cf2.post('/api/torneos/%d/posts' % tid3, json={'texto': 'saque plata', 'medalla': 'plata'})
md = c.get('/api/torneos').get_json()['medallero']
check('el medallero suma la medalla del post del alumno', md['plata'] == 2, json.dumps(md))
check('y el alumno queda en el ranking con esa medalla',
      [x for x in c.get('/api/torneos').get_json()['ranking'] if x['id'] == alu[1]][0]['plata'] == 2,
      'el alumno ya tenia 1 plata de antes')

# ===========================================================================
print('== SITIO WEB (/web) ==')
PAGINAS = ['/web', '/web/profesores', '/web/horarios', '/web/contacto']
h_ini = h_pro = h_hor = h_con = ''
for u in PAGINAS:
    r = c2anon.get(u)
    h = r.get_data(as_text=True)
    check('sitio: %s responde 200 sin loguearse' % u, r.status_code == 200, 'r=%s' % r.status_code)
    if u == '/web':
        h_ini = h
    elif u == '/web/profesores':
        h_pro = h
    elif u == '/web/horarios':
        h_hor = h
    else:
        h_con = h

check('sitio: menu con las 4 secciones', all(x in h_ini for x in
      ['/web/profesores', '/web/horarios', '/web/contacto']), 'falta alguna seccion del menu')
check('sitio: css compartido cargado', '/static/web.css' in h_ini, 'falta web.css')
check('sitio: instagram correcto en inicio', 'instagram.com/ikigai_viedma' in h_ini, 'no esta el link nuevo')
check('sitio: direccion en contacto',
      'Tucum' in h_con and '149' in h_con and 'Viedma' in h_con, 'falta la direccion')
check('sitio: link de google maps', 'google.com/maps' in h_con, 'falta el link del mapa')
check('sitio: horarios cargados', '19:30' in h_hor and '18:00' in h_hor, 'faltan horarios')
check('sitio: profes en su pagina', 'Profesores' in h_pro or 'profesores' in h_pro, 'falta el listado')
if profes:
    check('sitio: aparece el profe en /web/profesores',
          profes[0]['nombre'] in h_pro, 'nombre=%s' % profes[0]['nombre'])
check('sitio: CTA a la app', '/app' in h_ini, 'falta el link a la app')
check('sitio: whatsapp oculto si no hay numero',
      'wa.me' not in h_con, 'whatsapp deberia estar oculto con WHATSAPP_NUMERO vacio')

print()
print('RESULTADO: %d OK, %d FAIL' % (len(PASS), len(FAIL)))
if FAIL:
    print('FALLARON:', FAIL)
    sys.exit(1)
