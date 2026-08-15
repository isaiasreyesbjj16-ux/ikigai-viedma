import os
import base64
import json
import secrets
from datetime import datetime, date, timedelta

from flask import Flask, request, jsonify, session, redirect, url_for, render_template, g, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

import dbadapter
from dbadapter import DB_MODE

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.db')
app.config['MAX_CONTENT_LENGTH'] = 250 * 1024 * 1024

BELTS_ADULT = ['Blanco', 'Azul', 'Púrpura', 'Marrón', 'Negro']
BELTS_KIDS = ['Gris', 'Amarillo', 'Naranja', 'Verde', 'Blanco']
CATEGORIAS = ['adulto', 'juveniles', 'kids']
TIPOS_CLASE = ['Gi', 'NoGi', 'Kids', 'Abierto']
METODOS_PAGO = ['Efectivo', 'Transferencia', 'Débito', 'Crédito', 'Otro']
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

VAPID_PRIVATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vapid_private.pem')
VAPID_PUBLIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vapid_public.pem')

# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------

def get_db():
    if 'db' not in g:
        if DB_MODE == 'mysql':
            db = dbadapter.connect_mysql()
            row = db.execute(
                "SELECT COUNT(*) AS c FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name IN ('settings','videos')").fetchone()
            if row['c'] < 2:
                db.close()
                init_db()
                db = dbadapter.connect_mysql()
        elif DB_MODE == 'postgres':
            db = dbadapter.connect_postgres()
            row = db.execute(
                "SELECT COUNT(*) AS c FROM information_schema.tables "
                "WHERE table_schema = current_schema() AND table_name IN ('settings','videos')").fetchone()
            if row['c'] < 2:
                db.close()
                init_db()
                db = dbadapter.connect_postgres()
        else:
            db = dbadapter.connect_sqlite(app.config['DATABASE'])
            row = db.execute(
                "SELECT COUNT(*) AS c FROM sqlite_master WHERE type='table' AND name IN ('settings','videos')").fetchone()
            if row['c'] < 2:
                db.close()
                init_db()
                db = dbadapter.connect_sqlite(app.config['DATABASE'])
        g.db = db
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    k VARCHAR(100) PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','profesor','alumno')),
    nombre TEXT NOT NULL,
    edad INTEGER,
    peso REAL,
    cinturon TEXT,
    categoria TEXT DEFAULT 'adulto',
    gi_pref TEXT DEFAULT 'Ambas',
    cuota_mensual REAL,
    activo INTEGER DEFAULT 1,
    creado TEXT
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dia INTEGER NOT NULL,
    hora TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'Gi',
    nivel TEXT DEFAULT 'Todos',
    profesor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    duracion INTEGER DEFAULT 60
);

CREATE TABLE IF NOT EXISTS pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alumno_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profesor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    monto REAL NOT NULL,
    mes INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    metodo TEXT DEFAULT 'Efectivo',
    concepto TEXT DEFAULT 'Cuota mensual',
    nota TEXT,
    fecha TEXT,
    registrado_por INTEGER
);

CREATE TABLE IF NOT EXISTS avisos_pago (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alumno_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    monto REAL,
    mes INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    nota TEXT,
    estado TEXT DEFAULT 'pendiente',
    fecha TEXT,
    confirmado_por INTEGER,
    confirmado_fecha TEXT
);

CREATE TABLE IF NOT EXISTS asistencia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clase_id INTEGER REFERENCES classes(id) ON DELETE CASCADE,
    alumno_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fecha VARCHAR(10) NOT NULL,
    presente INTEGER DEFAULT 1,
    UNIQUE(clase_id, alumno_id, fecha)
);

CREATE TABLE IF NOT EXISTS notificaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    titulo TEXT,
    mensaje TEXT,
    tipo TEXT DEFAULT 'info',
    leida INTEGER DEFAULT 0,
    fecha TEXT
);

CREATE TABLE IF NOT EXISTS push_subs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    endpoint TEXT UNIQUE,
    p256dh TEXT,
    auth TEXT
);

CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    descripcion TEXT DEFAULT '',
    belt TEXT DEFAULT 'Todos',
    url TEXT NOT NULL,
    tipo TEXT DEFAULT 'upload',
    subido_por INTEGER REFERENCES users(id) ON DELETE SET NULL,
    fecha TEXT
);

