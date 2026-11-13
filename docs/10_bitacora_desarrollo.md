# 10. Bitácora de implementación y operación - NEFIJJ

## 1. Propósito y alcance
Esta bitácora registra lo que se preparó en el repositorio, lo que se ejecutó en el equipo local y las tareas que todavía requieren intervención o comprobación manual. No es una guía para producción ni reemplaza los contratos de [05_api.md](./05_api.md), la política de [06_seguridad.md](./06_seguridad.md) ni las instrucciones de [07_desarrollo_backend.md](./07_desarrollo_backend.md) y [08_desarrollo_mobile.md](./08_desarrollo_mobile.md).

**No se guardan aquí contraseñas, tokens, claves, valores completos de `.env`, ni datos personales de cuentas.** Los archivos `backend/.env` y `mobile/.env.local` son configuración local ignorada por Git. No pegarlos en reportes o conversaciones.

## 2. Secuencia realizada

### Paso 1 - Revisión de documentos y estructura
1. Se revisaron los nueve documentos iniciales (`01` a `09`) y se confirmó la estructura `docs/`, `backend/` y `mobile/`.
2. Se armonizó el alcance funcional: la primera versión no incluye notificaciones push, registro público, chat ni enrutamiento automático por áreas.
3. Se aclaró que cuentas, sedes y catálogos se administran mediante Django Admin/API; no mediante un panel completo dentro de la app móvil.

### Paso 2 - Entorno Python y backend
1. Se instaló Python 3.14.10 y se creó `backend/.venv`. Python 3.15 era el único disponible inicialmente y no estaba dentro de la matriz comprobada para Django 5.2 en esta configuración.
2. Se fijaron dependencias en `backend/requirements.txt`: Django 5.2.18, Django REST Framework 3.18.3, SimpleJWT 5.5.1, mysqlclient 2.3.0, django-cors-headers 4.9.0 y python-dotenv 1.2.4.
3. Se inicializaron Django y las apps `accounts` e `incidents`, incluido el modelo de usuario propio, sedes, categorías, incidencias, eventos de historial y protocolos.
4. Se configuraron JWT, throttling de autenticación, permisos, CORS y la conexión MySQL/MariaDB por variables de entorno. La configuración de prueba usa SQLite en memoria; no se usa `nefijj_db` para los tests.
5. Se generaron las migraciones iniciales y se ejecutaron contra la base local `nefijj_db`. En la última revisión, las migraciones aparecían aplicadas y no había cambios de migración pendientes.
6. La conexión local se comprobó. `SELECT VERSION()` identificó **MariaDB 10.11.16** (no MySQL 8.0); se verificaron charset `utf8mb4` y cotejamiento `utf8mb4_unicode_ci`. Django usa el backend compatible para MySQL/MariaDB.

### Paso 3 - Cuenta administrativa y seguridad de contraseña
1. Se creó el superusuario operativo `nesmundo` con el comando de Django. Durante el alta, la primera confirmación de contraseña no coincidió; luego Django señaló que la contraseña elegida era corta y completamente numérica, y se aceptó omitir esa validación.
2. La contraseña débil se compartió posteriormente en la conversación. El usuario confirmó después que ya la cambió. **No se registra el valor de ninguna contraseña.**
3. Para cualquier alta futura, no omitir las validaciones de Django. Si una contraseña se expone, cambiarla localmente con `manage.py changepassword <usuario>`.

### Paso 4 - API y aislamiento por sedes
1. Se implementaron login y renovación JWT, administración de usuarios/sedes, listado y creación de incidencias, detalle, eventos, asignación, cambios de estado, categorías y protocolos.
2. El servidor obtiene rol, reportante y sede de la cuenta autenticada; los campos que envía el cliente no pueden asignar una incidencia a otra sede.
3. El técnico ve incidencias de su sede, pero solo cambia las que tiene asignadas. El estudiante consulta sus propios reportes. La autorización se aplica en el backend.
4. Los cambios de asignación y estado escriben eventos de auditoría dentro de transacciones.

