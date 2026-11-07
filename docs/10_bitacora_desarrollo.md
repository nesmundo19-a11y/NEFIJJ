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
5. El registro histórico documenta que las migraciones iniciales se ejecutaron contra la base local `nefijj_db`. Para la base heredada actual, ese antecedente no sustituye una comprobación reciente de `django_migrations` ni confirma que el esquema físico coincida con las migraciones.
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
Los registros históricos de base local y red corresponden al **2 de noviembre de 2026**. Las pruebas de código y Expo anotadas a continuación se repitieron el **6 de noviembre de 2026**; no se deben confundir con la verificación de la base MariaDB ni con una prueba manual en teléfono.

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
1. Confirmar con permisos elevados que el firewall está limitado al perfil privado y a `LocalSubnet`, siempre que la red sea de confianza.
2. Ejecutar CP08 manualmente en el teléfono: login, lista, filtros de admin, asignación, cierre/reapertura, protocolos, cierre de sesión, sesión expirada y pérdida de red.
3. Mantener la contraseña actual del superusuario fuerte, única y fuera del repositorio/chat; no escribirla en bitácoras.
4. Repetir `npm audit --omit=dev` (el último resultado registrado fue de 5 vulnerabilidades moderadas) y encontrar una actualización compatible. No ejecutar `npm audit fix --force`: el arreglo automático implicaría degradar Expo a SDK 57. Evaluar alternativas antes de producción.
5. Antes de desplegar, configurar un entorno de producción aparte: `DEBUG=False`, dominio en `DJANGO_ALLOWED_HOSTS`, HTTPS, secretos gestionados de forma segura, CORS limitado si aplica y servidor de aplicación de producción.
6. Ensayar el backfill y reversión sobre una copia representativa de MariaDB, conciliando sedes, incidencias, categorías y membresías; no aplicar aún las migraciones a `nefijj_db`.
7. Arrancar Metro con `npx.cmd expo start --clear --lan --go` desde una terminal interactiva. Si reaparece el error TreeFS de OneDrive, investigar el watcher/ruta y probar el workspace fuera de OneDrive antes de declarar estable Expo Go. Escanear el QR de desarrollo y validar en dispositivo los cuatro roles y su acceso real a la API DEMO.
8. Revisar la autorización de lecturas del superadministrador sobre organizaciones suspendidas y agregar auditoría de cambios de organización/membresía antes de producción.
9. Diseñar e implementar áreas/departamentos separadas de categorías, con asignación automática determinista y pruebas del responsable activo, sede, organización y caso sin asignación.
10. Construir la UI de invitación/QR empresarial (diferente del QR de Expo), probar la lectura/aceptación y los límites de expiración; implementar métricas solo después de especificar sus definiciones.

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

## 10. Comprobación pendiente de migraciones y carga de evidencia
En la revisión inicial del 6 de noviembre de 2026 se aclaró que `nefijj_db` es una base MySQL/MariaDB heredada, con tablas y datos ya existentes, y que no se debe ejecutar `migrate` a ciegas. Se corrigieron los argumentos de restricciones de las migraciones de `accounts` a `check=`, compatibles con Django 4.2, y se verificó la importación de esos módulos bajo la configuración de pruebas. En la continuación descrita en la sección 11 se inspeccionó y reparó de forma acotada el desfase entre el historial y las tablas nativas.

Antes de decidir cualquier acción sobre el esquema, consultar `showmigrations --database default` o leer `django_migrations` con las consultas de solo lectura incluidas en [07_desarrollo_backend.md](./07_desarrollo_backend.md), y comparar el resultado con las tablas/columnas reales. Ese historial todavía debe verificarse por el operador; no asumir que las migraciones están aplicadas ni usar `--fake` sin comprobar equivalencia y contar con respaldo.

Los modelos incluyen `evidence_image` opcional, `MEDIA_ROOT`/`MEDIA_URL` están configurados y la vista de incidencias admite JSON y multipart. El serializador limita categorías a la organización activa. Se agregaron pruebas de imagen válida, archivo inválido y categoría de otro tenant. La columna `incidents_incident.evidence_image` se confirmó en la base heredada. La suite completa de 35 pruebas pasa con `config.test_settings` y SQLite; esto no valida las tablas faltantes en MySQL.

