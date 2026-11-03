import {RestaurantModel} from './model.js';
import {RestaurantView} from './view.js';
import {RestaurantController} from './controller.js';
const controller=new RestaurantController(new RestaurantModel(),new RestaurantView());
controller.start();
