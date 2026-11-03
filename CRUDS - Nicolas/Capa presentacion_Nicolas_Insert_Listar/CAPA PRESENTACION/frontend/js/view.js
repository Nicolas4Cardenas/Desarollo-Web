// VISTA (MVC): únicamente dibuja tablas, botones y formularios.
const safe = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const label = value => safe(value ?? '—');
const money = value => new Intl.NumberFormat('es-CO', {style:'currency',currency:'COP',maximumFractionDigits:0}).format(Number(value||0));
export class RestaurantView {
  constructor() {
    this.target = document.getElementById('content');
    this.title = document.getElementById('pageTitle');
    this.modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('editorModal'));
  }
  setTitle(title) { this.title.textContent=title; }
  loading() { this.target.innerHTML='<div class="panel text-muted">Cargando registros…</div>'; }
  notice(message, bad=false) {
    const el=document.createElement('div');
    el.className=`toast align-items-center text-bg-${bad?'danger':'success'} border-0`;
    el.innerHTML='<div class="d-flex"><div class="toast-body"></div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Cerrar"></button></div>';
    el.querySelector('.toast-body').textContent=message;
    document.getElementById('toasts').append(el);
    const toast=new bootstrap.Toast(el,{delay:3500});
    el.addEventListener('hidden.bs.toast',()=>el.remove());toast.show();
  }
  table(cols, rows) {
    if (!rows?.length) return '<div class="empty">No hay registros.</div>';
    return `<div class="table-responsive"><table class="table table-striped table-sm mb-0"><thead><tr>${cols.map(x=>`<th>${safe(x.label)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${cols.map(x=>`<td>${x.render?x.render(row):label(row[x.key])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }
  header(note,action='') { return `<div class="panel-header"><p class="small-note mb-0">${safe(note)}</p>${action}</div>`; }
  button(action, title) { return `<button type="button" class="btn btn-primary btn-sm" data-action="${action}">${safe(title)}</button>`; }
  orders(rows) {
    this.target.innerHTML=`<div class="panel">${this.header('Consulta de pedidos e inserción de un pedido de prueba.',this.button('new-order','Insertar pedido'))}${this.table([
      {label:'ID',key:'id_pedido'},{label:'Estado',key:'estado'},{label:'Mesa',key:'mesas'},
      {label:'Total',render:r=>money(r.total)},{label:'Fecha',render:r=>label(r.fecha_creacion)}
    ],rows)}</div>`;
  }
  kitchen(rows) {
    const states=[['PENDIENTE','HU-06: Cola pendiente'],['EN_PREPARACION','HU-07: En preparación'],['LISTO','HU-08: Listos']];
    this.target.innerHTML=`<p class="small-note">Esta versión solo consulta los estados. Los cambios de estado (UPDATE) se agregarán después.</p>${states.map(([status,name])=>`<div class="panel"><h3 class="h6 mb-3">${name}</h3>${this.table([
      {label:'Pedido',key:'id_pedido'},{label:'Mesa',key:'mesas'},
      {label:'Productos',render:r=>label((r.productos||[]).map(x=>`${x.producto} (x${x.cantidad})`).join(', ')||'—')},
      {label:'Total',render:r=>money(r.total)}
    ],rows.filter(r=>r.estado===status))}</div>`).join('')}`;
  }
  reports(rows) {
    this.target.innerHTML=`<div class="panel">${this.header('HU-13: Ventas / HU-14: Tiempos.',this.button('new-report','Insertar reporte'))}${this.table([
      {label:'ID',key:'id_reporte'},{label:'Nombre',key:'nombre'},{label:'Tipo',key:'tipo'},
      {label:'Desde',key:'fecha_inicio'},{label:'Hasta',key:'fecha_fin'}
    ],rows)}</div>`;
  }
  history(rows) {
    this.target.innerHTML=`<div class="panel">${this.header('HU-15: Consulta e inserción de registros de historial.',this.button('new-history','Insertar historial'))}${this.table([
      {label:'ID',key:'id_historial'},{label:'Pedido',key:'id_pedido'},
      {label:'Estado',key:'estado'},{label:'Fecha',key:'fecha'},{label:'Usuario',key:'usuario'}
    ],rows)}</div>`;
  }
  form(title, fields, onSubmit) {
    document.getElementById('modalTitle').textContent=title;
    document.getElementById('modalFields').innerHTML=fields.map(f=>`<div class="mb-3"><label class="form-label" for="f_${f.name}">${safe(f.label)}</label>${f.options
      ?`<select class="form-select" id="f_${f.name}" name="${f.name}" ${f.required?'required':''}>${f.options.map(o=>`<option value="${safe(o.value)}">${safe(o.label)}</option>`).join('')}</select>`
      :`<input class="form-control" id="f_${f.name}" name="${f.name}" type="${f.type||'text'}" value="${safe(f.value??'')}" ${f.min?`min="${f.min}"`:''} ${f.required?'required':''}>`}</div>`).join('');
    const form=document.getElementById('editorForm');
    form.onsubmit=async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(form).entries());const save=document.getElementById('saveButton');save.disabled=true;
      try { await onSubmit(data); this.modal.hide(); } catch(err) { this.notice(err.message,true); } finally { save.disabled=false; }
    };
    this.modal.show();
  }
}