## 11. Desfase de tablas nativas y tablas heredadas
Se identificó un desfase en `nefijj_db`: las tablas de negocio de `accounts` e `incidents` ya existían y sus migraciones se marcaron como aplicadas (`--fake`), mientras faltaban tablas nativas de Django, en particular `django_content_type`. El hecho de tener las migraciones de negocio registradas no crea las tablas de `contenttypes`, `auth` o `sessions`.

Se confirmó que la configuración `default` apunta a `nefijj_db` en `127.0.0.1:3308`. La consulta de solo lectura `showmigrations contenttypes auth sessions accounts incidents --database default` mostró `contenttypes` y `auth` como `[X]`, `sessions` como `[ ]`, y todas las migraciones de `accounts` e `incidents` como `[X]`. La introspección confirmó que faltaban `django_content_type`, `django_session`, `auth_group` y `auth_permission`.

Con respaldo confirmado y autorización expresa, se hizo una reconciliación acotada:
1. Se simuló el plan y se comprobó que revertir normalmente `contenttypes` alcanzaría migraciones de `accounts` e `incidents`; no se ejecutó esa reversión.
2. En una transacción se retiraron únicamente las 22 filas exactas y previamente verificadas de `django_migrations` para `accounts`, `incidents`, `auth` y `contenttypes`, usando `MigrationRecorder`. No se ejecutó ninguna operación de esquema en ese paso.
3. Se aplicaron las migraciones nativas con comandos separados (Django acepta un `app_label` por llamada):

```powershell
.\.venv\Scripts\python.exe manage.py migrate auth --database default --noinput
.\.venv\Scripts\python.exe manage.py migrate sessions --database default --noinput
```

4. Se restauró el historial de negocio como aplicado usando `--fake`, sin ejecutar DDL de `accounts` ni `incidents`:

```powershell
.\.venv\Scripts\python.exe manage.py migrate incidents 0003_backfill_organization_scope --fake --database default --noinput
.\.venv\Scripts\python.exe manage.py migrate accounts 0005_backfill_membership_location --fake --database default --noinput
```

La verificación final mostró todas las migraciones de `contenttypes`, `auth`, `sessions`, `accounts` e `incidents` como `[X]`. La introspección confirmó las tablas nativas `django_content_type`, `django_session`, `auth_group`, `auth_permission` y `auth_group_permissions`. También confirmó las tablas `accounts_user`, `accounts_location`, `accounts_organization`, `accounts_organizationmembership`, `accounts_organizationinvitation`, `incidents_category` e `incidents_incident`; `incidents_incident.evidence_image` existe.

**Pendientes detectados:** no aparecen las tablas `incidents_incidentevent` ni `incidents_emergencyprotocol` en MySQL, aunque sus migraciones iniciales están registradas como aplicadas. Los endpoints de incidentes escriben/consultan eventos y las rutas de emergencias consultan protocolos; esas funciones no están listas para operar sobre la instancia MySQL hasta reparar el esquema con autorización. Se preparó `incidents.0004_repair_missing_legacy_tables`, que es aditiva e idempotente: crea solo las dos tablas faltantes y conserva cualquier tabla existente. No se ejecutó en MySQL por la elección expresa de preparar la migración sin aplicarla. Tras respaldo y autorización, usar el comando documentado en [07_desarrollo_backend.md](./07_desarrollo_backend.md). También permanece la advertencia `mysql.W002` por MariaDB Strict Mode desactivado.

Para cerrar el desarrollo de API se añadieron `JSONParser`, `FormParser` y `MultiPartParser` a la vista de creación de incidencias, se limitaron las categorías y sedes seleccionables en serializadores según la organización activa, y se agregó evidencia PNG válida/inválida y rechazo de categoría ajena a la suite. La migración inicial de incidencias refleja `evidence_image`, que se verificó ya presente en la tabla heredada. Se agregó una prueba SQLite para la migración correctiva de tablas y su idempotencia. `.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings` pasó: 36 pruebas. No se alteró el esquema MySQL durante esta tarea.

