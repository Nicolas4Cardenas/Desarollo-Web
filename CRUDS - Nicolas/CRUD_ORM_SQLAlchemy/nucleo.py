from datetime import date,datetime
from decimal import Decimal
import json

ESTADOS=('PENDIENTE','EN_PREPARACION','LISTO','ENTREGADO','CANCELADO')
TRANSICIONES={'PENDIENTE':{'EN_PREPARACION','CANCELADO'},'EN_PREPARACION':{'LISTO','CANCELADO'},'LISTO':{'ENTREGADO'},'ENTREGADO':set(),'CANCELADO':set()}
class Negocio(Exception):
 def __init__(self,mensaje,status=400): super().__init__(mensaje); self.status=status

def serializar(v):
 if isinstance(v,(date,datetime)): return v.isoformat(sep=' ') if isinstance(v,datetime) else v.isoformat()
 if isinstance(v,Decimal): return float(v)
 raise TypeError(str(type(v)))

def limpiar(v): return json.loads(json.dumps(v,default=serializar,ensure_ascii=False))

def validar_rol(db,uid,roles):
 u=db.one('SELECT r.nombre AS rol FROM usuario u JOIN rol r ON r.id_rol=u.id_rol WHERE u.id_usuario=%s AND u.activo=1',(uid,))
 if not u or u['rol'] not in roles: raise Negocio('ACCESO_DENEGADO: usuario inactivo o rol no autorizado',403)
 return u['rol']

def existente(db,tabla,campo,id):
 r=db.one(f'SELECT * FROM {tabla} WHERE {campo}=%s',(id,))
 if not r: raise Negocio('Registro no encontrado',404)
 return r

def auditar(db,entidad,id,accion,antes,despues,uid):
 db.execute('INSERT INTO nicolas_auditoria(entidad,registro_id,accion,antes_json,despues_json,actor_id) VALUES (%s,%s,%s,%s,%s,%s)',(entidad,id,accion,json.dumps(limpiar(antes)) if antes is not None else None,json.dumps(limpiar(despues)) if despues is not None else None,uid))

def listar(db,recurso,uid,estado=None):
 validar_rol(db,uid,('COCINA','ADMINISTRADOR') if recurso in ('cola','preparacion','listos') else ('ADMINISTRADOR',))
 if recurso in ('cola','preparacion','listos'):
  e={'cola':'PENDIENTE','preparacion':'EN_PREPARACION','listos':'LISTO'}[recurso]
  return db.all('SELECT p.*, (SELECT GROUP_CONCAT(m.numero ORDER BY m.numero) FROM pedido_mesa pm JOIN mesa m ON m.id_mesa=pm.id_mesa WHERE pm.id_pedido=p.id_pedido) AS mesas, fn_total_pedido(p.id_pedido) AS total FROM pedido p WHERE p.estado=%s AND EXISTS (SELECT 1 FROM detalle_pedido d WHERE d.id_pedido=p.id_pedido) ORDER BY p.fecha_creacion,p.id_pedido',(e,))
 if recurso=='historial':
  return db.all('SELECT h.*,u.nombre AS usuario FROM historial_estado h JOIN usuario u ON u.id_usuario=h.id_usuario_cambio WHERE (%s IS NULL OR h.estado=%s) ORDER BY h.fecha DESC,h.id_historial DESC',(estado,estado))
 if recurso=='reportes': return db.all('SELECT * FROM nicolas_reporte_guardado ORDER BY id_reporte DESC')
 raise Negocio('Recurso desconocido',404)

def obtener(db,recurso,id,uid):
 validar_rol(db,uid,('COCINA','ADMINISTRADOR') if recurso=='pedidos' else ('ADMINISTRADOR',))
 tabla,pk={'pedidos':('pedido','id_pedido'),'historial':('historial_estado','id_historial'),'reportes':('nicolas_reporte_guardado','id_reporte')}[recurso]
 return existente(db,tabla,pk,id)

