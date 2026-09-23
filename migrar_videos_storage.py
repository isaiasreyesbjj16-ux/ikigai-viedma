# Mueve los videos que hoy viven como base64 en la base hacia Supabase Storage.
#
# Uso (desde tu PC, no en Render):
#   setx DATABASE_URL "postgresql://..."        (o export en Linux/Mac)
#   setx SUPABASE_URL "https://xxxx.supabase.co"
#   setx SUPABASE_SERVICE_ROLE_KEY "eyJ..."
#   python migrar_videos_storage.py
#
# Opcional: SUPABASE_BUCKET (default "ikigai-media").
#
# Solo se mueven videos de hasta 50MB (límite del plan gratis de Supabase);
# los más grandes quedan en la base (comportamiento híbrido). Es idempotente:
# volvé a correrlo las veces que quieras.

import os
import re
import base64
import json
import sys
import time
import urllib.request
import urllib.error

STORAGE_MAX = 50 * 1024 * 1024
EXT_MIME = {'.mp4': 'video/mp4', '.webm': 'video/webm', '.ogg': 'video/ogg', '.mov': 'video/quicktime'}

DB_URL = os.environ.get('DATABASE_URL') or ''
SUPABASE_URL = (os.environ.get('SUPABASE_URL') or '').rstrip('/')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or ''
SUPABASE_BUCKET = (os.environ.get('SUPABASE_BUCKET') or 'ikigai-media').strip().lower()

if not DB_URL or not SUPABASE_URL or not SUPABASE_KEY:
    print('Faltan variables. Necesitas: DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY')
    sys.exit(1)


def ext_from_mime(mime):
    for e, m in EXT_MIME.items():
        if m == mime:
            return e
    return '.mp4'


def storage_request(method, path, body=None, ctype=None, timeout=180):
    req = urllib.request.Request(SUPABASE_URL + '/storage/v1' + path, data=body, method=method)
    req.add_header('apikey', SUPABASE_KEY)
    req.add_header('Authorization', 'Bearer ' + SUPABASE_KEY)
    if ctype:
        req.add_header('Content-Type', ctype)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def ensure_bucket():
    body = json.dumps({'name': SUPABASE_BUCKET, 'public': True,
                       'file_size_limit': STORAGE_MAX}).encode('utf-8')
    status, _ = storage_request('POST', '/bucket', body=body, ctype='application/json')
    return status in (200, 201, 400, 409, 423)


def upload(key, raw, ctype):
    status, _ = storage_request(
        'POST', '/object/%s/%s' % (SUPABASE_BUCKET, key), body=raw, ctype=ctype)
    if status in (200, 201):
        return '%s/storage/v1/object/public/%s/%s' % (SUPABASE_URL, SUPABASE_BUCKET, key)
    return None


def connect():
    if DB_URL.startswith('postgres'):
        import psycopg
        return psycopg.connect(DB_URL)
    if DB_URL.startswith('sqlite'):
        import sqlite3
        return sqlite3.connect(DB_URL)
    raise SystemExit('DATABASE_URL debe ser postgres://... o sqlite:///...')


def migrate(conn, dry):
    cur = conn.cursor()
    moved = kept = errors = 0
    # videos: data es base64 puro
    cur.execute("SELECT id, url, data, titulo FROM videos WHERE data IS NOT NULL AND data <> '' ORDER BY id")
    for vid, url, data, titulo in cur.fetchall():
        try:
            raw = base64.b64decode(data)
        except Exception as e:
            print('  [!] video %s dañado (%s)' % (vid, e))
            errors += 1
            continue
        if len(raw) > STORAGE_MAX:
            kept += 1
            print('  [=] video %s (%dMB) grande, queda en la base' % (vid, len(raw) // (1024 * 1024)))
            continue
        key = 'videos/%s%s' % (os.urandom(8).hex(), ext_from_mime(EXT_MIME.get(os.path.splitext(url or 'x.mp4')[1].lower())))
        ctype = EXT_MIME.get(os.path.splitext(url or 'x.mp4')[1].lower(), 'video/mp4')
        pub = upload(key, raw, ctype) if not dry else '%s/public/%s' % (SUPABASE_URL, key)
        if not pub:
            print('  [x] video %s (upload falló)' % vid)
            errors += 1
            continue
        if not dry:
            conn.execute("UPDATE videos SET url=%s, data='' WHERE id=%s" if DB_URL.startswith('postgres')
                         else "UPDATE videos SET url=?, data='' WHERE id=?", (pub, vid))
            conn.commit()
        moved += 1
        print('  [->] video %s "%s" movido' % (vid, (titulo or '')[:40]))
    # muro_videos: data es data-URI
    cur.execute("SELECT id, url, data FROM muro_videos WHERE data IS NOT NULL AND data <> '' ORDER BY id")
    for mid, url, data in cur.fetchall():
        m = re.match(r'^data:([^;]+);base64,(.+)$', data, re.S)
        if not m:
            print('  [!] muro_video %s no es data-URI, queda' % mid)
            kept += 1
            continue
        try:
            raw = base64.b64decode(m.group(2))
        except Exception as e:
            print('  [!] muro_video %s dañado (%s)' % (mid, e))
            errors += 1
            continue
        if len(raw) > STORAGE_MAX:
            kept += 1
            print('  [=] muro_video %s (%dMB) grande, queda en la base' % (mid, len(raw) // (1024 * 1024)))
            continue
        key = 'muro/%s%s' % (os.urandom(8).hex(), ext_from_mime(m.group(1)))
        pub = upload(key, raw, m.group(1)) if not dry else '%s/public/%s' % (SUPABASE_URL, key)
        if not pub:
            print('  [x] muro_video %s (upload falló)' % mid)
            errors += 1
            continue
        if not dry:
            conn.execute("UPDATE muro_videos SET url=%s, data='' WHERE id=%s" if DB_URL.startswith('postgres')
                         else "UPDATE muro_videos SET url=?, data='' WHERE id=?", (pub, mid))
            conn.commit()
        moved += 1
        print('  [->] muro_video %s movido' % mid)
    print('---')
    print('movidos: %d | grandes que quedaron: %d | errores: %d' % (moved, kept, errors))


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if dry:
        print('Modo ensayo (--dry): NO se toca la base')
    print('Conectando a la base...')
    conn = connect()
    print('Asegurando bucket "%s"...' % SUPABASE_BUCKET)
    if not ensure_bucket():
        print('No pude crear/acceder el bucket. Revisá SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.')
        sys.exit(1)
    t0 = time.time()
    migrate(conn, dry)
    print('Tiempo: %.1fs' % (time.time() - t0))