### Paso 5 - Entorno Expo y conexión móvil
1. Se instaló Node.js LTS (26.13.0) y se creó la aplicación Expo. En PowerShell se usaron `npm.cmd`/`npx.cmd` cuando la resolución del comando o la política de scripts bloqueaba los lanzadores `.ps1`.
2. Una instalación de npm tardó varios minutos; se completó usando la caché local. Se instalaron Axios, React Navigation, SecureStore y módulos nativos compatibles con Expo.
3. La app usa Expo SDK 58 (`expo` 58.0.22), React Native 0.88.1 y React 19.3.0.
4. Inicialmente el cliente móvil apuntaba a la IP sin el prefijo `/api/v1`; eso no coincidía con las rutas del backend. Se corrigió `EXPO_PUBLIC_API_URL` para incluir el prefijo.
5. El usuario inició Django en `0.0.0.0:8000`, configuró la URL LAN en Expo y permitió el puerto de desarrollo en Windows Firewall. Se probó el login desde la app.
6. La IP `192.168.1.18` corresponde a la última lectura local, no es fija. Si cambia, actualizar `backend/.env` y `mobile/.env.local`, reiniciar Django y reiniciar Expo con `npx expo start --clear`.

### Paso 6 - Panel operativo y registros DEMO
1. Se detectó que un administrador autenticado veía una lista vacía y pocas acciones: no había incidencias sembradas y la app no tenía panel de operación administrativa.
2. Se implementó el panel operativo móvil para filtrar incidencias por sede y estado, asignar o retirar un técnico activo de la misma sede, cerrar una incidencia resuelta y reabrir una cerrada.
3. La administración móvil de cuentas, sedes, categorías y protocolos sigue fuera de alcance; se realiza con Django Admin o la API.
4. Con autorización expresa del usuario, se ejecutó `python manage.py seed_demo` contra la base local `nefijj_db`. Se agregaron de forma idempotente:
   - 2 sedes con códigos `DEMO-A` y `DEMO-B`.
   - 4 cuentas de prueba `demo_*`, sin contraseña utilizable.
   - 1 categoría `DEMO`.
   - 2 protocolos marcados como DEMO, con contacto ficticio.
   - 5 incidencias DEMO en los estados pendiente, en proceso, resuelta y cerrada, con 14 eventos de historial.
5. Se ejecutó el seed dos veces y los conteos no aumentaron. No se borraron ni modificaron registros preexistentes.
6. Los protocolos, nombres y reportes DEMO son datos de demostración: no son instrucciones reales de emergencia ni cuentas que deban utilizarse operativamente.

### Paso 7 - Arquitectura multiempresa y navegación por rol
1. Se añadieron `Organization`, `OrganizationMembership` y `OrganizationInvitation`; sedes, incidencias y categorías quedaron vinculadas a la organización. La API calcula el alcance por membresía y admite selección mediante `X-Organization-ID`.
2. Se añadieron endpoints de organizaciones, membresías e invitaciones; estas son revocables, de un uso y almacenan únicamente el hash del código. En esta continuación, la vigencia de invitaciones nuevas se cambió a siete días hábiles de Colombia (lunes-viernes, excluyendo festivos nacionales oficiales, zona `America/Bogota`, misma hora local de emisión).
3. La migración asigna sedes `DEMO-*` a `nefijj-demo` y las demás a `universidad-de-la-guajira`. Las categorías históricas utilizadas por más de una organización se duplican para evitar referencias compartidas.
4. Se detectó y corrigió un orden inválido de migraciones: el rol `superadmin` se asigna después de instalar la restricción de base de datos que lo permite.
5. La app móvil restaura y selecciona la organización activa, agrega `X-Organization-ID` a las llamadas API y separa flujos de `superadmin`, `organization_admin`, `technician` y `user`. El superadministrador puede crear, activar y suspender organizaciones.
6. La pantalla de invitación/QR, métricas, notificaciones, evidencia/GPS y la administración móvil completa siguen pendientes; la migración no se ha ensayado sobre una copia de MariaDB.

