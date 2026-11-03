// CONTROLADOR (MVC): recibe los clics y coordina Modelo + Vista.
export class RestaurantController {
  constructor(model,view) { this.model=model; this.view=view; this.page='pedidos'; }
  async start() {
    const user=document.getElementById('userId');user.value=this.model.userId;
    user.addEventListener('change',()=>{this.model.setUser(user.value);this.refresh();});
    document.querySelectorAll('[data-page]').forEach(button=>button.addEventListener('click',()=>{
      this.page=button.dataset.page;
      document.querySelectorAll('[data-page]').forEach(b=>b.classList.toggle('active',b===button));
      this.refresh();
    }));
    document.getElementById('content').addEventListener('click',event=>{
      const button=event.target.closest('[data-action]');
      if(button)this.action(button.dataset.action).catch(e=>this.view.notice(e.message,true));
    });
    await this.refresh();
  }
  async refresh() {
    this.view.setTitle(({pedidos:'Pedidos',cocina:'Cocina',reportes:'Reportes',historial:'Historial'})[this.page]);
    this.view.loading();
    const status=document.getElementById('apiStatus');
    try {
      await this.model.call('/salud');status.textContent='Conectado a Flask';status.className='small text-success mb-3';
      if(this.page==='pedidos') this.view.orders(await this.model.listar('pedidos'));
      if(this.page==='cocina') {
        const [pending,preparing,ready]=await Promise.all(['cola','preparacion','listos'].map(x=>this.model.listar(x)));
        this.view.kitchen([...pending,...preparing,...ready]);
      }
      if(this.page==='reportes') this.view.reports(await this.model.listar('reportes'));
      if(this.page==='historial') this.view.history(await this.model.listar('historial'));
    } catch(e) {
      status.textContent='No se pudieron cargar los datos';status.className='small text-danger mb-3';
      this.view.target.innerHTML='<div class="alert alert-warning" role="alert"></div>';
      this.view.target.querySelector('.alert').textContent=e.message+' — Revisa Flask, MySQL y los permisos de usuario.';
    }
  }
  async action(type) {
    const done=async message=>{this.view.notice(message);await this.refresh();};
    if(type==='new-order') {
      const catalog=await this.model.listar('catalogos');
      const mesas=catalog.mesas.filter(m=>String(m.estado).toLowerCase()==='libre');
      const productos=catalog.productos.filter(p=>p.disponibilidad);
      if(!mesas.length||!productos.length)throw new Error('Necesitas una mesa libre y un producto disponible.');
      this.view.form('Insertar pedido de prueba',[
        {name:'id_mesa',label:'Mesa libre',options:mesas.map(m=>({value:m.id_mesa,label:`Mesa ${m.numero}`})),required:true},
        {name:'id_producto',label:'Producto',options:productos.map(p=>({value:p.id_producto,label:`${p.nombre} - $${p.precio}`})),required:true},
        {name:'cantidad',label:'Cantidad',type:'number',min:1,value:1,required:true}
      ],async d=>{await this.model.crear('pedidos/demo',{id_mesa:Number(d.id_mesa),id_producto:Number(d.id_producto),cantidad:Number(d.cantidad)});await done('Pedido insertado');});
    }
    if(type==='new-report') {
      const today=new Date().toLocaleDateString('en-CA');
      this.view.form('Insertar reporte',[
        {name:'tipo',label:'Tipo',options:[{value:'VENTAS',label:'Ventas'},{value:'TIEMPOS',label:'Tiempos'}],required:true},
        {name:'nombre',label:'Nombre',required:true},
        {name:'fecha_inicio',label:'Fecha de inicio',type:'date',value:today,required:true},
        {name:'fecha_fin',label:'Fecha final',type:'date',value:today,required:true}
      ],async d=>{if(d.fecha_inicio>d.fecha_fin)throw new Error('La fecha inicial supera la final.');await this.model.crear('reportes',d);await done('Reporte insertado');});
    }
    if(type==='new-history') {
      this.view.form('Insertar registro de historial',[
        {name:'id_pedido',label:'ID del pedido',type:'number',min:1,required:true},
        {name:'estado',label:'Estado',options:['PENDIENTE','EN_PREPARACION','LISTO','ENTREGADO','CANCELADO'].map(x=>({value:x,label:x})),required:true}
      ],async d=>{await this.model.crear('historial',{id_pedido:Number(d.id_pedido),estado:d.estado});await done('Historial insertado');});
    }
  }
}
