# 06. Políticas de Seguridad - NEFIJJ

## 1. Principios
- Denegar por defecto y comprobar autenticación, rol, sede y acceso al objeto en el backend en cada operación.
- La interfaz móvil no es una frontera de seguridad. Un cliente puede modificar cualquier dato enviado.
- No confiar en `location_id`, `role`, `reported_by`, `assigned_to` o estados iniciales enviados por un usuario no autorizado.

## 2. Identidad y autenticación
- Usar los mecanismos de autenticación y hash de contraseñas de Django (PBKDF2 por defecto o Argon2 configurado). Un hash de contraseña no es cifrado reversible.
- Usar JWT con vida corta para el token de acceso y una política explícita para expiración, renovación y revocación del refresh token.
- Transportar tokens solo por HTTPS fuera de desarrollo local. No incluirlos en URLs, capturas, analítica ni logs.
- Limitar intentos de autenticación y devolver mensajes que no permitan enumerar cuentas.
- Las cuentas son administradas; no se acepta registro público en la primera versión.

## 3. Autorización y multisedes
- Estudiantes: crear incidencias para su propia sede y consultar solo las que reportaron.
- Técnicos: consultar incidencias de su sede y gestionar solo las que les fueron asignadas.
- Administradores: gestionar usuarios, sedes, catálogos y operaciones de todas las sedes.
- Validar que el técnico asignado pertenezca a la sede de la incidencia.
- Filtrar listados y proteger también detalle, historial, asignación, cambios de estado y cualquier endpoint relacionado. Una URL con ID conocido no concede acceso.

## 4. Aplicación móvil
- Guardar tokens con `expo-secure-store`, no en `AsyncStorage` ni en código fuente.
- Borrar la sesión al cerrar sesión y manejar expiración/renovación sin exponer tokens en mensajes de error.
- Las variables `EXPO_PUBLIC_*` son visibles en el paquete móvil: nunca usarlas para secretos, contraseñas, claves privadas o credenciales de base de datos.
- No registrar contraseñas ni tokens durante depuración.

## 5. API, datos y configuración
- Exigir HTTPS en producción y limitar CORS a los orígenes realmente usados.
- Validar tipos, longitudes, relaciones y transiciones; aplicar límites razonables de paginación y carga útil.
- Mantener `SECRET_KEY`, credenciales de MySQL, claves JWT y configuración sensible fuera del repositorio, usando variables de entorno o un gestor de secretos.
- Configurar `DEBUG=False`, `ALLOWED_HOSTS` y copias de seguridad protegidas en producción.
- Usar consultas parametrizadas/ORM y escapar contenido al mostrarlo. CSRF se configura según el mecanismo de autenticación: la protección CSRF no sustituye autorización, validación ni mitigación de XSS.
- Registrar eventos administrativos y cambios relevantes sin incluir secretos ni datos innecesarios.
- Para evidencia fotográfica, limitar tipo, tamaño y resolución en el servidor, limitar acceso a la imagen con las mismas reglas de tenant/objeto que la incidencia, evitar publicar `MEDIA_ROOT` como directorio abierto y definir retención y tratamiento de metadatos EXIF antes de producción. La URL del archivo no es autorización: cada lectura debe autenticar al usuario y volver a comprobar el alcance del reporte.
- Para alertas de peligro vital, autenticar y auditar quién puede emitir/actualizar/cancelar avisos, limitar destinatarios por zona/organización según la decisión aprobada y no presentarlas como garantizadas si el dispositivo está sin red. No usar alertas de prueba como avisos reales.

## 6. Seguridad del entorno de desarrollo Windows
- El archivo `backend/.env` y `mobile/.env.local` son locales e ignorados por Git. No copiarlos a incidencias, capturas, documentación compartida ni al repositorio; `EXPO_PUBLIC_*` sí queda visible dentro del paquete móvil y solo debe contener la URL pública de desarrollo.
- Durante desarrollo, mantener `DEBUG=True` solo en una máquina/red de confianza y enumerar explícitamente `localhost`, `127.0.0.1` y la IP LAN actual en `DJANGO_ALLOWED_HOSTS`. No usar `*`.
- Para Expo Go, iniciar Django con `python manage.py runserver 0.0.0.0:8000`; esto escucha en las interfaces de red y no convierte el servidor de desarrollo en seguro para Internet.
- Limitar la regla entrante de Windows Firewall del puerto TCP 8000 al perfil `Private` y `LocalSubnet`. Cambiar una red `Public` a `Private` únicamente si es una red propia y confiable. No abrir el puerto a `Any` ni a todos los perfiles.
- Si cambia la IP del computador, actualizarla tanto en `backend/.env` (`DJANGO_ALLOWED_HOSTS`) como en `mobile/.env.local` (`EXPO_PUBLIC_API_URL`) y reiniciar Django y Expo.
- Producción requiere `DEBUG=False`, `ALLOWED_HOSTS` con dominios controlados, HTTPS y un servidor de producción; no usar `runserver` ni reglas de firewall de desarrollo.

La bitácora [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md) registra el estado de red observado y los pasos pendientes. En este equipo se observó una regla `Django 8000` inicialmente abierta a cualquier dirección/perfil y una red Wi-Fi marcada como `Public`; se requiere elevar PowerShell como administrador para restringir la regla. No se debe asumir que ese cambio ya se aplicó.

## 7. Contraseña del superusuario
No usar una contraseña corta, numérica o compartida en chat. Si Django advierte que una contraseña es débil, no omitir la validación; detener el alta y elegir una contraseña larga, única y no reutilizada. Si una contraseña se expuso, cambiarla con `python manage.py changepassword <usuario>` en una terminal local y no documentar su valor. La bitácora registra únicamente que se reportó el cambio, nunca la contraseña.

## 8. Aislamiento multiempresa
El backend resuelve la organización mediante membresías y aplica el alcance en listados, detalles y escrituras. `X-Organization-ID` solo selecciona un tenant para el que el usuario ya tiene membresía activa; no concede acceso por sí mismo. Superadministrador es el único rol global. No confiar en la navegación móvil como control de autorización.

Las invitaciones usan un token aleatorio opaco; se almacena su SHA-256, es revocable y de un solo uso. Las nuevas invitaciones vencen a los siete días hábiles de Colombia (lunes-viernes, excluyendo festivos nacionales oficiales, zona `America/Bogota`, misma hora local de emisión). Las invitaciones existentes conservan la fecha ya almacenada. La aceptación exige autenticación y una sede activa de la organización. La app no tiene todavía pantalla de invitación/QR, y no se ha completado una auditoría de eventos administrativos organizacionales ni una prueba de seguridad integral.

La prueba actual cubre aislamiento entre organizaciones para incidencias y cuentas, suspensión y uso único de invitación, además del backfill y reversión en SQLite. El ensayo en MariaDB, pruebas manuales en dispositivo, métricas y controles de producción siguen pendientes. Consultar [09_pruebas.md](./09_pruebas.md) y [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md).