## 3. Verificaciones ejecutadas
Los registros históricos de base local y red corresponden al **2 de noviembre de 2026**. Las pruebas de código y Expo anotadas a continuación se repitieron el **6 de noviembre de 2026**; no se deben confundir con la verificación de la base MariaDB ni con una prueba manual en teléfono. El **13 de noviembre de 2026** se volvió a ejecutar la suite backend después de separar roles/estado de membresía de los datos globales de cuenta.

- Validación inicial anterior a la arquitectura multiempresa: `backend/.venv/Scripts/python.exe manage.py test accounts.tests incidents.tests --settings=config.test_settings`: **19 pruebas aprobadas** en SQLite en memoria.
- `manage.py check --settings=config.test_settings`: aprobado; `makemigrations --check --dry-run --settings=config.test_settings`: sin cambios de migración pendientes. La configuración de prueba no verifica la conexión MariaDB.
- `expo install --check`: la primera ejecución detectó dos dependencias desactualizadas; se alinearon mediante Expo CLI a `expo ~58.0.23` y `react-native-safe-area-context ~5.11.1`; el chequeo posterior pasó.
- `expo export --clear --platform android --output-dir <directorio-temporal>`: bundle Android exportado correctamente a `%TEMP%`; esto **no** genera un APK. La exportación sin `--clear` falló inicialmente al resolver una ruta reparseada de OneDrive/Metro; la caché limpia resolvió el error.
- `npm audit --omit=dev`: 5 vulnerabilidades moderadas asociadas a `glob` y `minimatch` en el árbol transitivo de Expo CLI. La corrección sugerida con `--force` bajaría Expo a `57.0.32`; no se aplicó.
- La conexión MariaDB 10.11.16, charset/cotejamiento y estado de migraciones se verificaron el 2 de noviembre, no durante esta auditoría.
- El smoke test autenticado de solo lectura y los conteos de datos DEMO son del 2 de noviembre; no se repitieron.
- CP08 en dispositivo físico y prueba de carga siguen pendientes. La exportación de bundle no sustituye ninguno de esos casos.
- El chequeo del bundle no equivale a compilar/firmar un APK ni a instalarlo en dispositivo.
- `git diff --check` y validación de enlaces/fences Markdown: aprobados en esta auditoría.
- En una verificación posterior de esta implementación: **29 pruebas backend aprobadas** en SQLite en memoria; `manage.py check` aprobado; `makemigrations --check --dry-run` sin cambios; prueba explícita de backfill y reversión aprobada.
- El 13 de noviembre: **35 pruebas backend aprobadas** con `config.test_settings` y SQLite en memoria; `manage.py check` aprobado; `makemigrations --check --dry-run` sin cambios. Se comprobó que los cambios de rol/estado afectan solo la membresía seleccionada, que un administrador organizacional no puede cambiar datos globales de cuenta y que la asignación de técnicos usa el rol de la membresía.
- En esa misma revisión, la consulta de solo lectura `showmigrations --database default` falló con MySQL 1045 (acceso denegado para la configuración local actual). No se leyeron registros de negocio ni se ejecutaron migraciones/escrituras en MySQL; volver a validar cuando se corrija localmente la conexión.
- El bundle Android se exportó de nuevo después de los cambios de rol y tenant. No es APK; no se hizo validación manual en teléfono.
- Para preparar pruebas manuales se creó y migró `backend/nefijj-demo.sqlite3` con `config.demo_settings`: el backfill creó dos organizaciones y el seed pobló la organización DEMO con dos sedes, seis cuentas y cinco incidencias ficticias. Se configuró la URL LAN local `192.168.1.23` en `mobile/.env.local`. No se conectó ni migró `nefijj_db`.
- Una petición GET al endpoint de login devolvió HTTP 405 en localhost y desde la IP LAN del equipo, consistente con una ruta que acepta POST; esto confirma acceso HTTP a la ruta, no un inicio de sesión correcto. El primer proceso Expo se cerró con `TreeFS: Failed to make parent directory entry`; además, una primera solicitud del bundle devolvió `500` porque Metro no resolvió el entry de Expo. PowerShell bloqueó `npx.ps1`; se detuvo el proceso y se reinició con `npx.cmd expo start --clear --lan --go`. El servidor nuevo contestó `200` en `/status`, el manifiesto y el bundle Android (`200`, 5.4 MB), solicitados por localhost y por la IP LAN desde el propio equipo. El QR no apareció en la salida no interactiva y todavía no se escaneó ni hay validación visual en teléfono.
- La autenticación JWT de las seis cuentas DEMO respondió `200` con access y refresh. Un primer lote demasiado rápido alcanzó `429` de throttling en la sexta solicitud; se repitió espaciando los intentos y los seis logins aprobaron sin desactivar ni modificar el límite. La contraseña temporal no se guardó en los documentos.

