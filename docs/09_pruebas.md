# 09. Plan de Pruebas y Validación - NEFIJJ

## 1. Preparación
Para las pruebas automatizadas, usar `config.test_settings` y su SQLite en memoria. Para la prueba manual desde Expo Go, usar `config.demo_settings` y la base aislada `backend/nefijj-demo.sqlite3`; los comandos exactos están en [08_desarrollo_mobile.md](./08_desarrollo_mobile.md). El backfill mantiene dos organizaciones; el seed completa `nefijj-demo` con dos sedes, una cuenta superadmin, una administradora organizacional, dos usuarios, dos técnicos, protocolos e incidencias.

No usar credenciales reales, tokens compartidos ni `nefijj_db`. Las pruebas deben validar permisos en la API, no solo el comportamiento de la interfaz. `seed_demo` rechaza cualquier base que no sea el SQLite aislado de `config.demo_settings`; los logins se habilitan con una contraseña aleatoria mostrada una sola vez en la terminal.

## 2. Casos de prueba

### CP01 - Autenticación y renovación
Iniciar sesión con credenciales válidas e inválidas; renovar un token; usar un token vencido.
**Esperado:** respuesta correcta con JWT para la cuenta válida; error `401` sin filtrar si el usuario existe; el token vencido no accede a endpoints protegidos.

### CP02 - Alcance del estudiante
Crear incidencias como estudiante de sede A y consultar el listado y el detalle de incidencias propias y ajenas, incluso usando directamente el ID de otra incidencia.
**Esperado:** puede crear para su sede y consultar solo las que reportó. No puede definir `location_id`, `reported_by`, rol, asignación ni estado enviando campos adicionales.

### CP03 - Aislamiento del técnico
Consultar incidencias de sede A como técnico A, incluyendo una no asignada a su cuenta; intentar consultar una incidencia de sede B y probar filtros con otra sede.
**Esperado:** ve las incidencias de su sede, pero solo puede modificar las asignadas a su cuenta. No puede acceder a la incidencia de otra sede; manipular filtros o IDs no amplía el acceso.

### CP04 - Administración y asignación
Como administrador, listar por sede, asignar un técnico de la misma sede e intentar asignar uno de otra sede o inactivo.
**Esperado:** acceso administrativo entre sedes; la asignación válida se registra; las inválidas se rechazan sin cambiar la incidencia.

### CP05 - Crear una incidencia
Enviar título, descripción, categoría y prioridad válida; repetir con campos requeridos vacíos, categoría inactiva y prioridad desconocida.
**Esperado:** la solicitud válida devuelve `201`, reportante/sede del usuario, estado `pendiente` y prioridad indicada o `media`; las inválidas devuelven `400` con errores por campo y no crean registros parciales.

### CP06 - Flujo e historial
Probar las transiciones autorizadas como técnico asignado y administrador, incluida la reapertura de una incidencia cerrada a `en_proceso`; intentar una transición fuera de flujo como técnico no asignado.
**Esperado:** solo se aceptan las transiciones definidas en [02_requisitos.md](./02_requisitos.md); cada cambio guarda actor, fecha y valores anterior/nuevo; una transición inválida no modifica ni el estado ni el historial.

### CP07 - Emergencias
Consultar protocolos como usuarios de sedes distintas y como administrador con y sin filtro de sede.
**Esperado:** cada usuario ve protocolos activos de su sede; el administrador puede consultar por sede; ningún usuario no administrador puede enumerar datos de otra sede.

### CP08 - Interfaz y conectividad móvil
Desde Expo Go, iniciar/cerrar sesión, consultar y crear incidencias, consultar emergencias y simular API inaccesible o sesión expirada.
**Esperado:** la app presenta estados de carga y errores comprensibles, no filtra tokens y permite recuperar o cerrar la sesión de forma segura.
La cuenta admin también debe poder filtrar por sede/estado, asignar un técnico activo de su sede, cerrar una incidencia resuelta y reabrir una cerrada. Estas acciones deben probarse desde el móvil, además de la API.