def estado(db,id,uid,nuevo,correccion=False):
 rol=validar_rol(db,uid,('COCINA','ADMINISTRADOR'))
 p=existente(db,'pedido','id_pedido',id)
 if nuevo not in ESTADOS: raise Negocio('Estado inválido')
 if nuevo==p['estado']: raise Negocio('El pedido ya tiene ese estado')
 if not correccion:
  if nuevo not in TRANSICIONES[p['estado']]: raise Negocio('Transición de estado inválida')
  if rol=='COCINA' and nuevo not in ('EN_PREPARACION','LISTO'): raise Negocio('Cocina solo puede iniciar o finalizar preparación',403)
  if nuevo=='EN_PREPARACION' and not db.one('SELECT id_detalle FROM detalle_pedido WHERE id_pedido=%s LIMIT 1',(id,)): raise Negocio('Pedido sin productos')
 else:
  if rol!='ADMINISTRADOR': raise Negocio('Solo administrador puede corregir estados',403)
  if nuevo in ('ENTREGADO','CANCELADO') and p['estado'] not in ('ENTREGADO','CANCELADO'): raise Negocio('Use flujo normal para cerrar pedidos')
 db.execute('UPDATE pedido SET estado=%s,fecha_ultima_actualizacion=NOW() WHERE id_pedido=%s',(nuevo,id))
 db.execute('INSERT INTO historial_estado(id_pedido,estado,fecha,id_usuario_cambio) VALUES (%s,%s,NOW(),%s)',(id,nuevo,uid))
 if nuevo in ('ENTREGADO','CANCELADO'): db.execute("UPDATE mesa m JOIN pedido_mesa pm ON pm.id_mesa=m.id_mesa SET m.estado='libre' WHERE pm.id_pedido=%s AND NOT EXISTS (SELECT 1 FROM pedido_mesa pm2 JOIN pedido p2 ON p2.id_pedido=pm2.id_pedido WHERE pm2.id_mesa=m.id_mesa AND pm2.id_pedido<>%s AND p2.estado IN ('PENDIENTE','EN_PREPARACION','LISTO'))",(id,id))
 if correccion and nuevo in ('PENDIENTE','EN_PREPARACION','LISTO'): db.execute("UPDATE mesa m JOIN pedido_mesa pm ON pm.id_mesa=m.id_mesa SET m.estado='ocupada' WHERE pm.id_pedido=%s",(id,))
 auditar(db,'pedido',id,'CORRECCION' if correccion else 'ESTADO',p,{'estado':nuevo},uid)
 return obtener(db,'pedidos',id,uid)

def crear_pedido_demo(db,uid,mesa,producto,cantidad=1):
 validar_rol(db,uid,('ADMINISTRADOR',))
 m=existente(db,'mesa','id_mesa',mesa)
 if m['estado']!='libre': raise Negocio('Mesa ocupada')
 pr=existente(db,'producto','id_producto',producto)
 if not pr['disponibilidad'] or int(cantidad)<=0: raise Negocio('Producto no disponible o cantidad inválida')
 mesero=db.one("SELECT u.id_usuario FROM usuario u JOIN rol r ON r.id_rol=u.id_rol WHERE r.nombre='MESERO' AND u.activo=1 ORDER BY u.id_usuario LIMIT 1")
 if not mesero: raise Negocio('Se necesita un mesero activo')
 id=db.execute("INSERT INTO pedido(id_usuario_mesero,estado) VALUES (%s,'PENDIENTE')",(mesero['id_usuario'],))
 db.execute('INSERT INTO pedido_mesa(id_pedido,id_mesa) VALUES (%s,%s)',(id,mesa))
 db.execute("UPDATE mesa SET estado='ocupada' WHERE id_mesa=%s",(mesa,))
 db.execute('INSERT INTO detalle_pedido(id_pedido,id_producto,cantidad,precio_unitario) VALUES (%s,%s,%s,%s)',(id,producto,int(cantidad),pr['precio']))
 db.execute("INSERT INTO historial_estado(id_pedido,estado,id_usuario_cambio) VALUES (%s,'PENDIENTE',%s)",(id,uid))
 auditar(db,'pedido',id,'CREAR',None,{'id_mesa':mesa,'id_producto':producto},uid)
 return id

