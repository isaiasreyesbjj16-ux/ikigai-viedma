/* Academia BJJ - app.js */
const BELTS_ADULT = window.BELTS_ADULT || ['Blanco', 'Azul', 'Púrpura', 'Marrón', 'Negro'];
const BELTS_KIDS = window.BELTS_KIDS || ['Gris', 'Amarillo', 'Naranja', 'Verde', 'Blanco'];
const BELTS_JUV = window.BELTS_JUV || ['Blanco', 'Gris', 'Amarillo', 'Naranja', 'Verde'];
const catLabel = (c) => ({ adulto: 'Adulto', juveniles: 'Juveniles', kids: 'Kids' })[c] || c;
const BELTS_POR_CAT = { kids: BELTS_KIDS, juveniles: BELTS_JUV, adulto: BELTS_ADULT };
const CATS_VIDEOS = ['kids', 'juveniles', 'adulto']; // todas las categorías para staff
function beltOptionsPorCategoriaConTodos(catSeleccionada, beltSel) {
  const opts = BELTS_POR_CAT[catSeleccionada] || BELTS_ADULT;
  return `<option value="Todos">Todos</option>` + opts.map(b => `<option ${b === beltSel ? 'selected' : ''}>${esc(b)}</option>`).join('');
}

function verTerminos() {
  const m = $('#tycModal');
  if (!m) return;
  m.style.display = 'flex';
}
function cerrarTerminos() {
  const m = $('#tycModal');
  if (m) m.style.display = 'none';
}
async function aceptarTerminosHoy() {
  try {
    const r = await api('/api/terminos/aceptar', { method: 'POST', body: {} });
    if (r.ok && r.acepto_tyc && window.USER) window.USER.acepto_tyc = r.acepto_tyc;
    toast('Gracias por aceptar los términos ✓');
    cerrarTerminos();
  } catch (e) { toast(e.message); }
}

const $ = (s, e) => (e || document).querySelector(s);
const $$ = (s, e) => [...(e || document).querySelectorAll(s)];
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = (s) => (s == null ? '' : Number(s).toLocaleString('es-AR'));
const normBelt = (s) => (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

function beltHTML(cinturon) {
  if (!cinturon) return '—';
  return `<span class="belt"><span class="belt-dot bel-${normBelt(cinturon)}"></span>${esc(cinturon)}</span>`;
}

function toast(msg, ms = 3200) {
  const t = $('#toast');
  t.textContent = msg;
  t.className = 'toast show';
  if (/✓|✅|correcto|guardad|actualizad|enviad|cread/.test(msg)) t.classList.add('ok');
  else if (/error|inválid|no se puede|rechazad|falta|conecta/i.test(msg)) t.classList.add('err');
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove('show'), ms);
}

function vib(ms) { if (navigator.vibrate) { try { navigator.vibrate(ms || 12); } catch (e) {} } }

function secHeader(title, sub) {
  return `<div class="sec-head"><span class="brand">IKIGAI · VIEDMA</span>
    <h2 class="sec-title">${title}</h2>${sub ? `<div class="sec-sub">${sub}</div>` : ''}</div>`;
}

function msgShow(el, text, ok) {
  el.textContent = text;
  el.className = 'msg ' + (ok ? 'ok' : 'error');
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  let data = {};
  try { data = await res.json(); } catch (e) {}
  if (!res.ok && !data.ok) throw new Error(data.error || 'Error de servidor');
  return data;
}

function openModal(html) { $('#modalBody').innerHTML = html; $('#modal').hidden = false; }
function closeModal() { $('#modal').hidden = true; }
$('#modalClose') && $('#modalClose').addEventListener('click', closeModal);
$('#modal') && $('#modal').addEventListener('click', (e) => { if (e.target === $('#modal')) closeModal(); });

/* =====================================================================
   PAGINA DE LOGIN / REGISTRO
   ===================================================================== */
if ($('#tab-login')) initLogin();
function initLogin() {
  const cats = ['adulto', 'juveniles', 'kids'];
  function fillBelts(sel, cat) {
    const opts = BELTS_POR_CAT[cat === 'adulto' ? 'adulto' : (cat === 'juveniles' ? 'juveniles' : 'kids')] || BELTS_ADULT;
    sel.innerHTML = opts.map(b => `<option value="${esc(b)}">${esc(b)}</option>`).join('');
  }
  fillBelts($('#regAlumnoCinturon'), 'adulto');
  fillBelts($('#regProfeCinturon'), 'adulto');
  $('#regAlumnoCat').addEventListener('change', (e) => {
    fillBelts($('#regAlumnoCinturon'), e.target.value);
    const menor = e.target.value === 'kids' || e.target.value === 'juveniles';
    const tf = $('#tutorFields');
    if (tf) tf.style.display = menor ? '' : 'none';
    const tt = $('#regAlumnoTelTutor');
    if (tt) tt.required = menor;
  });

  $$('.tab').forEach(t => t.addEventListener('click', () => {
    $$('.tab').forEach(x => x.classList.remove('active'));
    $$('.tabpanel').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    $('#tab-' + t.dataset.tab).classList.add('active');
    $('#loginMsg').className = 'msg';
  }));

  try { fetch('/api/settings').then(r => r.json()).then(s => {
    if (s.academy_name) { $('#academyTitle').textContent = s.academy_name; document.title = s.academy_name; }
  }).catch(() => {}); } catch (e) {}

  $('#tab-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    const m = $('#loginMsg');
    try {
      const d = await api('/api/login', { method: 'POST', body: {
        username: $('#loginUser').value.trim(), password: $('#loginPass').value } });
      if (d.ok) location.href = '/app';
    } catch (err) { msgShow(m, err.message, false); }
  });

  $('#btnOlvidada').addEventListener('click', () => abrirModalRecuperar());

  $('#tab-reg-alumno').addEventListener('submit', async (e) => {
    e.preventDefault();
    const m = $('#loginMsg');
    try {
      const d = await api('/api/register', { method: 'POST', body: {
        role: 'alumno', username: $('#regAlumnoUser').value.trim(),
        password: $('#regAlumnoPass').value, nombre: $('#regAlumnoNombre').value.trim(),
        edad: $('#regAlumnoEdad').value, peso: $('#regAlumnoPeso').value,
        categoria: $('#regAlumnoCat').value, cinturon: $('#regAlumnoCinturon').value,
        gi_pref: $('#regAlumnoGi').value, tel: $('#regAlumnoTel')?.value || '',
        dni: $('#regAlumnoDni')?.value.trim() || '', direccion: $('#regAlumnoDir')?.value.trim() || '',
        tel_tutor: $('#regAlumnoTelTutor')?.value || '', tel_2: $('#regAlumnoTel2')?.value || '',
        foto_ok: !!($('#regAlumnoFoto')?.checked || false),
        acepto_tyc: !!($('#regAlumnoTyC')?.checked || false) } });
      if (d.ok) location.href = '/app';
    } catch (err) { msgShow(m, err.message, false); }
  });

  $('#tab-reg-profesor').addEventListener('submit', async (e) => {
    e.preventDefault();
    const m = $('#loginMsg');
    try {
      const d = await api('/api/register', { method: 'POST', body: {
        role: 'profesor', username: $('#regProfeUser').value.trim(),
        password: $('#regProfePass').value, nombre: $('#regProfeNombre').value.trim(),
        codigo: $('#regProfeCodigo').value.trim(), edad: $('#regProfeEdad').value,
        peso: $('#regProfePeso').value, cinturon: $('#regProfeCinturon').value,
        acepto_tyc: !!($('#regProfeTyC')?.checked || false) } });
      if (d.ok) location.href = '/app';
    } catch (err) { msgShow(m, err.message, false); }
  });
}

/* =====================================================================
   DASHBOARD
   ===================================================================== */
if ($('#content')) initDashboard();

function initDashboard() {
  const R = USER.role;
  $('#userRoleLabel').textContent = R === 'admin' ? 'Administrador' : R === 'profesor' ? 'Profesor' : 'Alumno';
  $('#academyName').textContent = window.ACADEMY_NAME || 'IKIGAI VIEDMA';

  // barra de navegación inferior estilo Instagram
  const items = [
    { sec: 'inicio', ico: '🏠', lbl: 'Inicio' },
    { sec: 'horarios', ico: '📅', lbl: 'Horarios' },
  ];
  if (R === 'alumno') items.push({ sec: 'mispagos', ico: '🧾', lbl: 'Cuota' });
  else items.push({ sec: 'pagos', ico: '💳', lbl: 'Pagos' });
  items.push({ sec: 'videos', ico: '🎥', lbl: 'Videos' });
  items.push({ sec: 'perfil', ico: '👤', lbl: 'Perfil' });

  $('#bottombar').innerHTML = items.map(i =>
    `<button class="bb-item" data-sec="${i.sec}"><span class="bb-ico">${i.ico}</span><span>${i.lbl}</span></button>`
  ).join('');
  $$('#bottombar .bb-item').forEach(b => b.addEventListener('click', () => {
    $$('#bottombar .bb-item').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    showSec(b.dataset.sec);
  }));

  // gesto táctil: deslizar para cambiar de sección
  const secOrder = items.map(i => i.sec);
  let tX = 0, tY = 0, tEl = null;
  const content = $('#content');
  content.addEventListener('touchstart', (e) => {
    if (e.touches.length !== 1) return;
    tX = e.touches[0].clientX; tY = e.touches[0].clientY;
    tEl = e.target;
  }, { passive: true });
  content.addEventListener('touchend', (e) => {
    if (tEl == null) return;
    if (e.changedTouches.length !== 1) return;
    const dx = e.changedTouches[0].clientX - tX;
    const dy = e.changedTouches[0].clientY - tY;
    tEl = null;
    if (Math.abs(dx) < 65 || Math.abs(dx) < Math.abs(dy)) return;
    if (e.target.closest && e.target.closest('table, .semana, [style*="overflow"], input, select, .asCheck, .alum-actions')) return;
    const activeEl = Array.from($$('.sec')).find(s => s.classList.contains('active'));
    const cur = secOrder.indexOf(activeEl ? activeEl.id.replace('sec-', '') : 'inicio');
    const next = dx < 0 ? cur + 1 : cur - 1;
    if (next < 0 || next >= secOrder.length) return;
    vib(10);
    showSec(secOrder[next]);
  }, { passive: true });

  $('#logoutBtn').addEventListener('click', async () => {
    await api('/api/logout', { method: 'POST' }).catch(() => {});
    location.href = '/';
  });

  // notificaciones
  $('#bellBtn').addEventListener('click', () => {
    const p = $('#notifPanel');
    p.hidden = !p.hidden;
    if (!p.hidden) loadNotifs();
  });
  // tema claro/oscuro
  applyTheme(localStorage.getItem('ikigai_tema') || 'dark');
  $('#themeBtn').addEventListener('click', () => {
    applyTheme(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light');
  });
  $('#markAllRead').addEventListener('click', async () => {
    await api('/api/notificaciones/leer_todas', { method: 'POST' }).catch(() => {});
    loadNotifs();
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#bellBtn') && !e.target.closest('#notifPanel')) $('#notifPanel').hidden = true;
  });
  setInterval(() => { if ($('#notifPanel').hidden) refreshBadge(); }, 20000);
  refreshBadge();

  // push + instalación PWA
  setupPush();
  setupInstall();

  showSec('inicio');

  // Si el usuario aún no aceptó los Términos y Condiciones, mostrarlos
  try {
    if (window.USER && !window.USER.acepto_tyc) {
      setTimeout(() => verTerminos(), 800);
    }
  } catch (e) {}

  // QR auto-asistencia: si la URL tiene ?qr=1, marcar presente automáticamente
  if (new URLSearchParams(location.search).get('qr') === '1' && R === 'alumno') {
    marcarAsistenciaQR();
  }
}

function showSec(name) {
  $$('.sec').forEach(s => s.classList.remove('active'));
  let el = $('#sec-' + name);
  if (!el) {
    const div = document.createElement('div');
    div.className = 'sec';
    div.id = 'sec-' + name;
    $('#content').appendChild(div);
    el = div;
  }
  el.classList.add('active');
  $$('#bottombar .bb-item').forEach(x => x.classList.toggle('active', x.dataset.sec === name));
  vib(8);
  const renderers = {
    inicio: renderInicio, perfil: renderPerfil, horarios: renderHorarios,
    pagos: renderPagos, mispagos: renderMisPagos, alumnos: renderAlumnos,
    asistencia: renderAsistencia, deudores: renderDeudores,
    profesores: renderProfesores, config: renderConfig,
    mi_asistencia: renderMiAsistencia, videos: renderVideos,
    chat: renderChat, muro: renderMuro, galeria: renderGaleria,
    ranking: renderRanking, metas: renderMetas, encuestas: renderEncuestas,
    eventos: renderEventos, historial: renderHistorial,
  };
  if (renderers[name]) renderers[name](el);
}

/* ---------- NOTIFICACIONES ---------- */
async function refreshBadge() {
  try {
    const d = await api('/api/notificaciones');
    const b = $('#bellBadge');
    if (d.no_leidas > 0) { b.textContent = d.no_leidas; b.hidden = false; }
    else b.hidden = true;
  } catch (e) {}
}

async function loadNotifs() {
  const d = await api('/api/notificaciones');
  refreshBadge();
  const el = $('#notifList');
  if (!d.notificaciones.length) { el.innerHTML = '<div class="empty">Sin notificaciones</div>'; return; }
  el.innerHTML = d.notificaciones.map(n => `
    <div class="notif-item ${n.leida ? '' : 'unread'}" onclick="markRead(${n.id})">
      <span class="n-title">${esc(n.titulo)}</span>
      <span class="n-msg">${esc(n.mensaje)}</span>
      <small>${esc(n.fecha)}</small>
    </div>`).join('');
}
async function markRead(id) {
  await api('/api/notificaciones/' + id, { method: 'POST' }).catch(() => {});
  loadNotifs();
}

/* ---------- PUSH ---------- */
async function setupPush() {
  if (!('serviceWorker' in navigator)) return;
  try {
    await navigator.serviceWorker.register('/sw.js');
    const keyRes = await (await fetch('/api/vapid_public_key')).json();
    const reg = await navigator.serviceWorker.ready;
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(keyRes.key),
      });
    }
    await api('/api/push_subscribe', { method: 'POST', body: { subscription: sub.toJSON() } });
  } catch (e) { /* push no disponible (http/https) o permiso denegado */ }
}
function urlBase64ToUint8Array(base64) {
  const pad = '='.repeat((4 - base64.length % 4) % 4);
  const b64 = (base64 + pad).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(b64);
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}

/* ---------- AVATAR / FOTO ---------- */
function avatarHTML(foto, nombre, size) {
  const initial = esc((nombre || '?')[0].toUpperCase());
  const cls = 'avatar ' + (size || '');
  return `<span class="${cls}">${foto ? `<img src="${esc(foto)}" onerror="this.parentNode.innerHTML='${initial}'">` : initial}</span>`;
}

function setupFoto() {
  const input = $('#fotoInput');
  if (!input) return;
  input.addEventListener('change', async () => {
    const file = input.files && input.files[0];
    if (!file) return;
    if (!/^image\/(png|jpe?g|webp)/.test(file.type)) { toast('Elegí una imagen (JPG o PNG)'); return; }
    if (file.size > 5 * 1024 * 1024) { toast('La imagen es muy grande (máx 5MB)'); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const d = await api('/api/foto', { method: 'POST', body: { foto: reader.result } });
        toast('Foto de perfil actualizada ✓');
        USER.foto = d.foto;
        renderPerfil($('#sec-perfil'));
      } catch (err) { toast(err.message); }
    };
    reader.readAsDataURL(file);
  });
}

/* ---------- INSTALAR APP (PWA) ---------- */
let deferredPrompt = null;
function setupInstall() {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    const btn = $('#instalarBtn');
    if (btn) btn.hidden = false;
  });
  const btn = $('#instalarBtn');
  if (btn) btn.addEventListener('click', () => {
    if (deferredPrompt) { deferredPrompt.prompt(); }
    else if (/Android/i.test(navigator.userAgent) || /iPhone|iPad/i.test(navigator.userAgent)) {
      toast('En el teléfono: menú ⋮ o compartir → "Agregar a pantalla de inicio"');
    } else {
      toast('En tu navegador: mirá el ícono de instalar en la barra de direcciones, o usá el menú → "Instalar app"');
    }
  });
}

/* ---------- MI ASISTENCIA (alumno) ---------- */
async function renderMiAsistencia(el) {
  const d = await api('/api/mi_asistencia');
  el.innerHTML = `
    ${secHeader('Mis asistencias')}
    <div class="feed">
      <div class="feed-card">
        <div class="stat-card" style="margin-bottom:12px"><div class="num">${d.total}</div><div class="lbl">Clases a las que asistí</div></div>
        ${d.asistencia.length ? d.asistencia.map(a => `
          <div class="flex space-between" style="padding:8px 0;border-bottom:1px solid var(--line)">
            <div><b>${esc(a.dia)} ${esc(a.hora)}</b> · <span class="tag ${a.tipo.toLowerCase()}">${esc(a.tipo)}</span></div>
            <div class="small">${esc(a.fecha)} · ${esc(a.profesor || 'Sin profesor')}</div>
          </div>`).join('') : '<div class="empty">Todavía no tenés asistencias registradas.</div>'}
      </div>
    </div>`;
}

