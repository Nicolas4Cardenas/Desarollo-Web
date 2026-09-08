# 🍽️ Sistema de Gestión de Pedidos

### Proyecto de Desarrollo Web — Universidad Politécnico Grancolombiano

> Sistema web orientado a la gestión y seguimiento de pedidos en un entorno de restaurante.

---

## 📌 Descripción

Este proyecto consiste en el diseño y desarrollo de un sistema web para gestionar de manera organizada el proceso de pedidos de un restaurante.

La solución permite centralizar la información relacionada con **usuarios, roles, mesas, pedidos, productos y estados**, facilitando el control del proceso desde la creación del pedido hasta su entrega.

---

## 🎯 Objetivos

- 👤 Gestionar usuarios y roles.
- 🔐 Controlar el acceso al sistema.
- 🪑 Administrar las mesas.
- 📋 Crear y gestionar pedidos.
- 🔗 Asociar varias mesas a un mismo pedido.
- 🍔 Administrar productos y categorías.
- 📝 Registrar el detalle de cada pedido.
- 🔄 Mantener un historial de cambios de estado.
- 📊 Mantener la información organizada mediante un modelo de datos estructurado.

---

## 🚀 Funcionalidades principales

| Módulo | Descripción |
|---|---|
| 👤 Usuarios | Gestión de usuarios del sistema |
| 🔐 Roles | Control de los diferentes perfiles |
| 🪑 Mesas | Administración y estado de las mesas |
| 📋 Pedidos | Creación y seguimiento de pedidos |
| 🔗 Pedido-Mesa | Permite asociar varias mesas a un pedido |
| 🍔 Productos | Gestión de productos disponibles |
| 🗂️ Categorías | Clasificación de productos |
| 📝 Detalles | Productos y cantidades de cada pedido |
| 🔄 Historial | Registro de cambios de estado |

---

## 🏗️ Modelo de datos

El sistema se estructura mediante las siguientes relaciones principales:

```text
ROL 1 ───── N USUARIO
              │
              │ 1:N
              ▼
           PEDIDO
          /   │    \
         /    │     \
        ▼     ▼      ▼
 PEDIDO_MESA  DETALLE  HISTORIAL_ESTADO
      │          │           │
      ▼          ▼           ▼
     MESA     PRODUCTO     USUARIO
                  │
                  ▼
              CATEGORIA
