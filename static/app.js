/* Academia BJJ - app.js */
const BELTS_ADULT = window.BELTS_ADULT || ['Blanco', 'Azul', 'Rosa', 'Púrpura', 'Marrón', 'Negro'];
const BELTS_KIDS = window.BELTS_KIDS || ['Gris', 'Amarillo', 'Naranja', 'Verde', 'Blanco'];

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
  const cats = ['adulto', 'kids'];
  function fillBelts(sel, cat) {
    const opts = cat === 'kids' ? BELTS_KIDS : BELTS_ADULT;
    sel.innerHTML = opts.map(b => `<option value="${esc(b)}">${esc(b)}</option>`).join('');
  }
  fillBelts($('#regAlumnoCinturon'), 'adulto');
  fillBelts($('#regProfeCinturon'), 'adulto');
  $('#regAlumnoCat').addEventListener('change', (e) => fillBelts($('#regAlumnoCinturon'), e.target.value));

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

  $('#tab-reg-alumno').addEventListener('submit', async (e) => {
    e.preventDefault();
    const m = $('#loginMsg');
    try {
      const d = await api('/api/register', { method: 'POST', body: {
        role: 'alumno', username: $('#regAlumnoUser').value.trim(),
        password: $('#regAlumnoPass').value, nombre: $('#regAlumnoNombre').value.trim(),
        edad: $('#regAlumnoEdad').value, peso: $('#regAlumnoPeso').value,
        categoria: $('#regAlumnoCat').value, cinturon: $('#regAlumnoCinturon').value,
        gi_pref: $('#regAlumnoGi').value } });
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
        peso: $('#regProfePeso').value, cinturon: $('#regProfeCinturon').value } });
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
    const key = await (await fetch('/api/vapid_public_key')).json();
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(key.key),
    });
    await api('/api/push_subscribe', { method: 'POST', body: { subscription: sub.toJSON() } });
  } catch (e) { /* push no disponible (http/https) */ }
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
  return `<video controls preload="metadata" playsinline><source src="${esc(v.url)}"></video>`;
}