async function marcarAsistencia(claseId) {
  try {
    await api('/api/asistencia_yo', { method: 'POST', body: { clase_id: claseId } });
    toast('¡Asistencia marcada! ✓');
    renderInicio($('#sec-inicio'));
    renderMiAsistencia($('#sec-mi_asistencia')).catch(() => {});
  } catch (err) { toast(err.message); }
}

async function marcarAsistenciaQR(qrToken) {
  try {
    const token = qrToken || new URLSearchParams(location.search).get('t') || '';
    const [horarios] = await Promise.all([api('/api/horarios')]);
    const hoyIdx = new Date().getDay() === 0 ? 6 : new Date().getDay() - 1;
    const hoyClases = horarios.horarios.filter(h => h.dia === hoyIdx);
    if (hoyClases.length === 0) { toast('No hay clases programadas para hoy'); return; }
    let marcadas = 0;
    let error403 = false;
    for (const c of hoyClases) {
      try { await api('/api/asistencia_yo', { method: 'POST', body: { clase_id: c.id, qr_token: token } }); marcadas++; }
      catch (e) { error403 = true; }
    }
    if (marcadas > 0) {
      toast(`Asistencia marcada ✓ (${marcadas} clase${marcadas > 1 ? 's' : ''})`);
      renderInicio($('#sec-inicio'));
    } else {
      toast(error403 ? 'QR no válido. Escaneá el QR físico del gimnasio.' : 'Ya tenías asistencia marcada');
    }
  } catch (err) { toast('Error al marcar asistencia'); }
}

/* ---------- ESCÁNER DE QR CON CÁMARA ---------- */
function abrirScannerQR() {
  if (typeof jsQR === 'undefined') { toast('El escáner necesita recargar la página (Ctrl+F5)'); return; }
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;background:#000;z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:20px';
  overlay.innerHTML = `
    <video playsinline muted style="width:100%;max-width:420px;border-radius:14px;max-height:65vh"></video>
    <div style="color:#fff;font-size:14px" id="qrMsg">Apuntá la cámara al código QR del gimnasio</div>
    <button class="btn" style="background:#d63031;color:#fff;border:none;padding:12px 22px;border-radius:12px" id="qrCerrar">Cerrar</button>`;
  document.body.appendChild(overlay);
  let stream = null, timer = null, cerrado = false;

  function cerrar() {
    if (cerrado) return;
    cerrado = true;
    if (timer) clearInterval(timer);
    if (stream) stream.getTracks().forEach(t => t.stop());
    overlay.remove();
  }
  overlay.querySelector('#qrCerrar').onclick = cerrar;

  const video = overlay.querySelector('video');
  const msj = (t) => { overlay.querySelector('#qrMsg').textContent = t; };
  const esIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    msj('Este navegador no soporta cámara o falta HTTPS. Probá recargar (Ctrl+F5) en la URL principal.');
  } else {
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      .then(s => {
        stream = s;
        video.srcObject = s;
        video.setAttribute('autoplay', 'true');
        video.play();
        timer = setInterval(leer, 250);
      })
      .catch(err => {
        let m = '';
        if (err && (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')) {
          m = 'Permiso de cámara denegado. Tenés que habilitar la Cámara para este sitio en los ajustes del navegador Chrome, no de una app. En Chrome: Configuración > Sitios > Cámara; o borra el permiso y recargá.';
        } else if (err && (err.name === 'NotFoundError' || err.name === 'OverconstrainedError')) {
          m = 'No se encontró cámara. Probá con la otra cámara (girar el celular).';
        } else if (err && err.name === 'NotReadableError') {
          m = 'La cámara está siendo usada por otra app. Cerrá otras apps y reintentá.';
        } else if (err && err.name === 'SecurityError') {
          m = 'Bloqueado por seguridad: necesitás HTTPS o permisos de cámara en el navegador.';
        } else {
          m = 'Error de cámara: ' + (err && err.message ? err.message : 'desconocido');
        }
        msj(m);
      });
  }

  function leer() {
    const v = video;
    if (!v.videoWidth) return;
    const c = document.createElement('canvas');
    c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
    const img = c.getContext('2d').getImageData(0, 0, c.width, c.height);
    const code = jsQR(img.data, img.width, img.height, { inversionAttempts: 'dontInvert' });
    if (code && code.data && code.data.indexOf('qr=1') !== -1) {
      clearInterval(timer);
      timer = null;
      stream.getTracks().forEach(t => t.stop());
      const tParam = new URLSearchParams(code.data.split('?')[1] || '').get('t') || '';
      overlay.querySelector('#qrMsg').textContent = tParam ? '✓ QR válido. Marcando asistencia...' : '⚠ QR sin token válido';
      marcarAsistenciaQR(tParam);
      setTimeout(cerrar, 1600);
    }
  }
}

/* =====================================================================
   VIDEOS (por cinturón)
   ===================================================================== */
function youtubeId(url) {
  const m = String(url || '').match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{6,})/);
  return m ? m[1] : null;
}

