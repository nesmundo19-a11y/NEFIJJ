# 07. Guía de Desarrollo Backend - NEFIJJ

## 1. Requisitos
- Django 4.2.16, según la versión fijada actualmente en `backend/requirements.txt`.
- MySQL compatible con Django 4.2 o MariaDB 10.5 o superior. La instalación local XAMPP comprobada ejecuta MariaDB 10.11.16.
- Git y PowerShell en Windows.

La carpeta `backend/` puede estar vacía al iniciar. Los comandos de creación del proyecto son de inicialización y no deben repetirse sobre un proyecto ya creado.

## 2. Crear el entorno y las dependencias
Desde `backend/`, en PowerShell. Usa siempre el intérprete de Python del entorno virtual para que los paquetes estén disponibles para el proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Pillow ya está incluido en `requirements.txt`; al instalar ese archivo queda disponible para procesar imágenes de evidencia con `ImageField`. No hace falta instalarlo por separado.

## 3. Inspeccionar el historial de migraciones antes de operar sobre MySQL
La base heredada `nefijj_db` ya contiene tablas y datos. Antes de ejecutar cualquier migración, desde `backend/` inspecciona el registro que Django guarda en `django_migrations`:

```powershell
.\.venv\Scripts\python.exe manage.py showmigrations --database default
```

Este comando consulta qué migraciones aparecen como aplicadas (`[X]`) o pendientes (`[ ]`); no las aplica. También puedes consultar directamente el historial en MySQL/MariaDB. Conéctate de forma interactiva para que la contraseña no quede escrita en el comando:

```powershell
mysql -h 127.0.0.1 -P 3308 -u TU_USUARIO -p nefijj_db
```

Reemplaza `TU_USUARIO` por el usuario de MySQL; `-p` solicitará la contraseña sin incluirla en el comando. En el prompt de MySQL, ejecuta consultas de solo lectura:

```sql
SELECT app, name, applied
FROM django_migrations
ORDER BY app, applied, name;

SELECT app, name, applied
FROM django_migrations
WHERE app IN ('accounts', 'incidents')
ORDER BY app, applied, name;
```

`showmigrations` y estas consultas solo muestran el historial registrado: no comprueban que las tablas y columnas reales coincidan con cada migración. Contrasta el resultado con el esquema existente y con los modelos antes de decidir cómo alinear el historial. No ejecutes `migrate`, `migrate --fake`, ni generes/apliques migraciones para resolver discrepancias sin respaldar y verificar primero el esquema; `managed = False` evita que Django administre esas tablas en operaciones normales de sincronización, pero no vuelve seguras por sí solas las migraciones ya existentes.

Si se verificó que faltan tablas internas **y** las migraciones de esas apps nativas aparecen pendientes (`[ ]`), mientras las de `accounts` e `incidents` aparecen aplicadas (`[X]`), y se autorizó expresamente completar las tablas, aplica únicamente las apps nativas requeridas desde `backend/`:

```powershell
.\.venv\Scripts\python.exe manage.py migrate auth --database default --noinput
.\.venv\Scripts\python.exe manage.py migrate sessions --database default --noinput
```

`migrate` acepta un solo `app_label` por invocación. Aplicar `auth` también aplica su dependencia `contenttypes`; luego se aplica `sessions` en una invocación separada. No uses `migrate` sin etiquetas en esta base heredada. Comprueba el resultado con:

```powershell
.\.venv\Scripts\python.exe manage.py showmigrations contenttypes auth sessions accounts incidents --database default
```

Y confirma las tablas físicas con:

```powershell
.\.venv\Scripts\python.exe manage.py dbshell --database default
```

En `dbshell`, ejecuta:

```sql
SHOW TABLES FROM nefijj_db LIKE 'django_content_type';
SHOW TABLES FROM nefijj_db LIKE 'django_migrations';
SHOW TABLES FROM nefijj_db LIKE 'django_session';
SHOW TABLES FROM nefijj_db LIKE 'auth_group';
SHOW TABLES FROM nefijj_db LIKE 'auth_permission';
SHOW TABLES FROM nefijj_db LIKE 'accounts_%';
SHOW TABLES FROM nefijj_db LIKE 'incidents_%';
```