function videoCardHTML(v, isStaff) {
  const beltCls = 'tag ' + (v.belt === 'Todos' ? 'alumno' : 'nogi');
  const visto = v.visto ? ' visto' : '';
  const staffBtns = isStaff ? `<div class="post-views" id="views-${v.id}"></div>` : '';
  return `<div class="post-card" id="video-${v.id}">
    <div class="post-head">
      ${avatarHTML('', v.subidor_nombre || 'Profesor', 'sm')}
      <div style="flex:1">
        <b>${esc(v.subidor_nombre || 'Profesor')}</b>
        <div class="small">${esc(v.fecha || '')} · <span class="${beltCls}">${esc(v.belt)}</span></div>
      </div>
      ${isStaff && v.subido_por === USER.id || USER.role === 'admin' ? `<button class="btn bad small" onclick="borrarVideo(${v.id})">🗑</button>` : ''}
    </div>
    <div class="post-media">${videoMediaHTML(v)}</div>
    <div class="post-actions">
      <button class="post-btn${visto}" onclick="marcarVisto(${v.id}, this)">✓ Visto</button>
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
  const all = await api('/api/videos' + (isStaff ? '?belt=' + encodeURIComponent($('#videoBelt') && $('#videoBelt').value || 'Todos') : ''));
  const videos = all.videos;
  const belts = R === 'kids' ? BELTS_KIDS : BELTS_ADULT;
  el.innerHTML = `
    ${secHeader('Videos', isStaff ? 'Subí técnicas para cada cinturón y mirá quién las vio.' : 'Técnicas para tu cinturón. Mirá y marcá las que viste.')}
    <div class="flex space-between mb">
      ${isStaff ? `<select id="videoBelt" class="search" style="max-width:200px;padding:9px">
        <option value="Todos">Todos los cinturones</option>
        ${belts.map(b => `<option>${esc(b)}</option>`).join('')}
      </select>` : '<span></span>'}
      ${isStaff ? `<button class="btn primary small" onclick="subirVideo()">＋ Subir video</button>` : ''}
    </div>
    <div class="feed" id="videoFeed">
      ${videos.length ? videos.map(v => videoCardHTML(v, isStaff)).join('') : '<div class="feed-card empty">Todavía no hay videos para esta categoría.</div>'}
    </div>`;
  if (isStaff) {
    $('#videoBelt').addEventListener('change', () => renderVideos(el));
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
  const belts = USER.role === 'kids' ? BELTS_KIDS : BELTS_ADULT;
  openModal(`
    <h3>Subir video</h3>
    <form id="vForm" class="grid2">
      <div class="field" style="grid-column:1/-1"><label>Título</label><input id="vTitulo" required placeholder="Ej: Armbar desde guardia"></div>
      <div class="field" style="grid-column:1/-1"><label>Descripción (opcional)</label><input id="vDesc" placeholder="Qué técnica es, nivel, consejos..."></div>
      <div class="field"><label>Cinturón para el que es</label><select id="vBelt">
        <option value="Todos">Todos</option>
        ${belts.map(b => `<option>${esc(b)}</option>`).join('')}</select></div>
      <div class="field"><label>O link de YouTube</label><input id="vLink" placeholder="https://youtube.com/watch?v=..."></div>
      <div class="field" style="grid-column:1/-1"><label>O subí un archivo (MP4)</label>
        <input type="file" id="vFile" accept="video/mp4,video/webm,video/ogg,video/quicktime"></div>
      <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">Publicar video</button></div>
    </form>`);
  $('#vForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const titulo = $('#vTitulo').value.trim();
    const desc = $('#vDesc').value.trim();
    const belt = $('#vBelt').value;
    const file = $('#vFile').files && $('#vFile').files[0];
    const link = $('#vLink').value.trim();
    if (!file && !link) { toast('Subí un archivo o pegá un link'); return; }
    const btn = $('button[type="submit"]', $('#vForm'));
    btn.disabled = true; btn.textContent = 'Publicando...';
    try {
      if (file) {
        const fd = new FormData();
        fd.append('video', file); fd.append('titulo', titulo); fd.append('descripcion', desc); fd.append('belt', belt);
        const res = await fetch('/api/videos/upload', { method: 'POST', body: fd });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error || 'Error al subir');
      } else {
        await api('/api/videos', { method: 'POST', body: { titulo, descripcion, belt, url: link } });
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
          ${estado !== 'al_dia' ? `<p class="small" style="color:#ff9b8f;margin-bottom:0">⚠️ Pagá ${c.cuota ? '$' + num(c.cuota) : 'tu cuota'} y avisá a un profesor para que registre tu pago.</p>` : ''}
        </div>

        <div class="feed-card">
          <div class="small mb">📅 Clases de hoy</div>
          ${hoyClases.length ? hoyClases.map(h => `<div class="clase-item ${h.tipo.toLowerCase()}"><span class="hora">${esc(h.hora)}</span> · <span class="tag ${h.tipo.toLowerCase()}">${esc(h.tipo)}</span> · <span class="profe">${esc(h.profesor_nombre || 'Sin profesor')}</span></div>`).join('') : '<div class="small" style="color:var(--muted)">Hoy no hay clases cargadas. Mirá la sección Horarios.</div>'}
        </div>

        ${videos.length ? `<div class="post-card" style="padding:0;overflow:hidden">
          <div class="post-head" style="padding:10px 14px 0"><b style="color:var(--accent2)">🎥 Técnicas para vos (${esc(me.cinturon)})</b></div>
          <div class="feed" style="margin:0;padding:10px 14px 14px">${videos.map(v => videoCardHTML(v, false)).join('')}</div>
        </div>` : ''}

        <div class="chips">
          <button class="chip" onclick="showSec('horarios')">📅 Horarios</button>
          <button class="chip" onclick="showSec('videos')">🎥 Videos</button>
          <button class="chip" onclick="showSec('mispagos')">🧾 Mi cuota</button>
          <button class="chip" onclick="showSec('perfil')">👤 Mi perfil</button>
          <button class="chip" onclick="showSec('mi_asistencia')">✅ Mi asistencia</button>
        </div>
      </div>`;
  } else {
    const [stats, horarios, vids] = await Promise.all([
      api('/api/estadisticas'), api('/api/horarios'), api('/api/videos')]);
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
  const belts = cat === 'kids' ? BELTS_KIDS : BELTS_ADULT;
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
          <div class="field"><label>Edad</label><input type="number" id="pEdad" value="${me.edad != null ? me.edad : ''}"></div>
          <div class="field"><label>Peso (kg)</label><input type="number" step="0.1" id="pPeso" value="${me.peso != null ? me.peso : ''}"></div>
          <div class="field"><label>Categoría</label><select id="pCat">
            ${CATEGORIAS.map(c => `<option value="${c}" ${c === cat ? 'selected' : ''}>${c === 'kids' ? 'Kids' : 'Adulto'}</option>`).join('')}</select></div>
          <div class="field"><label>Cinturón / Faixa</label><select id="pCinturon">
            ${belts.map(b => `<option ${b === me.cinturon ? 'selected' : ''}>${esc(b)}</option>`).join('')}</select></div>
          <div class="field"><label>Modalidad</label><select id="pGi">
            <option ${me.gi_pref === 'Ambas' ? 'selected' : ''}>Ambas</option>
            <option ${me.gi_pref === 'Gi' ? 'selected' : ''}>Gi</option>
            <option ${me.gi_pref === 'NoGi' ? 'selected' : ''}>NoGi</option></select></div>
          <div class="field"><label>Cambiar contraseña (opcional)</label><input type="password" id="pPass" placeholder="Nueva contraseña"></div>
          <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">Guardar cambios</button></div>
        </form>
      </div>

      <div class="feed-card">
        <div class="small mb">📲 ¿Querés la app como si fuera de tu teléfono?</div>
        <button class="btn ghost" onclick="instalarManual()">📲 Instalar la app</button>
        <p class="small" style="margin-bottom:0">Se instala en tu pantalla de inicio sin pasar por Google. (En el celular: menú → "Agregar a pantalla de inicio".)</p>
      </div>
    </div>`;
  $('#pCat').addEventListener('change', (e) => {
    const b = e.target.value === 'kids' ? BELTS_KIDS : BELTS_ADULT;
    $('#pCinturon').innerHTML = b.map(x => `<option>${esc(x)}</option>`).join('');
  });
  $('#perfilForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/perfil', { method: 'PUT', body: {
        nombre: $('#pNombre').value.trim(), edad: $('#pEdad').value,
        peso: $('#pPeso').value, cinturon: $('#pCinturon').value,
        categoria: $('#pCat').value, gi_pref: $('#pGi').value,
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
        ${['Todos', 'Principiantes', 'Intermedios', 'Avanzados', 'Competencia'].map(n => `<option ${h && h[4] === n ? 'selected' : ''}>${n}</option>`).join('')}</select></div>
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

/* =====================================================================
   PAGOS (admin / profesor)
   ===================================================================== */
async function renderPagos(el) {
  const R = USER.role;
  const [pagos, alumnos, profesores] = await Promise.all([
    api('/api/pagos'), api('/api/alumnos'),
    R === 'admin' ? api('/api/profesores') : Promise.resolve({ profesores: [USER] })]);
  PROFESORES_CACHE = profesores.profesores;
  const mes = new Date().getMonth() + 1, anio = new Date().getFullYear();
  el.innerHTML = `
    ${secHeader('Registrar pago')}
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
      <h3>${R === 'profesor' ? 'Mis pagos recibidos' : 'Historial de pagos'}</h3>
      <div style="overflow:auto"><table>
        <tr><th>Fecha</th><th>Alumno</th><th>Profesor</th><th>Mes</th><th>Método</th><th>Monto</th>${R === 'admin' ? '<th></th>' : ''}</tr>
        ${pagos.pagos.length ? pagos.pagos.map(p => `<tr>
          <td>${esc(p.fecha)}</td><td><div class="flex" style="gap:8px">${avatarHTML('', p.alumno_nombre, 'sm')}<span>${esc(p.alumno_nombre)}</span></div></td>
          <td>${esc(p.profesor_nombre || '—')}</td><td>${p.mes}/${p.anio}</td>
          <td>${esc(p.metodo)}</td><td><b>$${num(p.monto)}</b></td>
          ${R === 'admin' ? `<td><button class="btn bad small" onclick="borrarPago(${p.id})">🗑</button></td>` : ''}</tr>`).join('')
          : '<tr><td colspan="6" class="empty">Todavía no hay pagos registrados</td></tr>'}
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
      await api('/api/pagos', { method: 'POST', body });
      toast('Pago registrado. Notificaciones enviadas ✓');
      renderPagos($('#sec-pagos'));
    } catch (err) { toast(err.message); }
  });
}
async function borrarPago(id) {
  if (!confirm('¿Eliminar este pago?')) return;
  await api('/api/pagos/' + id, { method: 'DELETE' }).catch(e => toast(e.message));
  renderPagos($('#sec-pagos'));
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
  el.innerHTML = `
    ${secHeader('Mi estado de cuenta')}
    <div class="card">
      <div class="flex space-between">
        <div>
          <h3 style="margin:0">Cuota de ${c.mes}/${c.anio}</h3>
          <p class="small">Tu cuota mensual es <b>$${num(c.cuota)}</b> · se considera paga hasta el día ${c.due_day} del mes.</p>
        </div>
        <div class="tag ${cls}" style="font-size:14px;padding:6px 14px">${lbl}</div>
      </div>
      <p class="small mt">💰 Para pagar: aboná ${c.cuota ? '$' + num(c.cuota) : 'tu cuota'} en la academia y avisá a un profesor para que registre el pago en la app. Te va a llegar una notificación.</p>
    </div>
    <div class="card"><h3>Mis pagos</h3>
      <div style="overflow:auto"><table>
        <tr><th>Fecha</th><th>Profesor que recibió</th><th>Mes</th><th>Método</th><th>Monto</th></tr>
        ${pagos.pagos.length ? pagos.pagos.map(p => `<tr>
          <td>${esc(p.fecha)}</td><td>${esc(p.profesor_nombre || '—')}</td>
          <td>${p.mes}/${p.anio}</td><td>${esc(p.metodo)}</td><td><b>$${num(p.monto)}</b></td></tr>`).join('')
          : '<tr><td colspan="5" class="empty">Aún no registraste pagos</td></tr>'}
      </table></div>
    </div>`;
}