function videoMediaHTML(v) {
  if (v.tipo === 'link') {
    const yid = youtubeId(v.url);
    if (yid) return `<iframe src="https://www.youtube.com/embed/${yid}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
    return `<div class="post-media-link"><a href="${esc(v.url)}" target="_blank" rel="noopener">🔗 ${esc(v.url)}</a></div>`;
  }
  return `<video controls preload="metadata" playsinline data-vid="${v.id}" ontimeupdate="trackProgreso(event)" onended="videoTerminado(event)"><source src="${esc(v.url)}"></video>`;
}

function applyTheme(t) {
  if (t !== 'light') t = 'dark';
  document.documentElement.dataset.theme = t;
  localStorage.setItem('ikigai_tema', t);
  const ic = document.querySelector('#themeIcon');
  if (ic) ic.innerHTML = t === 'light'
    ? '<path fill="currentColor" d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41l-1.06-1.06zm1.06-10.96c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05 18.36c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z"/>'
    : '<path fill="currentColor" d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/>';
}

async function trackProgreso(e) {
  const vid = e.currentTarget;
  const id = vid.dataset.vid;
  if (!id) return;
  // guarda cada ~5s
  if (trackProgreso._last === id && (Date.now() - trackProgreso._time) < 5000) return;
  trackProgreso._last = id; trackProgreso._time = Date.now();
  try {
    await api('/api/videos/' + id + '/progress', { method: 'POST',
      body: { segundos: Math.floor(vid.currentTime), duracion: Math.floor(vid.duration || 0) } });
  } catch (e) {}
}
async function videoTerminado(e) {
  const vid = e.currentTarget;
  const id = vid.dataset.vid;
  if (!id) return;
  try {
    await api('/api/videos/' + id + '/progress', { method: 'POST',
      body: { segundos: Math.floor(vid.duration || 0), duracion: Math.floor(vid.duration || 0) } });
    toast('🎉 Video completado');
    const sec = $('#sec-videos');
    if (sec && sec.classList.contains('active')) renderVideos(sec);
  } catch (err) {}
}

function videoCardHTML(v, isStaff) {
  const beltCls = 'tag ' + (v.belt === 'Todos' ? 'alumno' : 'nogi');
  const visto = v.visto ? ' visto' : '';
  const staffBtns = isStaff ? `<div class="post-views" id="views-${v.id}"></div>` : '';
  const vistoBtn = isStaff || v.tipo === 'link'
    ? `<button class="post-btn${visto}" onclick="marcarVisto(${v.id}, this, ${v.tipo === 'link'})">✓ Visto</button>`
    : `<button class="post-btn${visto}" ${v.completado ? '' : 'disabled style=opacity:.5'} onclick="marcarVisto(${v.id}, this)">✓ Visto</button>
       <div class="small" style="color:var(--muted)">${v.completado ? 'Completado ✓ (podés marcar visto)' : (v.progreso_pct ? 'Progreso ' + v.progreso_pct + '% — mirá el video hasta el final para poder marcarlo' : 'Mirá el video hasta el final para poder marcarlo como visto')}</div>`;
  return `<div class="post-card" id="video-${v.id}">
    <div class="post-head">
      ${avatarHTML('', v.subidor_nombre || 'Profesor', 'sm')}
      <div style="flex:1">
        <b>${esc(v.subidor_nombre || 'Profesor')}</b>
        <div class="small">${esc(v.fecha || '')} · <span class="${beltCls}">${esc(v.belt)}</span> ${v.categoria ? '<span class="tag alumno">' + catLabel(v.categoria) + '</span>' : ''}</div>
      </div>
      ${isStaff && v.subido_por === USER.id || USER.role === 'admin' ? `<button class="btn bad small" onclick="borrarVideo(${v.id})">🗑</button>` : ''}
    </div>
    <div class="post-media">${videoMediaHTML(v)}</div>
    <div class="post-actions">
      ${vistoBtn}
      <span class="post-count">👁 ${v.vistas} visto${v.vistas === 1 ? '' : 's'}</span>
      ${isStaff ? `<button class="post-btn" onclick="toggleVistos(${v.id})">Quién lo vio</button>` : ''}
    </div>
    <div class="post-caption">
      <b>${esc(v.titulo)}</b>${v.descripcion ? '<div>' + esc(v.descripcion) + '</div>' : ''}
    </div>
    ${staffBtns}
  </div>`;
}

async function renderVideos(el) {
  const R = USER.role;
  const isStaff = R !== 'alumno';
  const qCat = isStaff ? (($('#videoCat') && $('#videoCat').value) || 'Todas') : '';
  const qBelt = isStaff ? (($('#videoBelt') && $('#videoBelt').value) || 'Todos') : '';
  const all = await api('/api/videos' + (isStaff ? '?categoria=' + encodeURIComponent(qCat) + '&belt=' + encodeURIComponent(qBelt) : ''));
  const videos = all.videos;
  const filtros = isStaff ? `
    <div class="flex space-between mb" style="gap:6px">
      <select id="videoCat" class="search" style="max-width:130px;padding:9px">
        <option value="Todas">Todas</option>
        ${CATS_VIDEOS.map(c => `<option value="${c}" ${qCat === c ? 'selected' : ''}>${catLabel(c)}</option>`).join('')}
      </select>
      <select id="videoBelt" class="search" style="max-width:180px;padding:9px">
        <option value="Todos">Todos los cinturones</option>
        ${(BELTS_POR_CAT[qCat] || []).map(b => `<option ${b === qBelt ? 'selected' : ''}>${esc(b)}</option>`).join('')}
      </select>
      <button class="btn primary small" onclick="subirVideo()">＋ Subir video</button>
    </div>` : '<span></span>';
  el.innerHTML = `
    ${secHeader('Videos', isStaff ? 'Subí técnicas para cada cinturón y mirá quién las vio.' : 'Técnicas para tu cinturón. Mirá y marcá las que viste.')}
    ${filtros}
    <div class="feed" id="videoFeed">
      ${videos.length ? videos.map(v => videoCardHTML(v, isStaff)).join('') : '<div class="feed-card empty">Todavía no hay videos para esta categoría.</div>'}
    </div>`;
  if (isStaff) {
    const catSel = $('#videoCat'), beltSel = $('#videoBelt');
    catSel.addEventListener('change', () => {
      const c = catSel.value;
      beltSel.innerHTML = `<option value="Todos">Todos los cinturones</option>` +
        (BELTS_POR_CAT[c] || []).map(b => `<option>${esc(b)}</option>`).join('');
      beltSel.value = 'Todos';
      renderVideos(el);
    });
    beltSel.addEventListener('change', () => renderVideos(el));
    videos.forEach(v => cargarVistos(v.id));
  }
}

async function cargarVistos(vid) {
  try {
    const d = await api('/api/videos/' + vid + '/views');
    const el = $('#views-' + vid);
    if (!el) return;
    el.innerHTML = d.vistos.length
      ? '<div class="small" style="color:var(--muted)">👁 Vieron: ' + d.vistos.map(x => '<b>' + esc(x.nombre) + '</b>').join(', ') + '</div>'
      : '<div class="small" style="color:var(--muted)">Todavía nadie lo vio.</div>';
  } catch (e) {}
}

async function toggleVistos(vid) {
  const el = $('#views-' + vid);
  if (el) el.hidden = !el.hidden;
}

async function marcarVisto(vid, btn) {
  try {
    await api('/api/videos/' + vid + '/view', { method: 'POST' });
    vib(12);
    if (btn) btn.classList.add('visto');
    toast('Marcado como visto ✓');
    const sec = $('#sec-videos');
    if (sec && sec.classList.contains('active')) renderVideos(sec);
  } catch (err) { toast(err.message); }
}

function subirVideo() {
  openModal(`
    <h3>Subir video</h3>
    <form id="vForm" class="grid2">
      <div class="field" style="grid-column:1/-1"><label>Título</label><input id="vTitulo" required placeholder="Ej: Armbar desde guardia"></div>
      <div class="field" style="grid-column:1/-1"><label>Descripción (opcional)</label><input id="vDesc" placeholder="Qué técnica es, nivel, consejos..."></div>
      <div class="field"><label>Categoría</label><select id="vCat">
        ${CATS_VIDEOS.map(c => `<option value="${c}">${catLabel(c)}</option>`).join('')}</select></div>
      <div class="field"><label>Cinturón para el que es</label><select id="vBelt"></select></div>
      <div class="field" style="grid-column:1/-1"><label>O link de YouTube</label><input id="vLink" placeholder="https://youtube.com/watch?v=..."></div>
      <div class="field" style="grid-column:1/-1"><label>O subí un archivo (MP4)</label>
        <input type="file" id="vFile" accept="video/mp4,video/webm,video/ogg,video/quicktime"></div>
      <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">Publicar video</button></div>
    </form>`);
  function fillBelt() {
    const cat = $('#vCat').value;
    $('#vBelt').innerHTML = beltOptionsPorCategoriaConTodos(cat, 'Todos');
  }
  fillBelt();
  $('#vCat').addEventListener('change', fillBelt);
  $('#vForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const titulo = $('#vTitulo').value.trim();
    const desc = $('#vDesc').value.trim();
    const belt = $('#vBelt').value;
    const categoria = $('#vCat').value;
    const file = $('#vFile').files && $('#vFile').files[0];
    const link = $('#vLink').value.trim();
    if (!file && !link) { toast('Subí un archivo o pegá un link'); return; }
    const btn = $('button[type="submit"]', $('#vForm'));
    btn.disabled = true; btn.textContent = 'Publicando...';
    try {
      if (file) {
        const fd = new FormData();
        fd.append('video', file); fd.append('titulo', titulo); fd.append('descripcion', desc); fd.append('belt', belt); fd.append('categoria', categoria);
        const res = await fetch('/api/videos/upload', { method: 'POST', body: fd });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error || 'Error al subir');
      } else {
        await api('/api/videos', { method: 'POST', body: { titulo, descripcion, belt, categoria, url: link } });
      }
      closeModal(); toast('Video publicado ✓');
      renderVideos($('#sec-videos'));
    } catch (err) { toast(err.message); btn.disabled = false; btn.textContent = 'Publicar video'; }
  });
}

async function borrarVideo(vid) {
  if (!confirm('¿Eliminar este video?')) return;
  try {
    await api('/api/videos/' + vid, { method: 'DELETE' });
    toast('Video eliminado');
    const sec = $('#sec-videos');
    if (sec && sec.classList.contains('active')) renderVideos(sec);
    renderPerfil($('#sec-perfil'));
  } catch (err) { toast(err.message); }
}

function vidThumb(v) {
  return `<div class="vid-thumb" onclick="verVideo(${v.id})" title="${esc(v.titulo)}">
    <video muted playsinline preload="metadata"><source src="${esc(v.url)}"></video>
    <span class="play">▶</span>
    <span class="vid-belt">${esc(v.belt)}</span>
  </div>`;
}

async function verVideo(vid) {
  const d = await api('/api/videos');
  const v = d.videos.find(x => x.id === vid);
  if (!v) return;
  openModal(`<h3>${esc(v.titulo)}</h3>
    <div class="post-media" style="margin:10px 0">${videoMediaHTML(v)}</div>
    <div class="flex space-between">
      <span class="${v.belt === 'Todos' ? 'tag alumno' : 'tag nogi'}">${esc(v.belt)}</span>
      <button class="btn primary small" onclick="marcarVisto(${v.id}, this)">✓ ${v.visto ? 'Ya lo vi' : 'Marcar como visto'}</button>
    </div>`);
}

/* =====================================================================
   INICIO
   ===================================================================== */
async function renderInicio(el) {
  const R = USER.role;
  if (R === 'alumno') {
    const [me, asis, horarios, vids] = await Promise.all([
      api('/api/me'), api('/api/mi_asistencia'), api('/api/horarios'), api('/api/videos')]);
    const c = me.cuota || {};
    const estado = c.estado;
    const tagMap = { al_dia: ['tag-al-dia', 'Al día'], deuda: ['tag-deuda', 'Debe la cuota'], por_vencer: ['tag-por-vencer', 'Por vencer'] };
    const [cls, lbl] = tagMap[estado] || ['tag-al-dia', 'Al día'];
    const hoyIdx = new Date().getDay() === 0 ? 6 : new Date().getDay() - 1;
    const hoyClases = horarios.horarios.filter(h => h.dia === hoyIdx);
    const videos = vids.videos.slice(0, 3);
    el.innerHTML = `
      <div class="feed">
        <div class="feed-card">
          <div class="profile-top">
            ${avatarHTML(me.foto, me.nombre, 'lg')}
            <div style="flex:1">
              <h2 style="margin:0;font-size:20px">${esc(me.nombre)}</h2>
              <div class="small">${beltHTML(me.cinturon)}${me.peso ? ' · ' + esc(me.peso) + ' kg' : ''}${me.edad ? ' · ' + esc(me.edad) + ' años' : ''}</div>
              <div class="profile-stats">
                <div class="pstat"><b>${asis.total}</b><span>clases</span></div>
                <div class="pstat"><b>${me.cuota_mensual ? '$' + num(me.cuota_mensual) : '—'}</b><span>cuota</span></div>
                <div class="pstat"><b>${videos.length}</b><span>técnicas</span></div>
              </div>
            </div>
          </div>
        </div>

        <div class="feed-card">
          <div class="flex space-between">
            <div>
              <div class="lbl small">Estado de cuota (${c.mes}/${c.anio})</div>
              <div class="tag ${cls}" style="margin-top:6px">${lbl}</div>
            </div>
            <button class="btn ghost small" onclick="showSec('mispagos')">Ver mi cuenta</button>
          </div>
          ${estado !== 'al_dia' ? `<p class="small" style="color:#ff9b8f;margin-bottom:0">⚠️ Aboná tu cuota y <b>mandá el comprobante de pago</b>${me.pago_alias ? ' (por transferencia al alias/CVU de la academia)' : ''}. El pago se confirma solo cuando el profe/admin lo revisa.</p><button class="btn primary btn-block mt" onclick="avisarPago()">🧾 Mandar comprobante de pago</button>` : ''}
        </div>

        <div class="feed-card">
          <div class="small mb">📅 Clases de hoy</div>
          ${hoyClases.length ? hoyClases.map(h => `
            <div class="clase-item ${h.tipo.toLowerCase()}">
              <span class="hora">${esc(h.hora)}</span> · <span class="tag ${h.tipo.toLowerCase()}">${esc(h.tipo)}</span> · <span class="profe">${esc(h.profesor_nombre || 'Sin profesor')}</span>
              <div style="margin-top:6px">${(asis.hoy || []).includes(h.id) ? '<span class="tag tag-al-dia">✓ Asistencia marcada</span>' : `<button class="btn primary small" onclick="abrirScannerQR()">📷 Marcar con QR</button>`}</div>
            </div>`).join('') : '<div class="small" style="color:var(--muted)">Hoy no hay clases cargadas. Mirá la sección Horarios.</div>'}
        </div>

        ${videos.length ? `<div class="post-card" style="padding:0;overflow:hidden">
          <div class="post-head" style="padding:10px 14px 0"><b style="color:var(--accent2)">🎥 Técnicas para vos (${esc(me.cinturon)})</b></div>
          <div class="feed" style="margin:0;padding:10px 14px 14px">${videos.map(v => videoCardHTML(v, false)).join('')}</div>
        </div>` : ''}

        <div class="chips">
          <button class="chip" onclick="showSec('horarios')">📅 Horarios</button>
          <button class="chip" onclick="showSec('videos')">🎥 Videos</button>
          <button class="chip" onclick="showSec('mispagos')">🧾 Mi cuota</button>
          <button class="chip" onclick="showSec('mi_asistencia')">✅ Mi asistencia</button>
          <button class="chip" onclick="showSec('metas')">🎯 Mis metas</button>
          <button class="chip" onclick="showSec('muro')">📢 Muro</button>
          <button class="chip" onclick="showSec('chat')">💬 Chat</button>
          <button class="chip" onclick="showSec('eventos')">🗓️ Eventos</button>
          <button class="chip" onclick="showSec('encuestas')">📊 Encuestas</button>
          <button class="chip" onclick="abrirScannerQR()">📷 Escanear QR</button>
        </div>
      </div>`;
  } else {
    const [stats, horarios, vids, cums] = await Promise.all([
      api('/api/estadisticas'), api('/api/horarios'), api('/api/videos'), api('/api/cumpleanios')]);
    const hoyIdx = new Date().getDay() === 0 ? 6 : new Date().getDay() - 1;
    const hoyClases = horarios.horarios.filter(h => h.dia === hoyIdx);
    const videos = vids.videos.slice(0, 3);
    const chips = [
      `<button class="chip" onclick="showSec('horarios')">📅 Horarios</button>`,
      `<button class="chip" onclick="showSec('pagos')">💳 Registrar pago</button>`,
      `<button class="chip" onclick="showSec('alumnos')">🥋 Alumnos</button>`,
      `<button class="chip" onclick="showSec('asistencia')">✅ Asistencia</button>`,
      `<button class="chip" onclick="showSec('deudores')">⚠️ Deudas</button>`,
      `<button class="chip" onclick="showSec('videos')">🎥 Videos</button>`];
    if (R === 'admin') chips.push(`<button class="chip" onclick="showSec('profesores')">🧑‍🏫 Profesores</button>`, `<button class="chip" onclick="showSec('config')">⚙️ Configuración</button>`);
    chips.push(`<button class="chip" onclick="showSec('muro')">📢 Muro</button>`);
    chips.push(`<button class="chip" onclick="showSec('chat')">💬 Chat</button>`);
    chips.push(`<button class="chip" onclick="showSec('ranking')">🏆 Ranking</button>`);
    chips.push(`<button class="chip" onclick="showSec('eventos')">🗓️ Eventos</button>`);
    chips.push(`<button class="chip" onclick="showSec('encuestas')">📊 Encuestas</button>`);
    chips.push(`<button class="chip" onclick="showSec('historial')">📈 Historial</button>`);
    chips.push(`<button class="chip" onclick="showSec('galeria')">🖼️ Galería</button>`);
    chips.push(`<button class="chip" onclick="abrirMensajeMasivo()">📣 Mandar mensaje</button>`);
    chips.push(`<button class="chip" onclick="window.open('/qr_print','_blank')">📱 QR de asistencia</button>`);
    el.innerHTML = `
      <div class="feed">
        ${secHeader('Inicio')}
        <div class="home-grid">
          <div class="stat-card"><div class="num">${stats.total_alumnos}</div><div class="lbl">Alumnos activos</div></div>
          <div class="stat-card"><div class="num">$${num(stats.ingresos_mes)}</div><div class="lbl">Cobrado este mes</div></div>
          <div class="stat-card"><div class="num">${stats.clases}</div><div class="lbl">Clases/semana</div></div>
          ${R === 'profesor' ? `<div class="stat-card"><div class="num" style="color:var(--good)">$${num(stats.mi_ingreso_mes)}</div><div class="lbl">Tu dinero este mes</div></div>
          <div class="stat-card"><div class="num" style="color:var(--good)">$${num(stats.mi_ingreso_total)}</div><div class="lbl">Tu dinero total</div></div>` : ''}
        </div>
        <div class="chips">${chips.join('')}</div>
        <div class="feed-card">
          <div class="small mb">📅 Clases de hoy</div>
          ${hoyClases.length ? hoyClases.map(h => `<div class="clase-item ${h.tipo.toLowerCase()}"><span class="hora">${esc(h.hora)}</span> · <span class="tag ${h.tipo.toLowerCase()}">${esc(h.tipo)}</span> · ${esc(h.nivel)} · <span class="profe">${esc(h.profesor_nombre || 'Sin profesor')}</span></div>`).join('') : '<div class="small" style="color:var(--muted)">Hoy no hay clases cargadas.</div>'}
        </div>
        ${cums.cumpleanios.length ? `<div class="feed-card">
          <div class="small mb">🎂 Cumpleaños de ${['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'][cums.mes - 1]} <span class="small" style="color:var(--muted)">(${cums.cumpleanios.length})</span></div>
          ${cums.cumpleanios.map(x => `<div class="flex space-between" style="padding:6px 0;border-bottom:1px solid var(--line)"><span>${avatarHTML('', x.nombre, 'sm')} ${esc(x.nombre)}</span><b>${x.hoy ? '🎉 Hoy! · ' : ''}${x.dia}/${cums.mes}${x.edad ? ' · ' + x.edad + ' años' : ''}</b></div>`).join('')}
        </div>` : ''}
        ${videos.length ? `<div class="post-card" style="padding:0;overflow:hidden">
          <div class="post-head" style="padding:10px 14px 0"><b style="color:var(--accent2)">🎥 Últimos videos subidos</b> <button class="btn primary small" onclick="showSec('videos')">Subir video</button></div>
          <div class="feed" style="margin:0;padding:10px 14px 14px">${videos.map(v => videoCardHTML(v, true)).join('')}</div>
        </div>` : `<button class="btn primary btn-block" onclick="showSec('videos')">🎥 Subir el primer video</button>`}
      </div>`;
  }
}

/* =====================================================================
   PERFIL
   ===================================================================== */
async function renderPerfil(el) {
  const me = await api('/api/me');
  const cat = me.categoria || 'adulto';
  const belts = BELTS_POR_CAT[cat] || BELTS_ADULT;
  const vids = await api('/api/videos').catch(() => ({ videos: [] }));
  let stats = '';
  if (me.role === 'alumno') {
    const asis = await api('/api/mi_asistencia').catch(() => ({ total: 0 }));
    const pagos = await api('/api/mis_pagos').catch(() => ({ pagos: [] }));
    stats = `<div class="profile-stats">
      <div class="pstat"><b>${asis.total}</b><span>clases</span></div>
      <div class="pstat"><b>${pagos.pagos.length}</b><span>pagos</span></div>
      <div class="pstat"><b>${me.peso ? esc(me.peso) + 'kg' : '—'}</b><span>peso</span></div>
    </div>`;
  } else {
    stats = `<div class="profile-stats">
      <div class="pstat"><b>${me.edad || '—'}</b><span>edad</span></div>
      <div class="pstat"><b>${me.peso ? esc(me.peso) + 'kg' : '—'}</b><span>peso</span></div>
      <div class="pstat"><b>${beltHTML(me.cinturon)}</b><span>faixa</span></div>
    </div>`;
  }
  let grid = '';
  if (me.role === 'alumno') {
    const visto = vids.videos.filter(v => v.visto);
    grid = `<div class="feed-card">
      <div class="small mb">📼 Técnicas que viste (${visto.length})</div>
      <div class="vid-grid">${visto.length ? visto.map(v => vidThumb(v)).join('') : '<div class="empty">Todavía no marcaste videos como vistos. Entrá a la sección 🎥 Videos.</div>'}</div>
    </div>`;
  } else {
    const mios = vids.videos.filter(v => v.subido_por === me.id);
    grid = `<div class="feed-card">
      <div class="flex space-between mb"><div class="small">🎥 Videos que subí (${mios.length})</div>
        <button class="btn primary small" onclick="showSec('videos')">＋ Subir</button></div>
      <div class="vid-grid">${mios.length ? mios.map(v => vidThumb(v)).join('') : '<div class="empty">Todavía no subiste videos.</div>'}</div>
    </div>`;
  }
  el.innerHTML = `
    ${secHeader('Mi perfil')}
    <div class="feed">
      <div class="feed-card">
        <div class="profile-top">
          <div style="position:relative">
            ${avatarHTML(me.foto, me.nombre, 'lg')}
            <label style="position:absolute;bottom:-4px;right:-4px;background:var(--accent);color:#fff;width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;cursor:pointer;border:2px solid #000">📷
              <input type="file" id="fotoInput" accept="image/*" style="display:none">
            </label>
          </div>
          <div style="flex:1">
            <h2 style="margin:0;font-size:20px">${esc(me.nombre)}</h2>
            <div class="small">@${esc(me.username)} · ${me.role === 'alumno' ? 'Alumno' : me.role === 'profesor' ? 'Profesor' : 'Administrador'}</div>
            ${stats}
          </div>
        </div>
        <div class="small" style="color:var(--muted)">Tocá la cámara 📷 sobre tu foto para cambiarla.</div>
      </div>

      ${grid}

      <div class="feed-card">
        <form id="perfilForm" class="grid2">
          <div class="field"><label>Nombre y apellido</label><input type="text" id="pNombre" value="${esc(me.nombre)}"></div>
          <div class="field"><label>Usuario</label><input type="text" value="${esc(me.username)}" disabled></div>
          <div class="field"><label>DNI</label><input type="text" id="pDni" value="${esc(me.dni || '')}"></div>
          <div class="field"><label>Dirección / domicilio</label><input type="text" id="pDir" placeholder="Ej: Calle 1 N° 123, Viedma" value="${esc(me.direccion || '')}"></div>
          <div class="field"><label>Edad</label><input type="number" id="pEdad" value="${me.edad != null ? me.edad : ''}"></div>
          <div class="field"><label>Peso (kg)</label><input type="number" step="0.1" id="pPeso" value="${me.peso != null ? me.peso : ''}"></div>
          <div class="field"><label>Teléfono</label><input type="tel" id="pTel" value="${esc(me.tel || '')}"></div>
          <div class="field"><label>📞 Teléfono del padre/madre/tutor ${cat === 'kids' || cat === 'juveniles' ? '<span style="color:#ff9b8f">(obligatorio)</span>' : '(opcional)'}</label><input type="tel" id="pTelTutor" placeholder="Ej: 299 1234567" value="${esc(me.tel_tutor || '')}"></div>
          <div class="field"><label>📞 Segundo teléfono (opcional)</label><input type="tel" id="pTel2" placeholder="Otro teléfono de contacto" value="${esc(me.tel_2 || '')}"></div>
          <div class="field"><label>Fecha de nacimiento</label><input type="date" id="pNac" value="${me.nacimiento || ''}"></div>
          <div class="field"><label>Categoría</label><select id="pCat">
            ${CATEGORIAS.map(c => `<option value="${c}" ${c === cat ? 'selected' : ''}>${catLabel(c)}</option>`).join('')}</select></div>
          <div class="field"><label>Cinturón / Faixa</label><select id="pCinturon">
            ${belts.map(b => `<option ${b === me.cinturon ? 'selected' : ''}>${esc(b)}</option>`).join('')}</select></div>
          <div class="field"><label>Modalidad</label><select id="pGi">
            <option ${me.gi_pref === 'Ambas' ? 'selected' : ''}>Ambas</option>
            <option ${me.gi_pref === 'Gi' ? 'selected' : ''}>Gi</option>
            <option ${me.gi_pref === 'NoGi' ? 'selected' : ''}>NoGi</option></select></div>
          <div class="field"><label>Cambiar contraseña (opcional)</label><input type="password" id="pPass" placeholder="Nueva contraseña"></div>
          <div class="field" style="grid-column:1/-1"><label>🩺 Ficha médica (opcional)</label><textarea id="pMedic" rows="2" placeholder="Lesiones, alergias, medicación, operaciones...">${esc(me.medic_info || '')}</textarea></div>
          ${cat === 'kids' || cat === 'juveniles' ? `<div class="field" style="grid-column:1/-1"><label style="display:flex;align-items:center;gap:8px;cursor:pointer">
            <input type="checkbox" id="pFotoOk" style="width:18px;height:18px" ${me.foto_ok ? 'checked' : ''}>
            <span>Autorizo como mayor/padre/madre/tutor que <b>las fotos de este/a menor puedan ser expuestas</b> (redes y muro). <span style="color:#ff9b8f">(obligatorio para menores)</span></span></label></div>` : ''}
          <div class="field" style="grid-column:1/-1"><label>📞 Contacto de emergencia (opcional)</label><input type="text" id="pEmer" placeholder="Nombre y teléfono" value="${esc(me.emergency_contact || '')}"></div>
          <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">Guardar cambios</button></div>
        </form>
      </div>

      ${me.medic_info ? `<div class="feed-card">
        <div class="small mb">🩺 Mi ficha médica</div>
        <p class="small" style="white-space:pre-wrap;margin-bottom:0">${esc(me.medic_info)}</p>
      </div>` : ''}
      ${me.emergency_contact ? `<div class="feed-card">
        <div class="small mb">📞 Contacto de emergencia</div>
        <p class="small" style="margin-bottom:0">${esc(me.emergency_contact)}</p>
      </div>` : ''}

      <div class="feed-card">
        <div class="small mb">📲 ¿Querés la app como si fuera de tu teléfono?</div>
        <button class="btn ghost" onclick="instalarManual()">📲 Instalar la app</button>
        <p class="small" style="margin-bottom:0">Se instala en tu pantalla de inicio sin pasar por Google. (En el celular: menú → "Agregar a pantalla de inicio".)</p>
      </div>

      <div class="feed-card">
        <div class="small mb">🔐 Seguridad de la cuenta</div>
        <p class="small" style="margin-bottom:6px">Configurá una <b>pregunta de seguridad</b> para poder recuperar tu contraseña si alguna vez la olvidás. También podés cambiar tu contraseña acá.</p>
        <div class="field"><label>Pregunta de seguridad</label><input id="pSecQ" placeholder="Ej: ¿Nombre de tu mascota?" value="${esc(me.security_q || '')}"></div>
        <div class="field"><label>Respuesta</label><input id="pSecA" placeholder="Tu respuesta (se guarda visible solo para vos)"></div>
        <div class="field"><label>Nueva contraseña (opcional)</label><input type="password" id="pSecPass" placeholder="Dejalo en blanco para no cambiarla"></div>
        <button class="btn primary btn-block" onclick="guardarSeguridad()">Guardar seguridad</button>
      </div>
      <div class="feed-card">
        <div class="small mb">📄 Términos y Condiciones</div>
        ${me.acepto_tyc
          ? `<p class="small" style="margin-bottom:0">✔ Aceptaste los <b>Términos y Condiciones y la Política de Privacidad</b> el <b>${esc(me.acepto_tyc)}</b>. <a href="javascript:void(0)" onclick="verTerminos()" style="color:var(--accent2)">Ver términos</a></p>`
          : `<p class="small" style="margin-bottom:6px">Todavía no aceptaste los Términos y Condiciones.</p><button class="btn primary btn-block" onclick="verTerminos()">📄 Aceptar términos y condiciones</button>`}
      </div>
      ${me.role === 'alumno' ? `
      <div class="feed-card">
        <div class="small mb" style="color:var(--bad)">¿No vas a seguir entrenando?</div>
        <button class="btn bad btn-block" onclick="desactivarMiCuenta()">🚫 Desactivar mi cuenta</button>
        <p class="small" style="margin-bottom:0">Tus datos se guardan; si algún día volvés, el administrador puede reactivarte.</p>
      </div>` : ''}
    </div>`;
  $('#pCat').addEventListener('change', (e) => {
    const b = BELTS_POR_CAT[e.target.value] || BELTS_ADULT;
    $('#pCinturon').innerHTML = b.map(x => `<option>${esc(x)}</option>`).join('');
  });
  $('#perfilForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/perfil', { method: 'PUT', body: {
        nombre: $('#pNombre').value.trim(), edad: $('#pEdad').value,
        peso: $('#pPeso').value, cinturon: $('#pCinturon').value,
        categoria: $('#pCat').value, gi_pref: $('#pGi').value,
        tel: $('#pTel').value, nacimiento: $('#pNac').value,
        medic_info: $('#pMedic').value, emergency_contact: $('#pEmer').value,
        tel_tutor: $('#pTelTutor')?.value || '', tel_2: $('#pTel2')?.value || '',
        dni: $('#pDni')?.value.trim() || '', direccion: $('#pDir')?.value.trim() || '',
        foto_ok: !!($('#pFotoOk')?.checked || false),
        password: $('#pPass').value } });
      toast('Perfil actualizado ✓'); renderPerfil(el);
    } catch (err) { toast(err.message); }
  });
  setupFoto();
}

function instalarManual() {
  if (deferredPrompt) { deferredPrompt.prompt(); return; }
  toast('En el navegador: mirá el ícono de instalación (🚀) en la barra de direcciones, o menú → "Instalar". En el celular: menú → "Agregar a pantalla de inicio".');
}

async function desactivarMiCuenta() {
  if (!confirm('¿Seguro que querés desactivar tu cuenta?\n\nNo vas a poder entrar hasta que el administrador te reactive.')) return;
  try {
    await api('/api/perfil/desactivar', { method: 'POST' });
    toast('Tu cuenta fue desactivada. ¡Esperamos verte pronto!');
    setTimeout(() => { location.href = '/'; }, 800);
  } catch (e) { toast(e.message); }
}

/* =====================================================================
   HORARIOS
   ===================================================================== */
async function renderHorarios(el) {
  const R = USER.role;
  const d = await api('/api/horarios');
  const profesores = R !== 'alumno' ? (await api('/api/profesores').catch(() => ({ profesores: [] }))).profesores : [];
  PROFESORES_CACHE = profesores;
  const canEdit = R !== 'alumno';
  const cols = DIAS.map((dia, i) => {
    const items = d.horarios.filter(h => h.dia === i);
    return `<div class="dia-col"><h4>${dia}</h4>
      ${items.length ? items.map(h => `
        <div class="clase-item ${h.tipo.toLowerCase()}">
          <span class="hora">${esc(h.hora)}</span> · <span class="tag ${h.tipo.toLowerCase()}">${esc(h.tipo)}</span>
          <div class="small">${esc(h.nivel)} · ${h.duracion}min</div>
          <div class="profe">🧑‍🏫 ${esc(h.profesor_nombre || 'Sin profesor')}</div>
          ${canEdit ? `<div class="flex" style="margin-top:6px">
            <button class="btn ghost small" onclick="editarHorario(${h.id},${h.dia},'${esc(h.hora)}','${esc(h.tipo)}','${esc(h.nivel)}',${h.profesor_id != null ? h.profesor_id : 'null'},${h.duracion})">✏️ Editar</button>
            ${R === 'admin' ? `<button class="btn bad small" onclick="borrarHorario(${h.id})">🗑</button>` : ''}
          </div>` : ''}
        </div>`).join('') : '<p class="small" style="color:var(--muted)">Sin clases</p>'}
    </div>`;
  });
  el.innerHTML = `
    ${secHeader('Horarios semanales')}
    ${R !== 'alumno' ? `<div class="card flex space-between"><span class="small">Profesores pueden editar la tabla de horarios (${R === 'admin' ? 'solo admin puede eliminar' : 'edición permitida'}).</span>
      <button class="btn primary small" onclick="formHorario()">+ Agregar clase</button></div>` : ''}
    <div class="semana">${cols.join('')}</div>`;
}

function formHorario(h = null) {
  const horarios = [];
  const isEdit = !!h;
  openModal(`
    <h3>${isEdit ? 'Editar clase' : 'Nueva clase'}</h3>
    <form id="hForm" class="grid2">
      <div class="field"><label>Día</label><select id="hDia">
        ${DIAS.map((dd, i) => `<option value="${i}" ${h && h[1] === i ? 'selected' : ''}>${dd}</option>`).join('')}</select></div>
      <div class="field"><label>Hora</label><input type="time" id="hHora" value="${h ? h[2] : ''}" required></div>
      <div class="field"><label>Tipo</label><select id="hTipo">
        ${TIPOS_CLASE.map(t => `<option ${h && h[3] === t ? 'selected' : ''}>${t}</option>`).join('')}</select></div>
      <div class="field"><label>Nivel</label><select id="hNivel">
        ${['Todos', 'Principiantes', 'Intermedios', 'Avanzados', 'Competencia', 'Femenino'].map(n => `<option ${h && h[4] === n ? 'selected' : ''}>${n}</option>`).join('')}</select></div>
      <div class="field"><label>Profesor</label><select id="hProfesor">
        <option value="">Sin asignar</option>
        ${PROFESORES_CACHE.length ? PROFESORES_CACHE.map(p => `<option value="${p.id}" ${h && h[5] === p.id ? 'selected' : ''}>${esc(p.nombre)}</option>`).join('') : ''}</select></div>
      <div class="field"><label>Duración (min)</label><input type="number" id="hDur" value="${h ? h[6] : 60}"></div>
      <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">Guardar</button></div>
    </form>`);
  $('#hForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = { dia: +$('#hDia').value, hora: $('#hHora').value, tipo: $('#hTipo').value,
      nivel: $('#hNivel').value, profesor_id: $('#hProfesor').value ? +$('#hProfesor').value : null,
      duracion: +$('#hDur').value };
    try {
      if (isEdit) await api('/api/horarios/' + h[0], { method: 'PUT', body });
      else await api('/api/horarios', { method: 'POST', body });
      closeModal(); toast('Horario guardado ✓'); renderHorarios($('#sec-horarios'));
    } catch (err) { toast(err.message); }
  });
}
function editarHorario(id, dia, hora, tipo, nivel, prof, dur) { formHorario([id, dia, hora, tipo, nivel, prof, dur]); }
async function borrarHorario(id) {
  if (!confirm('¿Eliminar esta clase?')) return;
  await api('/api/horarios/' + id, { method: 'DELETE' }).catch(e => toast(e.message));
  toast('Clase eliminada'); renderHorarios($('#sec-horarios'));
}
let PROFESORES_CACHE = [];
let AVISOS_CACHE = {};

/* =====================================================================
   PAGOS (admin / profesor)
   ===================================================================== */
async function renderPagos(el) {
  const R = USER.role;
  const [pagos, alumnos, profesores, avisos] = await Promise.all([
    api('/api/pagos'), api('/api/alumnos'),
    R === 'admin' ? api('/api/profesores') : Promise.resolve({ profesores: [USER] }),
    api('/api/avisos_pago')]);
  PROFESORES_CACHE = profesores.profesores;
  const mes = new Date().getMonth() + 1, anio = new Date().getFullYear();
  const pendientes = (avisos.avisos || []).filter(a => a.estado === 'pendiente');
  AVISOS_CACHE = {};
  pendientes.forEach(a => { AVISOS_CACHE[a.id] = a; });
  el.innerHTML = `
    ${secHeader('Registrar pago')}
    ${pendientes.length ? `
    <div class="card">
      <h3>⏳ Avisos de pago pendientes (${pendientes.length})</h3>
      ${pendientes.map(a => `
        <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,.08)">
          <div><b>${esc(a.alumno_nombre)}</b> avisó que pagó la cuota de <b>${a.mes}/${a.anio}</b>${a.monto ? ' por <b>$' + num(a.monto) + '</b>' : ''}</div>
          <div class="small" style="color:var(--muted)">${esc(a.fecha)}${a.nota && a.nota !== 'Cuota mensual' ? ' · ' + esc(a.nota) : ''}</div>
          ${a.comprobante ? (a.comprobante.indexOf('data:image/') === 0
            ? `<div class="mt"><img src="${a.comprobante}" onclick="verComprobante(${a.id})" style="width:72px;height:72px;object-fit:cover;border-radius:8px;cursor:pointer" title="Ver comprobante"></div>`
            : `<div class="mt"><div onclick="verComprobante(${a.id})" style="width:72px;height:72px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.06);border-radius:8px;cursor:pointer;font-size:28px" title="Ver comprobante (PDF)">📄</div></div>`) : ''}
          <div class="flex mt" style="gap:8px">
            <button class="btn ghost small" onclick="verComprobante(${a.id})">🧾 Ver comprobante</button>
            <button class="btn primary small" onclick="confirmarAviso(${a.id})">✅ Confirmar y registrar</button>
            ${R === 'admin' ? `<button class="btn bad small" onclick="descartarAviso(${a.id})">🗑 Descartar</button>` : ''}
          </div>
        </div>`).join('')}
    </div>` : ''}
    <div class="card">
      <form id="pagoForm" class="grid2">
        <div class="field"><label>Alumno</label><select id="pAlumno" required>
          <option value="">— Elegí el alumno —</option>
          ${alumnos.alumnos.map(a => `<option value="${a.id}" data-cuota="${a.cuota_mensual || 0}">${esc(a.nombre)}</option>`).join('')}</select></div>
        <div class="field"><label>¿A qué profesor le pagó? (el dueño de este dinero)</label><select id="pProfe" required>
          ${profesores.profesores.map(p => `<option value="${p.id}">${esc(p.nombre)}</option>`).join('')}</select></div>
        <div class="field"><label>Monto ($)</label><input type="number" step="0.01" id="pMonto" required></div>
        <div class="field"><label>Método</label><select id="pMetodo">
          ${METODOS.map(m => `<option>${m}</option>`).join('')}</select></div>
        <div class="field"><label>Mes</label><select id="pMes">
          ${Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}" ${i + 1 === mes ? 'selected' : ''}>${i + 1}</option>`).join('')}</select></div>
        <div class="field"><label>Año</label><input type="number" id="pAnio" value="${anio}"></div>
        <div class="field" style="grid-column:1/-1"><label>Nota (opcional)</label><input type="text" id="pNota" placeholder="Ej: cuota agosto"></div>
        <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">💳 Registrar pago y notificar</button></div>
      </form>
    </div>
    <div class="card">
      <div class="flex space-between">
        <div><h3 style="margin:0">📊 Reporte mensual de ingresos</h3><p class="small">Total cobrado, métodos usados y deudores del mes.</p></div>
        <button class="btn primary small" onclick="abrirReporte()">Ver reporte</button>
      </div>
    </div>
    <div class="card">
      <h3>${R === 'profesor' ? 'Mis pagos recibidos' : 'Historial de pagos'}</h3>
      <div style="overflow:auto"><table>
        <tr><th>Fecha</th><th>Alumno</th><th>Profesor</th><th>Mes</th><th>Método</th><th>Monto</th><th>Recibo</th>${R === 'admin' ? '<th></th>' : ''}</tr>
        ${pagos.pagos.length ? pagos.pagos.map(p => `<tr>
          <td>${esc(p.fecha)}</td><td><div class="flex" style="gap:8px">${avatarHTML('', p.alumno_nombre, 'sm')}<span>${esc(p.alumno_nombre)}</span></div></td>
          <td>${esc(p.profesor_nombre || '—')}</td><td>${p.mes}/${p.anio}</td>
          <td>${esc(p.metodo)}</td><td><b>$${num(p.monto)}</b></td>
          <td><a class="btn ghost small" href="/recibo/${p.id}" target="_blank" rel="noopener">🧾</a></td>
          ${R === 'admin' ? `<td><button class="btn bad small" onclick="borrarPago(${p.id})">🗑</button></td>` : ''}</tr>`).join('')
          : '<tr><td colspan="7" class="empty">Todavía no hay pagos registrados</td></tr>'}
      </table></div>
    </div>`;

  $('#pAlumno').addEventListener('change', (e) => {
    const opt = e.target.selectedOptions[0];
    if (opt && opt.dataset.cuota) $('#pMonto').value = opt.dataset.cuota;
  });
  $('#pagoForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = { alumno_id: +$('#pAlumno').value, profesor_id: +$('#pProfe').value,
      monto: +$('#pMonto').value, metodo: $('#pMetodo').value, mes: +$('#pMes').value,
      anio: +$('#pAnio').value, nota: $('#pNota').value };
    try {
      const res = await api('/api/pagos', { method: 'POST', body });
      toast(res.cargo ? `Pago registrado ✓ (incluye $${num(res.cargo)} de recargo por demora)` : 'Pago registrado. Notificaciones enviadas ✓');
      renderPagos($('#sec-pagos'));
    } catch (err) { toast(err.message); }
  });
}
async function borrarPago(id) {
  if (!confirm('¿Eliminar este pago?')) return;
  await api('/api/pagos/' + id, { method: 'DELETE' }).catch(e => toast(e.message));
  renderPagos($('#sec-pagos'));
}
const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
function abrirMensajeMasivo() {
  openModal(`
    <h3>📣 Mandar mensaje</h3>
    <p class="small">Les llega como notificación (app + push si tienen permisos).</p>
    <div class="field"><label>Mensaje</label><textarea id="mMsg" rows="3" maxlength="500" placeholder='Ej: HOY A ENTRENAR 🥋'></textarea></div>
    <div class="field"><label>Título (opcional)</label><input id="mTit" value="📣 Mensaje de la academia"></div>
    <div class="field"><label>Enviar a</label><select id="mDesti">
      <option value="alumnos">A todos los alumnos</option>
      <option value="especifico">A un alumno específico...</option>
    </select></div>
    <div class="field" id="mEspecificoWrap" style="display:none"><label>Alumno</label><select id="mEspecifico"></select></div>
    <button class="btn primary btn-block" id="mBtn">Enviar</button>`);
  $('#mDesti').addEventListener('change', async (e) => {
    const w = $('#mEspecificoWrap');
    w.style.display = e.target.value === 'especifico' ? '' : 'none';
    if (e.target.value === 'especifico' && $('#mEspecifico').options.length === 0) {
      try {
        const d = await api('/api/alumnos');
        $('#mEspecifico').innerHTML = d.alumnos.filter(a => a.activo).map(a => `<option value="${a.id}">${esc(a.nombre)}</option>`).join('');
      } catch (err) {}
    }
  });
  $('#mBtn').addEventListener('click', async () => {
    const texto = $('#mMsg').value.trim();
    if (!texto) { toast('Escribí el mensaje'); return; }
    const body = { texto, titulo: $('#mTit').value };
    if ($('#mDesti').value === 'especifico') {
      const aid = +$('#mEspecifico').value;
      if (!aid) { toast('Elegí un alumno'); return; }
      body.alumno_id = aid;
    }
    closeModal();
    try {
      const r = await api('/api/mensajes/broadcast', { method: 'POST', body });
      toast('Mensaje enviado ✓');
    } catch (err) { toast(err.message); }
  });
}
function abrirReporte() {
  const hoy = new Date();
  openModal(`
    <h3>📊 Reporte mensual</h3>
    <div class="grid2">
      <div class="field"><label>Mes</label><select id="rMes">${MESES.map((m, i) => `<option value="${i + 1}" ${i + 1 === hoy.getMonth() + 1 ? 'selected' : ''}>${m}</option>`).join('')}</select></div>
      <div class="field"><label>Año</label><input type="number" id="rAnio" value="${hoy.getFullYear()}"></div>
    </div>
    <button class="btn primary btn-block" id="rBtn">Ver reporte</button>`);
  $('#rBtn').addEventListener('click', async () => {
    try {
      const rep = await api('/api/reporte?mes=' + $('#rMes').value + '&anio=' + $('#rAnio').value);
      const metodos = Object.entries(rep.por_metodo || {}).map(([k, v]) => `<div class="flex space-between" style="padding:6px 0;border-bottom:1px dashed var(--line)"><span>${esc(k)}</span><b>$${num(v)}</b></div>`).join('');
      const pctBar = (pct, color) => `<div style="background:${color};width:${pct}%;height:8px;border-radius:4px;min-width:${pct > 0 ? '8px' : '0'}"></div>`;
      $('#modalBody').innerHTML = `
        <h3>📊 Reporte ${MESES[rep.mes - 1]} ${rep.anio}</h3>
        <div class="stat-card"><div class="num">$${num(rep.total)}</div><div class="lbl">Total cobrado (${rep.cantidad} pago${rep.cantidad === 1 ? '' : 's'})</div></div>

        <div class="small mb mt" style="margin-top:14px"><b>💳 Pagos</b></div>
        <div style="display:flex;gap:4px;height:8px;border-radius:4px;overflow:hidden;margin-bottom:6px">
          ${pctBar(rep.pct_pagaron, 'var(--good)')}${pctBar(rep.pct_no_pagaron, 'var(--bad)')}
        </div>
        <div class="flex space-between small" style="margin-bottom:4px"><span style="color:var(--good)">✅ Pagaron: ${rep.cant_pagaron}/${rep.total_alumnos} (${rep.pct_pagaron}%)</span></div>
        <div class="flex space-between small" style="margin-bottom:8px"><span style="color:var(--bad)">❌ No pagaron: ${rep.cant_no_pagaron}/${rep.total_alumnos} (${rep.pct_no_pagaron}%)</span></div>
        ${rep.alumnos_que_pagaron && rep.alumnos_que_pagaron.length ? `<div style="max-height:120px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:4px 10px;margin-bottom:8px">${rep.alumnos_que_pagaron.map(a => `<div class="flex space-between" style="padding:3px 0;border-bottom:1px solid var(--line)"><span class="small">${esc(a.nombre)} <span style="color:var(--muted)">${esc(a.cinturon || '')}</span></span><span class="small">$${num(a.monto)} · ${esc(a.metodo)}</span></div>`).join('')}</div>` : ''}

        <div class="small mb mt" style="margin-top:14px"><b>✅ Asistencia</b></div>
        <div style="display:flex;gap:4px;height:8px;border-radius:4px;overflow:hidden;margin-bottom:6px">
          ${pctBar(rep.pct_asistieron, 'var(--accent2)')}${pctBar(rep.pct_no_asistieron, '#888')}
        </div>
        <div class="flex space-between small" style="margin-bottom:4px"><span style="color:var(--accent2)">🏃 Entrenaron: ${rep.cant_asistieron}/${rep.total_alumnos} (${rep.pct_asistieron}%)</span></div>
        <div class="flex space-between small" style="margin-bottom:8px"><span>💤 No entrenaron: ${rep.cant_no_asistieron}/${rep.total_alumnos} (${rep.pct_no_asistieron}%)</span></div>
        ${rep.alumnos_que_asistieron && rep.alumnos_que_asistieron.length ? `<div style="max-height:120px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:4px 10px;margin-bottom:8px">${rep.alumnos_que_asistieron.map(a => `<div class="flex space-between" style="padding:3px 0;border-bottom:1px solid var(--line)"><span class="small">${esc(a.nombre)} <span style="color:var(--muted)">${esc(a.cinturon || '')}</span></span><span class="small">${a.clases} clase${a.clases === 1 ? '' : 's'}</span></div>`).join('')}</div>` : ''}

        <div class="small mb mt" style="margin-top:14px"><b>💰 Por método de pago:</b></div>${metodos || '<div class="small" style="color:var(--muted)">Sin pagos este mes.</div>'}
        <div class="small mb mt" style="margin-top:12px">${rep.deudores.length} alumno${rep.deudores.length === 1 ? '' : 's'} debe${rep.deudores.length === 1 ? '' : 'n'} la cuota${rep.deudores.length ? ':' : ''}</div>
        ${rep.deudores.length ? `<div style="max-height:200px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:4px 10px">${rep.deudores.map(d => `<div class="flex space-between" style="padding:5px 0;border-bottom:1px solid var(--line)"><span>${esc(d.nombre)} <span class="small" style="color:var(--muted)">${esc(d.cinturon || '')}</span></span><b>$${num(d.cuota_mensual || 0)}</b></div>`).join('')}</div>` : ''}
        <p class="small" style="color:var(--warn)">${rep.avisos_pend} aviso(s) de pago pendiente(s) de revisar.</p>
        <button class="btn ghost btn-block" onclick="closeModal()">Cerrar</button>`;
    } catch (e) { toast(e.message); }
  });
}
function verComprobante(id) {
  const a = AVISOS_CACHE[id];
  if (!a || !a.comprobante) { toast('No hay comprobante'); return; }
  const esImg = a.comprobante.indexOf('data:image/') === 0;
  const cuerpo = esImg
    ? `<img src="${a.comprobante}" style="width:100%;border-radius:10px;background:#fff">`
    : `<div class="flex center" style="flex-direction:column;gap:10px;padding:20px 0;color:var(--muted)"><div style="font-size:44px">📄</div><p style="margin:0">Comprobante en formato PDF</p>
       <a class="btn primary small" href="${a.comprobante}" download="comprobante-${a.alumno_nombre || id}.pdf" style="text-decoration:none">⬇ Descargar PDF</a>
       <a class="btn ghost small" href="${a.comprobante}" target="_blank" rel="noopener" style="text-decoration:none">👁 Ver PDF</a></div>`;
  openModal(`
    <h3>🧾 Comprobante · ${esc(a.alumno_nombre)}</h3>
    <p class="small">Cuota de <b>${a.mes}/${a.anio}</b> por <b>$${num(a.monto)}</b>${a.nota && a.nota !== 'Cuota mensual' ? ' · ' + esc(a.nota) : ''}</p>
    ${cuerpo}
    <div class="flex mt" style="gap:8px">
      <button class="btn primary small" onclick="confirmarAviso(${a.id})">✅ Confirmar y registrar</button>
      ${USER.role === 'admin' ? `<button class="btn bad small" onclick="descartarAviso(${a.id})">🗑 Descartar</button>` : ''}
    </div>
  `);
}
async function confirmarAviso(id) {
  const a = AVISOS_CACHE[id] || {};
  if (!confirm(`¿Confirmar el pago de ${a.alumno_nombre || 'este alumno'} (cuota ${a.mes}/${a.anio})? Revisá antes el comprobante (tocá "Ver comprobante"). Se registra el pago y se notifica al alumno.`)) return;
  closeModal();
  try {
    await api('/api/avisos_pago/' + id + '/confirmar', { method: 'POST' });
    toast('Pago confirmado y registrado ✓ El alumno fue notificado.');
    renderPagos($('#sec-pagos'));
  } catch (e) { toast(e.message); }
}
async function descartarAviso(id) {
  if (!confirm('¿Descartar este aviso? No se registra ningún pago.')) return;
  closeModal();
  try {
    await api('/api/avisos_pago/' + id, { method: 'DELETE' });
    toast('Aviso descartado.');
    renderPagos($('#sec-pagos'));
  } catch (e) { toast(e.message); }
}

/* =====================================================================
   MIS PAGOS (alumno)
   ===================================================================== */
async function renderMisPagos(el) {
  const [me, pagos] = await Promise.all([api('/api/me'), api('/api/mis_pagos')]);
  const c = me.cuota || {};
  const estado = c.estado;
  const cls = estado === 'al_dia' ? 'tag-al-dia' : estado === 'por_vencer' ? 'tag-por-vencer' : 'tag-deuda';
  const lbl = estado === 'al_dia' ? 'Al día ✓' : estado === 'por_vencer' ? 'Por vencer' : 'Debe la cuota';
  const aviso = pagos.aviso_pendiente;
  el.innerHTML = `
    ${secHeader('Mi estado de cuenta')}
    <div class="card">
      <div class="flex space-between">
        <div>
          <h3 style="margin:0">Cuota de ${c.mes}/${c.anio}</h3>
          <p class="small">Tu cuota mensual es <b>$${num(c.cuota)}</b> · se considera paga hasta el día ${c.due_day} del mes${c.cargo_demora_pct ? ` · <b style="color:var(--warn)">si pagás después, se suma un ${c.cargo_demora_pct}% de recargo</b>` : ''}.</p>
        </div>
        <div class="tag ${cls}" style="font-size:14px;padding:6px 14px">${lbl}</div>
      </div>
      <p class="small mt">💰 Aboná ${c.cuota ? '$' + num(c.cuota) : 'tu cuota'}${me.pago_alias ? ' por transferencia al alias/CVU de la academia' : ' en la academia'} y <b>sí o sí mandá el comprobante de pago</b>: sin comprobante, el pago no se confirma.</p>
      ${aviso ? `<p class="small mt" style="color:var(--warn)">⏳ Comprobante de ${aviso.mes}/${aviso.anio} enviado. Esperá la confirmación.</p>` : ''}
      ${estado !== 'al_dia' && !aviso ? `<button class="btn primary btn-block" onclick="avisarPago()">🧾 Mandar comprobante de pago</button>` : ''}
      ${me.mp_habilitado && estado !== 'al_dia' && !aviso ? `<button class="btn primary btn-block" style="background:linear-gradient(90deg,#00c3ff,#0aa2e0);border:none" onclick="pagarMercadoPago()">💳 Pagar con MercadoPago</button>` : ''}
    </div>
    ${me.pago_alias ? `
    <div class="card">
      <h3>🏦 Pagar por transferencia</h3>
      <p class="small">Págale al alias/CVU de la academia y después <b>mandá el comprobante</b> (foto o captura). El pago se confirma cuando lo revisa el profe/admin.</p>
      <div class="alias-box" id="aliasBox">${esc(me.pago_alias)}</div>
      <button class="btn ghost btn-block" onclick="copiarAlias()">📋 Copiar alias / CVU</button>
    </div>` : ''}
    <div class="card"><h3>Mis pagos</h3>
      <div style="overflow:auto"><table>
        <tr><th>Fecha</th><th>Profesor que recibió</th><th>Mes</th><th>Método</th><th>Monto</th><th>Recibo</th></tr>
        ${pagos.pagos.length ? pagos.pagos.map(p => `<tr>
          <td>${esc(p.fecha)}</td><td>${esc(p.profesor_nombre || '—')}</td>
          <td>${p.mes}/${p.anio}</td><td>${esc(p.metodo)}</td><td><b>$${num(p.monto)}</b></td>
          <td><a class="btn ghost small" href="/recibo/${p.id}" target="_blank" rel="noopener">🧾</a></td></tr>`).join('')
          : '<tr><td colspan="6" class="empty">Aún no registraste pagos</td></tr>'}
      </table></div>
    </div>`;
}
async function pagarMercadoPago() {
  try {
    const r = await api('/api/checkout', { method: 'POST' });
    if (r.init_point) { window.open(r.init_point, '_blank'); }
    else toast(r.error || 'No se pudo generar el pago');
  } catch (e) { toast(e.message); }
}
async function avisarPago() {
  openModal(`
    <h3>🧾 Mandar comprobante de pago</h3>
    <p class="small">Subí una <b>foto, captura o PDF</b> del comprobante de pago. El profe/admin lo va a revisar y confirmar tu cuota.</p>
    <div class="field"><label>Comprobante (JPG, PNG o PDF)</label>
      <input type="file" id="avComprobante" accept="image/*,application/pdf">
      <div id="avPreview" class="mt" style="display:none"><img id="avPreviewImg" style="max-width:100%;border-radius:10px;background:#fff"></div>
      <div id="avFileName" class="small mt" style="display:none;color:var(--muted)"></div>
    </div>
    <button class="btn primary btn-block" id="avEnviar">📤 Enviar aviso</button>
    <p class="small" style="color:var(--muted)">No vas a poder volver a avisar hasta que confirmen o descarten tu aviso.</p>
  `);
  const input = $('#avComprobante');
  input.addEventListener('change', () => {
    const f = input.files && input.files[0];
    if (!f) return;
    if (!/^image\/(png|jpe?g|webp)|^application\/pdf/.test(f.type)) { toast('Elegí una imagen (JPG/PNG) o un PDF'); input.value = ''; return; }
    if (f.size > 12 * 1024 * 1024) { toast('El archivo es muy grande (máx 12MB)'); input.value = ''; return; }
    $('#avFileName').style.display = 'none';
    $('#avFileName').textContent = '';
    if (f.type.indexOf('image/') === 0) {
      const r = new FileReader();
      r.onload = () => { $('#avPreview').style.display = ''; $('#avPreviewImg').src = r.result; };
      r.readAsDataURL(f);
    } else {
      $('#avPreview').style.display = 'none';
      $('#avFileName').style.display = '';
      $('#avFileName').textContent = '📄 ' + f.name + ' (' + (Math.round(f.size / 1024)) + ' KB)';
    }
  });
  $('#avEnviar').addEventListener('click', () => {
    const f = input.files && input.files[0];
    if (!f) { toast('Elegí el comprobante primero'); return; }
    const r = new FileReader();
    r.onload = async () => {
      try {
        await api('/api/avisar_pago', { method: 'POST', body: { comprobante: r.result } });
        closeModal();
        toast('Aviso enviado ✓ Te avisamos cuando lo confirmen.');
        renderMisPagos($('#sec-mispagos'));
      } catch (e) { toast(e.message); }
    };
    r.readAsDataURL(f);
  });
}
async function copiarAlias() {
  const box = $('#aliasBox');
  if (!box) return;
  const txt = box.textContent.trim();
  try {
    await navigator.clipboard.writeText(txt);
    toast('Alias/CVU copiado ✓');
  } catch (e) {
    const ta = document.createElement('textarea');
    ta.value = txt;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); toast('Alias/CVU copiado ✓'); }
    catch (e2) { toast('Copialo manualmente'); }
    document.body.removeChild(ta);
  }
}

/* =====================================================================
   ALUMNOS (admin / profesor)
   ===================================================================== */
async function renderAlumnos(el) {
  const d = await api('/api/alumnos');
  el.innerHTML = `
    ${secHeader('Alumnos', 'Los alumnos se registran solos en la pantalla de ingreso')}
    ${USER.role === 'admin' || USER.role === 'profesor' ? `<div class="mb">
      <button class="btn good" onclick="exportarAlumnosExcel()">📥 Exportar alumnos activos a Excel</button>
      <p class="small" style="margin:6px 0 0">Descarga un archivo .xlsx con los datos de los alumnos activos (nombre, DNI, dirección, teléfonos, categoría, etc.). Solo alumnos <b>activos</b>.</p>
    </div>` : ''}
    <div class="mb">
      <input class="search" style="max-width:100%" id="alumnoBusq" placeholder="🔍 Buscar alumno...">
    </div>
    <div class="alum-grid" id="alumGrid">
      ${d.alumnos.map(a => {
        const c = a.cuota;
        const cls = c.estado === 'al_dia' ? 'tag-al-dia' : c.estado === 'por_vencer' ? 'tag-por-vencer' : 'tag-deuda';
        const lbl = c.estado === 'al_dia' ? 'Al día' : c.estado === 'por_vencer' ? 'Por vencer' : 'Debe ' + c.mes + '/' + c.anio;
        return `<div class="alum-card" data-q="${esc((a.nombre + ' ' + (a.cinturon || '')).toLowerCase())}">
          ${avatarHTML(a.foto, a.nombre, 'lg')}
          <div class="al-nombre">${esc(a.nombre)}${a.activo ? '' : '<div><span class="tag tag-deuda">inactivo</span></div>'}</div>
          <div class="small" style="margin-top:4px">${beltHTML(a.cinturon)} · ${a.edad != null ? a.edad + ' años' : '—'}</div>
          <div class="small">Modalidad: <span class="tag ${(a.gi_pref || 'Ambas').toLowerCase() === 'amabas' ? 'alumno' : (a.gi_pref || 'Ambas').toLowerCase()}">${esc(a.gi_pref || 'Ambas')}</span></div>
          <div class="small">Cuota: <b>$${num(a.cuota_mensual)}</b> · <span class="tag ${cls}">${lbl}</span></div>
          <div class="small">🥋 <b>${a.asistencias}</b> asistencias</div>
          <div class="al-actions">
            <button class="btn ghost small" onclick="formAlumno(${a.id})">✏️</button>
            <button class="btn ghost small" onclick="cambiarCuota(${a.id},'${esc(a.nombre)}',${a.cuota_mensual || 0})">💲</button>
            <button class="btn ghost small" onclick="verFicha(${a.id},'${esc(a.nombre)}')">🩺</button>
            <button class="btn good small" onclick="notificarDeuda(${a.id})">🔔</button>
            ${USER.role !== 'alumno' ? `<button class="btn ${a.activo ? 'bad' : 'good'} small" onclick="toggleActivo(${a.id},${a.activo ? 1 : 0})">${a.activo ? '🚫 Desactivar' : '✅ Reactivar'}</button>` : ''}
            ${USER.role === 'admin' ? `<button class="btn ghost small" onclick="reiniciarPassword(${a.id},'${esc(a.nombre)}')">🔑</button>` : ''}
            ${USER.role === 'admin' ? `<button class="btn bad small" onclick="eliminarAlumno(${a.id},'${esc(a.nombre)}')">🗑</button>` : ''}
          </div>
        </div>`;
      }).join('') || '<div class="empty">Todavía no hay alumnos. Los alumnos se registran solos desde la pantalla de ingreso.</div>'}
    </div>`;
  $('#alumnoBusq').addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    $$('#alumGrid .alum-card').forEach(c => { c.style.display = c.dataset.q.includes(q) ? '' : 'none'; });
  });
}

function exportarAlumnosExcel() {
  window.open('/api/exportar_alumnos', '_blank');
}

async function verFicha(id, nombre) {
  const a = (await api('/api/alumnos')).alumnos.find(x => x.id === id);
  openModal(`
    <h3>🩺 Ficha de ${esc(nombre)}</h3>
    ${a.tel ? `<div class="small mb">📱 ${esc(a.tel)}</div>` : ''}
    ${a.medic_info ? `<p class="small" style="white-space:pre-wrap;background:var(--bg2);border-radius:8px;padding:10px"><b>Ficha médica:</b><br>${esc(a.medic_info)}</p>` : '<div class="empty">Sin ficha médica cargada.</div>'}
    ${a.emergency_contact ? `<p class="small" style="white-space:pre-wrap;background:var(--bg2);border-radius:8px;padding:10px"><b>📞 Contacto de emergencia:</b> ${esc(a.emergency_contact)}</p>` : ''}
    <button class="btn ghost btn-block" onclick="closeModal()">Cerrar</button>`);
}

async function toggleActivo(id, activo) {
  const accion = activo ? 'desactivar' : 'reactivar';
  if (!confirm(activo ? '¿Desactivar a este alumno? No va a poder entrar hasta que lo reactives.' : '¿Reactivar a este alumno?')) return;
  try {
    await api('/api/alumnos/' + id, { method: 'PUT', body: { activo: activo ? 0 : 1 } });
    toast(activo ? 'Alumno desactivado.' : 'Alumno reactivado ✓');
    renderAlumnos($('#sec-alumnos'));
  } catch (err) { toast(err.message); }
}

async function formAlumno(id) {
  if (!id) { toast('Los alumnos se registran solos desde la pantalla de ingreso'); return; }
  const a = (await api('/api/alumnos')).alumnos.find(x => x.id === id);
  openModal(`
    <h3>Editar alumno</h3>
    <form id="alForm" class="grid2">
      <div class="field"><label>Nombre y apellido</label><input id="aNombre" value="${esc(a.nombre)}" required></div>
      <div class="field"><label>DNI</label><input type="text" id="aDni" value="${esc(a.dni || '')}"></div>
      <div class="field"><label>Dirección / domicilio</label><input type="text" id="aDir" placeholder="Ej: Calle 1 N° 123, Viedma" value="${esc(a.direccion || '')}"></div>
      <div class="field"><label>Edad</label><input type="number" id="aEdad" value="${a.edad != null ? a.edad : ''}"></div>
      <div class="field"><label>Peso (kg)</label><input type="number" step="0.1" id="aPeso" value="${a.peso != null ? a.peso : ''}"></div>
      <div class="field"><label>Teléfono</label><input type="tel" id="aTel" value="${esc(a.tel || '')}"></div>
      <div class="field"><label>📞 Tel. padre/madre/tutor ${a.categoria === 'kids' || a.categoria === 'juveniles' ? '<span style="color:#ff9b8f">(obligatorio)</span>' : ''}</label><input type="tel" id="aTutor" value="${esc(a.tel_tutor || '')}"></div>
      <div class="field"><label>📞 Segundo teléfono</label><input type="tel" id="aTel2" value="${esc(a.tel_2 || '')}"></div>
      <div class="field"><label>Fecha de nacimiento</label><input type="date" id="aNac" value="${a.nacimiento || ''}"></div>
      <div class="field"><label>Categoría</label><select id="aCat">${CATEGORIAS.map(c => `<option value="${c}" ${a.categoria === c ? 'selected' : ''}>${catLabel(c)}</option>`).join('')}</select></div>
      <div class="field"><label>Cinturón</label><select id="aCinturon"></select></div>
      <div class="field"><label>Modalidad</label><select id="aGi">
        ${['Ambas', 'Gi', 'NoGi'].map(g => `<option ${a.gi_pref === g ? 'selected' : ''}>${g}</option>`).join('')}</select></div>
      <div class="field"><label>Cuota mensual ($)</label><input type="number" step="0.01" id="aCuota" value="${a.cuota_mensual != null ? a.cuota_mensual : ''}" disabled></div>
      <div class="field" style="grid-column:1/-1"><label>🩺 Ficha médica (opcional)</label><textarea id="aMedic" rows="2" placeholder="Lesiones, alergias, medicación...">${esc(a.medic_info || '')}</textarea></div>
      <div class="field" style="grid-column:1/-1"><label>📞 Contacto de emergencia (opcional)</label><input type="text" id="aEmer" placeholder="Nombre y teléfono" value="${esc(a.emergency_contact || '')}"></div>
      ${a.categoria === 'kids' || a.categoria === 'juveniles' ? `<div class="field" style="grid-column:1/-1"><label style="display:flex;align-items:center;gap:8px;cursor:pointer">
        <input type="checkbox" id="aFotoOk" style="width:18px;height:18px" ${a.foto_ok ? 'checked' : ''}>
        <span>Autorizado por un mayor para exponer fotos del menor (redes y muro)</span></label></div>` : ''}
      <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">Guardar</button></div>
    </form>`);
  function fillBelt() {
    const cat = $('#aCat').value;
    const belts = BELTS_POR_CAT[cat] || BELTS_ADULT;
    $('#aCinturon').innerHTML = belts.map(b => `<option ${a && a.cinturon === b ? 'selected' : ''}>${esc(b)}</option>`).join('');
  }
  fillBelt();
  $('#aCat').addEventListener('change', fillBelt);
  $('#alForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = { nombre: $('#aNombre').value.trim(), edad: $('#aEdad').value, peso: $('#aPeso').value,
      cinturon: $('#aCinturon').value, categoria: $('#aCat').value, gi_pref: $('#aGi').value,
      tel: $('#aTel').value, nacimiento: $('#aNac').value,
      medic_info: $('#aMedic').value, emergency_contact: $('#aEmer').value,
      tel_tutor: $('#aTutor')?.value || '', tel_2: $('#aTel2')?.value || '',
      dni: $('#aDni')?.value.trim() || '', direccion: $('#aDir')?.value.trim() || '',
      foto_ok: !!($('#aFotoOk')?.checked || false) };
    try {
      await api('/api/alumnos/' + a.id, { method: 'PUT', body });
      toast('Alumno actualizado ✓');
      closeModal(); renderAlumnos($('#sec-alumnos'));
    } catch (err) { toast(err.message); }
  });
}

function cambiarCuota(id, nombre, actual) {
  openModal(`
    <h3>Cambiar cuota de ${esc(nombre)}</h3>
    <form id="cuotaForm">
      <div class="field"><label>Nueva cuota mensual ($) — solo admin/profesor puede cambiar</label>
        <input type="number" step="0.01" id="cMonto" value="${actual || ''}" required></div>
      <button class="btn primary btn-block" type="submit">Guardar cuota</button>
    </form>`);
  $('#cuotaForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/alumnos/' + id + '/cuota', { method: 'PUT', body: { cuota_mensual: +$('#cMonto').value } });
      closeModal(); toast('Cuota actualizada y alumno notificado ✓');
      renderAlumnos($('#sec-alumnos'));
    } catch (err) { toast(err.message); }
  });
}

async function eliminarAlumno(id, nombre) {
  if (!confirm(`¿Eliminar a ${nombre} y todos sus datos?`)) return;
  await api('/api/alumnos/' + id, { method: 'DELETE' }).catch(e => toast(e.message));
  toast('Alumno eliminado');
  renderAlumnos($('#sec-alumnos'));
}

async function notificarDeuda(id) {
  try {
    const d = await api('/api/notify_deuda', { method: 'POST', body: { alumno_id: id } });
    toast(`Recordatorio enviado a ${d.avisados} alumno(s) 🔔`);
  } catch (e) { toast(e.message); }
}

/* =====================================================================
   ASISTENCIA (admin / profesor)
   ===================================================================== */
async function renderAsistencia(el) {
  const [horarios, alumnos] = await Promise.all([api('/api/horarios'), api('/api/alumnos')]);
  const hoy = new Date().toISOString().slice(0, 10);
  el.innerHTML = `
    ${secHeader('Tomar asistencia')}
    <div class="card">
      <div class="flex mb">
        <select id="asClase" style="padding:10px;border-radius:9px;border:1px solid var(--line);background:var(--bg2);color:var(--txt);flex:1">
          <option value="">— Elegí la clase —</option>
          ${horarios.horarios.map(h => `<option value="${h.id}" data-profe="${h.profesor_id || ''}">${esc(h.dia_nombre)} ${esc(h.hora)} · ${esc(h.tipo)} · ${esc(h.nivel)}</option>`).join('')}
        </select>
        <input type="date" id="asFecha" value="${hoy}" style="padding:10px;border-radius:9px;border:1px solid var(--line);background:var(--bg2);color:var(--txt)">
      </div>
      <div id="asLista" class="mt">
        <div class="empty">Elegí una clase para marcar los alumnos presentes.</div>
      </div>
      <div class="flex space-between mt">
        <span class="marcador">✅ Presentes hoy: <b id="asCount">0</b></span>
        <button class="btn good" id="asGuardar" hidden>Guardar asistencia</button>
      </div>
    </div>`;

  async function cargar() {
    const cid = +$('#asClase').value;
    const fecha = $('#asFecha').value;
    const lista = $('#asLista');
    if (!cid) { lista.innerHTML = '<div class="empty">Elegí una clase.</div>'; $('#asGuardar').hidden = true; return; }
    const presentes = await api('/api/asistencia_dia?clase_id=' + cid + '&fecha=' + fecha).catch(() => ({ presentes: [] }));
    const set = new Set(presentes.presentes);
    lista.innerHTML = alumnos.alumnos.map(a => `
      <label class="check-row ${set.has(a.id) ? 'presente' : ''}">
        <input type="checkbox" class="asCheck" value="${a.id}" ${set.has(a.id) ? 'checked' : ''} data-nombre="${esc(a.nombre)}">
        ${avatarHTML(a.foto, a.nombre, 'sm')}
        <span class="nom">${esc(a.nombre)}</span>
        <span class="meta">${beltHTML(a.cinturon)} · ${a.edad != null ? a.edad : ''} años · 🥋${a.asistencias}</span>
      </label>`).join('') || '<div class="empty">No hay alumnos cargados.</div>';
    $('#asGuardar').hidden = false;
    contar();
    $$('.asCheck').forEach(c => c.addEventListener('change', () => {
      c.closest('.check-row').classList.toggle('presente', c.checked);
      contar();
    }));
  }
  function contar() {
    const n = $$('.asCheck:checked').length;
    $('#asCount').textContent = n;
  }
  $('#asClase').addEventListener('change', cargar);
  $('#asFecha').addEventListener('change', cargar);
  $('#asGuardar').addEventListener('click', async () => {
    const cid = +$('#asClase').value;
    const fecha = $('#asFecha').value;
    const presentes = $$('.asCheck:checked').map(c => +c.value);
    try {
      await api('/api/asistencia', { method: 'POST', body: { clase_id: cid, fecha, presentes } });
      toast(`Asistencia guardada: ${presentes.length} presentes ✓`);
    } catch (e) { toast(e.message); }
  });
}

/* =====================================================================
   DEUDORES (admin / profesor)
   ===================================================================== */
async function renderDeudores(el) {
  const d = await api('/api/deudores');
  el.innerHTML = `
    ${secHeader('Alumnos con deuda')}
    <div class="card">
      <div class="flex space-between mb">
        <span class="small">Alumnos sin pago del mes actual o por vencer.</span>
        <button class="btn warn" onclick="notificarTodas()">🔔 Notificar a todos</button>
      </div>
      <div style="overflow:auto"><table>
        <tr><th>Alumno</th><th>Cuota</th><th>Estado</th><th>Días sin pago</th><th>Acción</th></tr>
        ${d.deudores.length ? d.deudores.map(x => `
          <tr>
            <td><div class="flex" style="gap:8px">${avatarHTML(x.foto, x.nombre, 'sm')}<b>${esc(x.nombre)}</b></div> ${beltHTML(x.cinturon)}</td>
            <td>$${num(x.cuota_mensual)}</td>
            <td><span class="tag ${x.estado === 'deuda' ? 'tag-deuda' : 'tag-por-vencer'}">${x.estado === 'deuda' ? 'Debe' : 'Por vencer'}</span></td>
            <td>${x.dias_deuda}</td>
            <td><button class="btn warn small" onclick="notificarDeuda(${x.id})">🔔 Recordar</button></td>
          </tr>`).join('') : '<tr><td colspan="5" class="empty">🎉 No hay deudores. Todos al día.</td></tr>'}
      </table></div>
    </div>`;
}
async function notificarTodas() {
  try {
    const d = await api('/api/notify_deuda', { method: 'POST', body: {} });
    toast(`Recordatorio enviado a ${d.avisados} alumnos 🔔`);
  } catch (e) { toast(e.message); }
}

/* =====================================================================
   PROFESORES (admin)
   ===================================================================== */
async function renderProfesores(el) {
  const d = await api('/api/profesores');
  el.innerHTML = `
    ${secHeader('Profesores')}
    <div class="card">
      <p class="small">Los profesores se crean su propia cuenta con el <b>código de la academia</b> (lo encontrás en Configuración), o los podés crear vos acá.</p>
      <button class="btn primary" onclick="formProfesor()">+ Crear profesor</button>
    </div>
    <div class="card"><div style="overflow:auto"><table>
      <tr><th>Profesor</th><th>Faixa</th><th>Edad</th><th>Peso</th><th>Usuario</th><th>Clases</th><th></th></tr>
      ${d.profesores.length ? d.profesores.map(p => `
        <tr>
          <td><div class="flex" style="gap:8px">${avatarHTML(p.foto, p.nombre, 'sm')}<b>${esc(p.nombre)}</b></div></td><td>${beltHTML(p.cinturon)}</td>
          <td>${p.edad != null ? p.edad : '—'}</td><td>${p.peso ? p.peso + 'kg' : '—'}</td>
          <td>@${esc(p.username)}</td><td>${p.clases}</td>
          <td><button class="btn bad small" onclick="eliminarProfesor(${p.id},'${esc(p.nombre)}')">🗑 Eliminar</button></td>
        </tr>`).join('') : '<tr><td colspan="7" class="empty">Todavía no hay profesores.</td></tr>'}
    </table></div></div>`;
}

async function formProfesor() {
  openModal(`
    <h3>Crear profesor</h3>
    <form id="profeForm" class="grid2">
      <div class="field" style="grid-column:1/-1"><label>Nombre y apellido</label><input id="prNombre" required></div>
      <div class="field"><label>Usuario</label><input id="prUser" placeholder="si lo dejas vacío se genera"></div>
      <div class="field"><label>Contraseña</label><input id="prPass" placeholder="si lo dejas vacío: profe123"></div>
      <div class="field"><label>Edad</label><input type="number" id="prEdad"></div>
      <div class="field"><label>Peso (kg)</label><input type="number" step="0.1" id="prPeso"></div>
      <div class="field"><label>Faixa</label><select id="prCinturon">${BELTS_ADULT.map(b => `<option>${b}</option>`).join('')}</select></div>
      <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">Crear</button></div>
    </form>`);
  $('#profeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = { nombre: $('#prNombre').value.trim(), edad: $('#prEdad').value, peso: $('#prPeso').value,
      cinturon: $('#prCinturon').value };
    if ($('#prUser').value) body.username = $('#prUser').value.trim();
    if ($('#prPass').value) body.password = $('#prPass').value;
    try {
      const d = await api('/api/profesores', { method: 'POST', body });
      closeModal(); toast(`Profesor creado · usuario: ${d.username} · contraseña: ${d.password}`);
      renderProfesores($('#sec-profesores'));
    } catch (err) { toast(err.message); }
  });
}

async function eliminarProfesor(id, nombre) {
  if (!confirm(`¿Eliminar al profesor ${nombre}? Sus clases quedan sin asignar y sus pagos se conservan.`)) return;
  await api('/api/profesores/' + id, { method: 'DELETE' }).catch(e => toast(e.message));
  toast('Profesor eliminado');
  renderProfesores($('#sec-profesores'));
}

/* =====================================================================
   CONFIG (admin)
   ===================================================================== */
async function renderConfig(el) {
  const s = await api('/api/settings');
  el.innerHTML = `
    ${secHeader('Configuración')}
    <div class="card">
      <h3>Academia</h3>
      <form id="cfgForm" class="grid2">
        <div class="field"><label>Nombre de la academia</label><input id="cNombre" value="${esc(s.academy_name)}"></div>
        <div class="field"><label>Color principal</label><input type="color" id="cColor" value="${esc(s.academy_color || '#e05d13')}" style="padding:4px;height:42px"></div>
        <div class="field"><label>Código de la academia (para que los profes se registren)</label><input id="cCodigo" value="${esc(s.academy_code)}"></div>
        <div class="field"><label>Cuota mensual por defecto ($)</label><input id="cCuota" value="${esc(s.default_cuota)}"></div>
        <div class="field"><label>Día de vencimiento (día del mes)</label><input type="number" id="cDue" value="${esc(s.due_day)}"></div>
        <div class="field"><label>Recargo por pago con demora (%)</label><input type="number" id="cDemora" value="${esc(s.cargo_demora_pct ?? '10')}" placeholder="10"></div>
        <div class="field" style="grid-column:1/-1"><label>Link de pago en línea (ej: link de MercadoPago)</label><input id="cLink" value="${esc(s.pago_link || '')}" placeholder="https://link.mercadopago.com.ar/... (dejalo vacío para ocultar el botón de pago)"></div>
        <div class="field" style="grid-column:1/-1"><label>Alias o CVU para transferencia</label><input id="cAlias" value="${esc(s.pago_alias || '')}" placeholder="ej: academia.bjj.viedma (dejalo vacío para ocultarlo)"></div>
        <div class="field" style="grid-column:1/-1"><label>Access Token de MercadoPago (APP_USR-...) para el botón de pago en línea</label><input id="cMpTk" value="${esc(s.mp_access_token || '')}" placeholder="APP_USR-... (dejalo vacío para ocultar el botón de pago online)"></div>
        <div class="field"><label>Número WhatsApp de la academia (con código país)</label><input id="cWp" value="${esc(s.wp_numero || '')}" placeholder="549299..."></div>
        <div class="field"><label>Logro de asistencias (cada cuántas avisar)</label><input type="number" id="cLogroAsist" value="${esc(s.logro_asist ?? '50')}"></div>
        <div class="field"><label>Logro de videos vistos (cada cuántos avisar)</label><input type="number" id="cLogroVids" value="${esc(s.logro_videos ?? '25')}"></div>
        <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">Guardar configuración</button></div>
      </form>
    </div>
    <div class="card">
      <h3>📣 Mensajes automáticos</h3>
      <p class="small">Cada alumno recibe el mensaje <b>una vez por día</b> si supera los días sin entrenar o sin pagar (el que pase primero).</p>
      <form id="autoForm" class="grid2">
        <div class="field"><label>Mensaje que reciben</label><input id="aMsg" value="${esc(s.auto_mensaje || '')}" style="grid-column:1/-1"></div>
        <div class="field"><label>Días sin entrenar para avisar</label><input type="number" id="aInact" value="${esc(s.auto_inact_dias ?? '15')}"></div>
        <div class="field"><label>Días sin pagar para avisar</label><input type="number" id="aDeuda" value="${esc(s.auto_deuda_dias ?? '30')}"></div>
        <div class="field" style="grid-column:1/-1"><label><input type="checkbox" id="aActivo" ${s.auto_mensaje_activo === '1' ? 'checked' : ''}> Activar mensajes automáticos</label></div>
        <div class="field" style="grid-column:1/-1">
          <button class="btn primary btn-block" type="submit">💾 Guardar mensaje automático</button>
          <button class="btn ghost btn-block" type="button" onclick="enviarAutoAhora()">🚀 Enviar ahora a quienes corresponda</button>
        </div>
      </form>
    </div>
    <div class="card">
      <h3>📲 Notificaciones push</h3>
      <p class="small">Si no te llegan las notificaciones al celular, activá el permiso y probá una.</p>
      <button class="btn primary btn-block" onclick="activarPush()">🔔 Activar notificaciones</button>
      <button class="btn ghost btn-block mt" onclick="testPush()">🧪 Probar notificación</button>
      <p class="small mt" id="pushDiag" style="color:var(--muted)"></p>
    </div>
    <div class="card">
      <h3>Actualizar cuota masiva</h3>
      <p class="small">Aplica el valor de "Cuota mensual por defecto" a <b>todos los alumnos activos</b> y les manda una notificación a cada uno.</p>
      <button class="btn warn btn-block" onclick="aplicarCuotaTodos()">🔄 Aplicar cuota a todos los alumnos</button>
    </div>`;
  $('#cfgForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/settings', { method: 'PUT', body: {
        academy_name: $('#cNombre').value, academy_color: $('#cColor').value,
        academy_code: $('#cCodigo').value, default_cuota: $('#cCuota').value,
        due_day: $('#cDue').value, cargo_demora_pct: $('#cDemora').value, pago_link: $('#cLink').value, pago_alias: $('#cAlias').value,
        mp_access_token: $('#cMpTk').value, wp_numero: $('#cWp').value, logro_asist: $('#cLogroAsist').value, logro_videos: $('#cLogroVids').value } });
      toast('Configuración guardada ✓');
      if (location.reload) { /* color aplicado al recargar */ }
      window.ACADEMY_NAME = $('#cNombre').value;
      $('#academyName').textContent = $('#cNombre').value;
      $('#academyTitle') && ($('#academyTitle').textContent = $('#cNombre').value);
    } catch (err) { toast(err.message); }
  });
  $('#autoForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/settings', { method: 'PUT', body: {
        auto_mensaje: $('#aMsg').value, auto_inact_dias: $('#aInact').value,
        auto_deuda_dias: $('#aDeuda').value, auto_mensaje_activo: $('#aActivo').checked ? '1' : '0' } });
      toast('Mensaje automático guardado ✓');
    } catch (err) { toast(err.message); }
  });
}
async function testPush() {
  try {
    const r = await api('/api/test_push', { method: 'POST' });
    const el = $('#pushDiag');
    if (el) el.textContent = `✓ Enviado a ${r.enviados} dispositivo(s) de ${r.suscripciones} suscripción(es). ¿Te llegó?`;
    toast('Notificación enviada ✓ ¿Te llegó?');
  } catch (e) {
    toast(e.message);
    const el = $('#pushDiag');
    if (el) el.textContent = '✗ ' + e.message;
  }
}
async function activarPush() {
  try {
    if (!('Notification' in window)) { toast('Este navegador no soporta notificaciones'); return; }
    if (Notification.permission === 'denied') { toast('Permiso denegado en el navegador. Entrá a Ajustes del sitio y permití las notificaciones.'); return; }
    await setupPush();
    toast('Notificaciones activadas ✓ Probá con el botón de abajo.');
  } catch (e) { toast('No se pudo activar: ' + e.message); }
}
async function aplicarCuotaTodos() {
  if (!confirm('¿Actualizar la cuota de TODOS los alumnos activos al valor de "Cuota mensual por defecto"? Se les notifica a cada uno.')) return;
  try {
    const r = await api('/api/settings/aplicar_cuota', { method: 'POST' });
    toast(`Cuota actualizada en ${r.alumnos} alumnos ✓`);
  } catch (e) { toast(e.message); }
}
async function enviarAutoAhora() {
  try {
    const r = await api('/api/mensajes/auto', { method: 'POST' });
    toast(r.enviados.length ? `Mensaje enviado a ${r.enviados.length} alumnos (${r.enviados.map(x => x.nombre).join(', ')})` : 'Ningún alumno necesita aviso hoy.');
  } catch (e) { toast(e.message); }
}

/* fetch academy name para el título */
try { fetch('/api/settings').then(r => r.json()).then(s => {
  if (s.academy_name) window.ACADEMY_NAME = s.academy_name;
}).catch(() => {}); } catch (e) {}

/* =====================================================================
   CHAT + GRUPOS POR CATEGORÍA
   ===================================================================== */
let CHAT_ACTIVO = null;
let CHAT_TIMER = null;

async function renderChat(el) {
  const d = await api('/api/chats').catch(() => ({ chats: [] }));
  el.innerHTML = `
    ${secHeader('💬 Chat')}
    <div class="card">
      <h3>Grupos por categoría</h3>
      <p class="small">Podés abrir un chat grupal automático para cada categoría.</p>
      <div class="chips">
        <button class="chip" onclick="abrirGrupo('kids')">🧒 Grupo Kids</button>
        <button class="chip" onclick="abrirGrupo('juveniles')">👦 Grupo Juveniles</button>
        <button class="chip" onclick="abrirGrupo('adulto')">🧑 Grupo Adultos</button>
      </div>
    </div>
    <div class="card">
      <h3>Chats directos</h3>
      <button class="btn primary btn-block" onclick="nuevoChatDirecto()">➕ Nuevo chat</button>
    </div>
    <div class="card">
      <h3>Tus conversaciones</h3>
      <div id="chatLista">${d.chats.length ? d.chats.map(c =>
        `<div class="flex space-between" style="padding:10px 0;border-bottom:1px solid var(--line);cursor:pointer" onclick="abrirChatId(${c.id})">
          <span><b>${esc(c.nombre)}</b> <span class="small" style="color:var(--muted)">${c.tipo === 'grupo' ? '· ' + c.miembros + ' miembros' : ''}</span></span>
          <span class="small" style="color:var(--accent2)">Abrir →</span>
        </div>`).join('') : '<div class="empty">Todavía no tenés conversaciones.</div>'}</div>
    </div>`;
}

async function abrirGrupo(cat) {
  try {
    const r = await api('/api/chats', { method: 'POST', body: { categoria: cat } });
    abrirChatId(r.id);
  } catch (e) { toast(e.message); }
}

async function nuevoChatDirecto() {
  const d = await api('/api/contactos').catch(() => ({ contactos: [] }));
  openModal(`
    <h3>Nuevo chat</h3>
    <div>
      ${d.contactos.length ? d.contactos.map(c =>
        `<div class="flex space-between" style="padding:10px 0;border-bottom:1px solid var(--line);cursor:pointer" onclick="crearDirecto(${c.id})">
          <span>${avatarHTML(c.foto, c.nombre, 'sm')} <b>${esc(c.nombre)}</b> ${c.cinturon ? beltHTML(c.cinturon) : ''}</span>
          <span class="small" style="color:var(--accent2)">Abrir →</span>
        </div>`).join('') : '<div class="empty">No hay contactos disponibles</div>'}
    </div>
    <button class="btn ghost btn-block mt" onclick="closeModal()">Cerrar</button>`);
}

async function crearDirecto(uid) {
  try {
    const r = await api('/api/chats', { method: 'POST', body: { user_id: uid } });
    closeModal();
    abrirChatId(r.id);
  } catch (e) { toast(e.message); }
}

async function abrirChatId(cid) {
  CHAT_ACTIVO = cid;
  const d = await api('/api/chats/' + cid + '/mensajes').catch((err) => ({ __err: err.message }));
  if (!d || d.__err) {
    const msg = 'No pudimos abrir el chat: ' + (d ? d.__err : 'error desconocido');
    if (window.toastGlobal) console.error(msg);
    toast(msg);
    CHAT_ACTIVO = null;
    return;
  }
  const mensajes = (d.mensajes || []).map(m => `
    <div class="chat-msg ${m.user_id === USER.id ? 'own' : ''}">
      <div class="chat-bubble">${esc(m.mensaje)}</div>
      <div class="chat-meta">${esc(m.nombre)} · ${esc(m.fecha)}</div>
    </div>`).join('');
  // Activar la sección de chat sin volver a llamar a renderChat (que reemplazaría
  // esta conversación por la lista de chats al completar su fetch).
  $$('.sec').forEach(s => s.classList.remove('active'));
  let secEl = $('#sec-chat');
  if (!secEl) {
    secEl = document.createElement('div');
    secEl.className = 'sec';
    secEl.id = 'sec-chat';
    $('#content').appendChild(secEl);
  }
  secEl.classList.add('active');
  $$('#bottombar .bb-item').forEach(x => x.classList.toggle('active', x.dataset.sec === 'chat'));
  const el = secEl;
  el.innerHTML = `
    ${secHeader('💬 ' + esc(d.chat.nombre || 'Chat'))}
    <button class="btn ghost small mb" onclick="renderChat($('#sec-chat'))">← Volver a la lista</button>
    <div class="card">
      <div id="chatMsgs" style="max-height:55vh;overflow:auto;display:flex;flex-direction:column">${mensajes || '<div class="empty">Decí hola 👋</div>'}</div>
      <div style="display:flex;gap:8px;margin-top:12px">
        <input id="chatInput" placeholder="Escribí un mensaje..." style="flex:1">
        <button class="btn primary" onclick="enviarChat()">Enviar</button>
      </div>
    </div>`;
  const inp = $('#chatInput');
  const box = $('#chatMsgs'); box.scrollTop = box.scrollHeight;
  inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') enviarChat(); });
  if (CHAT_TIMER) clearInterval(CHAT_TIMER);
  CHAT_TIMER = setInterval(() => { if (CHAT_ACTIVO && $('#sec-chat') && !document.hidden) actualizarChatMsgs(); }, 5000);
}

async function actualizarChatMsgs() {
  const d = await api('/api/chats/' + CHAT_ACTIVO + '/mensajes').catch(() => null);
  if (!d || !$('#chatMsgs')) return;
  const box = $('#chatMsgs');
  const eraAbajo = box.scrollTop + box.clientHeight >= box.scrollHeight - 40;
  box.innerHTML = (d.mensajes || []).map(m => `
    <div class="chat-msg ${m.user_id === USER.id ? 'own' : ''}">
      <div class="chat-bubble">${esc(m.mensaje)}</div>
      <div class="chat-meta">${esc(m.nombre)} · ${esc(m.fecha)}</div>
    </div>`).join('');
  if (eraAbajo) box.scrollTop = box.scrollHeight;
}

async function enviarChat() {
  const inp = $('#chatInput');
  const msg = inp.value.trim();
  if (!CHAT_ACTIVO || !msg) return;
  inp.value = '';
  try {
    await api('/api/chats/' + CHAT_ACTIVO + '/mensajes', { method: 'POST', body: { mensaje: msg } });
    actualizarChatMsgs();
  } catch (e) { toast(e.message); }
}

/* =====================================================================
   MURO
   ===================================================================== */
async function renderMuro(el) {
  const d = await api('/api/muro').catch(() => ({ muro: [] }));
  el.innerHTML = `
    ${secHeader('📢 Muro de la academia')}
    <div class="card">
      <textarea id="muroTexto" placeholder="¿Qué está pasando en la academia? Compartí algo..." style="width:100%;min-height:70px"></textarea>
      <input type="file" id="muroFoto" accept="image/*" style="margin-top:8px">
      <button class="btn primary btn-block mt" onclick="publicarMuro()">Publicar</button>
    </div>
    <div id="muroFeed">
      ${d.muro.length ? d.muro.map(p => `
        <div class="post-card">
          <div class="post-head">
            ${avatarHTML(p.foto, p.nombre, 'sm')} <b>${esc(p.nombre)}</b> ${p.cinturon ? beltHTML(p.cinturon) : ''}
            <span class="small" style="color:var(--muted)">· ${esc(p.fecha)}</span>
            ${p.user_id === USER.id ? `<button class="btn ghost small" style="margin-left:auto" onclick="borrarMuro(${p.id})">🗑</button>` : ''}
          </div>
          ${p.texto ? `<p style="margin:8px 0">${esc(p.texto)}</p>` : ''}
          ${(p.fotos || []).length ? `<div style="display:flex;flex-wrap:wrap;gap:6px">${p.fotos.slice(0,4).map(f => `<img src="${esc(f)}" style="max-width:150px;max-height:150px;border-radius:8px;object-fit:cover">`).join('')}</div>` : ''}
        </div>`).join('') : '<div class="empty">Todavía no hay publicaciones.</div>'}
    </div>`;
}

async function publicarMuro() {
  const texto = $('#muroTexto').value.trim();
  const file = $('#muroFoto').files && $('#muroFoto').files[0];
  let foto = null;
  if (file) {
    try { foto = await leerArchivoBase64(file); } catch (e) {}
  }
  if (!texto && !foto) { toast('Escribí algo o subí una foto'); return; }
  try {
    await api('/api/muro', { method: 'POST', body: { texto, fotos: foto ? [foto] : [] } });
    toast('Publicado ✓');
    renderMuro($('#sec-muro'));
  } catch (e) { toast(e.message); }
}
function leerArchivoBase64(file) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(r.result);
    r.onerror = rej;
    r.readAsDataURL(file);
  });
}
async function borrarMuro(id) {
  if (!confirm('¿Eliminar esta publicación?')) return;
  try { await api('/api/muro/' + id, { method: 'DELETE' }); renderMuro($('#sec-muro')); }
  catch (e) { toast(e.message); }
}

/* =====================================================================
   GALERÍA DE FOTOS
   ===================================================================== */
async function renderGaleria(el) {
  const d = await api('/api/muro').catch(() => ({ muro: [] }));
  const fotos = [];
  d.muro.forEach(p => (p.fotos || []).forEach(f => fotos.push({ f, n: p.nombre })));
  el.innerHTML = `
    ${secHeader('🖼️ Galería de fotos')}
    <div class="card">${fotos.length
      ? `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px">${fotos.map(x => `<div style="position:relative"><img src="${esc(x.f)}" style="width:100%;height:120px;object-fit:cover;border-radius:10px" onclick="window.open('${esc(x.f)}','_blank')"><span class="small" style="position:absolute;bottom:4px;left:6px;color:#fff;text-shadow:0 1px 2px #000">${esc(x.n)}</span></div>`).join('')}</div>`
      : '<div class="empty">Aún no hay fotos. Publicá una en el Muro 🖼️</div>'}</div>`;
}

/* =====================================================================
   RANKING
   ===================================================================== */
async function renderRanking(el) {
  const d = await api('/api/ranking').catch(() => ({ ranking: [] }));
  const medallas = ['🥇', '🥈', '🥉'];
  el.innerHTML = `
    ${secHeader('🏆 Ranking de la academia')}
    <div class="card">
      <p class="small">Puntos: <b>+2</b> por asistencia · <b>+5</b> por video completado · <b>+1</b> por video visto.</p>
      ${d.ranking.length ? d.ranking.map((r, i) => `
        <div class="flex space-between" style="padding:10px 0;border-bottom:1px solid var(--line)">
          <span>${medallas[i] || (i + 1) + 'º'} ${avatarHTML(r.foto, r.nombre, 'sm')} <b>${esc(r.nombre)}</b> ${r.cinturon ? beltHTML(r.cinturon) : ''}</span>
          <span class="small">${r.asistencias} asist · ${r.completados} vid · <b style="color:var(--accent2)">${r.puntos} pts</b></span>
        </div>`).join('') : '<div class="empty">Todavía no hay datos para ranking.</div>'}
    </div>`;
}

/* =====================================================================
   METAS DE ENTRENAMIENTO
   ===================================================================== */
async function renderMetas(el) {
  const d = await api('/api/metas').catch(() => ({ metas: [] }));
  el.innerHTML = `
    ${secHeader('🎯 Mis metas de entrenamiento')}
    <div class="card">
      <form id="metaForm" class="grid2">
        <div class="field" style="grid-column:1/-1"><label>Meta</label><input id="mTitulo" placeholder="ej: Entrenar 3 veces por semana"></div>
        <div class="field"><label>Tipo</label><select id="mTipo"><option value="semanas">Por semana</option><option value="mes">Por mes</option><option value="objetivo">Objetivo puntual</option></select></div>
        <div class="field"><label>Objetivo (veces/valor)</label><input type="number" id="mObj" value="3"></div>
        <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">＋ Agregar meta</button></div>
      </form>
    </div>
    <div class="card">
      <h3>Mis metas</h3>
      ${d.metas.length ? d.metas.map(m => `
        <div class="flex space-between" style="padding:10px 0;border-bottom:1px solid var(--line)">
          <span>${m.cumplida ? '✅' : '⭕'} <b>${esc(m.titulo)}</b> <span class="small" style="color:var(--muted)">(${esc(m.tipo)} · ${m.objetivo})</span></span>
          <span>
            ${m.cumplida ? `<button class="btn ghost small" onclick="metaCumplida(${m.id},0)">Desmarcar</button>` : `<button class="btn primary small" onclick="metaCumplida(${m.id},1)">Cumplida ✓</button>`}
            <button class="btn ghost small" onclick="borrarMeta(${m.id})">🗑</button>
          </span>
        </div>`).join('') : '<div class="empty">No tenés metas todavía. Agrega la primera 🎯</div>'}
    </div>`;
  $('#metaForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/metas', { method: 'POST', body: { titulo: $('#mTitulo').value, tipo: $('#mTipo').value, objetivo: +$('#mObj').value } });
      renderMetas($('#sec-metas'));
    } catch (err) { toast(err.message); }
  });
}
async function metaCumplida(id, val) {
  try { await api('/api/metas/' + id, { method: 'POST', body: { cumplida: val } }); renderMetas($('#sec-metas')); }
  catch (e) { toast(e.message); }
}
async function borrarMeta(id) {
  try { await api('/api/metas/' + id, { method: 'DELETE' }); renderMetas($('#sec-metas')); }
  catch (e) { toast(e.message); }
}

/* =====================================================================
   ENCUESTAS
   ===================================================================== */
async function renderEncuestas(el) {
  const d = await api('/api/encuestas').catch(() => ({ encuestas: [] }));
  const esStaff = USER.role !== 'alumno';
  el.innerHTML = `
    ${secHeader('📊 Encuestas')}
    ${esStaff ? `<div class="card">
      <h3>Crear encuesta</h3>
      <form id="encForm" class="grid2">
        <div class="field" style="grid-column:1/-1"><label>Pregunta</label><input id="eTitulo"></div>
        <div class="field" style="grid-column:1/-1"><label>Opciones (una por línea)</label><textarea id="eOpc" style="width:100%;min-height:70px" placeholder="Opción 1&#10;Opción 2&#10;Opción 3"></textarea></div>
        <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">Publicar encuesta</button></div>
      </form>
    </div>` : ''}
    <div class="card"><h3>Encuestas</h3>
      ${d.encuestas.length ? d.encuestas.map(e => {
        const total = e.conteo.reduce((a, b) => a + b, 0);
        return `<div style="padding:10px 0;border-bottom:1px solid var(--line)">
          <b>${esc(e.titulo)}</b> <span class="small" style="color:var(--muted)">· ${total} voto${total === 1 ? '' : 's'}</span>
          ${e.opciones.map((o, i) => {
            const pct = total ? Math.round(e.conteo[i] * 100 / total) : 0;
            const esMi = e.mi_voto === i;
            return `<div style="margin-top:6px">
              <div class="flex space-between"><span class="small">${esMi ? '✓ ' : ''}${esc(o)}</span><span class="small">${e.conteo[i]} · ${pct}%</span></div>
              <button class="btn ghost small" style="width:100%;margin-top:2px" onclick="votarEncuesta(${e.id},${i})">${esMi ? 'Cambiar voto' : 'Votar'}</button>
              <div style="height:6px;background:var(--bg);border-radius:4px;margin-top:2px"><div style="height:100%;width:${pct}%;background:var(--red);border-radius:4px"></div></div>
            </div>`;
          }).join('')}
        </div>`;
      }).join('') : '<div class="empty">No hay encuestas todavía.</div>'}
    </div>`;
  if (esStaff) $('#encForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const opciones = $('#eOpc').value.split('\n').map(s => s.trim()).filter(Boolean);
    try {
      await api('/api/encuestas', { method: 'POST', body: { titulo: $('#eTitulo').value, opciones } });
      renderEncuestas($('#sec-encuestas'));
    } catch (err) { toast(err.message); }
  });
}
async function votarEncuesta(id, op) {
  try { await api('/api/encuestas/' + id + '/votar', { method: 'POST', body: { opcion: op } }); renderEncuestas($('#sec-encuestas')); }
  catch (e) { toast(e.message); }
}

/* =====================================================================
   EVENTOS Y ACTIVIDADES
   ===================================================================== */
async function renderEventos(el) {
  const d = await api('/api/eventos').catch(() => ({ eventos: [] }));
  const esStaff = USER.role !== 'alumno';
  el.innerHTML = `
    ${secHeader('🗓️ Eventos y actividades')}
    ${esStaff ? `<div class="card">
      <h3>Crear evento</h3>
      <form id="evForm" class="grid2">
        <div class="field"><label>Título</label><input id="vTitulo"></div>
        <div class="field"><label>Fecha del evento</label><input type="date" id="vFecha"></div>
        <div class="field"><label>Hora</label><input type="time" id="vHora"></div>
        <div class="field"><label>Lugar</label><input id="vLugar"></div>
        <div class="field" style="grid-column:1/-1"><label>Descripción</label><textarea id="vDesc" style="width:100%;min-height:60px"></textarea></div>
        <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">Publicar evento</button></div>
      </form>
    </div>` : ''}
    <div class="card"><h3>Próximos eventos</h3>
      ${d.eventos.length ? d.eventos.map(ev => `
        <div class="flex space-between" style="padding:10px 0;border-bottom:1px solid var(--line)">
          <div>
            <b>${esc(ev.titulo)}</b>
            <div class="small" style="color:var(--muted)">${esc(ev.fecha_evento)}${ev.hora ? ' · ' + esc(ev.hora) : ''}${ev.lugar ? ' · ' + esc(ev.lugar) : ''}</div>
            ${ev.descripcion ? `<div class="small">${esc(ev.descripcion)}</div>` : ''}
            <div class="small" style="color:var(--muted)">👥 ${ev.asisten_conf} confirmaron</div>
          </div>
          <span>
            <button class="btn ${ev.voy ? 'ghost' : 'primary'} small" onclick="asistirEvento(${ev.id}, ${ev.voy ? 1 : 0})">${ev.voy ? 'No asistiré' : 'Voy a ir ✓'}</button>
            ${USER.role === 'admin' ? `<button class="btn ghost small" onclick="borrarEvento(${ev.id})">🗑</button>` : ''}
          </span>
        </div>`).join('') : '<div class="empty">No hay eventos próximos.</div>'}
    </div>`;
  if (esStaff) $('#evForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/eventos', { method: 'POST', body: {
        titulo: $('#vTitulo').value, fecha_evento: $('#vFecha').value, hora: $('#vHora').value,
        lugar: $('#vLugar').value, descripcion: $('#vDesc').value } });
      renderEventos($('#sec-eventos'));
    } catch (err) { toast(err.message); }
  });
}
async function asistirEvento(id, voy) {
  try { await api('/api/eventos/' + id + '/asistir', { method: 'POST', body: { quitar: voy ? 1 : 0 } }); renderEventos($('#sec-eventos')); }
  catch (e) { toast(e.message); }
}
async function borrarEvento(id) {
  if (!confirm('¿Eliminar este evento?')) return;
  try { await api('/api/eventos/' + id, { method: 'DELETE' }); renderEventos($('#sec-eventos')); }
  catch (e) { toast(e.message); }
}

/* =====================================================================
   HISTORIAL CON GRÁFICOS
   ===================================================================== */
async function renderHistorial(el) {
  const d = await api('/api/historial').catch(() => ({ pagos: [], asistencia: [] }));
  const pagos = d.pagos || [];
  const asis = d.asistencia || [];
  const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
  const maxPagos = Math.max(1, ...pagos.map(p => p.monto));
  const maxAsis = Math.max(1, ...asis.map(a => a.alumnos));
  el.innerHTML = `
    ${secHeader('📈 Historial financiero y asistencia')}
    <div class="card">
      <h3>💵 Ingresos por mes</h3>
      ${pagos.length ? `<div style="display:flex;align-items:flex-end;gap:8px;height:180px;padding-top:10px">
        ${pagos.map(p => `<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end">
          <span class="small" style="color:var(--accent2)">$${num(p.monto)}</span>
          <div style="width:100%;background:var(--red);border-radius:6px 6px 0 0;height:${Math.max(4, Math.round(p.monto * 160 / maxPagos))}px"></div>
          <span class="small" style="color:var(--muted)">${MESES[p.mes - 1]}</span>
        </div>`).join('')}
      </div>` : '<div class="empty">Sin pagos registrados.</div>'}
    </div>
    <div class="card">
      <h3>🥋 Asistencia diaria (este mes)</h3>
      ${asis.length ? `<div style="display:flex;align-items:flex-end;gap:4px;height:160px;padding-top:10px;overflow-x:auto">
        ${asis.map(a => `<div style="flex:1;min-width:20px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end">
          <div style="width:100%;background:var(--blue);border-radius:4px 4px 0 0;height:${Math.max(4, Math.round(a.alumnos * 140 / maxAsis))}px"></div>
          <span class="small" style="color:var(--muted)">${a.fecha.slice(8)}</span>
        </div>`).join('')}
      </div>` : '<div class="empty">Sin asistencias este mes.</div>'}
    </div>
    <div class="card">
      <h3>Exportar</h3>
      <button class="btn primary" onclick="exportarExcel()">⬇️ Exportar historial a Excel</button>
    </div>`;
}

/* =====================================================================
   EXPORTAR A EXCEL
   ===================================================================== */
async function exportarExcel() {
  try {
    const hist = await api('/api/historial').catch(() => ({ pagos: [], asistencia: [] }));
    const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
    let csv = '\uFEFFMes,Año,Ingresos,Cantidad\n';
    (hist.pagos || []).forEach(p => csv += MESES[p.mes - 1] + ',' + p.anio + ',$' + p.monto + ',' + p.n + '\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'historial_ikigai.csv';
    a.click();
    toast('Historial exportado ✓');
  } catch (e) { toast(e.message); }
}

/* =====================================================================
   RECUPERAR CONTRASEÑA OLVIDADA
   ===================================================================== */
async function guardarSeguridad() {
  const q = ($('#pSecQ')?.value || '').trim();
  const a = ($('#pSecA')?.value || '').trim();
  const np = ($('#pSecPass')?.value || '');
  if (!q || !a) { toast('Completá la pregunta y la respuesta de seguridad'); return; }
  try {
    await api('/api/perfil/seguridad', { method: 'PUT', body: { pregunta: q, respuesta: a, nueva_password: np } });
    toast('Seguridad guardada ✓');
  } catch (e) { toast(e.message); }
}

async function reiniciarPassword(id, nombre) {
  openModal(`
    <h3>🔑 Reiniciar contraseña de ${esc(nombre)}</h3>
    <p class="small">Poné una contraseña nueva para ${esc(nombre)}. Se le notificará que su contraseña fue reiniciada.</p>
    <div class="field"><label>Contraseña nueva (mín. 4 caracteres)</label><input type="password" id="nuevaPass"></div>
    <button class="btn primary btn-block" onclick="hacerReinicio(${id})">Guardar y notificar</button>
    <button class="btn ghost btn-block" onclick="closeModal()">Cancelar</button>
  `);
}

async function hacerReinicio(id) {
  const np = $('#nuevaPass')?.value || '';
  if (np.length < 4) { toast('La contraseña debe tener al menos 4 caracteres'); return; }
  try {
    await api('/api/usuarios/' + id + '/password', { method: 'POST', body: { password: np } });
    closeModal();
    toast('Contraseña reiniciada ✓ Se notificó al alumno.');
  } catch (e) { toast(e.message); }
}
function overlayRecup(markup) {
  const old = document.getElementById('recupOverlay');
  if (old) old.remove();
  const ov = document.createElement('div');
  ov.id = 'recupOverlay';
  ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.62);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
  ov.innerHTML = `<div style="width:100%;max-width:400px;background:var(--card,#271619);border:1px solid var(--line,#421f24);border-radius:16px;padding:22px">${markup}</div>`;
  ov.addEventListener('click', (e) => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
  return ov;
}

function overlayRecupCerrar() {
  const old = document.getElementById('recupOverlay');
  if (old) old.remove();
}

function abrirModalRecuperar() {
  overlayRecup(`
    <h3 style="color:#fff;margin:0 0 14px">Recuperar contraseña</h3>
    <p class="small" style="color:var(--muted,#b0969b)">Escribí tu usuario. Si configuraste la pregunta de seguridad, la respondes para cambiar la clave. Si no, pedile al profe/admin que la reinicie.</p>
    <div class="field"><label>Tu usuario</label><input id="recUser" placeholder="Tu usuario"></div>
    <div id="recPasso"></div>
    <button type="button" class="btn primary btn-block" onclick="recPaso1()">Continuar</button>
    <button type="button" class="link-btn" style="width:100%;text-align:center;margin-top:10px" onclick="overlayRecupCerrar()">Cerrar</button>
  `);
}

async function recPaso1() {
  const user = ($('#recUser')?.value || '').trim();
  if (!user) { toast('Escribí tu usuario'); return; }
  try {
    const d = await api('/api/recuperar', { method: 'POST', body: { username: user } });
    const passo = document.getElementById('recPasso');
    if (d.ok) {
      if (passo) passo.innerHTML = `
        <div class="field" style="margin-top:10px"><label>Pregunta de seguridad</label>
          <input value="${esc(d.pregunta)}" disabled style="opacity:.7"></div>
        <div class="field"><label>Tu respuesta</label><input id="recResp" placeholder="Respuesta"></div>
        <div class="field"><label>Contraseña nueva (mín. 4 caracteres)</label><input type="password" id="recNueva"></div>
        <button type="button" class="btn primary btn-block" onclick="recPaso2('${esc(user)}')">Cambiar mi contraseña</button>`;
    } else {
      if (passo) passo.innerHTML = `
        <p style="color:var(--warn,#f1c40f)">${esc(d.error || 'No tiene pregunta de seguridad configurada.')}</p>
        <p class="small" style="color:var(--muted,#b0969b)">Pedile al profe/admin que reinicie tu contraseña desde la pantalla de Alumnos.</p>`;
    }
  } catch (e) {
    const passo = document.getElementById('recPasso');
    if (passo) passo.innerHTML = `<p style="color:var(--bad,#e74c3c)">${esc(e.message)}</p>`;
  }
}

async function recPaso2(user) {
  const resp = ($('#recResp')?.value || '').trim();
  const nueva = $('#recNueva')?.value || '';
  if (!resp) { toast('Respondé la pregunta de seguridad'); return; }
  if (nueva.length < 4) { toast('La contraseña debe tener al menos 4 caracteres'); return; }
  try {
    const d = await api('/api/recuperar/verificar', { method: 'POST', body: { username: user, respuesta: resp, nueva_password: nueva } });
    if (d.ok) {
      overlayRecupCerrar();
      toast('Contraseña cambiada ✓ Ingresá con tu clave nueva.');
    }
  } catch (e) { toast(e.message); }
}