Estas verificaciones no equivalen a certificar funcionamiento visual completo en un teléfono ni a una prueba de carga.

## 4. Red y firewall: estado que no debe darse por resuelto
En la última inspección local:

- `backend/.env` tenía `DJANGO_DEBUG=True` y se corrigió `DJANGO_ALLOWED_HOSTS` para contener `127.0.0.1`, `localhost` y la IP LAN observada `192.168.1.18`, sin comodín `*`.
- El Wi-Fi de Windows figuraba como perfil `Public`.
- La regla de entrada existente `Django 8000` estaba habilitada para cualquier perfil y dirección remota.
- La terminal utilizada no tenía privilegios de administrador; **no se confirmó que la regla de firewall se haya restringido**.
- El servidor de desarrollo estaba escuchando en el puerto TCP 8000 y la API respondió durante el smoke test. La disponibilidad puede cambiar al cerrar su terminal.
- La dirección `192.168.1.23` usada por la configuración local DEMO el 6 de noviembre de 2026 no es fija y puede diferir de la IP histórica `192.168.1.18`. Volver a detectar la IP antes de conectar un teléfono; confirmar también que la terminal del servidor siga activa.

Si la Wi-Fi es de confianza y el usuario decide marcarla privada, abrir PowerShell como administrador y revisar cuidadosamente la red antes de ejecutar:

```powershell
Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private
Set-NetFirewallRule -DisplayName "Django 8000" -Profile Private
Get-NetFirewallRule -DisplayName "Django 8000" |
  Get-NetFirewallAddressFilter |
  Set-NetFirewallAddressFilter -RemoteAddress LocalSubnet
```

No ejecutar el primer comando en redes públicas, institucionales compartidas o no confiables. La ejecución requiere privilegios de administrador. Después, revisar que la regla aplique solo a `Private` y `LocalSubnet`. No abrir el puerto a Internet. Para producción, no utilizar `runserver`, `DEBUG=True`, HTTP ni esta regla de desarrollo.

## 5. Pendientes
1. Corregir localmente las credenciales de `backend/.env` y repetir la inspección de solo lectura de migraciones MySQL; no imprimir ni compartir los valores del archivo.
2. Confirmar con permisos elevados que el firewall está limitado al perfil privado y a `LocalSubnet`, siempre que la red sea de confianza.
3. Ejecutar CP08 manualmente en el teléfono: login, lista, filtros de admin, asignación, cierre/reapertura, protocolos, cierre de sesión, sesión expirada y pérdida de red.
4. Mantener la contraseña actual del superusuario fuerte, única y fuera del repositorio/chat; no escribirla en bitácoras.
5. Repetir `npm audit --omit=dev` (el último resultado registrado fue de 5 vulnerabilidades moderadas) y encontrar una actualización compatible. No ejecutar `npm audit fix --force`: el arreglo automático implicaría degradar Expo a SDK 57. Evaluar alternativas antes de producción.
6. Antes de desplegar, configurar un entorno de producción aparte: `DEBUG=False`, dominio en `DJANGO_ALLOWED_HOSTS`, HTTPS, secretos gestionados de forma segura, CORS limitado si aplica y servidor de aplicación de producción.
7. Ensayar el backfill y reversión sobre una copia representativa de MariaDB, conciliando sedes, incidencias, categorías y membresías; no aplicar aún las migraciones a `nefijj_db`.
8. Arrancar Metro con `npx.cmd expo start --clear --lan --go` desde una terminal interactiva. Si reaparece el error TreeFS de OneDrive, investigar el watcher/ruta y probar el workspace fuera de OneDrive antes de declarar estable Expo Go. Escanear el QR de desarrollo y validar en dispositivo los cuatro roles y su acceso real a la API DEMO.
9. Completar auditoría de endpoints y agregar bitácora de cambios de organización/membresía antes de producción.
10. Diseñar e implementar áreas/departamentos separadas de categorías, con asignación automática determinista y pruebas del responsable activo, sede, organización y caso sin asignación.
11. Construir la UI de invitación/QR empresarial (diferente del QR de Expo), probar la lectura/aceptación y los límites de expiración; implementar métricas solo después de especificar sus definiciones.