### CP09 - Aislamiento entre organizaciones (implementación automatizada parcial)
Las pruebas automatizadas crean dos organizaciones y comprueban acceso cruzado a incidencias, usuarios y sedes, filtros por tenant, acceso global del superadministrador y bloqueo de organizaciones suspendidas. También verifican que cambiar rol/estado en una membresía no altere las otras membresías ni el estado global de la cuenta, y que solo el superadministrador pueda cambiar username, email o contraseña de otras cuentas. Ampliar cuando se agreguen pantallas, archivos, métricas o nuevos endpoints.
**Esperado:** ningún usuario organizacional accede ni modifica recursos de otra organización; el superadministrador solo obtiene acceso global por su rol autorizado.

### CP10 - Invitaciones y estado de organización (API automatizada)
Las pruebas comprueban que el código se almacena como hash, vence siete días hábiles después (Colombia, lunes-viernes, excluyendo festivos nacionales oficiales, `America/Bogota`, hora local preservada), es de un solo uso, y que los códigos expirados/revocados y organizaciones suspendidas no crean membresías. No hay todavía flujo QR/interfaz móvil; probarlo manualmente cuando exista.
**Esperado:** solo se crea una membresía autorizada; no se devuelven secretos reutilizables y los intentos fallidos no crean acceso.

### CP11 - Migración de datos a organizaciones (SQLite aprobada; MariaDB pendiente)
La prueba de migración crea sedes reales/DEMO, usuarios, superusuario, una categoría compartida y sus incidencias; verifica asignación, duplicación de categorías, membresías, rol superadmin y reversión. Aún falta ensayar en una copia representativa de MariaDB y conciliar conteos antes de producción.
**Esperado:** la prueba aislada conserva relaciones y revierte al esquema anterior; cualquier aplicación a datos operativos requiere respaldo y ensayo en MariaDB.

### CP12 - Flujos móviles por rol (implementación parcial; prueba manual pendiente)
La app ya enruta por rol, selecciona/cambia organización, envía `X-Organization-ID` y permite al superadministrador crear/activar/suspender organizaciones. Validar estos cambios en Expo Go/dispositivo. QR/vinculación visual, wizard, evidencia, GPS, radicado y métricas siguen pendientes.
**Esperado:** cada rol solo ve su flujo, los errores de permisos/red se pueden recuperar y el backend rechaza cualquier acción fuera del alcance aunque se invoque manualmente.

### CP13 - Áreas y asignación automática (no implementado)
Seguir el MVP definido en [04_modelo_datos.md](./04_modelo_datos.md): `IncidentArea` separado de `Category`, rol de membresía `resolver`, un responsable activo por combinación área/sede, asignación en backend durante la creación y rechazo explícito si falta una asignación válida. No promover técnicos existentes automáticamente.
**Esperado:** no se crea un reporte con ruta ambigua; cada caso válido se asigna a un responsable activo de la misma organización y sede, y el historial registra los cambios. Probar organización/sede cruzadas, área inactiva, resolver inactivo o de otra sede, falta de asignación, reasignación autorizada y aislamiento.

### CP14 - Arranque de prueba Expo Go (parcial; teléfono pendiente)
Arrancar API bajo `config.demo_settings`, confirmar HTTP `405` para GET al endpoint POST de login tanto en localhost como en la IP LAN, iniciar Expo con `npx.cmd expo start --clear --lan --go` en terminal interactiva y escanear su QR desde el teléfono. Iniciar sesión con cada rol DEMO y recorrer sus funciones. El QR de desarrollo de Expo es distinto del QR de invitación empresarial, cuya UI no existe.
**Resultado actual:** la base aislada se migró y sembró; GET al login devolvió `405` en localhost y desde la IP LAN del equipo. El primer proceso Expo falló con TreeFS y luego el bundle devolvió `500` al resolver el entry de Expo. Tras detener y reiniciar Metro con `npx.cmd expo start --clear --lan --go`, `/status`, el manifiesto y el bundle Android respondieron `200` (5.4 MB), también al solicitar usando la IP LAN desde el propio equipo. Las seis cuentas DEMO emitieron tokens (`200`) al espaciar las solicitudes tras un `429` de throttling en un primer intento rápido. Las pruebas de vigencia de invitación verifican siete días hábiles colombianos. Falta escanear el QR de desarrollo, cargar la app e inspeccionar los flujos en un teléfono; el acceso real desde otro dispositivo no está aún certificado.
**Esperado:** el móvil obtiene el bundle y accede al backend SQLite desde la misma LAN; usuarios, incidencias y cambios permanecen solo en la base DEMO ignorada por Git.

