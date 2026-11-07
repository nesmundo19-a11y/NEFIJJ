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
Las pruebas automatizadas crean dos organizaciones y comprueban acceso cruzado a incidencias, usuarios y sedes, filtros por tenant, acceso global del superadministrador y bloqueo de organizaciones suspendidas. Ampliar cuando se agreguen pantallas, archivos, métricas o nuevos endpoints.
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
**Resultado actual:** la SQLite DEMO se migró y sembró. El 6 de noviembre se inició su API con `config.demo_settings` en el puerto `8001`, dejando intacto el backend que ya usaba el puerto `8000`. Los logins de `demo_superadmin`, `demo_admin`, `demo_estudiante_a` y `demo_tecnico_a` fueron aceptados; sus listados de incidencias devolvieron 5, 5, 4 y 4 registros respectivamente. Organizaciones, categorías y emergencias respondieron `200` con 2, 1 y 2 registros. Expo se inició con `.env.local` apuntando a `http://192.168.1.5:8001/api/v1`; Metro `/status` respondió `200` por localhost y LAN, y el bundle Android respondió `200` (5.4 MB) con la URL correcta de API incluida. La dirección del proyecto para Expo Go es `exp://192.168.1.5:8081`. El backend DEMO y Metro permanecen activos para la sesión; falta la validación visual desde el teléfono, y se debe volver a comprobar la IP LAN si cambia.

### CP15 - Integración de lectura y escritura MySQL (prueba API aprobada; prueba móvil pendiente)
Conectar Expo Go al servidor que use `config.settings` y `nefijj_db`, nunca a `config.demo_settings`. La introspección confirmó las tablas requeridas después de la reparación controlada.

**Aceptación:** (1) login de una cuenta existente con hash válido; (2) listado y detalle que coinciden con registros existentes en MySQL; (3) alta de una cuenta por un administrador permitido, con membresía y sede/organización coherentes y contraseña guardada como hash; (4) cambio de contraseña del usuario autenticado tras validar la contraseña actual y los validadores de Django; (5) creación de incidencia autenticada, consulta posterior del registro por API y confirmación de persistencia con una consulta SQL de solo lectura; (6) aislamiento verificado para organización y sede; (7) si se prueba evidencia, ruta relativa en MySQL y archivo disponible bajo `media/`. Las escrituras de validación deben ser explícitamente autorizadas y, si son temporales, limpiarse solo por IDs exactos.

**Avance:** se verificó la conexión a `nefijj_db` en MariaDB 10.4.32, puerto 3308. Se creó y verificó respaldo fuera del repositorio (12,633 bytes). Se añadieron `django_migrations`, tablas nativas de `contenttypes`, `auth` y `sessions`; se reconciliaron las migraciones de negocio ya presentes sin repetir sus DDL/backfills y se creó la migración correctiva de eventos/protocolos. El historial final muestra `contenttypes`, `auth`, `sessions`, `accounts` e `incidents` hasta `0004` como aplicadas. Lecturas autenticadas devolvieron HTTP 200 para categorías (2), incidencias (2), emergencias (0) y organizaciones (1).

Con autorización se completó una prueba temporal por API: un administrador organizacional autenticado con JWT generado localmente creó un usuario (HTTP 201); el usuario inició sesión (HTTP 200), cambió su propia contraseña (HTTP 204) y volvió a iniciar sesión con la nueva (HTTP 200). Con esa sesión se creó una incidencia (HTTP 201), se leyó por API (HTTP 200) y se verificaron en MariaDB la incidencia, el usuario/membresía y su evento. Se borraron exclusivamente la cuenta temporal, su membresía, la incidencia y el evento; consultas posteriores confirmaron cero filas de prueba. Esto no valida la contraseña de una cuenta preexistente, la interacción móvil ni el envío de imágenes.

