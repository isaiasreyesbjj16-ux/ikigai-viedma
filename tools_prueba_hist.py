"""Prueba la seccion Historial renderizandola con datos de ejemplo, para ver si
los graficos se ven de verdad (el bug era una variable de color inexistente)."""
import json

hoy = 10
pagos = [{'anio': 2026, 'mes': m, 'monto': 15000 * (m % 4 + 1), 'n': m % 4 + 1} for m in range(1, hoy + 1)]
asistencia = [{'fecha': '2026-10-%02d' % d, 'alumnos': (d % 5) + 1} for d in range(1, hoy + 1)]

html = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>historial</title>
<link rel="stylesheet" href="style.css?v=33"></head>
<body class="dash-body">
<div class="content" style="padding-top:70px"><div id="sec-historial" class="sec"></div></div>
<script>
window.USER = {"id":1,"role":"admin","nombre":"Admin","username":"admin"};
window.DIAS = ['Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo'];
window.BELTS_ADULT = ['Blanco','Azul']; window.BELTS_KIDS = ['Blanco','Azul']; window.BELTS_JUV = ['Blanco','Azul'];
window.CATEGORIAS = ['adulto','juveniles','kids'];
window.TIPOS_CLASE = ['Gi','NoGi','Kids','Juveniles','Abierto'];
window.METODOS = ['Efectivo','Transferencia'];
</script>
<script src="app.js"></script>
<script>
var DATOS = %s;
async function api(path) { return DATOS; }
window.addEventListener('load', function () {
  renderHistorial(document.getElementById('sec-historial'));
  document.getElementById('sec-historial').classList.add('active');
  setTimeout(function () {
    var barras = document.querySelectorAll('#sec-historial div[style*="border-radius"]');
    var sinColor = 0;
    barras.forEach(function (b) {
      var bg = getComputedStyle(b).backgroundColor;
      if (!bg || bg === 'rgba(0, 0, 0, 0)') sinColor++;
    });
    document.title = 'barras=' + barras.length + ' invisibles=' + sinColor;
  }, 700);
});
</script>
</body></html>
""" % json.dumps({'pagos': pagos, 'asistencia': asistencia}, ensure_ascii=False)
open('static/_prueba_hist.html', 'w', encoding='utf-8').write(html)
print('ok: static/_prueba_hist.html con %d meses de pagos' % len(pagos))