Las migraciones marcadas `[X]` confirman el registro de Django; `SHOW TABLES` comprueba existencia física, no que todas las columnas o restricciones sean idénticas a la definición de migración.

**No ejecutes el comando anterior si `contenttypes` o `auth` muestran `[X]` pero sus tablas físicas faltan.** Django considera esas migraciones aplicadas y no reconstruye las tablas. La base está entonces inconsistente: inspecciona el plan con `migrate contenttypes zero --plan --database default` antes de considerar cualquier reparación. El plan puede incluir dependencias y migraciones de negocio; no apliques ni reviertas ese plan sobre la base heredada sin respaldo y un procedimiento de reconciliación que preserve las tablas físicas. En el caso documentado en [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md), se reconciliaron solo los registros verificados de `django_migrations`, se aplicaron las tablas nativas y se volvieron a marcar las migraciones de negocio como falsas. No repitas esa operación sin confirmar que el estado de la base coincide exactamente.

## 4. API de incidencias, evidencia e aislamiento
La vista de creación admite JSON y `multipart/form-data` mediante `JSONParser`, `FormParser` y `MultiPartParser`. El serializador expone `evidence_image` como opcional y escribible; Pillow valida JPG/PNG, con un máximo de 10 MB y 40 megapíxeles. Los campos de organización, sede, reportante, estado, asignación y marcas de tiempo permanecen bajo control del servidor. `GET /incidents/{id}/evidence/` sirve el archivo solo después de comprobar autenticación y alcance; `MEDIA_ROOT` no se publica como directorio estático.

La categoría aceptada por el serializador se limita a categorías activas de la organización seleccionada. La organización se determina desde la membresía activa y `X-Organization-ID` cuando el usuario pertenece a varias; sede y reportante se derivan de esa membresía. Listados, detalles e historial aplican el alcance de organización, sede y rol. Asignación y transiciones se validan en el servidor y registran eventos dentro de transacciones.

`MEDIA_ROOT` apunta a `backend/media/`, `MEDIA_URL` es `/media/` y `upload_to` guarda rutas relativas con estructura `evidences/año/mes/`. El directorio no se publica como ruta estática ni siquiera en desarrollo; se debe usar el endpoint autenticado de evidencia. En producción, el servidor web o almacenamiento dedicado debe conservar la misma restricción de acceso. Enviar formularios como `multipart/form-data`; el cliente HTTP debe generar automáticamente el boundary.