/* =====================================================================
   ALUMNOS (admin / profesor)
   ===================================================================== */
async function renderAlumnos(el) {
  const d = await api('/api/alumnos');
  el.innerHTML = `
    ${secHeader('Alumnos', 'Los alumnos se registran solos en la pantalla de ingreso')}
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
            <button class="btn good small" onclick="notificarDeuda(${a.id})">🔔</button>
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

async function formAlumno(id) {
  if (!id) { toast('Los alumnos se registran solos desde la pantalla de ingreso'); return; }
  const a = (await api('/api/alumnos')).alumnos.find(x => x.id === id);
  openModal(`
    <h3>Editar alumno</h3>
    <form id="alForm" class="grid2">
      <div class="field"><label>Nombre y apellido</label><input id="aNombre" value="${esc(a.nombre)}" required></div>
      <div class="field"><label>Edad</label><input type="number" id="aEdad" value="${a.edad != null ? a.edad : ''}"></div>
      <div class="field"><label>Peso (kg)</label><input type="number" step="0.1" id="aPeso" value="${a.peso != null ? a.peso : ''}"></div>
      <div class="field"><label>Categoría</label><select id="aCat">${CATEGORIAS.map(c => `<option value="${c}" ${a.categoria === c ? 'selected' : ''}>${c === 'kids' ? 'Kids' : 'Adulto'}</option>`).join('')}</select></div>
      <div class="field"><label>Cinturón</label><select id="aCinturon"></select></div>
      <div class="field"><label>Modalidad</label><select id="aGi">
        ${['Ambas', 'Gi', 'NoGi'].map(g => `<option ${a.gi_pref === g ? 'selected' : ''}>${g}</option>`).join('')}</select></div>
      <div class="field"><label>Cuota mensual ($)</label><input type="number" step="0.01" id="aCuota" value="${a.cuota_mensual != null ? a.cuota_mensual : ''}" disabled></div>
      <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">Guardar</button></div>
    </form>`);
  function fillBelt() {
    const cat = $('#aCat').value;
    const belts = cat === 'kids' ? BELTS_KIDS : BELTS_ADULT;
    $('#aCinturon').innerHTML = belts.map(b => `<option ${a && a.cinturon === b ? 'selected' : ''}>${esc(b)}</option>`).join('');
  }
  fillBelt();
  $('#aCat').addEventListener('change', fillBelt);
  $('#alForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = { nombre: $('#aNombre').value.trim(), edad: $('#aEdad').value, peso: $('#aPeso').value,
      cinturon: $('#aCinturon').value, categoria: $('#aCat').value, gi_pref: $('#aGi').value };
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
        <div class="field" style="grid-column:1/-1"><button class="btn primary btn-block" type="submit">Guardar configuración</button></div>
      </form>
    </div>
    <div class="card">
      <h3>Probar notificaciones push</h3>
      <p class="small">Enviate una notificación de prueba a este dispositivo.</p>
      <button class="btn ghost" onclick="testPush()">🔔 Probar notificación</button>
    </div>`;
  $('#cfgForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/settings', { method: 'PUT', body: {
        academy_name: $('#cNombre').value, academy_color: $('#cColor').value,
        academy_code: $('#cCodigo').value, default_cuota: $('#cCuota').value,
        due_day: $('#cDue').value } });
      toast('Configuración guardada ✓');
      window.ACADEMY_NAME = $('#cNombre').value;
      $('#academyName').textContent = $('#cNombre').value;
      $('#academyTitle') && ($('#academyTitle').textContent = $('#cNombre').value);
    } catch (err) { toast(err.message); }
  });
}
async function testPush() {
  try {
    await api('/api/test_push', { method: 'POST' });
    toast('Notificación enviada. Si no llega, revisá los permisos del navegador.');
  } catch (e) { toast(e.message); }
}

/* fetch academy name para el título */
try { fetch('/api/settings').then(r => r.json()).then(s => {
  if (s.academy_name) window.ACADEMY_NAME = s.academy_name;
}).catch(() => {}); } catch (e) {}
