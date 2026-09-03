import os
import io
import base64
import json
import secrets
import zipfile
from datetime import datetime, date, timedelta

from flask import Flask, request, jsonify, session, redirect, url_for, render_template, g, send_from_directory, Response
from werkzeug.security import generate_password_hash, check_password_hash

import dbadapter
from dbadapter import DB_MODE

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.db')
app.config['MAX_CONTENT_LENGTH'] = 250 * 1024 * 1024

# Token secreto embebido en el QR físico de asistencia. Solo quien escanea
# el QR del gimnasio (que contiene este token) puede registrar su asistencia.
QR_SECRET = os.environ.get('QR_SECRET', 'ikigai2024-nopuedesmarcardesdecasa')

BELTS_ADULT = ['Blanco', 'Azul', 'Púrpura', 'Marrón', 'Negro']
BELTS_KIDS = ['Gris', 'Amarillo', 'Naranja', 'Verde', 'Blanco']
CATEGORIAS = ['adulto', 'juveniles', 'kids']
TIPOS_CLASE = ['Gi', 'NoGi', 'Kids', 'Juveniles', 'Abierto']
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
    tel TEXT,
    nacimiento TEXT,
    medic_info TEXT,
    emergency_contact TEXT,
    activo INTEGER DEFAULT 1,
    security_q TEXT,
    security_a TEXT,
    tel_tutor TEXT,
    tel_2 TEXT,
    direccion TEXT,
    dni TEXT,
    foto_ok INTEGER DEFAULT 0,
    acepto_tyc TEXT,
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
    comprobante TEXT,
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
    categoria TEXT DEFAULT 'adulto',
    url TEXT NOT NULL,
    tipo TEXT DEFAULT 'upload',
    subido_por INTEGER REFERENCES users(id) ON DELETE SET NULL,
    fecha TEXT,
    data TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS video_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fecha TEXT,
    UNIQUE(video_id, user_id)
);

CREATE TABLE IF NOT EXISTS video_progress (
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    segundos INTEGER DEFAULT 0,
    duracion INTEGER DEFAULT 0,
    completado INTEGER DEFAULT 0,
    fecha TEXT,
    PRIMARY KEY (video_id, user_id)
);

CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    tipo TEXT DEFAULT 'grupo',
    creado_por INTEGER REFERENCES users(id) ON DELETE SET NULL,
    fecha TEXT
);

CREATE TABLE IF NOT EXISTS chat_members (
    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    mensaje TEXT,
    adjunto TEXT,
    adjunto_tipo TEXT,
    fecha TEXT
);

CREATE TABLE IF NOT EXISTS muro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    texto TEXT,
    fecha TEXT
);

CREATE TABLE IF NOT EXISTS muro_fotos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    muro_id INTEGER REFERENCES muro(id) ON DELETE CASCADE,
    data TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS metas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    titulo TEXT NOT NULL,
    tipo TEXT DEFAULT 'semanas',
    objetivo INTEGER DEFAULT 3,
    cumplida INTEGER DEFAULT 0,
    fecha TEXT
);

CREATE TABLE IF NOT EXISTS encuestas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    titulo TEXT NOT NULL,
    opciones TEXT,
    activa INTEGER DEFAULT 1,
    fecha TEXT
);

CREATE TABLE IF NOT EXISTS encuesta_votos (
    encuesta_id INTEGER NOT NULL REFERENCES encuestas(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    opcion INTEGER,
    PRIMARY KEY (encuesta_id, user_id)
);

CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    fecha TEXT,
    hora TEXT,
    lugar TEXT,
    fecha_evento TEXT
);

CREATE TABLE IF NOT EXISTS evento_asistencias (
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (evento_id, user_id)
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
    for col, ddl in [('tel', 'TEXT'), ('nacimiento', 'TEXT'), ('medic_info', 'TEXT'), ('emergency_contact', 'TEXT'),
                     ('security_q', 'TEXT'), ('security_a', 'TEXT'), ('tel_tutor', 'TEXT'), ('tel_2', 'TEXT'),
                     ('direccion', 'TEXT'), ('dni', 'TEXT'), ('foto_ok', 'INTEGER'),
                     ('acepto_tyc', 'TEXT')]:
        if col not in cols:
            c.execute('ALTER TABLE users ADD COLUMN %s %s' % (col, ddl))
    if DB_MODE == 'postgres':
        ap_cols = [r[0] for r in c.execute(
            "SELECT column_name AS name FROM information_schema.columns "
            "WHERE table_schema=current_schema() AND table_name='avisos_pago'").fetchall()]
    elif DB_MODE == 'mysql':
        ap_cols = [r[0] for r in c.execute('SHOW COLUMNS FROM avisos_pago').fetchall()]
    else:
        ap_cols = [r[1] for r in c.execute('PRAGMA table_info(avisos_pago)').fetchall()]
    if 'comprobante' not in ap_cols:
        c.execute('ALTER TABLE avisos_pago ADD COLUMN comprobante TEXT')
    if DB_MODE == 'postgres':
        v_cols = [r[0] for r in c.execute(
            "SELECT column_name AS name FROM information_schema.columns "
            "WHERE table_schema=current_schema() AND table_name='videos'").fetchall()]
    elif DB_MODE == 'mysql':
        v_cols = [r[0] for r in c.execute('SHOW COLUMNS FROM videos').fetchall()]
    else:
        v_cols = [r[1] for r in c.execute('PRAGMA table_info(videos)').fetchall()]
    if 'data' not in v_cols:
        c.execute('ALTER TABLE videos ADD COLUMN data TEXT')
    if 'categoria' not in v_cols:
        c.execute('ALTER TABLE videos ADD COLUMN categoria TEXT DEFAULT \'adulto\'')
    if DB_MODE == 'postgres':
        cm_cols = [r[0] for r in c.execute(
            "SELECT column_name AS name FROM information_schema.columns "
            "WHERE table_schema=current_schema() AND table_name='chat_messages'").fetchall()]
    elif DB_MODE == 'mysql':
        cm_cols = [r[0] for r in c.execute('SHOW COLUMNS FROM chat_messages').fetchall()]
    else:
        cm_cols = [r[1] for r in c.execute('PRAGMA table_info(chat_messages)').fetchall()]
    if 'adjunto' not in cm_cols:
        c.execute('ALTER TABLE chat_messages ADD COLUMN adjunto TEXT')
    if 'adjunto_tipo' not in cm_cols:
        c.execute('ALTER TABLE chat_messages ADD COLUMN adjunto_tipo TEXT')
    defaults = {
        'academy_name': 'IKIGAI VIEDMA',
        'academy_code': 'BJJ2026',
        'default_cuota': '15000',
        'due_day': '10',
        'cargo_demora_pct': '10',
        'academy_color': '#e05d13',
        'auto_mensaje': '',
        'auto_inact_dias': '15',
        'auto_deuda_dias': '30',
        'auto_mensaje_activo': '0',
        'logro_asist': '50',
        'logro_videos': '25',
        'mp_access_token': '',
        'wp_numero': '',
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
    priv = get_setting('vapid_private')
    pub = get_setting('vapid_public')
    if not (priv and pub):
        # Intento 1: py_vapid (API antiguo y moderno)
        try:
            from py_vapid import Vapid
            v = Vapid()
            try:
                v.generate_keys()
            except Exception:
                pass
            priv = v.private_pem()
            pub = v.public_pem()
            if isinstance(priv, bytes):
                priv = priv.decode()
            if isinstance(pub, bytes):
                pub = pub.decode()
        except Exception:
            priv = pub = None
        # Intento 2: fallback con cryptography, clave EC P-256
        if not (priv and pub):
            try:
                from cryptography.hazmat.primitives.asymmetric import ec
                from cryptography.hazmat.primitives import serialization
                sk = ec.generate_private_key(ec.SECP256R1())
                priv = sk.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption()).decode()
                pub = sk.public_key().public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo).decode()
            except Exception:
                priv = pub = None
        if priv and pub:
            set_setting('vapid_private', priv)
            set_setting('vapid_public', pub)
    # escribe archivos locales para pywebpush y compatibilidad
    for path, pem in ((VAPID_PRIVATE, priv), (VAPID_PUBLIC, pub)):
        try:
            with open(path, 'w') as f:
                f.write(pem)
        except OSError:
            pass
    # Para que el navegador pueda suscribirse, applicationServerKey debe ser el
    # "raw point" P-256 descomprimido (65 bytes, 04||X||Y), NO el DER/SPKI.
    try:
        from cryptography.hazmat.primitives import serialization
        pubkey = serialization.load_pem_public_key((pub or '').encode())
        raw_point = pubkey.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint)
        return base64.urlsafe_b64encode(raw_point).rstrip(b'=').decode()
    except Exception:
        pass
    pem = (pub or '').replace('-----BEGIN PUBLIC KEY-----', '').replace('-----END PUBLIC KEY-----', '').strip()
    try:
        return base64.urlsafe_b64encode(base64.b64decode(pem)).rstrip(b'=').decode()
    except Exception:
        return pem


