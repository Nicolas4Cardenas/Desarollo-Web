import {API_BASE} from './config.js';
export class RestaurantModel {
 constructor(){this.userId=localStorage.getItem('poli_user')||'1';}
 setUser(value){this.userId=value;localStorage.setItem('poli_user',value);}
 async call(route,{method='GET',body}={}){
  const response=await fetch(`${API_BASE}${route}`,{method,headers:{'X-Usuario-Id':this.userId,'Content-Type':'application/json'},...(body!==undefined?{body:JSON.stringify(body)}:{})});
  let result;try{result=await response.json();}catch{throw new Error('Respuesta inválida del servidor');}
  if(!response.ok||result.ok===false)throw new Error(typeof result.error==='string'?result.error:(result.error?.mensaje||`Error HTTP ${response.status}`));
  return result.datos??result;
 }
 listar(recurso){return this.call('/'+recurso);}
 obtener(recurso,id){return this.call('/'+recurso+'/'+id);}
 crear(recurso,payload){return this.call('/'+recurso,{method:'POST',body:payload});}

}