## 6. Documentos relacionados
- [01_propuesta.md](./01_propuesta.md): alcance y estado del producto.
- [05_api.md](./05_api.md): rutas y permisos de API.
- [06_seguridad.md](./06_seguridad.md): reglas de seguridad y operación de red.
- [07_desarrollo_backend.md](./07_desarrollo_backend.md): preparación y ejecución de Django.
- [08_desarrollo_mobile.md](./08_desarrollo_mobile.md): Expo, IP de API y flujos móviles.
- [09_pruebas.md](./09_pruebas.md): escenarios y resultados de validación.

## 7. Arquitectura multiempresa y flujos por rol
**Estado: backend implementado con pruebas automatizadas; app móvil parcial; migración y UX manual no certificadas.** La arquitectura por sedes se amplió con organizaciones. Los requisitos que no cuentan con endpoints o pantallas se mantienen explícitamente como pendientes.

### 7.1 Objetivo y alcance
Separar datos de varias organizaciones con autorización en el servidor y experiencias distintas según el rol. Los contextos actuales son:

1. **Superadministrador de plataforma (`superadmin`):** acceso global y gestión básica de organizaciones (alta/activación/suspensión). Las métricas globales aún no existen.
2. **Administrador de organización (`organization_admin`):** acceso restringido por membresía. Administra incidencias y, vía API/Django Admin, otros recursos de su organización; las pantallas móviles completas siguen pendientes.
3. **Técnico (`technician`):** rol operativo de una membresía, limitado a su sede y a incidencias asignadas para cambios de estado.
4. **Usuario final (`user`):** reporta y consulta únicamente sus incidencias. Puede tener varias membresías; la app permite seleccionar el tenant. La interfaz de invitación/QR aún no existe.

Solo `is_superuser` concede el alcance global de plataforma. La UI no sustituye la autorización del backend.

### 7.2 Modelo de datos requerido
- `Organization` tiene nombre, slug, estado y marcas de tiempo.
- `OrganizationMembership` asocia usuario, organización, rol, estado y sede opcional; admite varias organizaciones por usuario.
- `OrganizationInvitation` guarda hash de código aleatorio, creador, vencimiento, revocación y uso único. La vigencia actual para nuevas invitaciones es de siete días hábiles de Colombia; los registros existentes conservan su expiración almacenada.
- `Location`, `Incident` y `Category` tienen pertenencia organizacional; las categorías son únicas dentro de su organización. Protocolos se limitan a través de su sede.
- Backfill: `DEMO-*` se asigna a `nefijj-demo`; otras sedes a `universidad-de-la-guajira`. Usuarios/admins heredados y datos relacionados se asignan explícitamente; las categorías compartidas se duplican.
- La prueba de migración en SQLite verifica asignación y reversión. Falta un ensayo con respaldo/datos históricos representativos en MariaDB. No modificar la base persistente hasta completar ese ensayo.