def eliminar_pedido(db,id,uid):
 validar_rol(db,uid,('ADMINISTRADOR',))
 p=existente(db,'pedido','id_pedido',id)
 if p['estado'] not in ('PENDIENTE','CANCELADO'): raise Negocio('Solo se pueden borrar pedidos pendientes o cancelados')
 if p['estado']=='PENDIENTE':
  db.execute("UPDATE pedido SET estado='CANCELADO' WHERE id_pedido=%s",(id,))
  db.execute("UPDATE mesa m JOIN pedido_mesa pm ON pm.id_mesa=m.id_mesa SET m.estado='libre' WHERE pm.id_pedido=%s AND NOT EXISTS (SELECT 1 FROM pedido_mesa pm2 JOIN pedido p2 ON p2.id_pedido=pm2.id_pedido WHERE pm2.id_mesa=m.id_mesa AND pm2.id_pedido<>%s AND p2.estado IN ('PENDIENTE','EN_PREPARACION','LISTO'))",(id,id))
 db.execute('DELETE FROM historial_estado WHERE id_pedido=%s',(id,))
 db.execute('DELETE FROM detalle_pedido WHERE id_pedido=%s',(id,))
 db.execute('DELETE FROM pedido_mesa WHERE id_pedido=%s',(id,))
 db.execute('DELETE FROM pedido WHERE id_pedido=%s',(id,))
 auditar(db,'pedido',id,'ELIMINAR',p,None,uid)

def crear_historial(db,uid,datos):
 validar_rol(db,uid,('ADMINISTRADOR',))
 pid=int(datos['id_pedido']); existente(db,'pedido','id_pedido',pid)
 e=datos['estado']
 if e not in ESTADOS: raise Negocio('Estado inválido')
 actor=int(datos.get('id_usuario_cambio',uid)); existente(db,'usuario','id_usuario',actor)
 id=db.execute('INSERT INTO historial_estado(id_pedido,estado,fecha,id_usuario_cambio) VALUES (%s,%s,%s,%s)',(pid,e,datos.get('fecha') or datetime.now(),actor))
 nuevo=existente(db,'historial_estado','id_historial',id)
 auditar(db,'historial',id,'CREAR',None,nuevo,uid)
 return nuevo

def actualizar_historial(db,id,uid,datos):
 validar_rol(db,uid,('ADMINISTRADOR',))
 antes=existente(db,'historial_estado','id_historial',id)
 campos={k:datos[k] for k in ('estado','fecha','id_usuario_cambio') if k in datos}
 if not campos: raise Negocio('Sin campos para actualizar')
 if 'estado' in campos and campos['estado'] not in ESTADOS: raise Negocio('Estado inválido')
 if 'id_usuario_cambio' in campos: existente(db,'usuario','id_usuario',int(campos['id_usuario_cambio']))
 db.execute('UPDATE historial_estado SET '+','.join(k+'=%s' for k in campos)+' WHERE id_historial=%s',tuple(campos.values())+(id,))
 nuevo=existente(db,'historial_estado','id_historial',id)
 auditar(db,'historial',id,'EDITAR',antes,nuevo,uid)
 return nuevo

def eliminar_historial(db,id,uid):
 validar_rol(db,uid,('ADMINISTRADOR',))
 antes=existente(db,'historial_estado','id_historial',id)
 db.execute('DELETE FROM historial_estado WHERE id_historial=%s',(id,))
 auditar(db,'historial',id,'ELIMINAR',antes,None,uid)

def crear_reporte(db,uid,d):
 validar_rol(db,uid,('ADMINISTRADOR',))
 tipo=d['tipo'].upper()
 if tipo not in ('VENTAS','TIEMPOS'): raise Negocio('Tipo debe ser VENTAS o TIEMPOS')
 if str(d['fecha_inicio'])>str(d['fecha_fin']): raise Negocio('Rango de fechas inválido')
 id=db.execute('INSERT INTO nicolas_reporte_guardado(tipo,nombre,fecha_inicio,fecha_fin,filtro_categoria,filtro_producto,creado_por) VALUES (%s,%s,%s,%s,%s,%s,%s)',(tipo,d['nombre'],d['fecha_inicio'],d['fecha_fin'],d.get('filtro_categoria'),d.get('filtro_producto'),uid))
 nuevo=existente(db,'nicolas_reporte_guardado','id_reporte',id)
 auditar(db,'reporte',id,'CREAR',None,nuevo,uid)
 return nuevo