def send_push(user_id, titulo, mensaje, extra=None):
    """Envia notificacion push a todas las suscripciones del usuario."""
    try:
        ensure_vapid()
        if not os.path.exists(VAPID_PRIVATE):
            return 0
        from pywebpush import webpush, WebPushException
        subs = get_db().execute('SELECT id, endpoint, p256dh, auth FROM push_subs WHERE user_id=?',
                                (user_id,)).fetchall()
        payload = json.dumps({'title': titulo, 'body': mensaje, **(extra or {})})
        enviados = 0
        for s in subs:
            try:
                webpush(
                    subscription_info={
                        'endpoint': s['endpoint'],
                        'keys': {'p256dh': s['p256dh'], 'auth': s['auth']}},
                    data=payload,
                    vapid_private_key=VAPID_PRIVATE,
                    vapid_claims={'sub': 'mailto:admin@academia.local'})
                enviados += 1
            except WebPushException as wp:
                # Suscripciones vencidas/invalidas (410, 404, 403): borrarlas
                status = getattr(wp, 'response', None)
                code = status.status_code if status is not None else None
                if code in (404, 410, 403):
                    try:
                        get_db().execute('DELETE FROM push_subs WHERE id=?', (s['id'],))
                        get_db().commit()
                    except Exception:
                        pass
            except Exception:
                pass
        return enviados
    except Exception:
        return 0


def notify(user_id, titulo, mensaje, tipo='info', push=True):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    get_db().execute(
        'INSERT INTO notificaciones(user_id, titulo, mensaje, tipo, fecha) VALUES(?,?,?,?,?)',
        (user_id, titulo, mensaje, tipo, now))
    get_db().commit()
    if push:
        send_push(user_id, titulo, mensaje)


def chequear_logros(user_id):
    """Notifica cada vez que el alumno cruza un múltiplo del umbral configurable."""
    th = to_int(get_setting('logro_asist', '50')) or 50
    thv = to_int(get_setting('logro_videos', '25')) or 25
    db = get_db()
    asis = db.execute('SELECT COUNT(*) AS n FROM asistencia WHERE alumno_id=?',
                      (user_id,)).fetchone()['n']
    vids = db.execute('SELECT COUNT(*) AS n FROM video_views WHERE user_id=?',
                      (user_id,)).fetchone()['n']
    avisos = []
    if th > 0 and asis > 0 and asis % th == 0 and not _ya_logro(user_id, 'asis', asis):
        notify(user_id, '🎉 Logro alcanzado',
               '¡Llegaste a %d asistencias! Seguí así 🥋' % asis, 'logro', push=True)
        avisos.append('asistencias')
    if thv > 0 and vids > 0 and vids % thv == 0 and not _ya_logro(user_id, 'vids', vids):
        notify(user_id, '🎉 Logro alcanzado',
               '¡Viste %d videos! Buen progreso 🎥' % vids, 'logro', push=True)
        avisos.append('videos')
    return avisos


def _ya_logro(user_id, tipo, valor):
    key = 'logro_done_%d_%s_%d' % (user_id, tipo, valor)
    if get_setting(key, '0') == '1':
        return True
    set_setting(key, '1')
    return False


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
        'tel': u['tel'] if 'tel' in u.keys() else None,
        'nacimiento': u['nacimiento'] if 'nacimiento' in u.keys() else None,
        'medic_info': u['medic_info'] if 'medic_info' in u.keys() else None,
        'emergency_contact': u['emergency_contact'] if 'emergency_contact' in u.keys() else None,
        'security_q': u['security_q'] if 'security_q' in u.keys() else None,
        'tel_tutor': u['tel_tutor'] if 'tel_tutor' in u.keys() else None,
        'tel_2': u['tel_2'] if 'tel_2' in u.keys() else None,
        'direccion': u['direccion'] if 'direccion' in u.keys() else None,
        'dni': u['dni'] if 'dni' in u.keys() else None,
        'foto_ok': u['foto_ok'] if 'foto_ok' in u.keys() else None,
        'acepto_tyc': u['acepto_tyc'] if 'acepto_tyc' in u.keys() else None,
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
        'cargo_demora_pct': to_float(get_setting('cargo_demora_pct', '10')) or 0,
    }


def calcular_demora(monto, mes=None, anio=None, fecha=None):
    """Aplica el cargo por pago con demora (después del día de vencimiento).

    Devuelve (monto_base, cargo, monto_final). Sin cargo si no corresponde.
    """
    base = monto or 0
    if base <= 0:
        return base, 0, base
    hoy = fecha or date.today()
    due_day = to_int(get_setting('due_day', '10')) or 10
    pct = to_float(get_setting('cargo_demora_pct', '10')) or 0
    # Mes objetivo del pago (por defecto el mes actual)
    tmes = mes or hoy.month
    tanio = anio or hoy.year
    # Determinar el vencimiento: el día due_day del mes del pago
    try:
        venc = date(tanio, tmes, due_day)
    except ValueError:
        # si due_day no existe (ej 31 en feb) usar último día del mes
        import calendar
        last = calendar.monthrange(tanio, tmes)[1]
        venc = date(tanio, tmes, last)
    if hoy > venc and pct > 0:
        cargo = round(base * pct / 100)
        return base, cargo, base + cargo
    return base, 0, base


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


def dias_sin_entrenar(alumno):
    """Días desde la última asistencia marcada del alumno."""
    hoy = date.today()
    row = get_db().execute(
        "SELECT fecha FROM asistencia WHERE alumno_id=? AND presente=1 ORDER BY fecha DESC LIMIT 1",
        (alumno['id'],)).fetchone()
    if row and row['fecha']:
        try:
            last = datetime.strptime(row['fecha'], '%Y-%m-%d').date()
            return (hoy - last).days
        except Exception:
            pass
    # si nunca entrenó, usar fecha de creación
    if alumno['creado']:
        try:
            last = datetime.strptime(alumno['creado'][:10], '%Y-%m-%d').date()
            return (hoy - last).days
        except Exception:
            pass
    return 0


def run_auto_mensajes():
    """Dispara mensajes automáticos por inactividad y por deuda (una vez por alumno).

    Controla el envío con notificaciones tipo 'auto' para evitar duplicados.
    Devuelve lista de (alumno_nombre, motivo).
    """
    if not (get_setting('auto_mensaje_activo', '0') == '1'):
        return []
    texto = (get_setting('auto_mensaje', '') or '').strip()
    if not texto:
        return []
    inact_dias = to_int(get_setting('auto_inact_dias', '15')) or 15
    deuda_dias = to_int(get_setting('auto_deuda_dias', '30')) or 30
    alumnos = get_db().execute(
        "SELECT * FROM users WHERE role='alumno' AND activo=1").fetchall()
    enviados = []
    for a in alumnos:
        motivo = None
        if dias_sin_entrenar(a) >= inact_dias:
            motivo = 'inactividad'
        elif dias_deuda(a) >= deuda_dias:
            motivo = 'deuda'
        if not motivo:
            continue
        # verificar que no se le haya enviado ya el mensaje automático (tipo 'auto')
        ya = get_db().execute(
            "SELECT 1 FROM notificaciones WHERE user_id=? AND tipo='auto' AND fecha LIKE ? LIMIT 1",
            (a['id'], date.today().strftime('%Y-%m-%d') + '%')).fetchone()
        if ya:
            continue
        notify(a['id'], '📣 Mensaje de la academia', texto, tipo='auto', push=True)
        enviados.append((a['nombre'], motivo))
    return enviados


@app.route('/api/mensajes/auto', methods=['POST'])
@role_required('admin', 'profesor')
def api_mensajes_auto():
    enviados = run_auto_mensajes()
    return jsonify({'ok': True, 'enviados': [{'nombre': n, 'motivo': m} for n, m in enviados]})


@app.route('/api/perfil/desactivar', methods=['POST'])
@login_required
def api_perfil_desactivar():
    u = current_user()
    if u['role'] != 'alumno':
        return jsonify({'error': 'Solo los alumnos pueden desactivar su cuenta'}), 403
    get_db().execute('UPDATE users SET activo=0 WHERE id=?', (u['id'],))
    get_db().commit()
    session.clear()
    return jsonify({'ok': True})

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


@app.route('/recibo/<int:pid>')
@login_required
def recibo(pid):
    p = get_db().execute(
        """SELECT p.*, u.nombre AS alumno_nombre, pr.nombre AS profe_nombre
           FROM pagos p JOIN users u ON u.id=p.alumno_id
           LEFT JOIN users pr ON pr.id=p.profesor_id WHERE p.id=?""", (pid,)).fetchone()
    if not p:
        return render_template('error.html', message='Recibo no encontrado'), 404
    u = current_user()
    if u['role'] not in ('admin', 'profesor') and u['id'] != p['alumno_id']:
        return render_template('error.html', message='No tenés permiso para ver este recibo'), 403
    mes = to_int(p['mes'])
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    return render_template('recibo.html', p=p,
                           mes_nombre=meses[mes - 1] if mes and 1 <= mes <= 12 else '',
                           academy=get_setting('academy_name'),
                           color=get_setting('academy_color') or '#e05d13')


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


# ---------------------------------------------------------------------------
# Recuperacion de contrasena (pregunta de seguridad + reinicio por admin)
# ---------------------------------------------------------------------------

@app.route('/api/recuperar', methods=['POST'])
def api_recuperar():
    """Devuelve la pregunta de seguridad de un usuario (sin exponer la respuesta)."""
    data = parse_json()
    username = (data.get('username') or '').strip()
    u = get_db().execute('SELECT id, security_q FROM users WHERE username=?', (username,)).fetchone()
    if not u:
        return jsonify({'error': 'Ese usuario no existe'}), 404
    if not u['security_q']:
        return jsonify({'error': 'Ese usuario no configuró pregunta de seguridad. Pedile al profe/admin que reinicie tu contraseña.'}), 400
    return jsonify({'ok': True, 'pregunta': u['security_q']})