### 7.3 Autorización y API
- Resolver en el servidor las organizaciones accesibles para el usuario autenticado. Todo listado, detalle, búsqueda, filtro, actualización, exportación y agregado estadístico debe respetar ese alcance.
- No confiar en `organization_id`, rol, asignación, reportante ni estado enviados por el cliente para conceder acceso. Para un administrador organizacional, una organización solicitada solo es válida si forma parte de sus membresías autorizadas.
- El superadministrador puede crear organizaciones y cambiar su estado; las métricas globales no están implementadas.
- El administrador organizacional ve y gestiona únicamente sus incidencias; puede asignar responsables locales, usar filtros por estado, fecha y severidad, y administrar sus protocolos y notificaciones.
- El usuario final solo crea reportes dentro de una organización a la que pertenece o que haya seleccionado después de vincularse, y solo consulta sus propios reportes.
- Rutas implementadas: gestión de organizaciones, `/organizations/mine/`, invitaciones, aceptación de membresía y recursos operativos; los contratos exactos están en `05_api.md`.
- Los endpoints filtran por membresía y validan tenant; existe cobertura de aislamiento para incidencias, usuarios y sedes. Falta una revisión completa de todos los endpoints y registro de auditoría organizacional.

### 7.4 Experiencias implementadas y pendientes
**Superadministrador — React Native**
- Implementado: listado, creación y activación/suspensión de organizaciones.
- Pendiente: indicadores globales, comparación analítica y panel web.

**Administrador de organización**
- Implementado: panel de incidencias con filtros existentes y asignación/estado dentro de la organización activa; endpoints de personal/sedes/categorías/protocolos e invitaciones.
- Pendiente en móvil: gestión completa de personal, sedes, protocolos, generación/revocación visible de códigos QR e indicadores/gráficas. No hay entrega de notificaciones push.

**Técnico y usuario final — React Native**
- Implementado: navegación por rol, selector/cambio de tenant, envío de `X-Organization-ID`, lista de incidencias, protocolos y formulario de reporte existente.
- Pendiente: interfaz de aceptación de invitación, cámara/QR, evidencia fotográfica/video, GPS, wizard de tres pasos y radicado.

### 7.5 Secuencia y criterios de aceptación
1. **Completado en código:** modelos, migraciones, endpoints, permisos organizacionales, pruebas de aislamiento y selector/navegación móvil inicial.
2. **Validado en SQLite:** backfill, aislamiento de categorías, membresías y reversión. La migración no está aprobada para MariaDB hasta ensayarse en una copia/restauración.
3. **Pendiente:** revisar cada endpoint, decidir acceso del superadministrador a organizaciones suspendidas y añadir auditoría de cambios organizacionales.
4. **Pendiente:** implementar UI móvil de invitación/QR, administración organizacional completa, analíticas y notificaciones solo si se definen sus requisitos.
5. **Pendiente:** validar en un teléfono físico y cubrir permisos de cámara/GPS cuando se implemente evidencia.

La arquitectura no se considera lista para producción hasta que el aislamiento se pruebe de forma exhaustiva, la migración se ensaye en MariaDB, las pantallas se validen en dispositivo y se resuelvan los pendientes de seguridad/red documentados en esta bitácora.

## 8. Resultado de auditoría de la propuesta recibida
La auditoría inicial identificó una especificación repetida y mezclada con el estado entonces existente. Se conserva un solo contrato en esta sección y los documentos técnicos; esta tabla resume el estado actualizado de la implementación.

