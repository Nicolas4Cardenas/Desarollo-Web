## 🛠️ Herramientas

![UML](https://img.shields.io/badge/UML-Modelado-blue)
![PlantUML](https://img.shields.io/badge/PlantUML-Diagramas-orange)
![MySQL](https://img.shields.io/badge/MySQL-8.0-blue)
![Git](https://img.shields.io/badge/Git-Control%20de%20versiones-red)
![GitHub](https://img.shields.io/badge/GitHub-Repositorio-black)
![Web](https://img.shields.io/badge/Web-Development-green)

# 🍽️ Sistema de Gestión de Pedidos

### 🎓 Proyecto de Desarrollo Web — Universidad Politécnico Grancolombiano

> 💡 Sistema web diseñado para facilitar la gestión de pedidos de un restaurante de forma organizada, sencilla y eficiente.

---

## 🚀 ¿Qué hace?

El sistema permite administrar los principales elementos de un restaurante:

- 👤 **Usuarios y roles**
- 🪑 **Mesas**
- 📋 **Pedidos**
- 🍔 **Productos y categorías**
- 🔄 **Estados e historial de pedidos**

Una de las características principales es que **un pedido puede estar asociado a varias mesas**, permitiendo manejar pedidos compartidos entre diferentes mesas.

También se registra el **historial de estados** de cada pedido para conocer su evolución y el usuario responsable de cada cambio.

---

## 🏗️ Estructura del sistema

```text
Usuario
   │
   ▼
Pedido ──────────► Historial_Estado
   │
   ├──► Pedido_Mesa ───► Mesa
   │
   └──► Detalle_Pedido ───► Producto ───► Categoría
```

### 🔗 Relaciones principales

- 👤 **Rol → Usuario:** un rol puede estar asignado a varios usuarios.
- 📋 **Usuario → Pedido:** un usuario puede gestionar varios pedidos.
- 🪑 **Pedido → Mesa:** un pedido puede estar asociado a una o varias mesas.
- 📝 **Pedido → Detalle:** un pedido puede contener diferentes detalles.
- 🍔 **Detalle → Producto:** cada detalle corresponde a un producto.
- 🗂️ **Categoría → Producto:** una categoría puede contener varios productos.
- 🔄 **Pedido → Historial:** un pedido puede tener varios registros de estado.

---

## 🪑 Pedido y mesas

Una característica importante del sistema es permitir que un mismo pedido pueda involucrar diferentes mesas.

```text
📋 PEDIDO #001
     │
     ├── 🪑 Mesa 4
     ├── 🪑 Mesa 5
     └── 🪑 Mesa 6
```

Para esto se utiliza la entidad intermedia `pedido_mesa`.

Esto permite una mayor flexibilidad en la gestión de pedidos y evita limitar cada pedido a una única mesa.

---

## 🔄 Historial de pedidos

Cada pedido puede pasar por diferentes estados durante su proceso:

```text
🟡 Pendiente
      ↓
🔵 En preparación
      ↓
🟢 Listo
      ↓
✅ Entregado
```

El sistema registra el estado, la fecha y el usuario responsable del cambio, permitiendo mantener la **trazabilidad del pedido**.

---

## 🍔 Productos

Los productos se organizan mediante categorías y contienen información como:

- 🏷️ Nombre
- 📝 Descripción
- 💰 Precio
- 📦 Disponibilidad
- 🗂️ Categoría

Esto permite mantener un catálogo organizado y facilitar su utilización dentro de los pedidos.

---

## 👤 Usuarios y roles

El sistema contempla tres roles para controlar las responsabilidades de los usuarios:

```text
🔐 Rol
   │
   ├──► 👨‍💼 ADMINISTRADOR  — gestiona menú, usuarios y reportes
   ├──► 🧑‍🍳 COCINA         — ve la cola de pedidos y cambia su estado
   └──► 🧑‍🤝‍🧑 MESERO         — crea y gestiona pedidos en sala
```

El control de acceso se valida **en la base de datos**, no solo en el frontend (RNF-06), garantizando que cada rol solo pueda ejecutar las operaciones que le corresponden.

---

## 🗄️ Backend — Base de datos

El backend está implementado íntegramente en **MySQL 8** mediante procedimientos almacenados, triggers y funciones. No requiere ningún servidor de aplicaciones adicional para su funcionamiento.

### 📂 Archivos

El archivo `BackendPolirestaurante.rar` contiene:

| Archivo | Descripción |
|---|---|
| `backend.sql` | Esquema completo: tablas, triggers, funciones y stored procedures |
| `Prueba.sql` | Script de pruebas: flujo feliz (8 escenarios) y casos de error (13 escenarios) |

### ▶️ Cómo ejecutar

1. Tener instalado **MySQL 8** y **MySQL Workbench**
2. Abrir `backend.sql` en Workbench y ejecutar con `Ctrl + Shift + Enter`
3. Abrir `Prueba.sql` y ejecutar de la misma forma
4. El script de pruebas debe completarse con **1 solo error** (caso E1, intencional)

### 🧩 Módulos implementados

| Módulo | Procedimientos |
|---|---|
| 🧑‍🤝‍🧑 Mesero | Crear pedido, agregar/modificar/quitar productos, marcar entregado, cancelar |
| 🧑‍🍳 Cocina | Ver cola, iniciar preparación, marcar listo |
| 👨‍💼 Administración | Gestionar menú, usuarios, categorías, reportes de ventas y tiempos |
| 🔐 Autenticación | Login con validación de hash bcrypt |

### 🔒 Seguridad implementada

- Contraseñas almacenadas como **hash bcrypt** (nunca texto plano)
- Control de acceso por rol validado en cada procedimiento
- Historial de estados **inmutable** (protegido por triggers)
- Transacciones en todas las operaciones críticas

---

## 📐 Diagramas

### 📊 Diagrama de Relación

![Diagrama de Relacion](DiagramaClases_Corregido.png)

### 🏗️ Diagrama de Arquitectura

![Diagrama de Arquitectura](Diagrama%20Arquitectura.png)

### ⚙️ Diagrama de Componentes

![Diagrama de Componentes](Diagrama%20De%20Componentes.jpg)

### 📦 Diagrama de Despliegue

![Diagrama de Despliegue](diagrama%20de%20despliegue.png)

---

## 📊 Entidades principales

| Entidad | Descripción |
|---|---|
| 👤 `usuario` | Usuarios que interactúan con el sistema |
| 🔐 `rol` | Roles de los usuarios |
| 🪑 `mesa` | Mesas disponibles |
| 📋 `pedido` | Información general de los pedidos |
| 🔗 `pedido_mesa` | Relación entre pedidos y mesas |
| 📝 `detalle_pedido` | Productos incluidos en cada pedido |
| 🍔 `producto` | Productos disponibles |
| 🗂️ `categoria` | Clasificación de productos |
| 🔄 `historial_estado` | Historial de cambios de los pedidos |

---

## 📈 Estado del proyecto

🚧 **En desarrollo**

### 📐 Análisis y diseño

- ✅ Levantamiento de requisitos
- ✅ Historias de usuario
- ✅ Modelo de datos
- ✅ Corrección de relaciones
- ✅ Diagrama de clases
- ✅ Diagrama de arquitectura

### 💻 Desarrollo

- ⬜ Frontend
- ✅ Backend (MySQL 8 — stored procedures, triggers, control de roles)
- ✅ Base de datos
- ✅ Autenticación
- ✅ Gestión de usuarios y roles
- ✅ Gestión de mesas
- ✅ Gestión de pedidos
- ✅ Gestión de productos
- ✅ Historial de estados

### 🧪 Pruebas

- ✅ Pruebas funcionales (flujo feliz — 8 escenarios)
- ✅ Pruebas de control de acceso y errores (13 escenarios)
- ⬜ Pruebas de integración
- ⬜ Corrección de errores
- ⬜ 🚀 Despliegue

---

## 👥 Integrantes

- **Juan Miguel Parra Garzón**
- **Nicolas Abril Cárdenas**
- **Santiago Cortes Mojica**

## 🎓 Proyecto académico

**Universidad:** Politécnico Grancolombiano  
**Asignatura:** Desarrollo Web

