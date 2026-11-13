# 05. Especificación de la API REST - NEFIJJ

## 1. Convenciones
- Base de API: `http://127.0.0.1:8000/api/v1/` desde el mismo computador. Desde un dispositivo físico, usar `http://<IP-LAN-DEL-COMPUTADOR>:8000/api/v1/`. `localhost` en el teléfono no apunta al computador. Producción debe usar HTTPS.
- Contenido: `application/json; charset=utf-8`.
- Endpoints protegidos: `Authorization: Bearer <access_token>`.
- Listados paginados. Los filtros reducen resultados, pero nunca amplían los permisos del usuario.
- Fechas: ISO 8601. Los errores devuelven un objeto JSON con `detail` o errores por campo.
- Las rutas de las secciones siguientes son relativas a `/api/v1/`. Por ejemplo, el login completo es `POST /api/v1/auth/token/`.

## 2. Autenticación

### `POST /auth/token/`
Autentica una cuenta existente. No crea cuentas.

```json
{
  "username": "usuario",
  "password": "contraseña"
}
```

Respuesta `200 OK`: tokens `access` y `refresh`, más `user` (`id`, `username`, `role`, `location_id`, `organizations`). Cada elemento de `organizations` incluye `organization_id`, `organization_name`, `organization_status`, `role`, `location_id` y `location_name`. Para varias membresías, el rol del usuario es `member` hasta que la app elija una organización. Nunca registrar credenciales ni tokens.

### `POST /auth/token/refresh/`
Recibe `refresh` y devuelve un nuevo `access` (y el refresh si la configuración de rotación lo establece).

## 3. Incidencias

### `GET /incidents/`
Devuelve incidencias dentro del alcance del usuario final (propias), técnico (sede asignada), administrador organizacional (organización activa) o superadministrador (global). Admite filtros `status`, `priority`, `category`; `location` solo para administradores con alcance autorizado.

### `POST /incidents/`
Crea una incidencia para el usuario final autenticado dentro de su organización y sede activas.

```json
{
  "title": "Falla de conectividad en laboratorio 2",
  "description": "Los equipos no obtienen dirección IP.",
  "category_id": 2,
  "priority": "alta"
}
```

El cliente no envía `reported_by`, `location_id`, `status`, `assigned_to` ni marcas de tiempo. El servidor deriva esos valores. Respuesta `201 Created` con el recurso creado.

### `GET /incidents/{id}/`
Devuelve el detalle solo si el usuario tiene acceso a esa incidencia.

### `GET /incidents/{id}/events/`
Devuelve el historial de eventos del caso, aplicando el mismo alcance de acceso que el detalle.

### `PATCH /incidents/{id}/assign/`
Solo administrador organizacional o superadministrador con alcance seleccionado. Recibe `assigned_to`; el servidor valida que sea un técnico activo de la misma organización y sede. Registra el evento de asignación.

### `PATCH /incidents/{id}/status/`
El técnico asignado puede solicitar `en_proceso` o `resuelta` respetando el flujo. El administrador organizacional o superadministrador puede cerrar una incidencia resuelta o reabrir una cerrada en estado `en_proceso`. Por ejemplo:

```json
{
  "status": "en_proceso"
}
```

Una transición no permitida responde `400 Bad Request`; falta de autenticación responde `401`; falta de permiso responde `403` o `404` según la política para no revelar recursos.

## 4. Emergencias y catálogos
- `GET /emergencies/`: protocolos activos de la sede del usuario; el administrador organizacional puede filtrar por sede de su organización.
- `GET /categories/`: categorías activas disponibles para reportar.
- `POST /categories/` y `PATCH /categories/{id}/`: solo administrador organizacional o superadministrador; la categoría queda en el tenant activo.
- `POST /emergencies/` y `PATCH /emergencies/{id}/`: solo administrador organizacional o superadministrador; la sede debe pertenecer al tenant activo y estar activa.