## 3. Criterios de aceptación
- Todos los casos aplicables pasan en backend y móvil.
- Pruebas negativas confirman que ningún rol puede eludir restricciones manipulando campos, filtros o IDs.
- Las respuestas de error no exponen contraseñas, tokens, trazas ni datos de otras sedes.
- No hay errores críticos en consola durante los flujos básicos y los cambios relevantes están cubiertos por pruebas automatizadas.

## 4. Resultados actuales
- Backend automatizado (13 de noviembre de 2026): **35 pruebas aprobadas** con `config.test_settings` y SQLite en memoria. Incluye los casos nuevos de roles/estado por membresía y asignación por rol de membresía; no modifica ni valida la base MySQL.
- Django: `manage.py check` aprobado y `makemigrations --check --dry-run` sin cambios pendientes.
- La consulta de solo lectura `showmigrations --database default` no pudo conectarse a MySQL (1045, acceso denegado); no se ejecutaron migraciones ni escrituras sobre la base local.
- Base local MariaDB 10.11.16 y smoke test de API: verificaciones históricas del 2 de noviembre, no repetidas en este cambio. No se conectó ni migró `nefijj_db`.
- Expo: `expo export --platform android` aprobado después de adaptar autenticación, selector de organización y navegación por rol. La exportación produce bundle; no se compiló ni firmó un APK.
- Entorno de prueba local (6 de noviembre): se creó `backend/nefijj-demo.sqlite3` con `config.demo_settings`; backfill/migraciones y seed aprobados, con 2 organizaciones en el backfill, 2 sedes DEMO, 6 cuentas y 5 incidencias. La API contestó `405` por GET en el endpoint POST de login en `127.0.0.1:8000` y desde la IP LAN actual del equipo. El inicio JWT devolvió `200` para las seis cuentas DEMO; el throttle limita pruebas rápidas, así que los intentos se espacian. Tras un reinicio de Metro con caché limpia, `/status`, manifiesto y bundle Android respondieron `200` (5.4 MB) tanto en localhost como en la IP LAN solicitada desde el mismo equipo. No se ha comprobado el acceso desde un teléfono.
- Pendiente: CP08 y CP12 requieren una prueba manual de los roles y flujos desde Expo Go/dispositivo físico. El bundle no sustituye la interacción real.
- Seguridad de red pendiente: durante la comprobación la regla de firewall `Django 8000` aceptaba cualquier dirección y perfil, y la Wi-Fi figuraba como `Public`. La terminal no tenía privilegios de administrador para restringirla. No considerar cerrada esta tarea hasta limitar la regla conforme a [06_seguridad.md](./06_seguridad.md).
- Dependencias móviles: el último `npm audit --omit=dev` registrado informó 5 vulnerabilidades moderadas en dependencias transitivas `glob`/`minimatch` del árbol de Expo CLI. La propuesta `npm audit fix --force` degrada Expo a `57.0.32`; no se aplicó. Repetir el audit y revisar una solución compatible antes de producción. Este resultado del 6 de noviembre reemplaza el conteo histórico de 11 alertas anotado el 2 de noviembre.
- Multiempresa: CP09, CP10 y CP11 tienen cobertura automatizada parcial en SQLite; CP12 solo se validó con exportación de bundle. Ninguno equivale a la auditoría funcional manual o al ensayo de migración en MariaDB.

La secuencia y el alcance de cada cambio están en [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md).