| Tema | Evidencia comprobada | Decisión documental |
|---|---|---|
| Roles y alcance | La migración conserva el rol global superadmin y usa membresías por organización para `organization_admin`, `technician` y `user`. | Roles y permisos organizacionales implementados; se necesita ampliar pruebas de auditoría de cada endpoint antes de producción. |
| API / aislamiento | Existen endpoints y filtros de organización; la suite comprueba acceso cruzado a incidencias, usuarios y sedes. | No afirmar aislamiento integral de todos los futuros recursos; revalidar cuando se agreguen endpoints o datos nuevos. |
| Paneles y QR | La app permite al superadmin crear/activar/suspender organizaciones; invitaciones existen en API, pero no en UI. | Mantener como pendientes métricas globales, QR y gestión móvil completa. |
| Áreas y responsables | Hay categorías de incidencias y asignación manual de técnicos; no hay entidad de área ni enrutamiento automático. | Mantenerlo como fase futura: categoría describe el tipo de incidencia; el área selecciona el equipo/responsable. Definir su relación con sede, miembros activos y falta de responsable antes de implementar. |
| Navegación móvil actual | `AppNavigator` diferencia superadmin, administrador organizacional, técnico y usuario; soporta selector de organización. | El bundle compila. La UX todavía requiere prueba manual en dispositivo y la UI de organización suspendida/invitaciones necesita validación. |
| Reporte móvil | Existe un formulario simple; no hay wizard de tres pasos, cámara/video, GPS ni número de radicado. | No llamar implementado al reporte dinámico. Antes de construirlo, definir carga/almacenamiento de archivos, permisos, retención y privacidad de ubicación. |
| Analítica y notificaciones | No se encontraron gráficas de analítica ni entrega de notificaciones. | Conservarlas como requisitos futuros; especificar métricas, canales, consentimiento y operación antes de incorporarlas. |
| Controles redundantes o inseguros | La propuesta sugería modificar directamente la base para asignar roles; esto puede eludir validaciones y auditoría. | No recomendar cambios directos en SQL. Aún falta una bitácora completa de cambios de organización/membresía y una revisión exhaustiva de todos los endpoints. |
| Instalador Android | La exportación probada generó un bundle JS/estático, no un artefacto `.apk`. | Retirar la promesa de APK “100 % gratis”; un APK firmado requiere build y configuración Android. El servicio alojado puede tener límites/costos. |
| Consola superadmin y clientes | Existe Django Admin y una utilidad móvil básica de superadmin; no hay dashboard web de métricas. | Usar Django Admin como consola web del MVP y una sola app operativa. No crear un APK superadmin independiente sin necesidad funcional validada. |
| Invitaciones y vigencia | La API de invitaciones implementa token de uso único, revocable y siete días hábiles de Colombia para las nuevas invitaciones; no hay QR ni flujo móvil. | Se cuentan lunes-viernes, excluyendo festivos nacionales oficiales, en `America/Bogota`; se conserva la hora local y el conteo inicia el día hábil siguiente. |
| Base de datos | El entorno local se verificó históricamente con MariaDB 10.11.16 compatible con el backend MySQL; las pruebas y el seed DEMO usan SQLite aislado. | No instalar MySQL 8.0.46 ni migrar la base por recomendación documental. Primero ensayar las migraciones sobre una copia representativa y documentar la razón técnica para cualquier cambio de motor. |

La auditoría se limitó al código y documentos presentes en el repositorio y a los comandos anotados en la sección 3. No se revisó una instancia de producción ni se certificaron firewall, usabilidad en dispositivo, carga, costos de EAS o seguridad integral.

## 9. Herramientas utilizadas y propósito
Versiones históricas se conservan solo cuando constan en el registro o se pudieron confirmar. La columna de estado distingue las verificaciones repetidas de las documentadas anteriormente.