Para obtener acceso de prueba Expo Go se inicializó `backend/nefijj-demo.sqlite3` con `config.demo_settings` y se ejecutó `seed_demo --enable-login`, generando una contraseña temporal compartida que se comunicó al usuario, pero no se registra aquí. El proceso Django que ya escuchaba en el puerto 8000 rechazó `demo_superadmin` con `401`; por tanto, ese proceso no utiliza la base SQLite DEMO. Después se levantó la API DEMO en el puerto 8001, sin detener ni cambiar el servicio existente en 8000. Se verificó login para `demo_superadmin`, `demo_admin`, `demo_estudiante_a` y `demo_tecnico_a`; el endpoint de incidencias devolvió datos según rol (5, 5, 4 y 4 registros). Organizaciones, categorías y emergencias respondieron correctamente con 2, 1 y 2 resultados.

Se creó el archivo local ignorado `mobile/.env.local` apuntando la app a la API DEMO (`http://192.168.1.5:8001/api/v1`) y se inició Expo LAN en 8081. `/status` respondió `200` tanto en localhost como por la IP LAN, y el bundle Android respondió `200` con la URL de API esperada. Para probar en el teléfono, abrir Expo Go y escanear el QR de desarrollo o introducir `exp://192.168.1.5:8081`. El teléfono y el computador deben estar en la misma Wi-Fi; comprobar la IP si la conexión se pierde. La contraseña temporal de las cuentas DEMO se informó en el chat y no se almacena en esta bitácora.

La consulta final de tablas se hizo con introspección de solo lectura. El procedimiento general, la precaución para historial inconsistente y los comandos normales para migraciones nativas pendientes se documentan en [07_desarrollo_backend.md](./07_desarrollo_backend.md). No ejecutar `migrate` sin etiquetas ni repetir la reconciliación sin respaldar y comparar el estado exacto.

## 9. Herramientas utilizadas y propósito
Versiones históricas se conservan solo cuando constan en el registro o se pudieron confirmar. La columna de estado distingue las verificaciones repetidas de las documentadas anteriormente.

| Herramienta | Uso en NEFIJJ | Evidencia / estado |
|---|---|---|
| Python | Ejecutar Django, dependencias y pruebas del backend. | Esta verificación se ejecutó con Python 3.15 y Django 5.2.18; no constituye por sí sola una certificación de la matriz de soporte. |
| `pip` | Instalar las dependencias Python fijadas para el backend desde `requirements.txt`. | En esta continuación se instalaron porque el intérprete seleccionado no tenía Django; no se modificó el manifiesto. |
| Django y Django REST Framework | Modelos, autenticación, permisos, endpoints, migraciones y administración del backend. | Dependencias fijadas en `backend/requirements.txt`; endpoints y modelos en `backend/accounts/` y `backend/incidents/`. |
| SimpleJWT | Emisión y renovación de tokens JWT. | Dependencia y rutas presentes; prueba automatizada de autenticación aprobada. |
| MariaDB con XAMPP y `mysqlclient` | Base persistente del entorno local de desarrollo. | MariaDB 10.11.16 y `utf8mb4` verificados históricamente el 2 de noviembre; no se reconectó durante esta auditoría. |
| SQLite en memoria | Aislar las pruebas automatizadas para no tocar `nefijj_db`. | `config.test_settings`; la suite completa más reciente pasó 42 pruebas, incluidas migración, reversión, evidencia protegida, categorías e invitaciones. |
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

## 10. Conexión operativa con MySQL y gestión de cuentas

El objetivo de la siguiente fase es que la aplicación móvil consuma la instancia MySQL `nefijj_db` (y no la base SQLite DEMO) tanto para consultar información como para persistir incidencias. También se solicita habilitar la creación segura de usuarios y el cambio de contraseña.

El usuario compartió un script SQL de referencia que define `accounts_organization`, `accounts_location`, `accounts_user`, `accounts_organizationmembership`, `accounts_organizationinvitation`, `incidents_category` e `incidents_incident`. El esquema de `accounts_user` usa las columnas de autenticación de Django, más `role` y `location_id`; la contraseña debe almacenarse siempre con los hashers de Django, nunca como texto plano. El alta de cuentas debe respetar organización, sede, permisos y unicidad de `username` y `email`. El cambio de contraseña deberá exigir autenticación y validar la contraseña actual, excepto en una operación administrativa autorizada.