Las pruebas aisladas verifican creación de incidencia con imagen PNG, rechazo de imagen inválida, acceso autorizado a la foto y denegación entre usuarios, rechazo de categoría de otra organización, CRUD de categorías, permisos por rol/tenant y eventos. Ejecutar la suite sin conectar a `nefijj_db`:

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
```

La suite aislada pasó con 42 pruebas el 6 de noviembre de 2026. Esto valida el código en SQLite y no sustituye la verificación de MySQL.

**Reconciliación realizada en MySQL tras respaldo verificado:** se comprobó que no existía `django_migrations`; el plan inicial incluía crear tablas de negocio ya existentes. Se aplicaron únicamente `contenttypes`, `auth` y `sessions`; luego se marcaron con `--fake` las migraciones existentes de `accounts` e `incidents` después de inspeccionar columnas/relaciones y validar los datos de organización, sede, membresía y categoría. Finalmente, `incidents.0004_repair_missing_legacy_tables` se aplicó solo después de comprobar que su plan contenía una única operación Python aditiva. La migración crea las dos tablas faltantes usando claves primarias/foráneas `INT` compatibles con MariaDB y preserva las tablas de negocio existentes.

No ejecutar el SQL de referencia ni repetir una reconciliación a ciegas. El plan anterior que intentaba recrear las tablas de negocio era previo a la reconciliación y queda documentado como antecedente. El comando de reparación ya aplicado fue:

```powershell
.\.venv\Scripts\python.exe manage.py migrate incidents 0004_repair_missing_legacy_tables --database default --noinput
```

La instancia actual ya muestra las migraciones esperadas aplicadas y las tablas físicas presentes. Antes de cualquier operación futura, revisar `showmigrations` y `SHOW TABLES`; no aplicar de nuevo ni hacer rollback.

## 5. Conectar la API operativa a MySQL y habilitar cuentas
La app móvil se conecta exclusivamente a la API; nunca a MySQL directamente. Para consultar y guardar datos reales, Django debe iniciar con `config.settings` y su conexión `default` configurada para la base `nefijj_db` (XAMPP, puerto local 3308). `config.demo_settings` selecciona SQLite y no sirve para esta prueba.

### 5.1 Verificar conexión sin alterar el esquema
1. Revisar localmente `backend/.env` y `config/settings.py`: confirmar host, puerto, base de datos, usuario y el nombre de la variable que selecciona settings; no copiar valores secretos a documentación ni al chat.
2. Comprobar que `backend/.env` esté ignorado por Git y que `mobile/.env.local` apunte a la IP LAN del equipo, puerto del backend y prefijo `/api/v1`.
3. Contrastar la estructura real con `SHOW TABLES` y `SHOW COLUMNS`/`SHOW CREATE TABLE` de solo lectura. Comparar especialmente nombres/tipos con `accounts_user`, las membresías, categorías e incidencias; confirmar la presencia de las tablas de historial y protocolos que usa la API.
4. No ejecutar el SQL de referencia completo: contiene `DROP TABLE` y datos semilla de ejemplo. No usar `migrate`, `migrate --fake`, `makemigrations` ni `seed_demo` como método de conexión o prueba de lectura.
5. Si faltan tablas/columnas o no coincide un campo, detener la prueba que dependa de ese objeto. Preparar una propuesta separada y pedir autorización expresa antes de modificar el esquema.

Cuando la estructura sea compatible, iniciar el servidor para la LAN desde `backend/` con:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

El puerto debe estar accesible desde la red privada de confianza; `0.0.0.0` es solo la dirección de escucha. Esta orden no ejecuta migraciones. Verificar login y lecturas con una cuenta existente cuyo hash de contraseña sea válido. El ejemplo de hashes incluido en el SQL compartido es ficticio y no permite autenticarse.

### 5.2 Crear usuarios y cambiar contraseñas
Las cuentas nuevas se crean por una ruta autenticada y autorizada de la API, usando los validadores de Django y `set_password`/`create_user`. La escritura de usuario y membresía debe ser atómica, validar que la sede pertenezca a la organización activa y no permitir que el cliente asigne privilegios globales. Confirmar que no se persistan contraseñas en texto plano ni se devuelvan hashes.

El cambio de contraseña de autoservicio debe exigir contraseña actual, aplicar validadores de Django a la nueva y actualizar con `set_password`. No se debe incluir una contraseña en comandos, logs, respuestas ni bitácoras. Probar primero en SQLite aislada; probar luego con la instancia MySQL solo en una cuenta de prueba expresamente identificada. La creación de usuarios y el cambio de contraseña modifican datos, aunque no el esquema.

### 5.3 Prueba funcional con Expo Go
Configurar `mobile/.env.local` con `EXPO_PUBLIC_API_URL=http://<IP-LAN-DEL-EQUIPO>:8000/api/v1`, iniciar/reiniciar Expo con caché limpia y escanear el QR de desarrollo. Después del login, comprobar que el listado refleja registros existentes de MySQL. Crear una incidencia de prueba con la cuenta autorizada, consultar su detalle y confirmar su persistencia mediante la API y una consulta SQL de solo lectura; si se prueba imagen, confirmar que MySQL guarda la ruta relativa y que el archivo queda bajo `backend/media/`.

