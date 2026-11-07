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
Recibe `refresh` y devuelve un nuevo `access`. No rota el refresh token, para no depender de tablas de blacklist que no existen en el esquema MySQL inspeccionado. Los JWT incluyen una huella de la contraseña; al cambiarla, los tokens emitidos con la contraseña anterior dejan de ser válidos.

## 3. Incidencias

### `GET /incidents/`
Devuelve incidencias dentro del alcance del usuario final (propias), técnico (sede asignada), administrador organizacional (organización activa) o superadministrador (global). Admite filtros `status`, `priority`, `category`; `location` solo para administradores con alcance autorizado.

### `POST /incidents/`
Crea una incidencia para el usuario final autenticado dentro de su organización y sede activas.

Acepta `application/json` sin archivo o `multipart/form-data` con `evidence_image` opcional. Para solicitudes multipart, el cliente debe enviar el boundary correspondiente. Se admiten JPG/PNG de hasta 10 MB y un máximo de 40 megapíxeles; Pillow valida el contenido. El archivo se guarda bajo `MEDIA_ROOT` y la respuesta incluye la URL del endpoint protegido de evidencia.

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

### `GET /incidents/{id}/evidence/`
Entrega el archivo de evidencia de la incidencia si existe y el usuario autenticado puede ver ese mismo reporte. Si la incidencia está fuera de su alcance o no tiene archivo, devuelve `404`. Los listados y detalles devuelven `evidence_image` como URL de este endpoint protegido, no como una ruta pública de `MEDIA_ROOT`.

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

El alta de una cuenta requiere `username`, `email`, `password`, `role` y `location_id` para técnicos/usuarios finales. Acepta además `first_name` y `last_name`. La API exige una contraseña de al menos 12 caracteres y aplica los validadores de Django; el campo es de escritura únicamente y Django la almacena mediante hash. Usuario y membresía se guardan en una transacción. Solo superadministradores pueden asignar administradores organizacionales. Un administrador no puede modificar cuentas superusuario ni cambiar la contraseña de otra persona desde estas rutas.

### `POST /auth/password/change/`
Requiere JWT del usuario y recibe `old_password` y `new_password`. Comprueba la contraseña actual, rechaza reutilizarla, aplica los validadores de Django y responde `204 No Content`. El cambio invalida los JWT previos mediante la huella de contraseña; la app debe cerrar la sesión local e iniciar sesión con la nueva contraseña.

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
- `GET /organizations/mine/`: devuelve las membresías activas del usuario autenticado.
- `POST /organizations/{id}/invitations/`: administrador de esa organización o superadministrador, con contexto activo. Devuelve una sola vez el código aleatorio y su vencimiento siete días hábiles después de la emisión: lunes-viernes, excluyendo festivos nacionales oficiales de Colombia, calculados en `America/Bogota`. Se conserva la hora local de emisión y el conteo empieza el día hábil siguiente. Solo se guarda el hash del código.
- `POST /organizations/{id}/invitations/{invitation_id}/revoke/`: revoca una invitación aún no usada.
- `POST /memberships/join/`: cuenta autenticada; recibe `code` y `location_id` de una sede activa de la organización. Crea una membresía de usuario final. Una invitación usada, vencida, revocada o de una organización suspendida se rechaza.

Para solicitudes de usuarios que pertenecen a varias organizaciones, enviar `X-Organization-ID` con el ID seleccionado. El backend verifica la membresía; con una sola membresía activa se selecciona automáticamente. No enviar este header no amplía permisos. El superadministrador accede globalmente cuando no selecciona tenant.

## 8. Implementación móvil y límites
La app envía el tenant seleccionado, ofrece selección/cambio de organización, enruta por rol y permite al superadministrador crear/activar/suspender organizaciones. El administrador organizacional puede abrir el alta de usuarios y gestionar categorías para su organización; el superadministrador puede iniciar esas acciones desde una organización elegida. Toda cuenta autenticada puede cambiar su propia contraseña desde Cuenta. Usuario y técnico conservan sus flujos de reporte/atención; el usuario puede adjuntar fotos JPG/PNG de hasta 10 MB. No hay pantallas móviles para invitar/vincular mediante QR, administrar sedes/protocolos, ni métricas o alertas en tiempo real. Los protocolos de emergencia son informativos, no son alertas urgentes. Las categorías actuales no equivalen a departamentos/áreas ni provocan enrutamiento automático. Los permisos se verifican siempre en el backend.

No hay endpoints para avisos sísmicos ni registro de tokens push. El alcance acordado es enviar avisos informativos de sismos ya registrados por el SGC a todos los dispositivos registrados, sin acuse y con internet. La integración está bloqueada hasta verificar una API/feed oficial del SGC; la página principal proporcionada no identifica un endpoint o formato. Push requiere development build (no Expo Go). Se autorizó generar modelos/migración para persistencia, pero no ejecutar ni aplicar migraciones en MySQL. Los avisos no serán alertas tempranas ni sustituirán los servicios oficiales.

Las rutas documentadas corresponden al código actual, no equivalen a una API desplegada en producción. La cobertura, migración de datos y límites pendientes se registran en [09_pruebas.md](./09_pruebas.md).

## 9. Alta de usuarios y cambio de contraseña
El contrato de `POST /users/` debe crear una cuenta autenticable y su membresía para la organización activa dentro de una transacción. Acepta los datos de perfil, `username`, `email`, contraseña inicial y rol permitido; para roles con sede, exige `location_id` de la misma organización. El backend valida unicidad, política de contraseñas y permisos antes de guardar. La respuesta nunca incluye contraseña ni hash. El cliente no puede otorgar `is_superuser`, `is_staff` ni ampliar la organización o sede.

El endpoint de autoservicio y las pantallas móviles de alta/cambio están implementados. El cambio administrativo de credenciales de otra cuenta queda fuera del autoservicio y no se permite por `PATCH /users/{id}/`. El cambio no devuelve secretos y revoca access/refresh JWT antiguos mediante la huella del hash actual.
