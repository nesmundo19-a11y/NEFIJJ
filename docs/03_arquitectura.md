# 03. Arquitectura del Sistema - NEFIJJ

## 1. Vista general
NEFIJJ utiliza una arquitectura cliente-servidor en capas:

1. **Aplicación móvil:** React Native con Expo. Presenta formularios y resultados, conserva los tokens en almacenamiento seguro, adjunta fotografías de evidencia y consume la API por HTTPS en producción.
2. **API y lógica de negocio:** Django 5.x y Django REST Framework. Autentica usuarios, valida entradas, acepta evidencia de imagen en incidencias, aplica permisos y reglas de negocio, y serializa respuestas JSON.
3. **Persistencia:** backend Django para MySQL/MariaDB. En el entorno local XAMPP comprobado se detectó MariaDB 10.11.16, con `utf8mb4` y `utf8mb4_unicode_ci`. Guarda usuarios, sedes, categorías, incidencias, historial, protocolos **y las referencias a las imágenes de evidencia (las imágenes físicas quedan en la carpeta `media/` del servidor)**.

La aplicación móvil no se conecta directamente a MySQL. Toda lectura y escritura pasa por la API. La app permite elegir/tomar fotos JPG/PNG de hasta 10 MB y el backend las valida, las almacena fuera de MySQL y las entrega mediante un endpoint autenticado que comprueba el alcance del reporte.

### Fuente de datos para la prueba operativa
La conexión que se valide desde Expo Go debe usar el proceso Django configurado con `config.settings` y con `default` apuntando a `nefijj_db` en MariaDB/MySQL. `config.demo_settings` usa SQLite y sirve exclusivamente para la demostración aislada; una respuesta exitosa de esa configuración no demuestra que la app lea o escriba en MySQL. La app móvil solo cambia su URL de API (`EXPO_PUBLIC_API_URL`); no recibe credenciales ni se conecta directamente al motor.

La integración se considerará verificada cuando una sesión autenticada lea datos existentes de MySQL, cree una incidencia y vuelva a consultarla desde la API, y se compruebe que el registro quedó en la base. También se validará el alta de usuarios y el cambio seguro de contraseña mediante la API. Las pruebas deben respetar los permisos y el aislamiento por organización/sede. No se deben ejecutar scripts que borren/recreen tablas ni migraciones de esquema sin autorización expresa.

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
- Prefijo de API: `/api/v1/`; intercambio JSON UTF-8 **(y `multipart/form-data` para subida de archivos de evidencia)**.
- Autenticación: `Authorization: Bearer <access_token>`.
- Los errores usan códigos HTTP adecuados y mensajes JSON sin información sensible.
- Las operaciones de actualización que cambian estado, asignación o sede deben validar autorización y consistencia en el servidor; cambios relacionados se guardan en una transacción.
- JWT es stateless y no requiere tablas blacklist. Una huella firmada de la contraseña invalida los access/refresh emitidos antes de cambiarla.
- La configuración de base de datos, claves y hosts permitidos se obtiene del entorno, no del código fuente.

## 5. Entorno local frente a producción
- Desarrollo en Windows: Django se ejecuta en `0.0.0.0:8000` para que un teléfono de la LAN pueda acceder; la app usa `EXPO_PUBLIC_API_URL` con la IP LAN del computador y el prefijo `/api/v1`.
- `0.0.0.0` es la dirección de escucha del servidor, no la dirección que se configura en el teléfono. En el teléfono se usa una IP concreta del computador; `localhost` apunta al propio teléfono.
- `DEBUG=True` solo se admite para desarrollo local controlado. `ALLOWED_HOSTS` debe enumerar `localhost`, `127.0.0.1` y la IP LAN vigente; no usar `*`.
- El firewall de Windows debe limitar el puerto TCP 8000 al perfil de red privada de confianza y a la subred local. No convertir una red pública en privada para hacer funcionar la app.
- Producción requiere un despliegue distinto: `DEBUG=False`, dominio explícito, HTTPS, secretos protegidos y servidor de aplicación apropiado. Las evidencias son privadas: no exponer `MEDIA_ROOT` como directorio estático; servirlas mediante el endpoint autenticado que comprueba el alcance de la incidencia o almacenamiento privado equivalente. `runserver` no es un servidor de producción.
- CORS aplica principalmente a clientes web; no sustituye la conectividad IP, `ALLOWED_HOSTS` ni las reglas de firewall para la app nativa.

El estado y la configuración local comprobada se detallan en 10_bitacora_desarrollo.md.

## 6. Trabajo móvil de evidencia y categorías (implementado; falta prueba en teléfono)

Expo permite seleccionar o tomar una fotografía JPG/PNG de hasta 10 MB, previsualizarla y enviarla como multipart. El servidor entrega la imagen mediante una ruta autenticada que comprueba acceso a la incidencia; el directorio `media/` no se publica como contenido estático. La app incluye pantallas para listar, crear, editar y desactivar categorías con el tenant activo.

Se mejoraron las tarjetas de estado/prioridad, los formularios y las vistas de categorías/protocolos. La validación en un teléfono real sigue pendiente.

## 7. Avisos informativos de sismos del SGC (integración pendiente)
El alcance acordado es notificar por push a todos los dispositivos registrados cuando el SGC haya publicado un sismo; el aviso es informativo, no una alerta temprana, no requiere acuse y solo se entrega con internet. Se mostrará el área indicada por la fuente, sin filtrado por sede. La página principal del SGC no documenta el feed/API requerido; hasta verificar una URL y formato oficial no se implementará ingestión ni se enviarán notificaciones. Expo push requiere un development build, no Expo Go. Se autorizó preparar el código de persistencia y migración sin ejecutar cambios en MySQL. Los protocolos existentes siguen siendo estáticos; la app no sustituye canales oficiales ni promete entrega garantizada.

## 8. Arquitectura multiempresa implementada y límites
`Organization` es el tenant. `OrganizationMembership` asocia usuario, organización, rol y sede; `Location` sigue siendo una subdivisión. Incidencias y categorías guardan su organización y los endpoints filtran por membresía. La API elige automáticamente la única organización activa o exige `X-Organization-ID` para usuarios con varias. Solo `is_superuser` concede acceso global.

`OrganizationInvitation` guarda el hash de un código aleatorio, vence siete días hábiles después de su emisión y se consume una sola vez. La API permite crear, revocar y aceptar invitaciones; todavía no hay escaneo QR ni interfaz móvil para estos pasos. La pantalla superadmin móvil permite crear, activar y suspender organizaciones, pero no presenta métricas globales.

La migración asigna ubicaciones `DEMO-*` a `nefijj-demo` y las demás a `universidad-de-la-guajira`; la prueba de migración verifica el backfill y su reversión en SQLite aislado. No se ha ensayado todavía sobre una copia representativa de MariaDB; no aplicar la migración a la base operativa sin respaldo y ensayo.

Para operación inicial, usar Django Admin como consola web separada para el superadministrador; no crear un segundo APK ni añadir una segunda interfaz web hasta definir métricas y alcance. La pantalla móvil superadmin existente es una utilidad básica de pruebas, no sustituye la consola administrativa.