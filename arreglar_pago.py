# Ver los pagos registrados de Jairo Crespo y Fabio F. Fioravanti para corregir
# el caso "pagaron antes del vencimiento pero subieron el comprobante tarde".
#
# Uso (en tu PC, terminal NUEVA después del setx):
#   setx DATABASE_URL "postgresql://..."   (si no la tenés puesta todavía)
#   python arreglar_pago.py
#
# No modifica nada: solo muestra el estado actual.

import os
import sys

DB_URL = os.environ.get('DATABASE_URL') or ''
if not DB_URL:
    print('Falta DATABASE_URL. Corré:  setx DATABASE_URL "postgresql://..."  y abrí una terminal nueva.')
    sys.exit(1)

import psycopg

conn = psycopg.connect(DB_URL)
cur = conn.cursor()

cur.execute("""SELECT id, nombre, cuota_mensual, role, activo FROM users
               WHERE nombre ILIKE '%crespo%' OR nombre ILIKE '%fioravanti%'
               ORDER BY nombre""")
users = cur.fetchall()
if not users:
    print('No encontré ningún usuario con "crespo" o "fioravanti".')
    sys.exit(1)

for uid, nombre, cuota, role, activo in users:
    print('=' * 70)
    print('USUARIO id=%s | %s | cuota_mensual=%s | %s | activo=%s' % (uid, nombre, cuota, role, activo))
    cur.execute("""SELECT id, anio, mes, monto, metodo, concepto, nota, fecha, registrado_por
                   FROM pagos WHERE alumno_id=%s
                   ORDER BY anio DESC, mes DESC, id DESC LIMIT 8""", (uid,))
    for r in cur.fetchall():
        print('  PAGO  id=%s | %s/%s | $%s | %s | %s | nota=%s | registrado=%s'
              % (r[0], r[1], r[2], r[3], r[4] or '', r[6] or '', r[7] or '', r[8]))
    cur.execute("""SELECT id, anio, mes, monto, nota, estado, fecha
                   FROM avisos_pago WHERE alumno_id=%s
                   ORDER BY id DESC LIMIT 5""", (uid,))
    for r in cur.fetchall():
        print('  AVISO id=%s | %s/%s | $%s | %s | estado=%s | %s'
              % (r[0], r[1], r[2], r[3], r[4] or '', r[5], r[6]))

conn.close()