@app.route('/api/recuperar/verificar', methods=['POST'])
def api_recuperar_verificar():
    """Verifica la respuesta de seguridad y cambia la contrasena."""
    data = parse_json()
    username = (data.get('username') or '').strip()
    resp = (data.get('respuesta') or '').strip()
    nueva = data.get('nueva_password') or ''
    if len(nueva) < 4:
        return jsonify({'error': 'La nueva contrasena debe tener al menos 4 caracteres'}), 400
    u = get_db().execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    if not u:
        return jsonify({'error': 'Ese usuario no existe'}), 404
    if not u['security_a'] or not u['security_q']:
        return jsonify({'error': 'Ese usuario no configuró pregunta de seguridad.'}), 400
    if resp.lower() != (u['security_a'] or '').strip().lower():
        return jsonify({'error': 'La respuesta no es correcta'}), 401
    get_db().execute('UPDATE users SET password_hash=? WHERE id=?',
                     (generate_password_hash(nueva), u['id']))
    get_db().commit()
    notify(1, 'Contraseña cambiada', 'Se cambio la contraseña de %s con la pregunta de seguridad' % u['nombre'])
    return jsonify({'ok': True})


@app.route('/api/perfil/seguridad', methods=['PUT'])
@login_required
def api_perfil_seguridad():
    u = current_user()
    data = parse_json()
    q = (data.get('pregunta') or '').strip()
    a = (data.get('respuesta') or '').strip()
    nueva = data.get('nueva_password') or ''
    if not q or not a:
        return jsonify({'error': 'Completa la pregunta y la respuesta'}), 400
    db = get_db()
    if nueva:
        if len(nueva) < 4:
            return jsonify({'error': 'La contrasena debe tener al menos 4 caracteres'}), 400
        db.execute('UPDATE users SET password_hash=? WHERE id=?', (generate_password_hash(nueva), u['id']))
    db.execute('UPDATE users SET security_q=?, security_a=? WHERE id=?', (q, a, u['id']))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/terminos/aceptar', methods=['POST'])
@login_required
def api_terminos_aceptar():
    """Registra que el usuario aceptó los Términos y Condiciones (fecha y hora)."""
    u = current_user()
    db = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db.execute('UPDATE users SET acepto_tyc=? WHERE id=?', (now, u['id']))
    db.commit()
    return jsonify({'ok': True, 'acepto_tyc': now})