El SQL compartido incluye sentencias `DROP TABLE` y datos semilla con hashes de ejemplo que no son credenciales válidas. Es únicamente referencia de esquema: **no se ejecutó ni se debe ejecutar completo sobre la base existente**. No se borraron ni recrearon tablas de negocio. Las tablas `incidents_incidentevent` y `incidents_emergencyprotocol` que faltaban se crearon de forma aditiva después de autorización y respaldo verificado.

La conexión móvil a MySQL requiere configurar la API Django con `config.settings`, verificar que el proceso use la base y puerto esperados, y cambiar `EXPO_PUBLIC_API_URL` del entorno local para apuntar a esa API. Antes de declarar la integración lista se deben probar lecturas autenticadas y una escritura real autorizada (por ejemplo, crear una incidencia y volver a consultarla), comprobar que la fila quedó en MySQL y verificar la carga/servicio de imágenes si forma parte del flujo probado. No usar `config.demo_settings` para esa verificación.

Al finalizar la implementación se documentarán aquí los archivos/endpoints modificados, pruebas ejecutadas y resultados observados. Las validaciones automatizadas deberán usar SQLite aislada; cualquier prueba que escriba en MySQL requiere confirmación explícita, registro de los datos de prueba y limpieza únicamente de esos registros identificados. No registrar contraseñas, tokens ni datos personales.

### Implementación y verificación (6 de noviembre de 2026)
Se implementó `POST /auth/password/change/`: valida contraseña actual, aplica los validadores de Django, rechaza reutilizar la contraseña y la actualiza mediante `set_password`. Los JWT contienen una huella de la contraseña; al cambiarla, los access existentes se rechazan y el endpoint de refresh rechaza refresh anteriores. Se desactivó la rotación/blacklist JWT dependiente de base de datos porque `token_blacklist` no existe en la instancia inspeccionada. `POST /users/` ya creaba usuario y membresía atómicamente; se añadió soporte de nombres/apellidos, se prohibió cambiar contraseñas ajenas por `PATCH /users/{id}/`, y se agregaron pantallas móviles de alta de cuenta y cambio de contraseña.

Se ajustaron los largos de campos de `Category` e `Incident` para coincidir con `SHOW COLUMNS` del esquema físico. `mobile/.env.local` cambió del API SQLite DEMO en el puerto 8001 a la API local en `http://192.168.1.5:8000/api/v1`; verificar la IP LAN antes de volver a iniciar Expo.

La inspección de solo lectura confirmó `nefijj_db`, host local, puerto 3308 y MariaDB 10.4.32; `accounts_user` e `incidents_incident` tienen las columnas/tipos del DDL compartido. El plan inicial de migración intentaba crear modelos de negocio ya existentes, por lo que se detuvo antes de aplicar cambios y se solicitó autorización. Con autorización, se generó y verificó el respaldo externo `C:\Users\User\Documents\NEFIJJ-backups\nefijj_db_pre_repair.sql` (12,633 bytes; su contenido permanece fuera del repositorio).

Después del respaldo se aplicaron solo las migraciones nativas de `contenttypes`, `auth` y `sessions`. Se verificaron columnas/relaciones y agregados de organización/sede/membresía/categoría; los conteos de inconsistencias revisados fueron cero. Se marcaron como falsas las migraciones existentes de `accounts` hasta `0005` y `incidents` hasta `0003`, sin ejecutar su DDL ni backfills. Con ese historial, `migrate incidents 0004_repair_missing_legacy_tables --plan` mostró una única operación Python; se aplicó y creó las tablas `incidents_incidentevent` e `incidents_emergencyprotocol` con IDs/FKs `INT` compatibles con las tablas existentes. Ninguna tabla de negocio existente se borró o recreó.

La verificación final mostró las migraciones `contenttypes`, `auth`, `sessions`, `accounts` (`0001`-`0005`) e `incidents` (`0001`-`0004`) como `[X]`; la introspección confirmó las tablas nativas y las dos tablas de incidencias. La API MySQL devolvió HTTP 200 para categorías (2), incidencias (2), emergencias (0) y organizaciones del usuario (1).

