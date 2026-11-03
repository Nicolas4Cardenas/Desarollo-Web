from flask import Flask,request,jsonify
from flask_cors import CORS
from functools import wraps
from db import DB
from nucleo import *
from manager import PedidoManager  # AQUI se conecta Flask con el Manager
app=Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}}, allow_headers=["Content-Type","X-Usuario-Id"])

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

@app.get('/api/catalogos')
@accion
def catalogos(db,u):
 validar_rol(db,u,('COCINA','ADMINISTRADOR'))
 return {'mesas':db.all('SELECT id_mesa,numero,estado FROM mesa ORDER BY numero'),
         'productos':db.all('SELECT id_producto,nombre,precio,disponibilidad FROM producto ORDER BY nombre'),
         'usuarios':db.all("SELECT u.id_usuario,u.nombre,r.nombre AS rol FROM usuario u JOIN rol r ON r.id_rol=u.id_rol WHERE u.activo=1 ORDER BY u.id_usuario")}

@app.get('/api/pedidos')
@accion
def todos_pedidos(db,u):
 validar_rol(db,u,('COCINA','ADMINISTRADOR'))
 return db.all("SELECT p.*,fn_total_pedido(p.id_pedido) AS total,(SELECT GROUP_CONCAT(m.numero ORDER BY m.numero) FROM pedido_mesa pm JOIN mesa m ON m.id_mesa=pm.id_mesa WHERE pm.id_pedido=p.id_pedido) AS mesas FROM pedido p ORDER BY p.id_pedido DESC LIMIT 250")

@app.get('/api/<recurso>')
@accion
def ver_lista(db,u,recurso):
 if recurso not in ('cola','preparacion','listos','historial','reportes'): raise Negocio('Ruta no encontrada',404)
 if recurso=='cola':
  validar_rol(db,u,('COCINA','ADMINISTRADOR'))
  # AQUI Flask llama al MANAGER: este usa los dos DAO de la HU-06.
  return PedidoManager().consultar_cola(db)
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

@app.post('/api/historial')
@accion
def nuevo_historial(db,u): return crear_historial(db,u,request.get_json(silent=True) or {})

@app.post('/api/reportes')
@accion
def nuevo_reporte(db,u): return crear_reporte(db,u,request.get_json(silent=True) or {})


if __name__=='__main__': app.run(port=5001,debug=False)
