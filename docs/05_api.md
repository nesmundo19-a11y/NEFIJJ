# API
# 05. Especificación de la API REST - NEFIJJ

## 1. Introducción
La API REST del sistema **NEFIJJ** está construida sobre **Django 5.x** y **Django REST Framework (DRF)**. Utiliza el formato **JSON** para el intercambio de datos y autenticación basada en tokens JWT.

## 2. Convenciones de Enrutamiento
* **URL Base (Local):** `http://localhost:8000/api/v1/`
* **Formato de Respuesta:** `application/json`
* **Cabecera de Autenticación:** `Authorization: Bearer <token_jwt>`

## 3. Endpoints Principales

### A. Módulo de Autenticación (`/auth`)
* **POST `/api/v1/auth/login/`**
  * **Descripción:** Permite a los usuarios iniciar sesión.
  * **Cuerpo de la petición (JSON):**
    ```json
    {
      "username": "admin_riohacha",
      "password": "mi_password_segura"
    }
    ```
  * **Respuesta Exitosa (200 OK):** Devuelve el token JWT de acceso, el rol del usuario y su `location_id`.

### B. Módulo de Incidencias (`/incidents`)
* **GET `/api/v1/incidents/`**
  * **Descripción:** Obtiene el listado de incidencias. Filtra automáticamente por la sede (`location_id`) asignada al usuario autenticado (Arquitectura Multitenant).
  * **Respuesta Exitosa (200 OK):** Lista de incidencias formateada en JSON.

* **POST `/api/v1/incidents/`**
  * **Descripción:** Registra una nueva incidencia desde la app móvil.
  * **Cuerpo de la petición (JSON):**
    ```json
    {
      "title": "Falla de conectividad en laboratorio 2",
      "description": "Los equipos no obtienen dirección IP.",
      "category_id": 2,
      "priority": "alta"
    }
    ```
  * **Respuesta Exitosa (201 Created):** Devuelve el objeto de la incidencia creada con su ID generado.

* **PATCH `/api/v1/incidents/{id}/change-status/`**
  * **Descripción:** Permite a un técnico cambiar el estado de una incidencia (Pendiente -> En Proceso -> Resuelta).

### C. Módulo de Emergencias (`/emergencies`)
* **GET `/api/v1/emergencies/`**
  * **Descripción:** Obtiene los protocolos de emergencia y líneas de contacto de la sede actual.

  