Con autorización se probó el flujo de escritura completo por API usando una cuenta temporal: un administrador organizacional autenticado con JWT generado localmente creó la cuenta (HTTP 201); la cuenta inició sesión (HTTP 200), cambió su propia contraseña (HTTP 204) y volvió a autenticarse con la nueva (HTTP 200). Después creó una incidencia (HTTP 201), obtuvo su detalle por API (HTTP 200) y se verificaron en MariaDB la incidencia, la membresía, el hash de contraseña y el evento asociado. Se eliminaron la cuenta y sus datos relacionados exclusivamente por los IDs/valores únicos de esta prueba; una verificación posterior confirmó cero registros temporales.

La llamada ORM `User.delete()` falló porque no existe `django_admin_log`; la transacción revirtió la primera limpieza. Se inspeccionaron las relaciones FK y luego se borraron únicamente las filas temporales exactas con SQL parametrizado, verificando nuevamente su ausencia. No se creó `django_admin_log` ni se alteró el esquema durante la limpieza. Conviene planear la aplicación de la migración Django `admin` como cambio aditivo separado antes de depender del borrado ORM de usuarios.

La conexión LAN inicialmente devolvió `DisallowedHost` porque `192.168.1.5` no estaba en `DJANGO_ALLOWED_HOSTS`. Se agregó esa IP al `.env` local y se reinició `runserver`; la solicitud GET de comprobación a `/api/v1/auth/token/` respondió HTTP 405 por `192.168.1.5:8000`, confirmando que el host ya es aceptado. Expo/Metro se inició con `mobile/.env.local` apuntando a esa API y respondió HTTP 200 a `/status` por localhost y LAN. La interfaz todavía requiere confirmación manual en el dispositivo. No registrar contraseñas, tokens ni claves locales en esta bitácora.

La suite aislada pasó con 42 pruebas; Django `check` y exportación Android Expo pasaron. Se añadieron pruebas del límite de 10 MB y de la entrega protegida (sin ruta pública `/media/`). `makemigrations --check --dry-run` reporta cambios de opciones `Meta`; no se generaron migraciones. Sigue pendiente `mysql.W002` (MariaDB Strict Mode).

### Implementación de fotos, categorías y mejora visual
Se agregó `expo-image-picker` al cliente Expo. El formulario de reportes permite tomar/seleccionar y previsualizar fotos JPG/PNG (máximo 10 MB), y las envía como `multipart/form-data`. La API limita también la resolución a 40 megapíxeles y sirve el archivo con `GET /incidents/{id}/evidence/`, exigiendo autenticación y el mismo alcance de acceso que el reporte. Se quitó el servicio estático de `MEDIA_ROOT` en desarrollo para no exponer evidencias sin autorización. Las tarjetas muestran badges de prioridad/estado; se mejoraron formularios y se añadió en Protocolos el aviso de que la información es estática.

Se agregó la pantalla de administración móvil de categorías para administradores organizacionales y superadministradores: listar, crear, editar y activar/desactivar, respetando la organización seleccionada. La API ya protegía sus endpoints; se añadieron pruebas automatizadas para altas/cambios, rol y aislamiento.

Validaciones: 18 pruebas de `IncidentApiTests` aprobadas en SQLite y `manage.py check` aprobado; la exportación Android de Expo completó con 885 módulos. Aún falta probar en un teléfono los permisos/flujo de cámara, la administración de categorías y los roles, además de subir una foto a MySQL (requiere una escritura temporal autorizada y limpieza exacta). No se implementó ningún mecanismo de alerta.

### Fase pendiente: avisos informativos de sismos del SGC
Se acordó avisar por push a todos los dispositivos registrados sobre sismos ya publicados por el SGC (no alerta temprana), sin acuse y solo con internet. Se mostrará el área indicada por la fuente, sin filtrado por sede. El usuario proporcionó la página principal del SGC, no un endpoint/feed verificable; no se inventará uno ni se emitirán avisos simulados. Push requiere development build, no Expo Go. Se autorizó generar modelos/migración, sin ejecutar ni aplicar cambios a MySQL. `EmergencyProtocol` continúa siendo contenido informativo estático. La integración queda pendiente hasta identificar y verificar la fuente oficial. Ver [02_requisitos.md](./02_requisitos.md), [03_arquitectura.md](./03_arquitectura.md) y CP17 de [09_pruebas.md](./09_pruebas.md).
