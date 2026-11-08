// Punto de arranque. Ensambla MVC con inyección de dependencias, como en clase.
import { ApiModel } from "./models/ApiModel.js";
import { PedidoModel } from "./models/PedidoModel.js";
import { PedidoView } from "./views/PedidoView.js";
import { PedidoController } from "./controllers/PedidoController.js";
import { GestionModel } from "./models/GestionModel.js";
import { GestionView } from "./views/GestionView.js";
import { GestionController } from "./controllers/GestionController.js";
const api = new ApiModel();
const modelo = new PedidoModel(api);
const vista = new PedidoView();
const controlador = new PedidoController(api, modelo, vista);
controlador.gestion = new GestionController(api, new GestionModel(api), new GestionView(), controlador);
controlador.iniciar();