@app.route('/api/usuarios/<int:uid>/password', methods=['POST'])
@role_required('admin', 'profesor')
def api_usuario_password(uid):
    data = parse_json()
    nueva = data.get('password') or ''
    if len(nueva) < 4:
        return jsonify({'error': 'La contrasena debe tener al menos 4 caracteres'}), 400
    db = get_db()
    u = db.execute('SELECT nombre FROM users WHERE id=?', (uid,)).fetchone()
    if not u:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    db.execute('UPDATE users SET password_hash=? WHERE id=?', (generate_password_hash(nueva), uid))
    db.commit()
    notify(uid, 'Contraseña actualizada', 'Tu contraseña fue reiniciada por la academia. La próxima vez que entres, usá la nueva clave.')
    return jsonify({'ok': True})


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

    categoria = data.get('categoria') or 'adulto'
    tel_tutor = (data.get('tel_tutor') or '').strip()
    if role == 'alumno' and categoria in ('kids', 'juveniles') and not tel_tutor:
        return jsonify({'error': 'Para menores (Kids/Juveniles) es obligatorio el telefono del padre, madre o tutor responsable.'}), 400
    foto_ok = 1 if data.get('foto_ok') else 0
    if role == 'alumno' and categoria in ('kids', 'juveniles') and not foto_ok:
        return jsonify({'error': 'Para menores (Kids/Juveniles) debe autorizar el mayor, padre, madre o tutor que las fotos del menor puedan exponerse.'}), 400
    tel_2 = (data.get('tel_2') or '').strip() or None

    if not data.get('acepto_tyc'):
        return jsonify({'error': 'Debés aceptar los Términos y Condiciones para crear tu cuenta.'}), 400

    try:
        get_db().execute(
            """INSERT INTO users(username, password_hash, role, nombre, edad, peso, cinturon, categoria, gi_pref, cuota_mensual, tel, nacimiento, medic_info, emergency_contact, tel_tutor, tel_2, direccion, dni, foto_ok, acepto_tyc, creado)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (username, generate_password_hash(password), role, nombre,
             to_int(data.get('edad')), to_float(data.get('peso')),
             data.get('cinturon'), categoria,
             data.get('gi_pref') or 'Ambas',
             to_float(data.get('cuota_mensual')) if role == 'alumno' else None,
             (data.get('tel') or '').strip() or None,
             (data.get('nacimiento') or '').strip() or None,
             (data.get('medic_info') or '').strip() or None,
             (data.get('emergency_contact') or '').strip() or None,
             tel_tutor or None,
             tel_2,
             (data.get('direccion') or '').strip() or None,
             (data.get('dni') or '').strip() or None,
             foto_ok,
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
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
    d['mp_habilitado'] = bool((get_setting('mp_access_token', '') or '').strip())
    d['wp_numero'] = get_setting('wp_numero', '')
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
        """UPDATE users SET nombre=?, edad=?, peso=?, cinturon=?, categoria=?, gi_pref=?, activo=?, tel=?, nacimiento=?, medic_info=?, emergency_contact=?, tel_tutor=?, tel_2=?, direccion=?, dni=?, foto_ok=? WHERE id=?""",
        ((data.get('nombre') or u['nombre']), to_int(data.get('edad', u['edad'])),
         to_float(data.get('peso', u['peso'])), data.get('cinturon', u['cinturon']),
         data.get('categoria', u['categoria']), data.get('gi_pref', u['gi_pref']),
         1 if data.get('activo', u['activo']) else 0,
         (data.get('tel', u['tel']) or '').strip() or None,
         (data.get('nacimiento', u['nacimiento']) or '').strip() or None,
         data.get('medic_info', u['medic_info']),
         data.get('emergency_contact', u['emergency_contact']),
         (data.get('tel_tutor', u['tel_tutor']) or '').strip() or None,
         (data.get('tel_2', u['tel_2']) or '').strip() or None,
         (data.get('direccion', u['direccion']) or '').strip() or None,
         (data.get('dni', u['dni']) or '').strip() or None,
         1 if data.get('foto_ok', u['foto_ok']) else 0, uid))
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
    base, cargo, final = calcular_demora(monto, mes, anio)
    monto = final if (data.get('aplicar_cargo', True)) else monto
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
    nota_extra = f' (incluye ${cargo:,.0f} de recargo por demora).'.replace(',', '.') if cargo else '.'
    # notificaciones: al alumno
    notify(alumno_id, 'Pago registrado',
           f'Tu pago de ${monto:,.0f} por {mes}/{anio} fue registrado por {who["nombre"]}{nota_extra}'.replace(',', '.'),
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
    return jsonify({'ok': True, 'base': base, 'cargo': cargo, 'monto': monto})


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
    hoy = date.today().strftime('%Y-%m-%d')
    hoy_ids = [r['clase_id'] for r in get_db().execute(
        'SELECT clase_id FROM asistencia WHERE alumno_id=? AND fecha=? AND presente=1',
        (u['id'], hoy)).fetchall()]
    return jsonify({'asistencia': asis, 'total': total, 'hoy': hoy_ids, 'fecha_hoy': hoy})


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
    comp = (data.get('comprobante') or '').strip()
    if not (comp.startswith('data:image/') or comp.startswith('data:application/pdf')):
        return jsonify({'error': 'Tenés que subir el comprobante de pago (foto, captura o PDF)'}), 400
    if len(comp) > 12 * 1024 * 1024:
        return jsonify({'error': 'El comprobante es muy grande (máx 12MB)'}), 400
    get_db().execute(
        'INSERT INTO avisos_pago(alumno_id, monto, mes, anio, nota, comprobante, estado, fecha) VALUES(?,?,?,?,?,?,?,?)',
        (u['id'], monto, mes, anio, data.get('nota') or 'Cuota mensual', comp, 'pendiente',
         datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    get_db().commit()
    staff = get_db().execute(
        "SELECT id FROM users WHERE role IN ('admin','profesor') AND activo=1").fetchall()
    for s in staff:
        notify(s['id'], 'Aviso de pago con comprobante',
               f'{u["nombre"]} avisó que pagó la cuota de {mes}/{anio}. Revisá el comprobante y confirmá el pago.',
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
    base, cargo, final = calcular_demora(a['monto'] or 0, a['mes'], a['anio'])
    get_db().execute(
        'INSERT INTO pagos(alumno_id, profesor_id, monto, mes, anio, metodo, concepto, nota, fecha, registrado_por) VALUES(?,?,?,?,?,?,?,?,?,?)',
        (a['alumno_id'], None, final, a['mes'], a['anio'], 'Aviso', 'Cuota mensual',
         'Confirmado desde aviso de pago' + (f' (recargo por demora ${cargo:,.0f})'.replace(',', '.') if cargo else ''),
         datetime.now().strftime('%Y-%m-%d %H:%M:%S'), who['id']))
    get_db().execute(
        "UPDATE avisos_pago SET estado='confirmado', confirmado_por=?, confirmado_fecha=? WHERE id=?",
        (who['id'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), aid))
    get_db().commit()
    alumno = get_db().execute('SELECT * FROM users WHERE id=?', (a['alumno_id'],)).fetchone()
    nota = f' (incluye ${cargo:,.0f} de recargo por demora)'.replace(',', '.') if cargo else ''
    notify(a['alumno_id'], 'Pago confirmado',
           f'Tu aviso de pago de la cuota {a["mes"]}/{a["anio"]} por ${final:,.0f} fue confirmado por {who["nombre"]}{nota}.'.replace(',', '.'),
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


@app.route('/api/asistencia_yo', methods=['POST'])
@role_required('alumno')
def api_asistencia_yo():
    u = current_user()
    data = parse_json()
    clase_id = to_int(data.get('clase_id'))
    fecha = data.get('fecha') or date.today().strftime('%Y-%m-%d')
    # Seguridad: solo se puede marcar asistencia presentando el token del QR físico.
    if not data.get('qr_token') or data.get('qr_token') != QR_SECRET:
        return jsonify({'error': 'Debés escanear el QR del gimnasio para registrar tu asistencia.'}), 403
    if not clase_id:
        return jsonify({'error': 'Falta la clase'}), 400
    c = get_db().execute('SELECT * FROM classes WHERE id=?', (clase_id,)).fetchone()
    if not c:
        return jsonify({'error': 'Clase no encontrada'}), 404
    get_db().execute(
        'INSERT OR IGNORE INTO asistencia(clase_id, alumno_id, fecha, presente) VALUES(?,?,?,1)',
        (clase_id, u['id'], fecha))
    get_db().commit()
    chequear_logros(u['id'])
    return jsonify({'ok': True})


@app.route('/api/reporte')
@role_required('admin', 'profesor')
def api_reporte():
    hoy = date.today()
    mes = to_int(request.args.get('mes')) or hoy.month
    anio = to_int(request.args.get('anio')) or hoy.year
    pagos = get_db().execute(
        """SELECT p.*, u.nombre AS alumno_nombre FROM pagos p
           JOIN users u ON u.id=p.alumno_id
           WHERE p.mes=? AND p.anio=? ORDER BY p.fecha DESC""",
        (mes, anio)).fetchall()
    total = sum((p['monto'] or 0) for p in pagos)
    por_metodo = {}
    for p in pagos:
        k = p['metodo'] or 'Otro'
        por_metodo[k] = por_metodo.get(k, 0) + (p['monto'] or 0)
    deudores = get_db().execute(
        """SELECT u.id, u.nombre, u.cinturon, u.cuota_mensual FROM users u
           WHERE u.role='alumno' AND u.activo=1
           AND NOT EXISTS (SELECT 1 FROM pagos p WHERE p.alumno_id=u.id AND p.mes=? AND p.anio=?)""",
        (mes, anio)).fetchall()
    avisos_pend = get_db().execute(
        "SELECT COUNT(*) AS c FROM avisos_pago WHERE estado='pendiente'").fetchone()['c']
    # Porcentajes de alumnos
    total_alumnos = get_db().execute(
        "SELECT COUNT(*) AS c FROM users WHERE role='alumno' AND activo=1").fetchone()['c']
    pagaron_ids = [p['alumno_id'] for p in pagos]
    cant_pagaron = len(set(pagaron_ids))
    cant_no_pagaron = len(deudores)
    pct_pagaron = round(cant_pagaron * 100 / total_alumnos) if total_alumnos else 0
    pct_no_pagaron = round(cant_no_pagaron * 100 / total_alumnos) if total_alumnos else 0
    # Alumnos que pagaron (detalle)
    alumnos_que_pagaron = get_db().execute(
        """SELECT DISTINCT u.id, u.nombre, u.cinturon, p.monto, p.metodo, p.fecha
           FROM pagos p JOIN users u ON u.id=p.alumno_id
           WHERE p.mes=? AND p.anio=? ORDER BY u.nombre""",
        (mes, anio)).fetchall()
    # Asistencia del mes (primer y último día del mes)
    primer_dia = f'{anio}-{mes:02d}-01'
    if mes == 12:
        ultimo_dia = f'{anio + 1}-01-01'
    else:
        ultimo_dia = f'{anio}-{mes + 1:02d}-01'
    asistieron = get_db().execute(
        """SELECT DISTINCT u.id, u.nombre, u.cinturon, COUNT(*) AS clases
           FROM asistencia a JOIN users u ON u.id=a.alumno_id
           WHERE a.presente=1 AND a.fecha>=? AND a.fecha<?
           GROUP BY u.id ORDER BY u.nombre""",
        (primer_dia, ultimo_dia)).fetchall()
    no_asistieron = get_db().execute(
        """SELECT u.id, u.nombre, u.cinturon FROM users u
           WHERE u.role='alumno' AND u.activo=1
           AND NOT EXISTS (SELECT 1 FROM asistencia a WHERE a.alumno_id=u.id
                           AND a.presente=1 AND a.fecha>=? AND a.fecha<?)""",
        (primer_dia, ultimo_dia)).fetchall()
    cant_asistieron = len(asistieron)
    cant_no_asistieron = len(no_asistieron)
    pct_asistieron = round(cant_asistieron * 100 / total_alumnos) if total_alumnos else 0
    pct_no_asistieron = round(cant_no_asistieron * 100 / total_alumnos) if total_alumnos else 0
    return jsonify({'mes': mes, 'anio': anio, 'total': total, 'cantidad': len(pagos),
                    'por_metodo': por_metodo, 'deudores': [dict(d) for d in deudores],
                    'avisos_pend': int(avisos_pend),
                    'total_alumnos': total_alumnos,
                    'cant_pagaron': cant_pagaron, 'pct_pagaron': pct_pagaron,
                    'cant_no_pagaron': cant_no_pagaron, 'pct_no_pagaron': pct_no_pagaron,
                    'alumnos_que_pagaron': [dict(a) for a in alumnos_que_pagaron],
                    'cant_asistieron': cant_asistieron, 'pct_asistieron': pct_asistieron,
                    'cant_no_asistieron': cant_no_asistieron, 'pct_no_asistieron': pct_no_asistieron,
                    'alumnos_que_asistieron': [{'nombre': a['nombre'], 'cinturon': a['cinturon'], 'clases': a['clases']} for a in asistieron],
                    'alumnos_que_no_asistieron': [{'nombre': a['nombre'], 'cinturon': a['cinturon']} for a in no_asistieron]})


@app.route('/api/cumpleanios')
@login_required
def api_cumpleanios():
    hoy = date.today()
    rows = get_db().execute(
        "SELECT id, nombre, nacimiento FROM users "
        "WHERE role='alumno' AND activo=1 AND nacimiento IS NOT NULL AND nacimiento != ''"
    ).fetchall()
    res = []
    for r in rows:
        try:
            parts = r['nacimiento'].split('-')
            mes_n = int(parts[1])
            dia = int(parts[2]) if len(parts) > 2 else 0
            anio_n = int(parts[0]) if parts[0] else None
            if mes_n == hoy.month:
                res.append({'id': r['id'], 'nombre': r['nombre'], 'dia': dia,
                            'edad': (hoy.year - anio_n) if anio_n else None,
                            'hoy': dia == hoy.day})
        except Exception:
            pass
    res.sort(key=lambda x: (0 if x['hoy'] else 1, x['dia']))
    return jsonify({'cumpleanios': res, 'mes': hoy.month})


@app.route('/api/perfil', methods=['PUT'])
@login_required
def api_perfil_update():
    u = current_user()
    data = parse_json()
    cat = data.get('categoria', u['categoria'])
    tel_tutor = (data.get('tel_tutor', u['tel_tutor']) or '').strip() or None
    if u['role'] == 'alumno' and cat in ('kids', 'juveniles') and not tel_tutor:
        return jsonify({'error': 'Para menores (Kids/Juveniles) es obligatorio el telefono del padre, madre o tutor responsable.'}), 400
    foto_ok = data.get('foto_ok', u['foto_ok'])
    if u['role'] == 'alumno' and cat in ('kids', 'juveniles') and not foto_ok:
        return jsonify({'error': 'Para menores (Kids/Juveniles) debe autorizar el mayor, padre, madre o tutor que las fotos del menor puedan exponerse.'}), 400
    get_db().execute(
        'UPDATE users SET nombre=?, edad=?, peso=?, cinturon=?, categoria=?, gi_pref=?, tel=?, nacimiento=?, medic_info=?, emergency_contact=?, tel_tutor=?, tel_2=?, direccion=?, dni=?, foto_ok=? WHERE id=?',
        ((data.get('nombre') or u['nombre']), to_int(data.get('edad', u['edad'])),
         to_float(data.get('peso', u['peso'])), data.get('cinturon', u['cinturon']),
         cat, data.get('gi_pref', u['gi_pref']),
         (data.get('tel', u['tel']) or '').strip() or None,
         (data.get('nacimiento', u['nacimiento']) or '').strip() or None,
         data.get('medic_info', u['medic_info']),
         data.get('emergency_contact', u['emergency_contact']),
         tel_tutor,
         (data.get('tel_2', u['tel_2']) or '').strip() or None,
         (data.get('direccion', u['direccion']) or '').strip() or None,
         (data.get('dni', u['dni']) or '').strip() or None,
         1 if foto_ok else 0, u['id']))
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
        buf = io.BytesIO()
        img.save(buf, 'JPEG', quality=85)
        data_uri = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')
    except Exception:
        return jsonify({'error': 'Formato de imagen invalido (usa JPG o PNG)'}), 400
    uid = current_user()['id']
    get_db().execute('UPDATE users SET foto=? WHERE id=?', (data_uri, uid))
    get_db().commit()
    return jsonify({'ok': True, 'foto': data_uri})


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
    out = {
        'id': v['id'], 'titulo': v['titulo'], 'descripcion': v['descripcion'],
        'belt': v['belt'], 'categoria': v['categoria'], 'url': v['url'], 'tipo': v['tipo'],
        'subido_por': v['subido_por'], 'fecha': v['fecha'],
        'subidor_nombre': v['subidor_nombre'], 'vistas': vistas, 'visto': visto,
    }
    if u['role'] == 'alumno':
        prog = d.execute('SELECT * FROM video_progress WHERE video_id=? AND user_id=?',
                         (v['id'], u['id'])).fetchone()
        completado = bool(prog and prog['completado'])
        pct = 0
        if prog and prog['duracion'] > 0:
            pct = min(99, int(prog['segundos'] * 100 / prog['duracion']))
        out['completado'] = completado
        out['progreso_pct'] = pct
    return out


def _list_videos(u, belt=None, categoria=None):
    db = get_db()
    q = ('SELECT v.id, v.titulo, v.descripcion, v.belt, v.categoria, v.url, v.tipo, v.subido_por, v.fecha, '
         's.nombre AS subidor_nombre FROM videos v '
         'LEFT JOIN users s ON s.id = v.subido_por ')
    args = []
    where = []
    if u['role'] == 'alumno':
        where.append("v.categoria = ?")
        args.append(u['categoria'])
        where.append("(v.belt = 'Todos' OR v.belt = ?)")
        args.append(u['cinturon'])
    else:
        if belt and belt != 'Todos':
            where.append('v.belt = ?')
            args.append(belt)
        if categoria and categoria != 'Todas':
            where.append('v.categoria = ?')
            args.append(categoria)
    if where:
        q += ' WHERE ' + ' AND '.join(where)
    q += ' ORDER BY v.id DESC'
    rows = db.execute(q, args).fetchall()
    return [_video_public(r, u) for r in rows]


@app.route('/api/videos')
@login_required
def api_videos_list():
    u = current_user()
    return jsonify({'videos': _list_videos(u, request.args.get('belt'), request.args.get('categoria'))})


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
        'INSERT INTO videos(titulo, descripcion, belt, categoria, url, tipo, subido_por, fecha) VALUES(?,?,?,?,?,?,?,?)',
        (titulo, (data.get('descripcion') or '').strip(), (data.get('belt') or 'Todos'),
         (data.get('categoria') or 'adulto'), url, 'link', u['id'], now))
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
    raw = f.read()
    if not raw:
        return jsonify({'error': 'El archivo está vacío'}), 400
    if len(raw) > 25 * 1024 * 1024:
        return jsonify({'error': 'El video es muy grande (máx 25MB). Para videos largos usá un link de YouTube.'}), 400
    titulo = (request.form.get('titulo') or '').strip() or os.path.splitext(f.filename)[0]
    belt = (request.form.get('belt') or 'Todos').strip()
    categoria = (request.form.get('categoria') or 'adulto').strip()
    desc = (request.form.get('descripcion') or '').strip()
    data_b64 = base64.b64encode(raw).decode('ascii')
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    db = get_db()
    cur = db.execute(
        'INSERT INTO videos(titulo, descripcion, belt, categoria, url, tipo, subido_por, fecha, data) VALUES(?,?,?,?,?,?,?,?,?)',
        (titulo, desc, belt, categoria, '/api/video/0/archivo', 'upload', u['id'], now, data_b64))
    vid = cur.lastrowid
    db.execute('UPDATE videos SET url=? WHERE id=?', ('/api/video/%d/archivo' % vid, vid))
    db.commit()
    return jsonify({'ok': True, 'id': vid})


@app.route('/api/video/<int:vid>/archivo')
def api_video_archivo(vid):
    v = get_db().execute('SELECT url, data FROM videos WHERE id=?', (vid,)).fetchone()
    if not v or not v['data']:
        return jsonify({'error': 'Video no encontrado'}), 404
    ext = os.path.splitext(v['url'])[1].lower()
    mime = {'.mp4': 'video/mp4', '.webm': 'video/webm', '.ogg': 'video/ogg', '.mov': 'video/quicktime'}.get(ext, 'video/mp4')
    try:
        raw = base64.b64decode(v['data'])
    except Exception:
        return jsonify({'error': 'Video dañado'}), 500
    return Response(raw, mimetype=mime, headers={'Accept-Ranges': 'bytes'})


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
# Chat + grupos por categoria
# ---------------------------------------------------------------------------

@app.route('/api/chats')
@login_required
def api_chats():
    u = current_user()
    db = get_db()
    rows = db.execute(
        'SELECT c.* FROM chats c JOIN chat_members m ON m.chat_id=c.id '
        'WHERE m.user_id=? ORDER BY c.id DESC', (u['id'],)).fetchall()
    chats = []
    for c in rows:
        nombre = c['nombre']
        if c['tipo'] == 'grupo':
            miembros = db.execute(
                'SELECT COUNT(*) AS n FROM chat_members WHERE chat_id=?', (c['id'],)).fetchone()['n']
            chats.append({'id': c['id'], 'nombre': nombre or 'Grupo', 'tipo': c['tipo'],
                          'miembros': miembros})
        else:
            otro = db.execute(
                'SELECT u.id, u.nombre, u.foto FROM users u JOIN chat_members m ON m.user_id=u.id '
                'WHERE m.chat_id=? AND u.id<>?', (c['id'], u['id'])).fetchone()
            chats.append({'id': c['id'], 'nombre': (otro['nombre'] if otro else 'Chat'),
                          'tipo': c['tipo']})
    return jsonify({'chats': chats})


@app.route('/api/chats', methods=['POST'])
@login_required
def api_chat_crear():
    u = current_user()
    data = parse_json()
    db = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    if data.get('categoria') in ('kids', 'juveniles', 'adulto'):
        cat = data['categoria']
        try:
            # reutilizar un chat de grupo existente de esa categoria
            exist = db.execute(
                "SELECT id FROM chats WHERE tipo='grupo' AND nombre=? ORDER BY id ASC LIMIT 1",
                (cat,)).fetchone()
            if exist:
                return jsonify({'ok': True, 'id': exist['id'], 'nombre': cat, 'tipo': 'grupo'})
            cur = db.execute(
                "INSERT INTO chats(nombre, tipo, creado_por, fecha) VALUES(?,?,?,?)",
                (cat, 'grupo', u['id'], now))
            chat_id = cur.lastrowid
            ids = [r['id'] for r in db.execute(
                "SELECT id FROM users WHERE role in ('admin','profesor') OR (role='alumno' AND categoria=?)",
                (cat,)).fetchall()]
            for uid in ids:
                db.execute('INSERT OR IGNORE INTO chat_members(chat_id, user_id) VALUES(?,?)', (chat_id, uid))
            db.commit()
            return jsonify({'ok': True, 'id': chat_id, 'nombre': cat, 'tipo': 'grupo'})
        except Exception as e:
            return jsonify({'error': 'Error al crear el grupo: %s' % str(e)}), 500
    # chat directo
    otro = to_int(data.get('user_id'))
    if not otro or otro == u['id']:
        return jsonify({'error': 'Elegí un contacto válido'}), 400
    exist = db.execute(
        'SELECT c.id FROM chats c JOIN chat_members m1 ON m1.chat_id=c.id JOIN chat_members m2 ON m2.chat_id=c.id '
        'WHERE c.tipo=\'directo\' AND m1.user_id=? AND m2.user_id=? '
        'AND (SELECT COUNT(*) FROM chat_members WHERE chat_id=c.id)=2', (u['id'], otro)).fetchone()
    if exist:
        return jsonify({'ok': True, 'id': exist['id'], 'tipo': 'directo'})
    cur = db.execute("INSERT INTO chats(nombre, tipo, creado_por, fecha) VALUES(?,?,?,?)",
                     (None, 'directo', u['id'], now))
    chat_id = cur.lastrowid
    db.execute('INSERT OR IGNORE INTO chat_members(chat_id, user_id) VALUES(?,?)', (chat_id, u['id']))
    db.execute('INSERT OR IGNORE INTO chat_members(chat_id, user_id) VALUES(?,?)', (chat_id, otro))
    db.commit()
    return jsonify({'ok': True, 'id': chat_id, 'tipo': 'directo'})


@app.route('/api/chats/<int:chat_id>/mensajes')
@login_required
def api_chat_mensajes(chat_id):
    u = current_user()
    db = get_db()
    miembro = db.execute('SELECT 1 FROM chat_members WHERE chat_id=? AND user_id=?', (chat_id, u['id'])).fetchone()
    chat = db.execute('SELECT * FROM chats WHERE id=?', (chat_id,)).fetchone()
    if not chat or not miembro:
        return jsonify({'error': 'No tenés acceso a este chat'}), 403
    filas = db.execute(
        'SELECT m.id, m.user_id, m.mensaje, m.adjunto, m.adjunto_tipo, m.fecha, us.nombre, us.foto '
        'FROM chat_messages m JOIN users us ON us.id=m.user_id '
        'WHERE m.chat_id=? ORDER BY m.id ASC LIMIT 200', (chat_id,)).fetchall()
    return jsonify({'mensajes': [dict(r) for r in filas], 'chat': dict(chat)})


@app.route('/api/chats/<int:chat_id>/mensajes', methods=['POST'])
@login_required
def api_chat_enviar(chat_id):
    u = current_user()
    data = parse_json()
    msj = (data.get('mensaje') or '').strip()
    adjunto = (data.get('adjunto') or '').strip()
    adjunto_tipo = (data.get('adjunto_tipo') or '').strip()
    if not msj and not adjunto:
        return jsonify({'error': 'Escribí un mensaje o adjuntá una foto/video'}), 400
    # solo permitir imagenes y videos en el adjunto
    if adjunto and not (adjunto.startswith('data:image/') or adjunto.startswith('data:video/')):
        return jsonify({'error': 'El adjunto debe ser una imagen o un video'}), 400
    if len(adjunto) > 25 * 1024 * 1024:
        return jsonify({'error': 'El archivo es muy grande (máx 25MB)'}), 400
    db = get_db()
    chat = db.execute('SELECT * FROM chats WHERE id=?', (chat_id,)).fetchone()
    if not chat or not db.execute('SELECT 1 FROM chat_members WHERE chat_id=? AND user_id=?', (chat_id, u['id'])).fetchone():
        return jsonify({'error': 'No tenés acceso a este chat'}), 403
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    db.execute('INSERT INTO chat_messages(chat_id, user_id, mensaje, adjunto, adjunto_tipo, fecha) VALUES(?,?,?,?,?,?)',
               (chat_id, u['id'], msj or None, adjunto or None, adjunto_tipo or None, now))
    db.commit()
    try:
        txt = adjunto_tipo if not msj else msj
        for m in db.execute('SELECT user_id FROM chat_members WHERE chat_id=? AND user_id<>?', (chat_id, u['id'])).fetchall():
            notify(m['user_id'], 'Nuevo mensaje', '%s: %s' % (u['nombre'], txt), 'chat', push=True)
    except Exception:
        pass
    return jsonify({'ok': True})


@app.route('/api/contactos')
@login_required
def api_contactos():
    u = current_user()
    if u['role'] == 'alumno':
        rows = get_db().execute(
            "SELECT id, nombre, cinturon, foto FROM users WHERE activo=1 AND id<>? AND role IN ('admin','profesor')",
            (u['id'],)).fetchall()
    else:
        rows = get_db().execute(
            "SELECT id, nombre, cinturon, categoria, foto FROM users WHERE activo=1 AND id<>? AND role='alumno'",
            (u['id'],)).fetchall()
    return jsonify({'contactos': [dict(r) for r in rows]})


# ---------------------------------------------------------------------------
# Video progress (no removible hasta terminar)
# ---------------------------------------------------------------------------

@app.route('/api/videos/<int:vid>/progress', methods=['POST'])
@login_required
def api_video_progress(vid):
    u = current_user()
    data = parse_json()
    seg = max(0, to_int(data.get('segundos')) or 0)
    dur = max(0, to_int(data.get('duracion')) or 0)
    db = get_db()
    v = db.execute('SELECT * FROM videos WHERE id=?', (vid,)).fetchone()
    if not v:
        return jsonify({'error': 'Video no encontrado'}), 404
    completado = 1 if (dur > 0 and seg >= dur * 0.95) else 0
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    db.execute(
        'INSERT OR IGNORE INTO video_views(video_id, user_id, fecha) VALUES(?,?,?)',
        (vid, u['id'], now))
    db.execute(
        'INSERT INTO video_progress(video_id, user_id, segundos, duracion, completado, fecha) VALUES(?,?,?,?,?,?) '
        'ON CONFLICT(video_id, user_id) DO UPDATE SET segundos=excluded.segundos, duracion=excluded.duracion, completado=MAX(video_progress.completado, excluded.completado), fecha=excluded.fecha',
        (vid, u['id'], seg, dur, completado, now))
    db.commit()
    if completado and u['role'] == 'alumno':
        chequear_logros(u['id'])
    if completado and v['subido_por']:
        notify(v['subido_por'], 'Video completado',
               '%s terminó de ver "%s"' % (u['nombre'], v['titulo']), 'info', push=True)
    return jsonify({'ok': True, 'completado': completado})


@app.route('/api/videos/<int:vid>/progress')
@login_required
def api_video_progress_get(vid):
    u = current_user()
    r = get_db().execute('SELECT * FROM video_progress WHERE video_id=? AND user_id=?',
                         (vid, u['id'])).fetchone()
    return jsonify({'progress': dict(r) if r else {'segundos': 0, 'duracion': 0, 'completado': 0}})


# ---------------------------------------------------------------------------
# Metas de entrenamiento
# ---------------------------------------------------------------------------

@app.route('/api/metas')
@login_required
def api_metas():
    u = current_user()
    filas = get_db().execute('SELECT * FROM metas WHERE user_id=? ORDER BY id DESC', (u['id'],)).fetchall()
    return jsonify({'metas': [dict(r) for r in filas]})


@app.route('/api/metas', methods=['POST'])
@login_required
def api_meta_crear():
    u = current_user()
    data = parse_json()
    titulo = (data.get('titulo') or '').strip()
    if not titulo:
        return jsonify({'error': 'Poné el título de la meta'}), 400
    obj = to_int(data.get('objetivo')) or 3
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    cur = get_db().execute('INSERT INTO metas(user_id, titulo, tipo, objetivo, fecha) VALUES(?,?,?,?,?)',
                           (u['id'], titulo, data.get('tipo') or 'semanas', obj, now))
    get_db().commit()
    return jsonify({'ok': True, 'id': cur.lastrowid})


@app.route('/api/metas/<int:meta_id>', methods=['POST'])
@login_required
def api_meta_actualizar(meta_id):
    u = current_user()
    db = get_db()
    if not db.execute('SELECT 1 FROM metas WHERE id=? AND user_id=?', (meta_id, u['id'])).fetchone():
        return jsonify({'error': 'Meta no encontrada'}), 404
    data = parse_json()
    cumplida = 1 if (data.get('cumplida') or data.get('cumplida') == 'on') else 0
    if cumplida:
        db.execute('UPDATE metas SET cumplida=1 WHERE id=?', (meta_id,))
    else:
        db.execute('UPDATE metas SET titulo=?, tipo=?, objetivo=? WHERE id=?',
                   ((data.get('titulo') or '').strip(), data.get('tipo') or 'semanas',
                    to_int(data.get('objetivo')) or 3, meta_id))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/metas/<int:meta_id>', methods=['DELETE'])
@login_required
def api_meta_borrar(meta_id):
    u = current_user()
    db = get_db()
    db.execute('DELETE FROM metas WHERE id=? AND user_id=?', (meta_id, u['id']))
    db.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Ranking (asistencia + progreso + videos vistos)
# ---------------------------------------------------------------------------

@app.route('/api/ranking')
@role_required('admin', 'profesor')
def api_ranking():
    db = get_db()
    asis = db.execute(
        'SELECT a.alumno_id AS uid, COUNT(*) AS n FROM asistencia a GROUP BY a.alumno_id').fetchall()
    vids = db.execute(
        'SELECT vv.user_id AS uid, COUNT(*) AS n FROM video_views vv GROUP BY vv.user_id').fetchall()
    comp = db.execute(
        'SELECT vp.user_id AS uid, COUNT(*) AS n FROM video_progress vp WHERE vp.completado=1 GROUP BY vp.user_id').fetchall()
    nmap = {a['uid']: a['n'] for a in asis}
    vmap = {v['uid']: v['n'] for v in vids}
    cmap = {c['uid']: c['n'] for c in comp}
    filas = db.execute(
        "SELECT id, nombre, cinturon, categoria, foto FROM users WHERE activo=1 AND role='alumno'").fetchall()
    lista = []
    for r in filas:
        punt = (nmap.get(r['id'], 0) * 2) + (cmap.get(r['id'], 0) * 5) + (vmap.get(r['id'], 0) * 1)
        lista.append({'id': r['id'], 'nombre': r['nombre'], 'cinturon': r['cinturon'],
                      'categoria': r['categoria'], 'asistencias': nmap.get(r['id'], 0),
                      'videos': vmap.get(r['id'], 0), 'completados': cmap.get(r['id'], 0), 'puntos': punt})
    lista.sort(key=lambda x: x['puntos'], reverse=True)
    return jsonify({'ranking': lista})


# ---------------------------------------------------------------------------
# Muro + galería de fotos
# ---------------------------------------------------------------------------

@app.route('/api/muro')
@login_required
def api_muro():
    filas = get_db().execute(
        'SELECT m.*, us.nombre, us.cinturon, us.foto '
        'FROM muro m JOIN users us ON us.id=m.user_id ORDER BY m.id DESC LIMIT 100').fetchall()
    db = get_db()
    out = []
    for r in filas:
        fotos = [f['data'] for f in db.execute('SELECT data FROM muro_fotos WHERE muro_id=?', (r['id'],)).fetchall()]
        out.append({**dict(r), 'fotos': fotos})
    return jsonify({'muro': out})


@app.route('/api/muro', methods=['POST'])
@login_required
def api_muro_crear():
    u = current_user()
    data = parse_json()
    texto = (data.get('texto') or '').strip()
    fotos = data.get('fotos') or []
    if not texto and not fotos:
        return jsonify({'error': 'Escribí algo o subí una foto'}), 400
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    db = get_db()
    cur = db.execute('INSERT INTO muro(user_id, texto, fecha) VALUES(?,?,?)', (u['id'], texto, now))
    mid = cur.lastrowid
    for f in fotos[:5]:
        if isinstance(f, str) and f.startswith('data:image/'):
            db.execute('INSERT INTO muro_fotos(muro_id, data) VALUES(?,?)', (mid, f))
    db.commit()
    return jsonify({'ok': True, 'id': mid})


@app.route('/api/muro/<int:muro_id>', methods=['DELETE'])
@login_required
def api_muro_borrar(muro_id):
    u = current_user()
    db = get_db()
    db.execute('DELETE FROM muro WHERE id=? AND user_id=?', (muro_id, u['id']))
    db.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Encuestas
# ---------------------------------------------------------------------------

@app.route('/api/encuestas')
@login_required
def api_encuestas():
    u = current_user()
    db = get_db()
    filas = db.execute('SELECT * FROM encuestas ORDER BY id DESC').fetchall()
    out = []
    for r in filas:
        opciones = json.loads(r['opciones']) if r['opciones'] else []
        mi_voto = db.execute('SELECT opcion FROM encuesta_votos WHERE encuesta_id=? AND user_id=?',
                             (r['id'], u['id'])).fetchone()
        conteo = []
        for i in range(len(opciones)):
            conteo.append(db.execute('SELECT COUNT(*) AS n FROM encuesta_votos WHERE encuesta_id=? AND opcion=?',
                                     (r['id'], i)).fetchone()['n'])
        out.append({**dict(r), 'opciones': opciones, 'conteo': conteo,
                    'mi_voto': mi_voto['opcion'] if mi_voto else None})
    return jsonify({'encuestas': out})


@app.route('/api/encuestas', methods=['POST'])
@role_required('admin', 'profesor')
def api_encuesta_crear():
    u = current_user()
    data = parse_json()
    titulo = (data.get('titulo') or '').strip()
    opciones = [str(x).strip() for x in (data.get('opciones') or []) if str(x).strip()]
    if not titulo or len(opciones) < 2:
        return jsonify({'error': 'Necesitás título y al menos 2 opciones'}), 400
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    cur = get_db().execute('INSERT INTO encuestas(user_id, titulo, opciones, fecha) VALUES(?,?,?,?)',
                           (u['id'], titulo, json.dumps(opciones), now))
    get_db().commit()
    return jsonify({'ok': True, 'id': cur.lastrowid})


@app.route('/api/encuestas/<int:eid>/votar', methods=['POST'])
@login_required
def api_encuesta_votar(eid):
    u = current_user()
    data = parse_json()
    opcion = to_int(data.get('opcion'))
    db = get_db()
    e = db.execute('SELECT * FROM encuestas WHERE id=?', (eid,)).fetchone()
    if not e:
        return jsonify({'error': 'Encuesta no encontrada'}), 404
    n_opts = len(json.loads(e['opciones'])) if e['opciones'] else 0
    if opcion is None or opcion < 0 or opcion >= n_opts:
        return jsonify({'error': 'Opción inválida'}), 400
    db.execute('DELETE FROM encuesta_votos WHERE encuesta_id=? AND user_id=?', (eid, u['id']))
    db.execute('INSERT INTO encuesta_votos(encuesta_id, user_id, opcion) VALUES(?,?,?)', (eid, u['id'], opcion))
    db.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Eventos y actividades
# ---------------------------------------------------------------------------

@app.route('/api/eventos')
@login_required
def api_eventos():
    filas = get_db().execute('SELECT * FROM eventos ORDER BY fecha_evento ASC').fetchall()
    db = get_db()
    u = current_user()
    out = []
    for r in filas:
        asisten = db.execute('SELECT COUNT(*) AS n FROM evento_asistencias WHERE evento_id=?', (r['id'],)).fetchone()['n']
        voy = db.execute('SELECT 1 FROM evento_asistencias WHERE evento_id=? AND user_id=?', (r['id'], u['id'])).fetchone()
        out.append({**dict(r), 'asisten_conf': asisten, 'voy': 1 if voy else 0})
    return jsonify({'eventos': out})


@app.route('/api/eventos', methods=['POST'])
@role_required('admin', 'profesor')
def api_evento_crear():
    u = current_user()
    data = parse_json()
    titulo = (data.get('titulo') or '').strip()
    if not titulo:
        return jsonify({'error': 'Poné el título del evento'}), 400
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    cur = get_db().execute(
        'INSERT INTO eventos(user_id, titulo, descripcion, fecha, hora, lugar, fecha_evento) VALUES(?,?,?,?,?,?,?)',
        (u['id'], titulo, (data.get('descripcion') or '').strip(), now,
         (data.get('hora') or '').strip(), (data.get('lugar') or '').strip(),
         (data.get('fecha_evento') or '').strip() or now[:10]))
    get_db().commit()
    return jsonify({'ok': True, 'id': cur.lastrowid})


@app.route('/api/eventos/<int:eid>/asistir', methods=['POST'])
@login_required
def api_evento_asistir(eid):
    u = current_user()
    db = get_db()
    data = parse_json()
    quitar = data.get('quitar')
    if quitar:
        db.execute('DELETE FROM evento_asistencias WHERE evento_id=? AND user_id=?', (eid, u['id']))
    else:
        db.execute('INSERT OR IGNORE INTO evento_asistencias(evento_id, user_id) VALUES(?,?)', (eid, u['id']))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/eventos/<int:eid>', methods=['DELETE'])
@role_required('admin')
def api_evento_borrar(eid):
    get_db().execute('DELETE FROM eventos WHERE id=?', (eid,))
    get_db().commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Historial financiero + asistencias (gráficos)
# ---------------------------------------------------------------------------

@app.route('/api/historial')
@role_required('admin', 'profesor')
def api_historial():
    db = get_db()
    pagos = db.execute(
        'SELECT anio, mes, COALESCE(SUM(monto),0) AS monto, COUNT(*) AS n '
        'FROM pagos GROUP BY anio, mes ORDER BY anio, mes').fetchall()
    asis = db.execute(
        'SELECT DATE(fecha) AS d, COUNT(DISTINCT alumno_id) AS n FROM asistencia '
        'WHERE fecha >= ? GROUP BY d ORDER BY d',
        (datetime.now().strftime('%Y-%m-01'))).fetchall()
    return jsonify({
        'pagos': [dict(r) for r in pagos],
        'asistencia': [{'fecha': r['d'], 'alumnos': r['n']} for r in asis]
    })


# ---------------------------------------------------------------------------
# MercadoPago (link de checkout)
# ---------------------------------------------------------------------------

@app.route('/api/checkout', methods=['POST'])
@login_required
def api_checkout():
    """Genera un link de pago de MercadoPago para la cuota del alumno."""
    u = current_user()
    token = (get_setting('mp_access_token', '') or '').strip()
    if not token:
        return jsonify({'error': 'MercadoPago aún no está configurado'}), 400
    cuota = u['cuota_mensual'] or to_float(get_setting('default_cuota')) or 0
    if cuota <= 0:
        return jsonify({'error': 'No hay un monto de cuota definido'}), 400
    desc = 'Cuota IKIGAI VIEDMA'
    email = (u.get('username') or '') + '@alumno.local' if '@' not in (u.get('username') or '') else u.get('username')
    import urllib.request
    payload = {
        'items': [{'title': desc, 'quantity': 1, 'unit_price': float(cuota), 'currency_id': 'ARS'}],
        'back_urls': {'success': 'https://ikigai-viedma.onrender.com/app', 'failure': 'https://ikigai-viedma.onrender.com/app'},
        'auto_return': 'approved',
        'notification_url': 'https://ikigai-viedma.onrender.com/api/mp_webhook',
        'external_reference': 'cuota-%s-%d' % (u['id'], int(datetime.now().timestamp())),
    }
    req = urllib.request.Request(
        'https://api.mercadopago.com/checkout/preferences',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
        method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return jsonify({'init_point': data.get('init_point'), 'preference_id': data.get('id')})
    except Exception as e:
        return jsonify({'error': 'No se pudo crear el pago: %s' % e}), 502


@app.route('/api/mp_webhook', methods=['POST'])
def api_mp_webhook():
    """Webhook de MercadoPago: registra el aviso de pago cuando se aprueba."""
    try:
        data = request.get_json(silent=True) or {}
        ext = data.get('external_reference') or ''
        if ext.startswith('cuota-'):
            parts = ext.split('-')
            alumno_id = int(parts[1])
            now = datetime.now().strftime('%Y-%m-%d %H:%M')
            hoy = date.today()
            db = get_db()
            cur = db.execute(
                'INSERT INTO avisos_pago(alumno_id, monto, mes, anio, nota, comprobante, estado, fecha) '
                'VALUES(?,?,?,?,?,?,?,?)',
                (alumno_id, 0, hoy.month, hoy.year, 'Pago por MercadoPago', None, 'pendiente', now))
            db.commit()
            aviso_id = cur.lastrowid
            # notificar a staff
            staff = db.execute("SELECT id FROM users WHERE role IN ('admin','profesor') AND activo=1").fetchall()
            for s in staff:
                notify(s['id'], '🧾 Nuevo pago por MercadoPago',
                       'El alumno pagó por MercadoPago. Revisá y confirmá el aviso #%d.' % aviso_id,
                       'info', push=True)
        return jsonify({'ok': True})
    except Exception:
        return jsonify({'ok': True}), 200


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


@app.route('/api/mensajes/broadcast', methods=['POST'])
@role_required('admin', 'profesor')
def api_mensajes_broadcast():
    data = parse_json()
    texto = (data.get('texto') or '').strip()
    if not texto:
        return jsonify({'error': 'Escribe el mensaje para los alumnos'}), 400
    if len(texto) > 500:
        return jsonify({'error': 'El mensaje es muy largo (máx 500 caracteres)'}), 400
    titulo = data.get('titulo') or '📣 Mensaje de la academia'
    quienes = data.get('quienes') or 'alumnos'
    envio = data.get('push', True)
    who = current_user()['nombre']
    alumno_id = to_int(data.get('alumno_id'))
    if alumno_id:
        rows = get_db().execute("SELECT id, nombre FROM users WHERE id=? AND activo=1", (alumno_id,)).fetchall()
    elif quienes == 'todos':
        rows = get_db().execute("SELECT id, nombre FROM users WHERE activo=1").fetchall()
    else:
        rows = get_db().execute("SELECT id, nombre FROM users WHERE role='alumno' AND activo=1").fetchall()
    for r in rows:
        notify(r['id'], titulo, f'{texto}',
               tipo='mensaje', push=envio)
    return jsonify({'ok': True, 'destinatarios': len(rows)})


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
        #upsert: re-suscribir siempre actualiza el usuario y las claves del endpoint
        get_db().execute(
            'INSERT OR REPLACE INTO push_subs(user_id, endpoint, p256dh, auth) VALUES(?,?,?,?)',
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
    keys = ['academy_name', 'default_cuota', 'due_day', 'cargo_demora_pct', 'academy_code', 'pago_link', 'pago_alias',
            'auto_mensaje', 'auto_inact_dias', 'auto_deuda_dias', 'auto_mensaje_activo', 'logro_asist', 'logro_videos',
            'mp_access_token', 'wp_numero']
    if u['role'] == 'admin':
        keys += ['academy_color']
    return jsonify({k: get_setting(k) for k in keys})


@app.route('/api/settings', methods=['PUT'])
@role_required('admin')
def api_settings_put():
    data = parse_json()
    for k in ['academy_name', 'default_cuota', 'due_day', 'cargo_demora_pct', 'academy_code', 'academy_color', 'pago_link', 'pago_alias',
              'auto_mensaje', 'auto_inact_dias', 'auto_deuda_dias', 'auto_mensaje_activo', 'logro_asist', 'logro_videos',
              'mp_access_token', 'wp_numero']:
        if k in data and data[k] is not None:
            set_setting(k, data[k])
    return jsonify({'ok': True})


@app.route('/api/settings/aplicar_cuota', methods=['POST'])
@role_required('admin')
def api_settings_aplicar_cuota():
    cuota = to_float(get_setting('default_cuota'))
    if not cuota or cuota <= 0:
        return jsonify({'error': 'Configura una cuota mensual valida primero'}), 400
    alumnos = get_db().execute(
        "SELECT id, nombre FROM users WHERE role='alumno' AND activo=1").fetchall()
    for a in alumnos:
        get_db().execute('UPDATE users SET cuota_mensual=? WHERE id=?', (cuota, a['id']))
    get_db().commit()
    who = current_user()['nombre']
    for a in alumnos:
        notify(a['id'], 'Tu cuota cambio',
               f'{who} actualizo tu cuota mensual a ${cuota:,.0f}'.replace(',', '.'),
               'cuota')
    return jsonify({'ok': True, 'alumnos': len(alumnos)})


# ---------------------------------------------------------------------------
# Probar push manualmente (para desarrollo)
# ---------------------------------------------------------------------------

@app.route('/api/test_push', methods=['POST'])
@login_required
def api_test_push():
    u = current_user()
    n = get_db().execute('SELECT COUNT(*) AS n FROM push_subs WHERE user_id=?', (u['id'],)).fetchone()['n']
    if not n:
        return jsonify({'ok': False, 'error': 'Tu dispositivo no está suscrito a notificaciones. Abrí la app, andá a Configuración y tocá "Activar notificaciones" (o recargá la app).'}), 400
    enviados = send_push(u['id'], '✅ Notificación de prueba',
                         '¡Funciona! Si ves esto, las notificaciones push están activas.')
    return jsonify({'ok': True, 'suscripciones': n, 'enviados': enviados})


# ---------------------------------------------------------------------------
# QR de asistencia imprimible
# ---------------------------------------------------------------------------

@app.route('/qr_print')
@role_required('admin', 'profesor')
def qr_print():
    return render_template('qr_print.html')


@app.route('/qr_print.png')
@role_required('admin', 'profesor')
def qr_print_png():
    import qrcode
    url = request.host_url + '?qr=1&t=' + QR_SECRET
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png',
                    headers={'Cache-Control': 'no-cache'})


# ---------------------------------------------------------------------------

@app.route('/api/exportar_alumnos')
@role_required('admin', 'profesor')
def api_exportar_alumnos():
    rows = get_db().execute(
        """SELECT u.*,
            (SELECT COUNT(*) FROM asistencia a WHERE a.alumno_id=u.id AND a.presente=1) AS asistencias,
            (SELECT COUNT(*) FROM pagos p WHERE p.alumno_id=u.id) AS pagos_totales
           FROM users u WHERE u.role='alumno' AND u.activo=1 ORDER BY u.nombre""").fetchall()

    def cel(v):
        if v is None:
            return ''
        if isinstance(v, (int, float)):
            return str(v)
        return str(v)

    headers = ['Nombre', 'DNI', 'Direccion / Domicilio', 'Telefono', 'Celular 2',
               'Telefono tutor/padre', 'Email/Usuario',
               'Fecha de nacimiento', 'Edad', 'Peso (kg)', 'Categoria', 'Cinturon / Faixa',
               'Modalidad', 'Ficha medica', 'Contacto emergencia', 'Autoriza fotos (menores)',
               'Cuota mensual ($)', 'Estado de pago',
               'Asistencias', 'Total pagos registrados', 'Miembro desde']

    data_rows = []
    for r in rows:
        cat = (r['categoria'] or '').lower()
        if cat in ('kids', 'juveniles'):
            aut_foto = 'SI' if r['foto_ok'] else 'NO'
        else:
            aut_foto = 'N/A (adulto)'
        try:
            cs = cuota_status(r)
            estado_label = {
                'al_dia': 'Al dia',
                'por_vencer': 'Por vencer (antes del dia %s)' % (cs.get('due_day') or 10),
                'deuda': 'Deuda',
            }.get(cs['estado'], cs['estado'])
        except Exception:
            estado_label = ''
        data_rows.append([
            r['nombre'], r['dni'], r['direccion'], r['tel'], r['tel_2'], r['tel_tutor'],
            r['username'], r['nacimiento'],
            r['edad'], r['peso'], r['categoria'], r['cinturon'], r['gi_pref'],
            r['medic_info'], r['emergency_contact'], aut_foto,
            r['cuota_mensual'], estado_label,
            r['asistencias'], r['pagos_totales'],
            (r['creado'] or '')[:10],
        ])

    from xml.sax.saxutils import escape as xesc

    def x(row):
        return '<row>' + ''.join(f'<c t="inlineStr"><is><t>{xesc(str(c))}</t></is></c>' for c in row) + '</row>'
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        + x(headers)
        + ''.join(x(r) for r in data_rows)
        + '</sheetData></worksheet>'
    )

    shared = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="0" uniqueCount="0"></sst>'
    )

    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
        '<cellXfs count="1"><xf/></cellXfs>'
        '</styleSheet>'
    )

    def rels():
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                '</Relationships>')

    def content_types():
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
                '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                '</Types>')

    def workbook():
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="Alumnos Activos" sheetId="1" r:id="rId1"/></sheets></workbook>')

    def workbook_rels():
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
                '</Relationships>')

    def core():
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
                'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                '<dc:creator>IKIGAI VIEDMA</dc:creator>'
                '<cp:lastModifiedBy>IKIGAI VIEDMA</cp:lastModifiedBy>'
                '<dcterms:created xsi:type="dcterms:W3CDTF">' + datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ') + '</dcterms:created>'
                '</cp:coreProperties>')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types())
        z.writestr('_rels/.rels', rels())
        z.writestr('docProps/core.xml', core())
        z.writestr('xl/workbook.xml', workbook())
        z.writestr('xl/_rels/workbook.xml.rels', workbook_rels())
        z.writestr('xl/worksheets/sheet1.xml', sheet_xml)
        z.writestr('xl/styles.xml', styles)
        z.writestr('xl/sharedStrings.xml', shared)
    buf.seek(0)

    from flask import send_file
    return send_file(buf, as_attachment=True, download_name='alumnos_activos.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)),
            debug=os.environ.get('FLASK_DEBUG', '0') == '1')