## 5. Administración de sedes y cuentas
Estas rutas requieren administrador organizacional o superadministrador y limitan la operación al tenant seleccionado:
- `GET /locations/` y `POST /locations/`; `GET /locations/{id}/` y `PATCH /locations/{id}/`.
- `GET /users/` y `POST /users/`; `GET /users/{id}/` y `PATCH /users/{id}/`.

El alta de una cuenta requiere `username`, `email`, `password`, `role` y `location_id` para técnicos/usuarios finales. La API exige una contraseña de al menos 12 caracteres y aplica los validadores de Django; el campo es de escritura únicamente y Django la almacena mediante hash. Solo superadministradores pueden asignar administradores organizacionales. Un administrador no puede modificar cuentas superusuario desde estas rutas. Django Admin queda disponible para gestión operativa.

En `PATCH /users/{id}/`, `role`, `location_id` e `is_active` modifican únicamente la membresía de la organización seleccionada. Desactivar una membresía no desactiva la cuenta global ni sus membresías en otras organizaciones. `username`, `email` y `password` son datos globales de la cuenta y solo los puede cambiar el superadministrador. No hay un endpoint de autoservicio para cambiar la contraseña.

## 6. Códigos de respuesta
- `200 OK`: consulta o actualización exitosa.
- `201 Created`: recurso creado.
- `400 Bad Request`: datos inválidos o transición no permitida.
- `401 Unauthorized`: token ausente, inválido o expirado.
- `403 Forbidden` / `404 Not Found`: operación o recurso fuera del alcance.
- `429 Too Many Requests`: límite de solicitudes excedido, si se configura.

## 7. Organizaciones, membresías e invitaciones
- `GET /organizations/` y `POST /organizations/`: solo superadministrador. Crear requiere `name` y `slug`.
- `PATCH /organizations/{id}/status/`: solo superadministrador; recibe `status` (`active` o `suspended`).
- `GET /organizations/mine/`: devuelve las membresías activas del usuario autenticado en organizaciones activas.
- `POST /organizations/{id}/invitations/`: administrador de esa organización o superadministrador, con contexto activo. Devuelve una sola vez el código aleatorio y su vencimiento siete días hábiles después de la emisión: lunes-viernes, excluyendo festivos nacionales oficiales de Colombia, calculados en `America/Bogota`. Se conserva la hora local de emisión y el conteo empieza el día hábil siguiente. Solo se guarda el hash del código.
- `POST /organizations/{id}/invitations/{invitation_id}/revoke/`: revoca una invitación aún no usada.
- `POST /memberships/join/`: cuenta autenticada; recibe `code` y `location_id` de una sede activa de la organización. Crea una membresía de usuario final. Una invitación usada, vencida, revocada o de una organización suspendida se rechaza.

Para solicitudes de usuarios que pertenecen a varias organizaciones, enviar `X-Organization-ID` con el ID seleccionado. El backend verifica la membresía; con una sola membresía activa se selecciona automáticamente. No enviar este header no amplía permisos. El superadministrador accede globalmente cuando no selecciona tenant.

## 8. Implementación móvil y límites
La app envía el tenant seleccionado, ofrece selección/cambio de organización, enruta por rol y permite al superadministrador crear/activar/suspender organizaciones. El administrador organizacional tiene panel móvil de incidencias; usuario y técnico conservan sus flujos de reporte/atención. No hay pantallas móviles para invitar/vincular mediante QR, administrar personal/sedes/catálogos/protocolos, ni métricas o notificaciones. Las categorías actuales clasifican incidencias, pero no equivalen a departamentos/áreas y no provocan enrutamiento automático a responsables. Los permisos se verifican siempre en el backend.

Las rutas documentadas corresponden al código actual, no equivalen a una API desplegada en producción. La cobertura, migración de datos y límites pendientes se registran en [09_pruebas.md](./09_pruebas.md).