La prueba final requiere una escritura en MySQL y por tanto debe realizarse solo con autorización para los registros de prueba y un plan de limpieza limitado a esos registros identificados. No borrar/recrear tablas ni ejecutar migraciones para realizarla. Registrar el resultado en [09_pruebas.md](./09_pruebas.md) y [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md).

### 5.4 Estado verificado en la revisión actual
La conexión de solo lectura confirmó `nefijj_db` en `127.0.0.1:3308`, MariaDB 10.4.32. Las columnas físicas de `accounts_user` e `incidents_incident` coinciden con el DDL compartido; se ajustaron en el modelo de incidencias los largos de título, estado, prioridad y nombre de categoría para reflejar esos tipos.

La introspección inicial encontró ausentes `django_migrations`, `django_content_type`, `auth_permission`, las tablas de blacklist, `incidents_incidentevent` e `incidents_emergencyprotocol`. Se creó un respaldo completo fuera del repositorio y verificado (12,633 bytes). Luego se aplicaron las migraciones nativas `contenttypes`, `auth` y `sessions`, se conciliaron como falsas las migraciones de negocio que ya correspondían al esquema/datos existentes y se aplicó `incidents.0004_repair_missing_legacy_tables` tras confirmar que el plan ya no incluía DDL de tablas preexistentes.

La verificación final encontró todas esas migraciones como aplicadas y ambas tablas de incidencias presentes. Una prueba autenticada de solo lectura a través de la API local devolvió HTTP 200 para categorías (2), incidencias (2), emergencias (0) y organizaciones del usuario (1). No se creó ningún registro ni se cambió una contraseña en MySQL. La advertencia `mysql.W002` por Strict Mode de MariaDB permanece.

La ruta `POST /auth/password/change/` y las interfaces móviles de cambio de contraseña/alta de usuarios están implementadas. La suite aislada de backend pasa con 42 pruebas y el bundle Android de Expo se exportó correctamente. Se verificaron por API las lecturas MySQL y una prueba controlada de alta de usuario, login, cambio de contraseña, alta/consulta de incidencia y limpieza de registros temporales. Las imágenes multipart tienen pruebas aisladas con SQLite; aún no se ha probado una carga de archivo en la instancia MySQL ni desde el teléfono.

Durante la conexión LAN, el registro de Django mostró `DisallowedHost` para `192.168.1.5`. Se añadió esa IP a `DJANGO_ALLOWED_HOSTS` en el `.env` local y se reinició Django; el GET de comprobación a `/api/v1/auth/token/` respondió `405`, que confirma ruta accesible por LAN. No guardar en documentación contraseñas ni tokens. La interacción real desde Expo Go en un teléfono todavía no está verificada.

#### Estado de la fase de fotos, categorías y experiencia móvil
La implementación está completa y tiene 42 pruebas aprobadas en SQLite aislada; se verificaron `manage.py check` y la exportación Android de Expo. Falta probar cámara/galería, administración por roles y carga de fotos desde un teléfono, además de una escritura de foto en MySQL con autorización y limpieza exacta. La persistencia de evidencia se protege mediante el endpoint autenticado; no habilitar `/media/` como ruta pública.

#### Avisos informativos de sismos del SGC (pendientes)
Se acordó notificar por push a todos los dispositivos registrados sobre sismos ya publicados (no alertas tempranas), sin acuse y con internet. El área se toma del dato publicado, sin filtrado por sede. No se encontró una API/feed verificable en la página principal proporcionada; no inventar una URL ni enviar alertas simuladas. El push requiere `expo-notifications`, credenciales de plataforma y un development build (no Expo Go). Se autorizó preparar el código de persistencia y migraciones, pero no ejecutar ni aplicar cambios de esquema en MySQL.

La especificación de alcance y aceptación de esta fase está en [02_requisitos.md](./02_requisitos.md) y [09_pruebas.md](./09_pruebas.md).