CREATE TABLE IF NOT EXISTS video_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fecha TEXT,
    UNIQUE(video_id, user_id)
);
"""


def init_db():
    if DB_MODE == 'postgres':
        db = dbadapter.connect_postgres()
    elif DB_MODE == 'mysql':
        db = dbadapter.connect_mysql()
    else:
        db = dbadapter.connect_sqlite(app.config['DATABASE'])
    db.executescript(SCHEMA)
    c = db.cursor()
    # migracion: agregar columnas nuevas si faltan
    if DB_MODE == 'postgres':
        cols = [r[0] for r in c.execute(
            "SELECT column_name AS name FROM information_schema.columns "
            "WHERE table_schema=current_schema() AND table_name='users'").fetchall()]
    elif DB_MODE == 'mysql':
        cols = [r[0] for r in c.execute('SHOW COLUMNS FROM users').fetchall()]
    else:
        cols = [r[1] for r in c.execute('PRAGMA table_info(users)').fetchall()]
    if 'foto' not in cols:
        c.execute('ALTER TABLE users ADD COLUMN foto TEXT')
    defaults = {
        'academy_name': 'IKIGAI VIEDMA',
        'academy_code': 'BJJ2026',
        'default_cuota': '15000',
        'due_day': '10',
        'academy_color': '#e05d13',
    }
    for k, v in defaults.items():
        c.execute('INSERT OR IGNORE INTO settings(k, value) VALUES(?,?)', (k, v))
    # admin por defecto
    row = c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
    if not row:
        c.execute(
            "INSERT INTO users(username, password_hash, role, nombre) VALUES(?,?,?,?)",
            ('admin', generate_password_hash('admin123'), 'admin', 'Administrador'))
        print('=' * 60)
        print('  ADMIN CREADO ->  usuario: admin   contrasena: admin123')
        print('  CAMBIA LA CONTRASENA EN MI PERFIL cuando puedas.')
        print('=' * 60)
    db.commit()
    db.close()


def get_setting(key, default=None):
    row = get_db().execute('SELECT value FROM settings WHERE k=?', (key,)).fetchone()
    return row['value'] if row else default


def set_setting(key, value):
    get_db().execute(
        'INSERT OR REPLACE INTO settings(k, value) VALUES(?,?)',
        (key, str(value)))
    get_db().commit()


# ---------------------------------------------------------------------------
# VAPID keys para push
# ---------------------------------------------------------------------------

def ensure_vapid():
    """Claves VAPID persistentes en la BD (Render pierde archivos al redeployar)."""
    from py_vapid import Vapid
    priv = get_setting('vapid_private')
    pub = get_setting('vapid_public')
    if not (priv and pub):
        v = Vapid()
        v.generate_keys()
        priv = v.private_pem().decode()
        pub = v.public_pem().decode()
        set_setting('vapid_private', priv)
        set_setting('vapid_public', pub)
    # escribe archivos locales para pywebpush y compatibilidad
    for path, pem in ((VAPID_PRIVATE, priv), (VAPID_PUBLIC, pub)):
        try:
            with open(path, 'w') as f:
                f.write(pem)
        except OSError:
            pass
    pem = pub.replace('-----BEGIN PUBLIC KEY-----', '').replace('-----END PUBLIC KEY-----', '').strip()
    try:
        return base64.urlsafe_b64encode(base64.b64decode(pem)).rstrip(b'=').decode()
    except Exception:
        return pem


def send_push(user_id, titulo, mensaje, extra=None):
    """Envia notificacion push a todas las suscripciones del usuario."""
    ensure_vapid()
    if not os.path.exists(VAPID_PRIVATE):
        return
    from pywebpush import webpush, WebPushException
    subs = get_db().execute('SELECT endpoint, p256dh, auth FROM push_subs WHERE user_id=?',
                            (user_id,)).fetchall()
    payload = json.dumps({'title': titulo, 'body': mensaje, **(extra or {})})
    for s in subs:
        try:
            webpush(
                subscription_info={
                    'endpoint': s['endpoint'],
                    'keys': {'p256dh': s['p256dh'], 'auth': s['auth']}},
                data=payload,
                vapid_private_key=VAPID_PRIVATE,
                vapid_claims={'sub': 'mailto:admin@academia.local'})
        except WebPushException:
            pass
        except Exception:
            pass


def notify(user_id, titulo, mensaje, tipo='info', push=True):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    get_db().execute(
        'INSERT INTO notificaciones(user_id, titulo, mensaje, tipo, fecha) VALUES(?,?,?,?,?)',
        (user_id, titulo, mensaje, tipo, now))
    get_db().commit()
    if push:
        send_push(user_id, titulo, mensaje)


# ---------------------------------------------------------------------------
# Utilidades de sesion / auth
# ---------------------------------------------------------------------------

def current_user():
    if 'user_id' not in session:
        return None
    return get_db().execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()


def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def deco(f):
        from functools import wraps
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'No autorizado'}), 401
            u = current_user()
            if u['role'] not in roles:
                return jsonify({'error': 'Sin permisos'}), 403
            return f(*args, **kwargs)
        return wrapper
    return deco


def parse_json():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def user_public(u):
    return {
        'id': u['id'],
        'username': u['username'],
        'role': u['role'],
        'nombre': u['nombre'],
        'edad': u['edad'],
        'peso': u['peso'],
        'cinturon': u['cinturon'],
        'categoria': u['categoria'],
        'gi_pref': u['gi_pref'],
        'cuota_mensual': u['cuota_mensual'],
        'foto': u['foto'] if 'foto' in u.keys() else None,
        'activo': u['activo'],
        'creado': u['creado'],
    }


def cuota_status(alumno):
    """Estado de la cuota del alumno en el mes actual."""
    hoy = date.today()
    pago = get_db().execute(
        'SELECT * FROM pagos WHERE alumno_id=? AND mes=? AND anio=? ORDER BY id DESC LIMIT 1',
        (alumno['id'], hoy.month, hoy.year)).fetchone()
    due_day = to_int(get_setting('due_day', '10')) or 10
    estado = 'al_dia' if pago else 'deuda'
    if not pago and hoy.day <= due_day:
        estado = 'por_vencer'
    cuota = alumno['cuota_mensual']
    return {
        'mes': hoy.month,
        'anio': hoy.year,
        'estado': estado,
        'pago': dict(pago) if pago else None,
        'cuota': cuota,
        'due_day': due_day,
    }


def dias_deuda(alumno):
    hoy = date.today()
    pago = get_db().execute(
        'SELECT fecha FROM pagos WHERE alumno_id=? ORDER BY fecha DESC LIMIT 1',
        (alumno['id'],)).fetchone()
    if pago and pago['fecha']:
        try:
            last = datetime.strptime(pago['fecha'][:10], '%Y-%m-%d').date()
            return (hoy - last).days
        except Exception:
            pass
    # si nunca pago
    creado = alumno['creado']
    if creado:
        try:
            last = datetime.strptime(creado[:10], '%Y-%m-%d').date()
            return (hoy - last).days
        except Exception:
            pass
    return 0


# ---------------------------------------------------------------------------
# Paginas
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('app_page'))
    return render_template('login.html', academy_name=get_setting('academy_name'))


@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')


@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')


@app.route('/app')
def app_page():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    u = current_user()
    return render_template('dashboard.html', user=user_public(u), belts_adult=BELTS_ADULT,
                           belts_kids=BELTS_KIDS, categorias=CATEGORIAS,
                           tipos_clase=TIPOS_CLASE, metodos=METODOS_PAGO,
                           dias=DIAS, academy_name=get_setting('academy_name'))


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/') or request.path.startswith('/static/'):
        return jsonify({'error': 'No encontrado'}), 404
    return redirect(url_for('index'))


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', message='Error del servidor. Revisá que el archivo data.db no esté bloqueado o roto.'), 500


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.route('/api/login', methods=['POST'])
def api_login():
    data = parse_json()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    u = get_db().execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    if not u or not check_password_hash(u['password_hash'], password):
        return jsonify({'error': 'Usuario o contrasena incorrectos'}), 401
    if not u['activo']:
        return jsonify({'error': 'Tu cuenta esta desactivada. Contacta al administrador.'}), 403
    session.clear()
    session['user_id'] = u['id']
    return jsonify({'ok': True, 'user': user_public(u)})


@app.route('/api/register', methods=['POST'])
def api_register():
    data = parse_json()
    role = data.get('role')
    if role not in ('alumno', 'profesor'):
        return jsonify({'error': 'Rol invalido'}), 400
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    nombre = (data.get('nombre') or '').strip()
    if not username or not password or not nombre:
        return jsonify({'error': 'Completa usuario, contrasena y nombre'}), 400
    if len(password) < 4:
        return jsonify({'error': 'La contrasena debe tener al menos 4 caracteres'}), 400
    if get_db().execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
        return jsonify({'error': 'Ese usuario ya existe'}), 400

    if role == 'profesor':
        codigo = (data.get('codigo') or '').strip()
        if codigo != get_setting('academy_code'):
            return jsonify({'error': 'Codigo de academia incorrecto. Pedile el codigo al administrador.'}), 400

    try:
        get_db().execute(
            """INSERT INTO users(username, password_hash, role, nombre, edad, peso, cinturon, categoria, gi_pref, cuota_mensual, creado)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (username, generate_password_hash(password), role, nombre,
             to_int(data.get('edad')), to_float(data.get('peso')),
             data.get('cinturon'), data.get('categoria') or 'adulto',
             data.get('gi_pref') or 'Ambas',
             to_float(data.get('cuota_mensual')) if role == 'alumno' else None,
             datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        get_db().commit()
    except dbadapter.IntegrityError:
        return jsonify({'error': 'Ese usuario ya existe'}), 400

    new_id = get_db().execute('SELECT last_insert_rowid() AS id').fetchone()['id']
    if role == 'alumno' and not data.get('cuota_mensual'):
        cuota = to_float(get_setting('default_cuota', '15000')) or 15000
        get_db().execute('UPDATE users SET cuota_mensual=? WHERE id=?', (cuota, new_id))
        get_db().commit()
    notify(1, 'Nuevo registro', f'Se registro un nuevo {role}: {nombre}')
    session.clear()
    session['user_id'] = new_id
    return jsonify({'ok': True, 'user': user_public(
        get_db().execute('SELECT * FROM users WHERE id=?', (new_id,)).fetchone())})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/me')
@login_required
def api_me():
    u = current_user()
    d = user_public(u)
    if u['role'] == 'alumno':
        d['cuota'] = cuota_status(u)
    d['pago_link'] = get_setting('pago_link', '')
    d['pago_alias'] = get_setting('pago_alias', '')
    return jsonify(d)


# ---------------------------------------------------------------------------
# Horarios
# ---------------------------------------------------------------------------

@app.route('/api/horarios')
@login_required
def api_horarios():
    u = current_user()
    rows = get_db().execute(
        """SELECT c.*, u.nombre AS profesor_nombre
           FROM classes c LEFT JOIN users u ON u.id=c.profesor_id
           ORDER BY c.dia, c.hora""").fetchall()
    horarios = []
    for r in rows:
        horarios.append({
            'id': r['id'], 'dia': r['dia'], 'dia_nombre': DIAS[r['dia']],
            'hora': r['hora'], 'tipo': r['tipo'], 'nivel': r['nivel'],
            'duracion': r['duracion'], 'profesor_id': r['profesor_id'],
            'profesor_nombre': r['profesor_nombre']})
    return jsonify({'horarios': horarios})


@app.route('/api/horarios', methods=['POST'])
@role_required('admin', 'profesor')
def api_horarios_create():
    data = parse_json()
    dia = to_int(data.get('dia'))
    hora = (data.get('hora') or '').strip()
    tipo = data.get('tipo') or 'Gi'
    if dia is None or dia not in range(7) or not hora:
        return jsonify({'error': 'Dia u hora invalidos'}), 400
    prof = to_int(data.get('profesor_id'))
    get_db().execute(
        'INSERT INTO classes(dia, hora, tipo, nivel, profesor_id, duracion) VALUES(?,?,?,?,?,?)',
        (dia, hora, tipo, data.get('nivel') or 'Todos', prof, to_int(data.get('duracion')) or 60))
    get_db().commit()
    return jsonify({'ok': True})


@app.route('/api/horarios/<int:cid>', methods=['PUT'])
@role_required('admin', 'profesor')
def api_horarios_update(cid):
    data = parse_json()
    dia = to_int(data.get('dia'))
    hora = (data.get('hora') or '').strip()
    if dia is None or dia not in range(7) or not hora:
        return jsonify({'error': 'Dia u hora invalidos'}), 400
    get_db().execute(
        'UPDATE classes SET dia=?, hora=?, tipo=?, nivel=?, profesor_id=?, duracion=? WHERE id=?',
        (dia, hora, data.get('tipo') or 'Gi', data.get('nivel') or 'Todos',
         to_int(data.get('profesor_id')), to_int(data.get('duracion')) or 60, cid))
    get_db().commit()
    return jsonify({'ok': True})


@app.route('/api/horarios/<int:cid>', methods=['DELETE'])
@role_required('admin')
def api_horarios_delete(cid):
    get_db().execute('DELETE FROM classes WHERE id=?', (cid,))
    get_db().commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Alumnos (admin / profesor)
# ---------------------------------------------------------------------------

@app.route('/api/alumnos')
@role_required('admin', 'profesor')
def api_alumnos():
    rows = get_db().execute(
        """SELECT u.*,
            (SELECT COUNT(*) FROM asistencia a WHERE a.alumno_id=u.id AND a.presente=1) AS asistencias,
            (SELECT COUNT(*) FROM pagos p WHERE p.alumno_id=u.id) AS pagos_totales
           FROM users u WHERE u.role='alumno' ORDER BY u.nombre""").fetchall()
    alumnos = []
    for r in rows:
        d = user_public(r)
        d['asistencias'] = r['asistencias']
        d['pagos_totales'] = r['pagos_totales']
        d['cuota'] = cuota_status(r)
        d['dias_deuda'] = dias_deuda(r)
        alumnos.append(d)
    return jsonify({'alumnos': alumnos})


@app.route('/api/alumnos', methods=['POST'])
@role_required('admin', 'profesor')
def api_alumnos_create():
    data = parse_json()
    nombre = (data.get('nombre') or '').strip()
    if not nombre:
        return jsonify({'error': 'El nombre es obligatorio'}), 400
    username = (data.get('username') or '').strip() or f"alumno{secrets.token_hex(3)}"
    if get_db().execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
        return jsonify({'error': 'Ese usuario ya existe'}), 400
    password = data.get('password') or 'alumno123'
    cuota = to_float(data.get('cuota_mensual'))
    get_db().execute(
        """INSERT INTO users(username, password_hash, role, nombre, edad, peso, cinturon, categoria, gi_pref, cuota_mensual, creado)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (username, generate_password_hash(password), 'alumno', nombre,
         to_int(data.get('edad')), to_float(data.get('peso')),
         data.get('cinturon'), data.get('categoria') or 'adulto',
         data.get('gi_pref') or 'Ambas', cuota,
         datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    get_db().commit()
    new_id = get_db().execute('SELECT last_insert_rowid() AS id').fetchone()['id']
    return jsonify({'ok': True, 'id': new_id, 'username': username, 'password': password})


@app.route('/api/alumnos/<int:uid>', methods=['PUT'])
@role_required('admin', 'profesor')
def api_alumnos_update(uid):
    data = parse_json()
    u = get_db().execute('SELECT * FROM users WHERE id=? AND role="alumno"', (uid,)).fetchone()
    if not u:
        return jsonify({'error': 'Alumno no encontrado'}), 404
    get_db().execute(
        """UPDATE users SET nombre=?, edad=?, peso=?, cinturon=?, categoria=?, gi_pref=?, activo=? WHERE id=?""",
        ((data.get('nombre') or u['nombre']), to_int(data.get('edad', u['edad'])),
         to_float(data.get('peso', u['peso'])), data.get('cinturon', u['cinturon']),
         data.get('categoria', u['categoria']), data.get('gi_pref', u['gi_pref']),
         1 if data.get('activo', u['activo']) else 0, uid))
    get_db().commit()
    return jsonify({'ok': True})


@app.route('/api/alumnos/<int:uid>', methods=['DELETE'])
@role_required('admin', 'profesor')
def api_alumnos_delete(uid):
    get_db().execute('DELETE FROM users WHERE id=? AND role="alumno"', (uid,))
    get_db().commit()
    return jsonify({'ok': True})


@app.route('/api/alumnos/<int:uid>/cuota', methods=['PUT'])
@role_required('admin', 'profesor')
def api_alumnos_cuota(uid):
    data = parse_json()
    cuota = to_float(data.get('cuota_mensual'))
    if not cuota or cuota <= 0:
        return jsonify({'error': 'Monto de cuota invalido'}), 400
    u = get_db().execute('SELECT * FROM users WHERE id=? AND role="alumno"', (uid,)).fetchone()
    if not u:
        return jsonify({'error': 'Alumno no encontrado'}), 404
    get_db().execute('UPDATE users SET cuota_mensual=? WHERE id=?', (cuota, uid))
    get_db().commit()
    who = current_user()['nombre']
    notify(uid, 'Tu cuota cambio',
           f'{who} actualizo tu cuota mensual a ${cuota:,.0f}'.replace(',', '.'), 'cuota')
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Profesores
# ---------------------------------------------------------------------------

@app.route('/api/profesores')
@role_required('admin', 'profesor')
def api_profesores():
    rows = get_db().execute(
        """SELECT u.*,
            (SELECT COUNT(*) FROM classes c WHERE c.profesor_id=u.id) AS clases
           FROM users u WHERE u.role='profesor' ORDER BY u.nombre""").fetchall()
    return jsonify({'profesores': [dict(user_public(r), **{'clases': r['clases']}) for r in rows]})


@app.route('/api/profesores', methods=['POST'])
@role_required('admin')
def api_profesores_create():
    data = parse_json()
    nombre = (data.get('nombre') or '').strip()
    if not nombre:
        return jsonify({'error': 'El nombre es obligatorio'}), 400
    username = (data.get('username') or '').strip() or f"profe{secrets.token_hex(3)}"
    if get_db().execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
        return jsonify({'error': 'Ese usuario ya existe'}), 400
    password = data.get('password') or 'profe123'
    get_db().execute(
        """INSERT INTO users(username, password_hash, role, nombre, edad, peso, cinturon, categoria, gi_pref, creado)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (username, generate_password_hash(password), 'profesor', nombre,
         to_int(data.get('edad')), to_float(data.get('peso')),
         data.get('cinturon'), data.get('categoria') or 'adulto',
         data.get('gi_pref') or 'Ambas',
         datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    get_db().commit()
    new_id = get_db().execute('SELECT last_insert_rowid() AS id').fetchone()['id']
    return jsonify({'ok': True, 'id': new_id, 'username': username, 'password': password})


@app.route('/api/profesores/<int:uid>', methods=['DELETE'])
@role_required('admin')
def api_profesores_delete(uid):
    u = get_db().execute('SELECT * FROM users WHERE id=? AND role="profesor"', (uid,)).fetchone()
    if not u:
        return jsonify({'error': 'Profesor no encontrado'}), 404
    admin = get_db().execute('SELECT id FROM users WHERE role="admin" LIMIT 1').fetchone()
    # quita las clases del profesor
    get_db().execute('UPDATE classes SET profesor_id=NULL WHERE profesor_id=?', (uid,))
    # conserva pagos: profesor_id queda con SET NULL
    get_db().execute('DELETE FROM users WHERE id=?', (uid,))
    get_db().commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Pagos
# ---------------------------------------------------------------------------

@app.route('/api/pagos', methods=['GET'])
@role_required('admin', 'profesor')
def api_pagos():
    u = current_user()
    q = """SELECT p.*, al.nombre AS alumno_nombre, pr.nombre AS profesor_nombre
           FROM pagos p
           JOIN users al ON al.id=p.alumno_id
           LEFT JOIN users pr ON pr.id=p.profesor_id"""
    params = []
    if u['role'] == 'profesor':
        q += ' WHERE p.profesor_id=?'
        params.append(u['id'])
    q += ' ORDER BY p.id DESC LIMIT 500'
    rows = get_db().execute(q, params).fetchall()
    pagos = []
    for r in rows:
        pagos.append({
            'id': r['id'], 'alumno_id': r['alumno_id'], 'alumno_nombre': r['alumno_nombre'],
            'profesor_id': r['profesor_id'], 'profesor_nombre': r['profesor_nombre'],
            'monto': r['monto'], 'mes': r['mes'], 'anio': r['anio'],
            'metodo': r['metodo'], 'concepto': r['concepto'], 'nota': r['nota'],
            'fecha': r['fecha']})
    return jsonify({'pagos': pagos})


@app.route('/api/pagos', methods=['POST'])
@role_required('admin', 'profesor')
def api_pagos_create():
    data = parse_json()
    alumno_id = to_int(data.get('alumno_id'))
    profesor_id = to_int(data.get('profesor_id'))
    monto = to_float(data.get('monto'))
    mes = to_int(data.get('mes')) or date.today().month
    anio = to_int(data.get('anio')) or date.today().year
    if not alumno_id or not monto or monto <= 0:
        return jsonify({'error': 'Alumno y monto son obligatorios'}), 400
    if profesor_id == -1 or (profesor_id is None and (data.get('profesor_id') == -1)):
        profesor_id = None
    get_db().execute(
        """INSERT INTO pagos(alumno_id, profesor_id, monto, mes, anio, metodo, concepto, nota, fecha, registrado_por)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (alumno_id, profesor_id, monto, mes, anio,
         data.get('metodo') or 'Efectivo', data.get('concepto') or 'Cuota mensual',
         data.get('nota'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
         current_user()['id']))
    get_db().commit()
    alumno = get_db().execute('SELECT * FROM users WHERE id=?', (alumno_id,)).fetchone()
    who = current_user()
    # notificaciones: al alumno
    notify(alumno_id, 'Pago registrado',
           f'Tu pago de ${monto:,.0f} por {mes}/{anio} fue registrado por {who["nombre"]}.'.replace(',', '.'),
           'pago')
    # al profesor que recibio el pago
    if profesor_id and profesor_id != who['id']:
        profe = get_db().execute('SELECT * FROM users WHERE id=?', (profesor_id,)).fetchone()
        if profe:
            notify(profesor_id, 'Recibiste un pago',
                   f'{alumno["nombre"]} te pago ${monto:,.0f} ({data.get("metodo") or "Efectivo"}).'.replace(',', '.'),
                   'pago')
    # a los admins (si no es el que registro)
    admins = get_db().execute('SELECT id FROM users WHERE role="admin"').fetchall()
    for a in admins:
        if a['id'] != who['id']:
            notify(a['id'], 'Nuevo pago registrado',
                   f'{alumno["nombre"]} pago ${monto:,.0f} registrado por {who["nombre"]}.'.replace(',', '.'),
                   'pago')
    return jsonify({'ok': True})


@app.route('/api/pagos/<int:pid>', methods=['DELETE'])
@role_required('admin')
def api_pagos_delete(pid):
    get_db().execute('DELETE FROM pagos WHERE id=?', (pid,))
    get_db().commit()
    return jsonify({'ok': True})


@app.route('/api/deudores')
@role_required('admin', 'profesor')
def api_deudores():
    rows = get_db().execute(
        "SELECT * FROM users WHERE role='alumno' AND activo=1 ORDER BY nombre").fetchall()
    deudores = []
    for r in rows:
        st = cuota_status(r)
        if st['estado'] in ('deuda', 'por_vencer'):
            deudores.append({
                **user_public(r),
                'estado': st['estado'],
                'cuota': st['cuota'],
                'dias_deuda': dias_deuda(r),
            })
    return jsonify({'deudores': deudores})


@app.route('/api/notify_deuda', methods=['POST'])
@role_required('admin', 'profesor')
def api_notify_deuda():
    data = parse_json()
    alumno_id = to_int(data.get('alumno_id'))
    if alumno_id:
        ids = [alumno_id]
    else:
        rows = get_db().execute("SELECT id FROM users WHERE role='alumno' AND activo=1").fetchall()
        ids = [r['id'] for r in rows if cuota_status(r)['estado'] in ('deuda', 'por_vencer')]
    who = current_user()['nombre']
    for aid in ids:
        alumno = get_db().execute('SELECT * FROM users WHERE id=?', (aid,)).fetchone()
        if not alumno:
            continue
        st = cuota_status(alumno)
        notify(aid, 'Recordatorio de deuda',
               f'{who} te recuerda que tu cuota de {st["mes"]}/{st["anio"]} ({st["cuota"]:,.0f} pesos) esta pendiente.'.replace(',', '.'),
               'deuda')
    return jsonify({'ok': True, 'avisados': len(ids)})


# ---------------------------------------------------------------------------
# Asistencia
# ---------------------------------------------------------------------------

@app.route('/api/asistencia', methods=['POST'])
@role_required('admin', 'profesor')
def api_asistencia_marcar():
    data = parse_json()
    clase_id = to_int(data.get('clase_id'))
    fecha = (data.get('fecha') or date.today().strftime('%Y-%m-%d'))
    presentes = data.get('presentes') or []
    if not clase_id:
        return jsonify({'error': 'Selecciona una clase'}), 400
    # borra asistencia existente de ese dia/clase para re-marcar
    get_db().execute('DELETE FROM asistencia WHERE clase_id=? AND fecha=?', (clase_id, fecha))
    for pid in presentes:
        get_db().execute(
            'INSERT OR IGNORE INTO asistencia(clase_id, alumno_id, fecha, presente) VALUES(?,?,?,1)',
            (clase_id, to_int(pid), fecha))
    get_db().commit()
    return jsonify({'ok': True})


@app.route('/api/asistencia_dia', methods=['GET'])
@role_required('admin', 'profesor')
def api_asistencia_dia():
    clase_id = to_int(request.args.get('clase_id'))
    fecha = request.args.get('fecha') or date.today().strftime('%Y-%m-%d')
    rows = get_db().execute('SELECT alumno_id FROM asistencia WHERE clase_id=? AND fecha=? AND presente=1',
                            (clase_id, fecha)).fetchall()
    return jsonify({'presentes': [r['alumno_id'] for r in rows]})


@app.route('/api/mi_asistencia')
@role_required('alumno')
def api_mi_asistencia():
    u = current_user()
    rows = get_db().execute(
        """SELECT a.fecha, c.tipo, c.hora, c.dia, u.nombre AS profesor
           FROM asistencia a JOIN classes c ON c.id=a.clase_id
           LEFT JOIN users u ON u.id=c.profesor_id
           WHERE a.alumno_id=? AND a.presente=1 ORDER BY a.fecha DESC""",
        (u['id'],)).fetchall()
    asis = [{'fecha': r['fecha'], 'tipo': r['tipo'], 'hora': r['hora'],
             'dia': DIAS[r['dia']], 'profesor': r['profesor']} for r in rows]
    total = get_db().execute(
        'SELECT COUNT(*) AS n FROM asistencia WHERE alumno_id=? AND presente=1', (u['id'],)).fetchone()['n']
    return jsonify({'asistencia': asis, 'total': total})


@app.route('/api/historial_asistencia')
@role_required('admin', 'profesor')
def api_historial_asistencia():
    u = current_user()
    q = """SELECT a.id, a.fecha, a.clase_id, c.tipo, c.hora, al.nombre AS alumno
           FROM asistencia a JOIN classes c ON c.id=a.clase_id
           JOIN users al ON al.id=a.alumno_id"""
    params = []
    if u['role'] == 'profesor':
        q += ' WHERE c.profesor_id=?'
        params.append(u['id'])
    q += ' ORDER BY a.id DESC LIMIT 300'
    rows = get_db().execute(q, params).fetchall()
    return jsonify({'asistencia': [dict(r) for r in rows]})


# ---------------------------------------------------------------------------
# Perfil / alumno
# ---------------------------------------------------------------------------

@app.route('/api/mis_pagos')
@login_required
def api_mis_pagos():
    u = current_user()
    rows = get_db().execute(
        """SELECT p.*, pr.nombre AS profesor_nombre FROM pagos p
           LEFT JOIN users pr ON pr.id=p.profesor_id
           WHERE p.alumno_id=? ORDER BY p.id DESC LIMIT 100""", (u['id'],)).fetchall()
    aviso = get_db().execute(
        "SELECT * FROM avisos_pago WHERE alumno_id=? AND estado='pendiente' ORDER BY id DESC LIMIT 1",
        (u['id'],)).fetchone()
    return jsonify({'pagos': [dict(r) for r in rows],
                    'aviso_pendiente': dict(aviso) if aviso else None})


@app.route('/api/avisar_pago', methods=['POST'])
@login_required
def api_avisar_pago():
    u = current_user()
    data = parse_json()
    hoy = date.today()
    mes = to_int(data.get('mes')) or hoy.month
    anio = to_int(data.get('anio')) or hoy.year
    ex = get_db().execute(
        "SELECT * FROM avisos_pago WHERE alumno_id=? AND mes=? AND anio=? AND estado='pendiente'",
        (u['id'], mes, anio)).fetchone()
    if ex:
        return jsonify({'error': 'Ya enviaste un aviso para este mes. Esperá la confirmación.'}), 400
    monto = to_float(data.get('monto'))
    if not monto:
        monto = to_float(u['cuota_mensual']) or 0
    get_db().execute(
        'INSERT INTO avisos_pago(alumno_id, monto, mes, anio, nota, estado, fecha) VALUES(?,?,?,?,?,?,?)',
        (u['id'], monto, mes, anio, data.get('nota') or 'Cuota mensual', 'pendiente',
         datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    get_db().commit()
    staff = get_db().execute(
        "SELECT id FROM users WHERE role IN ('admin','profesor') AND activo=1").fetchall()
    for s in staff:
        notify(s['id'], 'Aviso de pago',
               f'{u["nombre"]} avisó que pagó la cuota de {mes}/{anio}. Confirmá el pago.',
               'pago')
    return jsonify({'ok': True})


@app.route('/api/avisos_pago')
@role_required('admin', 'profesor')
def api_avisos_pago():
    rows = get_db().execute(
        """SELECT a.*, u.nombre AS alumno_nombre
           FROM avisos_pago a JOIN users u ON u.id=a.alumno_id
           ORDER BY a.estado, a.id DESC LIMIT 300""").fetchall()
    return jsonify({'avisos': [dict(r) for r in rows]})


@app.route('/api/avisos_pago/<int:aid>/confirmar', methods=['POST'])
@role_required('admin', 'profesor')
def api_avisos_confirmar(aid):
    a = get_db().execute('SELECT * FROM avisos_pago WHERE id=?', (aid,)).fetchone()
    if not a:
        return jsonify({'error': 'Aviso no encontrado'}), 404
    if a['estado'] == 'confirmado':
        return jsonify({'error': 'Este aviso ya fue confirmado'}), 400
    who = current_user()
    get_db().execute(
        'INSERT INTO pagos(alumno_id, profesor_id, monto, mes, anio, metodo, concepto, nota, fecha, registrado_por) VALUES(?,?,?,?,?,?,?,?,?,?)',
        (a['alumno_id'], None, a['monto'] or 0, a['mes'], a['anio'], 'Aviso', 'Cuota mensual',
         'Confirmado desde aviso de pago', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), who['id']))
    get_db().execute(
        "UPDATE avisos_pago SET estado='confirmado', confirmado_por=?, confirmado_fecha=? WHERE id=?",
        (who['id'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), aid))
    get_db().commit()
    alumno = get_db().execute('SELECT * FROM users WHERE id=?', (a['alumno_id'],)).fetchone()
    notify(a['alumno_id'], 'Pago confirmado',
           f'Tu aviso de pago de la cuota {a["mes"]}/{a["anio"]} fue confirmado por {who["nombre"]}.',
           'pago')
    return jsonify({'ok': True})


@app.route('/api/avisos_pago/<int:aid>', methods=['DELETE'])
@role_required('admin')
def api_avisos_delete(aid):
    a = get_db().execute('SELECT * FROM avisos_pago WHERE id=?', (aid,)).fetchone()
    if not a:
        return jsonify({'error': 'Aviso no encontrado'}), 404
    get_db().execute('DELETE FROM avisos_pago WHERE id=?', (aid,))
    get_db().commit()
    return jsonify({'ok': True})


@app.route('/api/perfil', methods=['PUT'])
@login_required
def api_perfil_update():
    u = current_user()
    data = parse_json()
    get_db().execute(
        'UPDATE users SET nombre=?, edad=?, peso=?, cinturon=?, categoria=?, gi_pref=? WHERE id=?',
        ((data.get('nombre') or u['nombre']), to_int(data.get('edad', u['edad'])),
         to_float(data.get('peso', u['peso'])), data.get('cinturon', u['cinturon']),
         data.get('categoria', u['categoria']), data.get('gi_pref', u['gi_pref']), u['id']))
    if data.get('password'):
        if len(data['password']) < 4:
            return jsonify({'error': 'La contrasena debe tener al menos 4 caracteres'}), 400
        get_db().execute('UPDATE users SET password_hash=? WHERE id=?',
                         (generate_password_hash(data['password']), u['id']))
    get_db().commit()
    return jsonify({'ok': True})


@app.route('/api/foto', methods=['POST'])
@login_required
def api_foto():
    data = parse_json()
    b64 = data.get('foto') or ''
    if ',' not in b64:
        return jsonify({'error': 'No hay imagen'}), 400
    try:
        img_bytes = base64.b64decode(b64.split(',', 1)[1])
    except Exception:
        return jsonify({'error': 'Imagen invalida'}), 400
    if len(img_bytes) > 5 * 1024 * 1024:
        return jsonify({'error': 'Imagen muy grande (max 5MB)'}), 400
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(img_bytes))
        img.load()
        img = img.convert('RGB')
        img.thumbnail((400, 400))
    except Exception:
        return jsonify({'error': 'Formato de imagen invalido (usa JPG o PNG)'}), 400
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    uid = current_user()['id']
    img.save(os.path.join(upload_dir, 'user%d.jpg' % uid), 'JPEG', quality=85)
    url = '/static/uploads/user%d.jpg' % uid
    get_db().execute('UPDATE users SET foto=? WHERE id=?', (url, uid))
    get_db().commit()
    return jsonify({'ok': True, 'foto': url})


# ---------------------------------------------------------------------------
# VIDEOS por cinturón (profesor sube, marca quién los vio)
# ---------------------------------------------------------------------------

def _video_public(v, u):
    d = get_db()
    vistas = d.execute(
        'SELECT COUNT(*) AS n FROM video_views WHERE video_id=?', (v['id'],)).fetchone()['n']
    visto = bool(d.execute(
        'SELECT 1 FROM video_views WHERE video_id=? AND user_id=?',
        (v['id'], u['id'])).fetchone())
    return {
        'id': v['id'], 'titulo': v['titulo'], 'descripcion': v['descripcion'],
        'belt': v['belt'], 'url': v['url'], 'tipo': v['tipo'],
        'subido_por': v['subido_por'], 'fecha': v['fecha'],
        'subidor_nombre': v['subidor_nombre'], 'vistas': vistas, 'visto': visto,
    }


def _list_videos(u, belt=None):
    db = get_db()
    q = ('SELECT v.*, s.nombre AS subidor_nombre FROM videos v '
         'LEFT JOIN users s ON s.id = v.subido_por ')
    args = []
    where = []
    if u['role'] == 'alumno':
        where.append("(v.belt = 'Todos' OR v.belt = ?)")
        args.append(u['cinturon'])
    elif belt and belt != 'Todos':
        where.append('v.belt = ?')
        args.append(belt)
    if where:
        q += ' WHERE ' + ' AND '.join(where)
    q += ' ORDER BY v.id DESC'
    rows = db.execute(q, args).fetchall()
    return [_video_public(r, u) for r in rows]


@app.route('/api/videos')
@login_required
def api_videos_list():
    u = current_user()
    return jsonify({'videos': _list_videos(u, request.args.get('belt'))})


@app.route('/api/videos', methods=['POST'])
@role_required('admin', 'profesor')
def api_videos_create():
    u = current_user()
    data = parse_json()
    titulo = (data.get('titulo') or '').strip()
    if not titulo:
        return jsonify({'error': 'El título es obligatorio'}), 400
    url = (data.get('url') or '').strip()
    if not url:
        return jsonify({'error': 'Falta el link o el video'}), 400
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    db = get_db()
    cur = db.execute(
        'INSERT INTO videos(titulo, descripcion, belt, url, tipo, subido_por, fecha) VALUES(?,?,?,?,?,?,?)',
        (titulo, (data.get('descripcion') or '').strip(), (data.get('belt') or 'Todos'),
         url, 'link', u['id'], now))
    db.commit()
    return jsonify({'ok': True, 'id': cur.lastrowid})


@app.route('/api/videos/upload', methods=['POST'])
@role_required('admin', 'profesor')
def api_videos_upload():
    u = current_user()
    f = request.files.get('video')
    if not f or not f.filename:
        return jsonify({'error': 'Elegí un archivo de video'}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ('.mp4', '.webm', '.ogg', '.mov'):
        return jsonify({'error': 'Formato no permitido (usa MP4, WebM o MOV)'}), 400
    titulo = (request.form.get('titulo') or '').strip() or os.path.splitext(f.filename)[0]
    belt = (request.form.get('belt') or 'Todos').strip()
    desc = (request.form.get('descripcion') or '').strip()
    video_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'videos')
    os.makedirs(video_dir, exist_ok=True)
    name = 'v%d_%d%s' % (u['id'], int(datetime.now().timestamp()), ext)
    f.save(os.path.join(video_dir, name))
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    db = get_db()
    cur = db.execute(
        'INSERT INTO videos(titulo, descripcion, belt, url, tipo, subido_por, fecha) VALUES(?,?,?,?,?,?,?)',
        (titulo, desc, belt, '/static/uploads/videos/' + name, 'upload', u['id'], now))
    db.commit()
    return jsonify({'ok': True, 'id': cur.lastrowid})


@app.route('/api/videos/<int:vid>/view', methods=['POST'])
@login_required
def api_videos_view(vid):
    u = current_user()
    db = get_db()
    v = db.execute('SELECT * FROM videos WHERE id=?', (vid,)).fetchone()
    if not v:
        return jsonify({'error': 'Video no encontrado'}), 404
    if u['role'] == 'alumno' and v['belt'] != 'Todos' and v['belt'] != u['cinturon']:
        return jsonify({'error': 'Este video no es para tu cinturón'}), 403
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    db.execute(
        'INSERT OR IGNORE INTO video_views(video_id, user_id, fecha) VALUES(?,?,?)',
        (vid, u['id'], now))
    db.commit()
    if v['subido_por']:
        notify(v['subido_por'], 'Nuevo visto',
               '%s vio el video "%s"' % (u['nombre'], v['titulo']), 'info', push=True)
    return jsonify({'ok': True, 'visto': True})


@app.route('/api/videos/<int:vid>/views')
@role_required('admin', 'profesor')
def api_videos_views(vid):
    rows = get_db().execute(
        'SELECT us.nombre, vv.fecha FROM video_views vv JOIN users us ON us.id = vv.user_id '
        'WHERE vv.video_id=? ORDER BY vv.id DESC', (vid,)).fetchall()
    return jsonify({'vistos': [dict(r) for r in rows]})


@app.route('/api/videos/<int:vid>', methods=['DELETE'])
@role_required('admin', 'profesor')
def api_videos_delete(vid):
    u = current_user()
    db = get_db()
    v = db.execute('SELECT * FROM videos WHERE id=?', (vid,)).fetchone()
    if not v:
        return jsonify({'error': 'Video no encontrado'}), 404
    if u['role'] != 'admin' and v['subido_por'] != u['id']:
        return jsonify({'error': 'Solo el profesor que lo subió o el admin pueden borrarlo'}), 403
    if v['tipo'] == 'upload':
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), v['url'].lstrip('/'))
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
    db.execute('DELETE FROM videos WHERE id=?', (vid,))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/estadisticas')
@role_required('admin', 'profesor')
def api_estadisticas():
    u = current_user()
    hoy = date.today()
    total_alumnos = get_db().execute(
        "SELECT COUNT(*) AS n FROM users WHERE role='alumno' AND activo=1").fetchone()['n']
    ingresos_mes = get_db().execute(
        'SELECT COALESCE(SUM(monto),0) AS n FROM pagos WHERE mes=? AND anio=?',
        (hoy.month, hoy.year)).fetchone()['n']
    clases = get_db().execute('SELECT COUNT(*) AS n FROM classes').fetchone()['n']
    if u['role'] == 'profesor':
        # dinero del profesor
        propio = get_db().execute(
            'SELECT COALESCE(SUM(monto),0) AS n FROM pagos WHERE profesor_id=? AND mes=? AND anio=?',
            (u['id'], hoy.month, hoy.year)).fetchone()['n']
        total_propio = get_db().execute(
            'SELECT COALESCE(SUM(monto),0) AS n FROM pagos WHERE profesor_id=?',
            (u['id'],)).fetchone()['n']
        return jsonify({
            'total_alumnos': total_alumnos, 'ingresos_mes': ingresos_mes,
            'clases': clases, 'mi_ingreso_mes': propio, 'mi_ingreso_total': total_propio})
    return jsonify({'total_alumnos': total_alumnos, 'ingresos_mes': ingresos_mes, 'clases': clases})


# ---------------------------------------------------------------------------
# Notificaciones en la app + push
# ---------------------------------------------------------------------------

@app.route('/api/notificaciones')
@login_required
def api_notificaciones():
    u = current_user()
    rows = get_db().execute(
        'SELECT * FROM notificaciones WHERE user_id=? ORDER BY id DESC LIMIT 50',
        (u['id'],)).fetchall()
    no_leidas = get_db().execute(
        'SELECT COUNT(*) AS n FROM notificaciones WHERE user_id=? AND leida=0',
        (u['id'],)).fetchone()['n']
    return jsonify({'notificaciones': [dict(r) for r in rows], 'no_leidas': no_leidas})


@app.route('/api/notificaciones/<int:nid>', methods=['POST'])
@login_required
def api_notificaciones_leer(nid):
    get_db().execute('UPDATE notificaciones SET leida=1 WHERE id=? AND user_id=?',
                     (nid, current_user()['id']))
    get_db().commit()
    return jsonify({'ok': True})


@app.route('/api/notificaciones/leer_todas', methods=['POST'])
@login_required
def api_notificaciones_leer_todas():
    get_db().execute('UPDATE notificaciones SET leida=1 WHERE user_id=?', (current_user()['id'],))
    get_db().commit()
    return jsonify({'ok': True})


@app.route('/api/vapid_public_key')
def api_vapid_key():
    return jsonify({'key': ensure_vapid()})


@app.route('/api/push_subscribe', methods=['POST'])
@login_required
def api_push_subscribe():
    data = parse_json()
    sub = data.get('subscription') or {}
    endpoint = sub.get('endpoint')
    keys = sub.get('keys') or {}
    if not endpoint or not keys.get('p256dh') or not keys.get('auth'):
        return jsonify({'error': 'Suscripcion incompleta'}), 400
    try:
        get_db().execute(
            'INSERT INTO push_subs(user_id, endpoint, p256dh, auth) VALUES(?,?,?,?)',
            (current_user()['id'], endpoint, keys['p256dh'], keys['auth']))
        get_db().commit()
    except dbadapter.IntegrityError:
        pass
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Settings / admin
# ---------------------------------------------------------------------------

@app.route('/api/settings', methods=['GET'])
@login_required
def api_settings_get():
    u = current_user()
    keys = ['academy_name', 'default_cuota', 'due_day', 'academy_code', 'pago_link', 'pago_alias']
    if u['role'] == 'admin':
        keys += ['academy_color']
    return jsonify({k: get_setting(k) for k in keys})


@app.route('/api/settings', methods=['PUT'])
@role_required('admin')
def api_settings_put():
    data = parse_json()
    for k in ['academy_name', 'default_cuota', 'due_day', 'academy_code', 'academy_color', 'pago_link', 'pago_alias']:
        if k in data and data[k] is not None:
            set_setting(k, data[k])
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Probar push manualmente (para desarrollo)
# ---------------------------------------------------------------------------

@app.route('/api/test_push', methods=['POST'])
@login_required
def api_test_push():
    send_push(current_user()['id'], 'Prueba de notificacion',
              'Si ves esto, las notificaciones push funcionan.')
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)),
            debug=os.environ.get('FLASK_DEBUG', '0') == '1')
