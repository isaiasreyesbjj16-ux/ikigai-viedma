"""Renderiza el dashboard real (con sesion) a un HTML estatico para poder
sacarle una captura y revisar como queda el fondo con el logo."""
import os
import re

import app as A

A.app.config['TESTING'] = True
c = A.app.test_client()
r = c.post('/api/login', json={'username': os.environ.get('IK_USER', 'admin'),
                               'password': os.environ.get('IK_PASS', 'admin123')})
if r.status_code != 200:
    print('login fallo:', r.status_code, r.get_data(as_text=True)[:200])
    raise SystemExit(1)
r = c.get('/app')
html = r.get_data(as_text=True)
html = html.replace('<head>', '<head><base href="http://127.0.0.1:5077/">', 1)
# se saca app.js para que no vacie el contenido y quedamos con la maqueta real
html = re.sub(r'<script src="/static/app\.js[^"]*"></script>', '', html)
html = re.sub(r'<script src="/static/jsQR\.js"></script>', '', html)

tarjetas = '''
<div class="content">
  <div class="card">
    <h3>Mi estado de cuenta</h3>
    <p class="small">Tu cuota mensual es <b>$18.000</b> · se considera paga hasta el día 10 del mes.</p>
    <div class="flex space-between"><span>Cuota de 10/2026</span><span class="tag tag-al-dia">Al día ✓</span></div>
    <button class="btn primary btn-block mt">🧾 Mandar comprobante de pago</button>
  </div>
  <div class="card">
    <h3>👨‍👩‍👧 Cuota familiar · Familia Rodríguez</h3>
    <p class="small">Con 2 o más integrantes, todos pagan con descuento. Mandá un solo comprobante.</p>
    <div class="flex space-between" style="padding:5px 0"><span>Ana Rodríguez · Esposa</span><span><b>$16.200</b></span></div>
    <div class="flex space-between" style="padding:5px 0"><span>Leo Rodríguez · Hijo/a</span><span><b>$16.200</b> <span class="tag tag-por-vencer">esperando</span></span></div>
    <button class="btn warn btn-block mt">🧾 Mandar comprobante de la cuota familiar</button>
  </div>
  <div class="card">
    <h3>Mis pagos</h3>
    <table><tr><th>Fecha</th><th>Mes</th><th>Método</th><th>Monto</th></tr>
    <tr><td>02/10/2026</td><td>10/2026</td><td>Transferencia</td><td><b>$18.000</b></td></tr></table>
  </div>
</div>
'''
html = html.replace('</main>', tarjetas + '</main>', 1) if '</main>' in html else html + tarjetas
destino = 'static/_prueba_dash.html'
open(destino, 'w', encoding='utf-8').write(html)
print('ok:', destino, len(html), 'bytes; login como', os.environ.get('IK_USER', 'admin'))