| Herramienta | Uso en NEFIJJ | Evidencia / estado |
|---|---|---|
| Python | Ejecutar Django, dependencias y pruebas del backend. | Esta verificación se ejecutó con Python 3.15 y Django 5.2.18; no constituye por sí sola una certificación de la matriz de soporte. |
| `pip` | Instalar las dependencias Python fijadas para el backend desde `requirements.txt`. | En esta continuación se instalaron porque el intérprete seleccionado no tenía Django; no se modificó el manifiesto. |
| Django y Django REST Framework | Modelos, autenticación, permisos, endpoints, migraciones y administración del backend. | Dependencias fijadas en `backend/requirements.txt`; endpoints y modelos en `backend/accounts/` y `backend/incidents/`. |
| SimpleJWT | Emisión y renovación de tokens JWT. | Dependencia y rutas presentes; prueba automatizada de autenticación aprobada. |
| MariaDB con XAMPP y `mysqlclient` | Base persistente del entorno local de desarrollo. | MariaDB 10.11.16 y `utf8mb4` verificados históricamente el 2 de noviembre; no se reconectó durante esta auditoría. |
| SQLite en memoria | Aislar las pruebas automatizadas para no tocar `nefijj_db`. | `config.test_settings`; 29 pruebas aprobadas, incluidas migración, reversión e invitaciones expiradas/revocadas. |
| SQLite DEMO en archivo | Preparar datos ficticios persistentes para probar la API móvil sin depender de MariaDB. | `config.demo_settings` + `seed_demo`; base aislada `backend/nefijj-demo.sqlite3`, ignorada por Git. Logins habilitados con contraseña aleatoria temporal impresa en la terminal, no guardada en la documentación. |
| `holidays` | Consultar días festivos oficiales de Colombia para calcular expiración de invitaciones en días hábiles. | Dependencia fijada `holidays==0.108`; probada con fechas de diciembre de 2026 y enero de 2027 que incluyen Navidad y Año Nuevo. |
| Node.js y npm | Runtime y gestión de paquetes de la aplicación móvil. | Node.js 26.13.0 y npm 11.20.0 confirmados el 6 de noviembre. |
| React Native y Expo | Aplicación móvil, ejecución en desarrollo y exportación del bundle Android. | `mobile/package.json`; bundle Android servido por Metro con HTTP 200 después de reiniciar con caché limpia. Falta mostrar/leer el QR Expo en terminal interactiva y probar en dispositivo. |
| Axios, React Navigation y Expo SecureStore | Cliente HTTP, navegación móvil y almacenamiento seguro de tokens. | Dependencias y usos presentes en `mobile/src/`. |
| Expo CLI (`npx.cmd`) | `expo install --check` verifica compatibilidad; `expo export --platform android` genera el bundle; `expo start --lan --go` inicia el cliente de desarrollo. | El chequeo de dependencias y la exportación pasaron históricamente. Tras el fallo inicial de TreeFS y el bloqueo de `npx.ps1`, el proceso nuevo iniciado con `npx.cmd` y caché limpia sirvió manifiesto y bundle Android con HTTP 200. Falta validación en teléfono. |
| Visual Studio Code | Editor/workspace del proyecto y selección del intérprete Python del backend. | Usado como entorno de trabajo; esto no implica que se hayan ejecutado extensiones adicionales. |
| PowerShell | Ejecutar comandos locales de Windows, Django, Expo y configuración de red. | Entorno operativo usado; los comandos de firewall requieren elevación y siguen pendientes. |
| Biblioteca estándar `urllib` de Python | Hacer solicitudes HTTP locales a la API DEMO y comprobar emisión JWT sin mostrar la contraseña temporal ni imprimir tokens. | Se verificó `GET` esperado `405`, estado de Metro `200` y login `200` de seis cuentas. Un intento rápido fue limitado con `429`; el lote espaciado aprobó. |
| Git | Revisar cambios, estado del repositorio y whitespace (`git diff --check`). | Usado durante la auditoría. Los cambios preexistentes del usuario no se han descartado ni confirmado. |
| Expo Go | Cargar en el teléfono el bundle de desarrollo a partir del QR que genera Expo CLI. | Aún no se escaneó el QR. Expo Go no genera el QR empresarial ni enlaza una cuenta a una organización. |
| `curl.exe` | Comprobar respuestas HTTP de Metro y del API DEMO sin descargar/imprimir el bundle. | Verificados Metro `/status` (`200`), bundle Android (`200`, 5.4 MB) y ruta GET del login (`405`, esperado). |

`npm audit --omit=dev` se ejecutó y reportó cinco vulnerabilidades moderadas; EAS Build, Gradle local, un emulador Android y pruebas automáticas JavaScript no se usaron. No se añade infraestructura de test móvil redundante: primero se deben cerrar los flujos objetivo y después seleccionar una estrategia automatizada adecuada.
