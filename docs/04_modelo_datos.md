# Modelo de datos
# 04. Modelo de Datos - NEFIJJ

## 1. Introducción al Esquema de Base de Datos
El almacenamiento de **NEFIJJ** está diseñado en una base de datos relacional **MySQL 8.0**, optimizada para soportar la arquitectura *multitenant* por sedes y mantener la integridad referencial entre usuarios, roles e incidencias.

## 2. Entidades Principales y Tablas

### A. Tabla `locations` (Sedes / Tenants)
Almacena las diferentes sedes o campus universitarios para segmentar la operación.
* `id` (INT, PK, Auto Increment)
* `name` (VARCHAR, ej: "Sede Principal Riohacha", "Sede Maicao")
* `code` (VARCHAR, identificador único)
* `created_at` (TIMESTAMP)

### B. Tabla `users` (Usuarios y Roles)
Almacena los usuarios del sistema y define su rol y su sede asignada.
* `id` (INT, PK, Auto Increment)
* `username` (VARCHAR, único)
* `email` (VARCHAR, único)
* `password` (VARCHAR, encriptada con Argon2/PBKDF2)
* `role` (ENUM: 'admin', 'technician', 'student')
* `location_id` (INT, FK hacia `locations.id` - Clave para el Multitenant)
* `is_active` (BOOLEAN)

### C. Tabla `categories` (Categorías de Incidencias)
Clasifica el tipo de reporte.
* `id` (INT, PK, Auto Increment)
* `name` (VARCHAR, ej: "Infraestructura", "Redes y Conectividad", "Eléctrica")
* `description` (TEXT)

### D. Tabla `incidents` (Incidencias / Reportes)
Contiene el núcleo operativo de las solicitudes de soporte.
* `id` (INT, PK, Auto Increment)
* `title` (VARCHAR)
* `description` (TEXT)
* `status` (ENUM: 'pendiente', 'en_proceso', 'resuelta', 'cerrada')
* `priority` (ENUM: 'baja', 'media', 'alta', 'critica')
* `category_id` (INT, FK hacia `categories.id`)
* `location_id` (INT, FK hacia `locations.id`)
* `reported_by` (INT, FK hacia `users.id`)
* `assigned_to` (INT, FK hacia `users.id`, NULL si no está asignada)
* `created_at` (TIMESTAMP)
* `updated_at` (TIMESTAMP)

### E. Tabla `emergency_protocols` (Módulo de Emergencia)
Almacena la información de respuesta rápida.
* `id` (INT, PK, Auto Increment)
* `title` (VARCHAR)
* `content` (TEXT)
* `contact_phone` (VARCHAR)
* `location_id` (INT, FK hacia `locations.id`)