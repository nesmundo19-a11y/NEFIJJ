# 04. Modelo de datos - NEFIJJ

## 1. Criterios de diseño
El esquema es compartido entre organizaciones (multi-tenant). Toda consulta y mutación de datos operativos debe limitarse por organización en el backend; no basta con que el cliente envíe un `organization_id`. `AUTH_USER_MODEL` es el modelo de cuenta de Django. Las contraseñas las gestiona Django como hashes no reversibles.

## 2. Entidades implementadas

### `Organization`
- `id`, `name`, `slug` único, `status` (`active` o `suspended`), `created_at` y `updated_at`.
- Una organización suspendida no se elimina; las operaciones permitidas para ese estado deben validarse en la API.

### `OrganizationMembership`
- Relaciona `user`, `organization`, rol y estado activo.
- Roles actuales: `organization_admin`, `technician` y `user`. Un usuario puede pertenecer a varias organizaciones.
- `location` es opcional para administradores organizacionales y obligatoria para técnicos y usuarios.
- Una restricción impide más de una membresía por usuario y organización; la sede debe pertenecer a la misma organización.

### `OrganizationInvitation`
- Relaciona organización y usuario creador; guarda solo el hash de un código aleatorio, además de vencimiento, revocación y uso.
- El código es de un uso y se puede revocar. Las invitaciones nuevas vencen siete días hábiles de Colombia después de la emisión: lunes-viernes, excluyendo festivos nacionales oficiales, en `America/Bogota`; se conserva la hora local y el conteo comienza el siguiente día hábil. Los registros existentes conservan su `expires_at` almacenado.

### `User` (usuario Django)
- Conserva `username`, correo único, contraseña, `is_active`, `is_staff`, `is_superuser`, `role` y una sede histórica/compatibilidad.
- `is_superuser` representa el acceso global a la plataforma y se fuerza al rol global `superadmin`.
- Los roles actuales del campo global son `superadmin`, `admin`, `technician` y `student`. Para las operaciones de tenant, prevalece la membresía activa; el campo global no concede acceso a otra organización.
- Las membresías son el origen de verdad para rol y sede dentro de una organización. No asignar roles mediante SQL directo.

### `Location` (sede)
- Pertenece a una `Organization`; tiene nombre, código único, estado activo y fecha de creación.
- Las sedes no se eliminan si tienen incidencias o historial.

### `Category` (categoría)
- Pertenece a una organización; contiene nombre, descripción y estado activo.
- El nombre es único dentro de la organización. Clasifica el tipo de incidencia; no representa un área o departamento de enrutamiento.

### `Incident` (incidencia)
- Contiene título, descripción, estado (`pendiente`, `en_proceso`, `resuelta`, `cerrada`) y prioridad (`baja`, `media`, `alta`, `critica`).
- Relaciona organización, categoría, sede, reportante y asignado opcional.
- El backend debe validar coherencia de tenant y sede al crear, filtrar y asignar. El reportante y organización se derivan de la sesión/contexto autorizados, no de campos confiados al cliente.
- Tiene `created_at` y `updated_at`. La sede y organización no deben cambiarse mediante una actualización ordinaria.

### `IncidentEvent` (historial)
- Registra incidencia, actor, tipo de evento, valores anterior/nuevo y fecha.
- Es de solo lectura para clientes; el servidor crea los eventos en la misma transacción que el cambio que documentan.

### `EmergencyProtocol` (protocolo de emergencia)
- Se asocia a una sede y contiene título, contenido, contacto, estado y marcas de tiempo.
- Su acceso se limita a la organización propietaria de la sede.

## 3. Extensión pendiente: áreas y responsables
No existe actualmente una entidad de área ni asignación automática. Para el MVP de enrutamiento, implementar el siguiente esquema y validaciones en una migración nueva; no reutilizar `Category` como área:

- `IncidentArea`: organización, nombre, estado activo y descripción opcional; nombre único por organización.
- Añadir rol de membresía `resolver`, con sede requerida. No convertir automáticamente a todos los `technician` existentes en resolutores.
- `AreaResolverAssignment`: área, sede y una membresía activa `resolver`; una asignación única por pareja área/sede. El área y sede deben pertenecer a la misma organización y la membresía debe corresponder a esa organización y sede.
- Añadir `area` opcional a incidencias históricas. En reportes nuevos debe ser obligatoria; el backend determina `assigned_to` desde la asignación activa del área y sede.
- Si no existe asignación válida, rechazar la creación con un error de validación explícito; no crear silenciosamente un caso sin responsable. Los cambios administrativos de responsable deben generar un evento de historial.
- La reasignación manual solo se permite a un administrador de esa organización, hacia una membresía `resolver` activa de la misma sede. Mantener el aislamiento multiempresa.
- Alcance MVP: un responsable por área y sede. Asignación por turnos, múltiples responsables y reparto de carga quedan fuera hasta especificar reglas de equipo.

Pruebas requeridas: selección de área/categoría separadas, organización y sede cruzadas, área inactiva, resolver inactivo o de otra sede, falta de asignación, modificación de asignación, historial y aislamiento frente a otra organización.

## 4. Integridad, índices y datos históricos
- Usar restricciones relacionales/de unicidad para las reglas representables en la base y validación de servidor para coherencia entre organización, sede, categoría y membresía.
- Índices de incidencias cubren organización/estado, sede/estado, reportante/fecha y asignado/estado.
- Desactivar cuentas, sedes y categorías en vez de eliminar datos que tengan referencias históricas.
- Guardar fechas coherentemente (UTC en almacenamiento) y devolverlas en formato ISO 8601.
- El backfill asigna sedes `DEMO-*` a `nefijj-demo` y las demás a `universidad-de-la-guajira`; las categorías compartidas se duplican por organización.
- El backfill y reversión se probaron en SQLite en memoria. Sigue pendiente ensayar en una copia representativa de MariaDB y conciliar conteos; no aplicar cambios a la base persistente sin respaldo y ensayo.

## 5. Datos ficticios y aislamiento de pruebas
`seed_demo` solo se ejecuta con `config.demo_settings` contra el SQLite de archivo `backend/nefijj-demo.sqlite3`; rechaza otras configuraciones/bases. Crea datos ficticios repetibles de organizaciones, sedes, cuentas, membresías, categoría, protocolos e incidencias. Por defecto las cuentas no obtienen una contraseña de acceso; `--enable-login` establece una contraseña temporal aleatoria para las cuentas DEMO y la imprime una vez en la terminal. No registrar ese valor ni usar las cuentas en servicios reales.

Las pruebas automatizadas usan `config.test_settings` y SQLite en memoria. No conectar pruebas, seed DEMO ni migraciones de ensayo a `nefijj_db`.
