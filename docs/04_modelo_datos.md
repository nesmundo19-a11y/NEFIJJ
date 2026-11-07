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
- **`evidence_image`:** campo `ImageField` (requiere la librería `Pillow`) para almacenar la ruta de la fotografía o captura adjunta al reporte. Admite nulos y guarda solo el texto de la ruta relativa (ej. `evidences/2026/11/...`) en MySQL. La API y app procesan imágenes JPG/PNG de hasta 10 MB; validar permisos/UX en un teléfono sigue pendiente.
- El backend debe validar coherencia de tenant y sede al crear, filtrar y asignar. El reportante y organización se derivan de la sesión/contexto autorizados, no de campos confiados al cliente.
- Tiene `created_at` y `updated_at`. La sede y organización no deben cambiarse mediante una actualización ordinaria.

### `IncidentEvent` (historial)
- Registra incidencia, actor, tipo de evento, valores anterior/nuevo y fecha.
- Es de solo lectura para clientes; el servidor crea los eventos en la misma transacción que el cambio que documentan.

### `EmergencyProtocol` (protocolo de emergencia)
- Se asocia a una sede y contiene título, contenido, contacto, estado y marcas de tiempo.
- Su acceso se limita a la organización propietaria de la sede.
- Es contenido informativo estático, no una alarma, un canal de notificación ni una detección de terremotos/peligros.

## 3. Notas de seguridad y evolución
Las fotos se almacenan fuera de MySQL y solo la ruta relativa se guarda en `evidence_image`; el acceso se controla mediante la API autenticada. Antes de producción deben definirse retención y tratamiento de metadatos de ubicación de la imagen.

No se han creado modelos de alerta ni tablas adicionales. Antes de proponer un esquema de alertas, definir origen y autoridad de los avisos, geografía de destinatarios, estados (por ejemplo, actualización/cancelación), confirmaciones, retención y auditoría. No reutilizar `EmergencyProtocol` como registro de una alerta en vivo.

## 4. Extensión pendiente: áreas y responsables
No existe actualmente una entidad de área ni asignación automática. Para el MVP de enrutamiento, implementar el siguiente esquema y validaciones en una migración nueva; no reutilizar `Category` como área:

- `IncidentArea`: organización, nombre, estado activo y descripción opcional; nombre único por organización.
- Añadir rol de membresía `resolver`, con sede requerida. No convertir automáticamente a todos los `technician` existentes en resolutores.
- `AreaResolverAssignment`: área, sede y una membresía activa `resolver`; una asignación única por pareja área/sede. El área y sede deben pertenecer a la misma organización y la membresía debe corresponder a esa organización y sede.
- Añadir `area` opcional a incidencias históricas. En reportes nuevos debe ser obligatoria; el backend determina `assigned_to` desde la asignación activa del área y sede.
- Si no existe asignación válida, rechazar la creación con un error de validación explícito; no crear silenciosamente un caso sin responsable. Los cambios administrativos de responsable deben generar un evento de historial.
- La reasignación manual solo se permite a un administrador de esa organización, hacia una membresía `resolver` activa de la misma sede. Mantener el aislamiento multiempresa.
- Alcance MVP: un responsable por área y sede. Asignación por turnos, múltiples responsables y reparto de carga quedan fuera hasta especificar reglas de equipo.

Pruebas requeridas: selección de área/categoría separadas, organización y sede cruzadas, área inactiva, resolver inactivo o de otra sede, falta de asignación, modificación de asignación, historial y aislamiento frente a otra organización.

## 5. Integridad, índices y datos históricos
- Usar restricciones relacionales/de unicidad para las reglas representables en la base y validación de servidor para coherencia entre organización, sede, categoría y membresía.
- **Archivos físicos:** Las imágenes y archivos multimedia no se almacenan como blobs binarios en MySQL; se alojan en el sistema de archivos del servidor (carpeta `media/`) y la base de datos conserva únicamente la ruta relativa. Las evidencias de incidencias se entregan mediante un endpoint autenticado con el mismo alcance de acceso del reporte; no exponer `MEDIA_ROOT` directamente como directorio estático.
- Índices de incidencias cubren organización/estado, sede/estado, reportante/fecha y asignado/estado.
- Desactivar cuentas, sedes y categorías en vez de eliminar datos que tengan referencias históricas.
- Guardar fechas coherentemente (UTC en almacenamiento) y devolverlas en formato ISO 8601.
- El backfill asigna sedes `DEMO-*` a `nefijj-demo` y las demás a `universidad-de-la-guajira`; las categorías compartidas se duplican por organización.
- El backfill y reversión se probaron en SQLite en memoria. Sigue pendiente ensayar en una copia representativa de MariaDB y conciliar conteos; no aplicar cambios a la base persistente sin respaldo y ensayo.

## 6. Datos ficticios y aislamiento de pruebas
`seed_demo` solo se ejecuta con `config.demo_settings` contra el SQLite de archivo `backend/nefijj-demo.sqlite3`; rechaza otras configuraciones/bases. Crea datos ficticios repetibles de organizaciones, sedes, cuentas, membresías, categoría, protocolos e incidencias. Por defecto las cuentas no obtienen una contraseña de acceso; `--enable-login` establece una contraseña temporal aleatoria para las cuentas DEMO y la imprime una vez en la terminal. No registrar ese valor ni usar las cuentas en servicios reales.

Las pruebas automatizadas usan `config.test_settings` y SQLite en memoria. No conectar pruebas, seed DEMO ni migraciones de ensayo a `nefijj_db`.

## 7. Compatibilidad con el esquema MySQL heredado
El DDL compartido como referencia define las tablas `accounts_organization`, `accounts_location`, `accounts_user`, `accounts_organizationmembership`, `accounts_organizationinvitation`, `incidents_category` e `incidents_incident`. La tabla `accounts_user` conserva las columnas centrales de autenticación de Django y añade `role` y `location_id`; los nombres y tipos deben cotejarse con los modelos y con la estructura física real antes de conectar la API.

Ese DDL es documentación de referencia, no un script para ejecutar: contiene `DROP TABLE` y ejemplos de contraseñas que no son hashes utilizables. No ejecutar el script completo, no borrar/recrear datos y no alterar el esquema. Las tablas de historial `incidents_incidentevent` y de protocolos `incidents_emergencyprotocol` no aparecen en el DDL compartido y se habían reportado ausentes en una inspección anterior; verificar de nuevo su existencia antes de usar los endpoints que dependen de ellas. Si faltan, detener esos flujos y solicitar autorización antes de cualquier reparación de esquema.

Las cuentas nuevas se crean con `create_user`/`set_password` y los validadores de Django; nunca se almacena una contraseña recibida en texto plano ni se actualiza directamente por SQL. El usuario autenticado puede cambiar su contraseña solo tras validar la actual; la asignación de organización, rol y sede se limita por los permisos administrativos y la membresía activa. No se debe cambiar la contraseña de otra cuenta mediante el flujo de autoservicio.

La autenticación JWT es stateless para no depender de tablas de blacklist que no están presentes en la instancia inspeccionada. Los tokens llevan una huella firmada de la contraseña almacenada; después de cambiarla, la huella ya no coincide y se rechazan los tokens previos. Los refresh no rotan.