La limpieza mediante `User.delete()` no pudo completarse porque falta la tabla `django_admin_log`; la transacción se revirtió y los registros temporales se inspeccionaron y eliminaron de forma directa y acotada, verificando antes las claves foráneas. No se creó la tabla ni se hizo otra modificación de esquema. Después se inició Expo/Metro y se comprobó HTTP 200 en `/status` por localhost y LAN. Django rechazó inicialmente solicitudes con `DisallowedHost` para `192.168.1.5`; se añadió la IP a `DJANGO_ALLOWED_HOSTS`, se reinició el servidor y la ruta de login respondió `405` por LAN a GET, como se espera. Esto no sustituye la interacción visual/funcional desde el teléfono. No se guardan credenciales ni contraseñas temporales en documentación.
**Esperado:** el móvil obtiene el bundle y accede al backend SQLite desde la misma LAN; usuarios, incidencias y cambios permanecen solo en la base DEMO ignorada por Git.

### CP16 - Fotos, categorías y experiencia visual (implementado; prueba en teléfono pendiente)
Expo permite tomar/seleccionar, previsualizar y adjuntar JPG/PNG de hasta 10 MB; la API valida tamaño/resolución/formato, almacena fuera de MySQL y devuelve evidencia solo mediante endpoint autenticado dentro del alcance del incidente. La pantalla móvil permite administrar categorías y se mejoraron formularios y tarjetas. El bundle Android se exportó correctamente; falta comprobar permisos de cámara/galería, carga/descarga y roles en un dispositivo real. La persistencia de foto en MySQL requiere un ensayo autorizado y limpiar solo el recurso temporal exacto.

**Aceptación de evidencia:** probar cámara/galería, cancelación, previsualización, tamaño y formato permitido, envío multipart, errores/reintento, ruta relativa guardada y archivo disponible; confirmar que solo usuarios autorizados pueden consultar la imagen. Ensayar con SQLite primero y, para escritura en MySQL, usar autorización y limpieza de un registro temporal exacto.

**Aceptación de categorías:** como administrador autorizado, listar, crear, editar y desactivar una categoría en el tenant activo; confirmar que se refleja en el formulario de reporte y que usuarios de otra organización no pueden verla ni modificarla. Probar formularios vacíos, duplicados y categorías inactivas. CRUD y aislamiento API tienen pruebas automatizadas.

**Aceptación visual:** revisar cada rol en un dispositivo real y validar navegación, legibilidad, contraste, accesibilidad, formularios, carga, estados vacío/error/éxito, conectividad intermitente y que errores/API no revelen secretos ni datos fuera del tenant.

### CP17 - Avisos informativos de sismos del SGC (integración pendiente)
Contrato acordado: eventos sísmicos ya publicados por el SGC (no alerta temprana), push a todos los dispositivos registrados, sin acuse, entrega solo con internet y área del aviso según la fuente. Falta un endpoint/feed oficial verificable: la página principal proporcionada no basta para implementar ingestión. Push requiere development build, no Expo Go. Se autorizó generar código de esquema/migración, pero no ejecutar ni aplicar cambios en MySQL.

Antes de habilitar: verificar fuente y formato oficiales; probar deduplicación, normalización, fallos y reintentos, avisos de prueba claramente rotulados, registro/revocación de tokens, permisos denegados, dispositivos no disponibles y expiración/actualizaciones según la fuente. No prometer entrega garantizada ni sustituir los canales oficiales. No se debe mostrar un catálogo como alerta temprana.

## 3. Criterios de aceptación
- Todos los casos aplicables pasan en backend y móvil.
- Pruebas negativas confirman que ningún rol puede eludir restricciones manipulando campos, filtros o IDs.
- Las respuestas de error no exponen contraseñas, tokens, trazas ni datos de otras sedes.
- No hay errores críticos en consola durante los flujos básicos y los cambios relevantes están cubiertos por pruebas automatizadas.