def actualizar_reporte(db,id,uid,d):
 validar_rol(db,uid,('ADMINISTRADOR',))
 antes=existente(db,'nicolas_reporte_guardado','id_reporte',id)
 campos={k:d[k] for k in ('nombre','fecha_inicio','fecha_fin','filtro_categoria','filtro_producto','tipo') if k in d}
 if not campos: raise Negocio('Sin campos para actualizar')
 merged={**antes,**campos}
 if str(merged['fecha_inicio'])>str(merged['fecha_fin']): raise Negocio('Rango inválido')
 if merged['tipo'] not in ('VENTAS','TIEMPOS'): raise Negocio('Tipo inválido')
 db.execute('UPDATE nicolas_reporte_guardado SET '+','.join(k+'=%s' for k in campos)+' WHERE id_reporte=%s',tuple(campos.values())+(id,))
 nuevo=existente(db,'nicolas_reporte_guardado','id_reporte',id)
 auditar(db,'reporte',id,'EDITAR',antes,nuevo,uid)
 return nuevo

def eliminar_reporte(db,id,uid):
 validar_rol(db,uid,('ADMINISTRADOR',))
 antes=existente(db,'nicolas_reporte_guardado','id_reporte',id)
 db.execute('DELETE FROM nicolas_reporte_guardado WHERE id_reporte=%s',(id,))
 auditar(db,'reporte',id,'ELIMINAR',antes,None,uid)

def calcular_reporte(db,id,uid):
 validar_rol(db,uid,('ADMINISTRADOR',))
 r=existente(db,'nicolas_reporte_guardado','id_reporte',id)
 if r['tipo']=='VENTAS':
  rows=db.all('''SELECT p.id_pedido,pr.nombre AS producto,c.nombre AS categoria,d.cantidad,d.precio_unitario,d.cantidad*d.precio_unitario AS subtotal FROM pedido p JOIN detalle_pedido d ON d.id_pedido=p.id_pedido JOIN producto pr ON pr.id_producto=d.id_producto JOIN categoria c ON c.id_categoria=pr.id_categoria WHERE p.estado='ENTREGADO' AND EXISTS (SELECT 1 FROM historial_estado h WHERE h.id_pedido=p.id_pedido AND h.estado='ENTREGADO' AND h.fecha >= %s AND h.fecha < DATE_ADD(%s,INTERVAL 1 DAY)) AND (%s IS NULL OR c.id_categoria=%s) AND (%s IS NULL OR pr.id_producto=%s) ORDER BY p.id_pedido''',(r['fecha_inicio'],r['fecha_fin'],r['filtro_categoria'],r['filtro_categoria'],r['filtro_producto'],r['filtro_producto']))
  return {'reporte':r,'detalle':rows,'total_ventas':round(sum(float(x['subtotal']) for x in rows),2),'pedidos_entregados':len(set(x['id_pedido'] for x in rows)),'unidades':sum(x['cantidad'] for x in rows)}
 rows=db.all('''SELECT p.id_pedido,MIN(CASE WHEN h.estado='PENDIENTE' THEN h.fecha END) AS creado,MIN(CASE WHEN h.estado='EN_PREPARACION' THEN h.fecha END) AS preparacion,MIN(CASE WHEN h.estado='LISTO' THEN h.fecha END) AS listo,TIMESTAMPDIFF(SECOND,MIN(CASE WHEN h.estado='EN_PREPARACION' THEN h.fecha END),MIN(CASE WHEN h.estado='LISTO' THEN h.fecha END))/60 AS minutos_preparacion FROM pedido p JOIN historial_estado h ON h.id_pedido=p.id_pedido WHERE p.estado<>'CANCELADO' AND p.fecha_creacion >= %s AND p.fecha_creacion < DATE_ADD(%s,INTERVAL 1 DAY) GROUP BY p.id_pedido ORDER BY p.id_pedido''',(r['fecha_inicio'],r['fecha_fin']))
 tiempos=[float(x['minutos_preparacion']) for x in rows if x['minutos_preparacion'] is not None]
 return {'reporte':r,'detalle':rows,'pedidos_preparados':len(tiempos),'promedio_minutos':round(sum(tiempos)/len(tiempos),2) if tiempos else None}
