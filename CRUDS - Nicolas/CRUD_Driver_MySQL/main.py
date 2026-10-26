import json
from db import DB
from nucleo import *

def mostrar(x): print(json.dumps(limpiar(x),ensure_ascii=False,indent=2))
def run():
 print('POLIRESTAURANTE | CRUD '+__import__('os').path.basename(__import__('os').getcwd()))
 while True:
  print('\n1 Cola HU06 | 2 Preparación HU07 | 3 Listos HU08 | 4 Cambiar estado | 5 Crear pedido demo | 6 Borrar pedido | 7 Historial listar | 8 Historial crear | 9 Historial editar | 10 Historial borrar | 11 Reportes listar | 12 Reporte crear | 13 Reporte editar | 14 Reporte borrar | 15 Calcular reporte | 0 Salir')
  op=input('Opción: ').strip()
  if op=='0': break
  try:
   uid=int(input('ID usuario (cocina=4, admin=1): '))
   with DB() as db:
    if op in ('1','2','3'): mostrar(listar(db,{'1':'cola','2':'preparacion','3':'listos'}[op],uid))
    elif op=='4': mostrar(estado(db,int(input('Pedido: ')),uid,input('Nuevo estado: ').upper(),input('¿Corrección admin? s/n: ').lower()=='s'))
    elif op=='5': mostrar({'id_pedido':crear_pedido_demo(db,uid,int(input('Mesa: ')),int(input('Producto: ')),int(input('Cantidad: ')))})
    elif op=='6': eliminar_pedido(db,int(input('Pedido: ')),uid);print('Eliminado')
    elif op=='7': mostrar(listar(db,'historial',uid))
    elif op=='8': mostrar(crear_historial(db,uid,json.loads(input('JSON: '))))
    elif op=='9': mostrar(actualizar_historial(db,int(input('Historial ID: ')),uid,json.loads(input('JSON: '))))
    elif op=='10': eliminar_historial(db,int(input('Historial ID: ')),uid);print('Eliminado')
    elif op=='11': mostrar(listar(db,'reportes',uid))
    elif op=='12': mostrar(crear_reporte(db,uid,json.loads(input('JSON: '))))
    elif op=='13': mostrar(actualizar_reporte(db,int(input('Reporte ID: ')),uid,json.loads(input('JSON: '))))
    elif op=='14': eliminar_reporte(db,int(input('Reporte ID: ')),uid);print('Eliminado')
    elif op=='15': mostrar(calcular_reporte(db,int(input('Reporte ID: ')),uid))
    else: print('Opción inválida')
  except (Negocio,ValueError,KeyError,Exception) as e: print('ERROR:',str(e))
if __name__=='__main__':run()
