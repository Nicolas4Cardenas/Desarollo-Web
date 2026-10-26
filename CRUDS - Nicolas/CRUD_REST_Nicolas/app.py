from flask import Flask,request,jsonify
from functools import wraps
from db import DB
from nucleo import *
app=Flask(__name__)

def respuesta(obj,status=200): return app.response_class(json.dumps(limpiar(obj),ensure_ascii=False),status=status,mimetype='application/json')

def ejecutar(func,*args,**kwargs):
 try:
  with DB() as db: result=func(db,*args,**kwargs)
  return respuesta({'ok':True,'datos':result},201 if request.method=='POST' else 200)
 except Negocio as e: return respuesta({'ok':False,'error':str(e)},e.status)
 except (KeyError,ValueError,TypeError) as e: return respuesta({'ok':False,'error':'Datos inválidos: '+str(e)},400)
 except Exception as e:
  app.logger.exception('Error interno')
  return respuesta({'ok':False,'error':'Error interno de servidor; compruebe MySQL y la extensión SQL'},500)

def uid():
 v=request.headers.get('X-Usuario-Id','')
 if not v.isdigit() or int(v)<1: raise Negocio('Falta X-Usuario-Id (entero positivo)',401)
 return int(v)

def accion(f):
 @wraps(f)
 def wrapper(*args,**kwargs): return ejecutar(lambda db:f(db,uid(),*args,**kwargs))
 return wrapper

@app.get('/api/salud')
def salud(): return respuesta({'ok':True,'servicio':'Nicolas REST'})

@app.get('/api/<recurso>')
@accion
def ver_lista(db,u,recurso):
 if recurso not in ('cola','preparacion','listos','historial','reportes'): raise Negocio('Ruta no encontrada',404)
 return listar(db,recurso,u,request.args.get('estado'))

@app.get('/api/<recurso>/<int:id>')
@accion
def ver_uno(db,u,recurso,id):
 if recurso not in ('pedidos','historial','reportes'): raise Negocio('Ruta no encontrada',404)
 return obtener(db,recurso,id,u)

@app.post('/api/pedidos/demo')
@accion
def pedido_demo(db,u):
 d=request.get_json(silent=True) or {}
 return {'id_pedido':crear_pedido_demo(db,u,int(d['id_mesa']),int(d['id_producto']),int(d.get('cantidad',1)))}

@app.put('/api/pedidos/<int:id>/estado')
@app.patch('/api/pedidos/<int:id>/estado')
@accion
def cambio(db,u,id):
 d=request.get_json(silent=True) or {}
 return estado(db,id,u,d['estado'],bool(d.get('correccion',False)))

@app.delete('/api/pedidos/<int:id>')
@accion
def borrar_pedido(db,u,id): eliminar_pedido(db,id,u);return {'eliminado':id}

@app.post('/api/historial')
@accion
def nuevo_historial(db,u): return crear_historial(db,u,request.get_json(silent=True) or {})

@app.put('/api/historial/<int:id>')
@app.patch('/api/historial/<int:id>')
@accion
def editar_historial(db,u,id): return actualizar_historial(db,id,u,request.get_json(silent=True) or {})

@app.delete('/api/historial/<int:id>')
@accion
def borrar_historial(db,u,id): eliminar_historial(db,id,u);return {'eliminado':id}

@app.post('/api/reportes')
@accion
def nuevo_reporte(db,u): return crear_reporte(db,u,request.get_json(silent=True) or {})

@app.put('/api/reportes/<int:id>')
@app.patch('/api/reportes/<int:id>')
@accion
def editar_reporte(db,u,id): return actualizar_reporte(db,id,u,request.get_json(silent=True) or {})

@app.delete('/api/reportes/<int:id>')
@accion
def borrar_reporte(db,u,id): eliminar_reporte(db,id,u);return {'eliminado':id}

@app.get('/api/reportes/<int:id>/calcular')
@accion
def calcular(db,u,id): return calcular_reporte(db,id,u)

@app.get('/api/auditoria')
@accion
def auditoria(db,u):
 validar_rol(db,u,('ADMINISTRADOR',))
 return db.all('SELECT * FROM nicolas_auditoria ORDER BY id_auditoria DESC LIMIT 200')

if __name__=='__main__': app.run(port=5001,debug=False)
