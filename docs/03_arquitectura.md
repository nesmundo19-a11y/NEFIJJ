# 03. Arquitectura del Sistema - NEFIJJ

## 1. Vista general
NEFIJJ utiliza una arquitectura cliente-servidor en capas:

1. **Aplicación móvil:** React Native con Expo. Presenta formularios y resultados, conserva los tokens en almacenamiento seguro y consume la API por HTTPS en producción.
2. **API y lógica de negocio:** Django 5.x y Django REST Framework. Autentica usuarios, valida entradas, aplica permisos y reglas de negocio, y serializa respuestas JSON.
3. **Persistencia:** backend Django para MySQL/MariaDB. En el entorno local XAMPP comprobado se detectó MariaDB 10.11.16, con `utf8mb4` y `utf8mb4_unicode_ci`. Guarda usuarios, sedes, categorías, incidencias, historial y protocolos.

La aplicación móvil no se conecta directamente a MySQL. Toda lectura y escritura pasa por la API.

## 2. Aislamiento multisedes
La primera versión usa una base de datos y un esquema compartidos. Cada incidencia y protocolo se relaciona con una sede (`location_id`); las cuentas técnicas y estudiantiles también tienen sede. El administrador general puede no estar asociado a una sede.

- El servidor obtiene rol y sede del usuario autenticado.
- Los estudiantes solo acceden a incidencias que reportaron.
- Los técnicos solo acceden a incidencias de su sede y solo actualizan las que tienen asignadas.
- El administrador general puede operar entre sedes; al crear o filtrar información debe indicar una sede cuando corresponda.
- Al asignar un técnico, el backend comprueba que pertenezca a la misma sede que la incidencia.

La separación se aplica en los querysets, permisos y validaciones del backend; ocultar registros en la interfaz no constituye una medida de seguridad.

## 3. Flujo principal de una incidencia
1. El usuario inicia sesión y obtiene tokens JWT.
2. La aplicación envía una solicitud autenticada para crear la incidencia, sin definir `reported_by`, `status` ni `location_id`.
3. El backend valida la categoría y los datos, deriva reportante y sede de la cuenta, establece prioridad/estado iniciales y persiste el registro.
4. Un administrador asigna un técnico de la sede correspondiente.
5. El técnico asignado actualiza el estado mediante las transiciones autorizadas. El backend registra los cambios en el historial.
6. El usuario consulta el estado de su reporte; los endpoints aplican el mismo control de acceso.

## 4. Contratos y operación
- Prefijo de API: `/api/v1/`; intercambio JSON UTF-8.
- Autenticación: `Authorization: Bearer <access_token>`.
- Los errores usan códigos HTTP adecuados y mensajes JSON sin información sensible.
- Las operaciones de actualización que cambian estado, asignación o sede deben validar autorización y consistencia en el servidor; cambios relacionados se guardan en una transacción.
- La configuración de base de datos, claves y hosts permitidos se obtiene del entorno, no del código fuente.

## 5. Entorno local frente a producción
- Desarrollo en Windows: Django se ejecuta en `0.0.0.0:8000` para que un teléfono de la LAN pueda acceder; la app usa `EXPO_PUBLIC_API_URL` con la IP LAN del computador y el prefijo `/api/v1`.
- `0.0.0.0` es la dirección de escucha del servidor, no la dirección que se configura en el teléfono. En el teléfono se usa una IP concreta del computador; `localhost` apunta al propio teléfono.
- `DEBUG=True` solo se admite para desarrollo local controlado. `ALLOWED_HOSTS` debe enumerar `localhost`, `127.0.0.1` y la IP LAN vigente; no usar `*`.
- El firewall de Windows debe limitar el puerto TCP 8000 al perfil de red privada de confianza y a la subred local. No convertir una red pública en privada para hacer funcionar la app.
- Producción requiere un despliegue distinto: `DEBUG=False`, dominio explícito, HTTPS, secretos protegidos y servidor de aplicación apropiado. `runserver` no es un servidor de producción.
- CORS aplica principalmente a clientes web; no sustituye la conectividad IP, `ALLOWED_HOSTS` ni las reglas de firewall para la app nativa.

El estado y la configuración local comprobada se detallan en [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md).

## 6. Arquitectura multiempresa implementada y límites
`Organization` es el tenant. `OrganizationMembership` asocia usuario, organización, rol y sede; `Location` sigue siendo una subdivisión. Incidencias y categorías guardan su organización y los endpoints filtran por membresía. La API elige automáticamente la única organización activa o exige `X-Organization-ID` para usuarios con varias. Solo `is_superuser` concede acceso global.

`OrganizationInvitation` guarda el hash de un código aleatorio, vence siete días hábiles después de su emisión (lunes-viernes, excluyendo festivos nacionales colombianos, en `America/Bogota`) y se consume una sola vez. La API permite crear, revocar y aceptar invitaciones; todavía no hay escaneo QR ni interfaz móvil para estos pasos. La pantalla superadmin móvil permite crear, activar y suspender organizaciones, pero no presenta métricas globales.

La migración asigna ubicaciones `DEMO-*` a `nefijj-demo` y las demás a `universidad-de-la-guajira`; la prueba de migración verifica el backfill y su reversión en SQLite aislado. No se ha ensayado todavía sobre una copia representativa de MariaDB; no aplicar la migración a la base operativa sin respaldo y ensayo.

Para operación inicial, usar Django Admin como consola web separada para el superadministrador; no crear un segundo APK ni añadir una segunda interfaz web hasta definir métricas y alcance. La pantalla móvil superadmin existente es una utilidad básica de pruebas, no sustituye la consola administrativa.