## 4. Resultados actuales
- Validación actual (6 de noviembre): 42 pruebas del backend aprobadas en SQLite; `manage.py check` aprobado; exportación Android Expo aprobada. Incluye carga multipart, límite de 10 MB, acceso autenticado a evidencia y verificación de que `/media/` no se resuelve como ruta pública. El `makemigrations --check --dry-run` reporta cambios de opciones `Meta`; no se generaron/aplicaron migraciones de modelo.
- MySQL: respaldo verificado; migraciones nativas y reconciliación del historial de negocio completadas bajo autorización. La migración `incidents.0004` creó únicamente las tablas faltantes de eventos/protocolos. Lectura autenticada y prueba controlada de alta/login/cambio de contraseña/creación y lectura de incidencia aprobadas; datos temporales limpiados y ausencia verificada. La limpieza ORM de usuarios requiere resolver la tabla `django_admin_log` faltante.
- Backend automatizado: el conteo histórico de 29 pruebas corresponde a una validación anterior; la suite completa más reciente tiene **42 pruebas aprobadas** con `config.test_settings` y SQLite en memoria, incluidas evidencia fotográfica, límite de tamaño, acceso protegido, categorías, aislamiento multiorganización, invitaciones y backfill con reversión.
- Django: `manage.py check` aprobado y `makemigrations --check --dry-run` sin cambios pendientes.
- Base local MariaDB 10.11.16 y smoke test de API: verificaciones históricas del 2 de noviembre, no repetidas en este cambio. No se conectó ni migró `nefijj_db`.
- Expo: `expo export --platform android` aprobado después de adaptar autenticación, selector de organización y navegación por rol. La exportación produce bundle; no se compiló ni firmó un APK.
- Entorno de prueba local (6 de noviembre): se creó `backend/nefijj-demo.sqlite3` con `config.demo_settings`; backfill/migraciones y seed aprobados, con 2 organizaciones en el backfill, 2 sedes DEMO, 6 cuentas y 5 incidencias. La API contestó `405` por GET en el endpoint POST de login en `127.0.0.1:8000` y desde la IP LAN actual del equipo. El inicio JWT devolvió `200` para las seis cuentas DEMO; el throttle limita pruebas rápidas, así que los intentos se espacian. Tras un reinicio de Metro con caché limpia, `/status`, manifiesto y bundle Android respondieron `200` (5.4 MB) tanto en localhost como en la IP LAN solicitada desde el mismo equipo. No se ha comprobado el acceso desde un teléfono.
- Pendiente: CP08, CP12, CP14 y CP16 requieren comprobación manual de roles y flujos desde Expo Go/dispositivo físico. CP17 espera un endpoint/feed oficial verificable del SGC y después requerirá development build y configuración de credenciales push. El bundle y la respuesta LAN no sustituyen la interacción real.
- Seguridad de red pendiente: durante la comprobación la regla de firewall `Django 8000` aceptaba cualquier dirección y perfil, y la Wi-Fi figuraba como `Public`. La terminal no tenía privilegios de administrador para restringirla. No considerar cerrada esta tarea hasta limitar la regla conforme a [06_seguridad.md](./06_seguridad.md).
- Dependencias móviles: el último `npm audit --omit=dev` registrado informó 5 vulnerabilidades moderadas en dependencias transitivas `glob`/`minimatch` del árbol de Expo CLI. La propuesta `npm audit fix --force` degrada Expo a `57.0.32`; no se aplicó. Repetir el audit y revisar una solución compatible antes de producción. Este resultado del 6 de noviembre reemplaza el conteo histórico de 11 alertas anotado el 2 de noviembre.
- Multiempresa: CP09, CP10 y CP11 tienen cobertura automatizada parcial en SQLite; CP12 solo se validó con exportación de bundle. Ninguno equivale a la auditoría funcional manual o al ensayo de migración en MariaDB.

La secuencia y el alcance de cada cambio están en [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md).
