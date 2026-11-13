# 07. Guía de Desarrollo Backend - NEFIJJ

## 1. Requisitos
- Python compatible con Django 5.2. La verificación del 13 de noviembre de 2026 ejecutó 35 pruebas con Python 3.14.10; esto no constituye certificación completa de la matriz de versiones.
- MySQL compatible con Django 5.2 o MariaDB 10.5 o superior. La instalación local XAMPP comprobada ejecuta MariaDB 10.11.16.
- Git y PowerShell en Windows.

La carpeta `backend/` puede estar vacía al iniciar. Los comandos de creación del proyecto son de inicialización y no deben repetirse sobre un proyecto ya creado.

## 2. Crear el entorno y las dependencias
Desde `backend/`, en PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

El entorno implementado fija las dependencias en `requirements.txt`. Usar el ejecutable dentro de `.venv` evita depender del Python seleccionado en el editor. La activación de PowerShell es opcional; si la política de ejecución bloquea `Activate.ps1`, no es necesario cambiarla: ejecutar directamente `.\.venv\Scripts\python.exe`.

## 3. Inicializar Django
Solo si todavía no existe `manage.py`:

```powershell
.\.venv\Scripts\python.exe -m django startproject config .
.\.venv\Scripts\python.exe manage.py startapp accounts
.\.venv\Scripts\python.exe manage.py startapp incidents
```

Configurar un modelo de usuario propio basado en `AbstractUser` y `AUTH_USER_MODEL` antes de ejecutar la primera migración. Integrar DRF, JWT, las aplicaciones, el backend MySQL y el enrutamiento `/api/v1/` según los documentos de arquitectura, datos y API.

## 4. Base de datos y entorno
1. Iniciar el servicio de base de datos desde XAMPP y crear una base `nefijj_db` con charset `utf8mb4` y cotejamiento `utf8mb4_unicode_ci`; usar una cuenta local con permisos solo sobre esa base. Verificar el motor y versión con `SELECT VERSION();`; XAMPP puede usar MariaDB en lugar de MySQL.
2. Crear un `.env` local (no versionado) con la configuración requerida, por ejemplo:

```text
DJANGO_SECRET_KEY=valor-local-no-versionado
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,192.168.1.20
DB_NAME=nefijj_db
DB_USER=nefijj
DB_PASSWORD=contraseña-local
DB_HOST=127.0.0.1
DB_PORT=3306
```

Leer estas variables desde la configuración Django, validar que estén presentes y proporcionar un `.env.example` sin secretos. En producción, usar valores seguros, HTTPS, `DEBUG=False` y un gestor de secretos.
La IP anterior es solo un ejemplo: sustituirla por la IP LAN vigente del computador. No poner `*` en `DJANGO_ALLOWED_HOSTS`. No compartir ni versionar el `.env`.

## 5. Migrar, crear administrador y ejecutar
Una vez configurado `.env` y con el servicio MySQL de XAMPP iniciado, desde `backend/`:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

`0.0.0.0` permite probar desde un dispositivo de la misma red; no debe exponerse así a una red pública. Para el primer acceso desde otro dispositivo, usar la IP LAN del equipo y autorizarla en `ALLOWED_HOSTS`.
No ejecutes datos de demostración contra la base de desarrollo persistente. `seed_demo` solo funciona con `config.demo_settings` y su SQLite aislado; los comandos y los logins temporales están documentados en [08_desarrollo_mobile.md](./08_desarrollo_mobile.md). El seed crea dos sedes DEMO, seis cuentas y registros ficticios; no uses estos datos como información operativa.

Para acceder desde Expo Go: comprobar que teléfono y computador estén en la misma red confiable; configurar la IP vigente en `DJANGO_ALLOWED_HOSTS` y `mobile/.env.local`; restringir Windows Firewall al perfil privado y la subred local; iniciar el servidor arriba. Una respuesta `405 Method Not Allowed` al abrir `http://<IP-LAN>:8000/api/v1/auth/token/` en el navegador es esperada para GET y confirma que esa ruta responde. Si se cambia `.env`, detener y reiniciar el proceso Django.

No usar `createsuperuser` para saltarse advertencias de contraseña. Ante una contraseña expuesta, cambiarla localmente con:

```powershell
.\.venv\Scripts\python.exe manage.py changepassword <usuario>
```

No escribir la contraseña en esta guía ni enviarla por chat.

## 6. Verificación
Ejecutar pruebas desde `backend/`:

```powershell
.\.venv\Scripts\python.exe manage.py test accounts.tests incidents.tests --settings=config.test_settings
```

La configuración de prueba usa SQLite en memoria y credenciales ficticias; no reemplaza la validación final de migraciones y cotejamiento en MySQL. Antes de aceptar cambios, verificar autenticación, permisos por rol/sede, validaciones, transiciones de estado e historial según [09_pruebas.md](./09_pruebas.md). No usar datos personales reales ni subir `.env`, tokens o copias de bases de datos.

## 7. Estado comprobado y seguridad de red
La bitácora [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md) describe la instalación realizada, la conexión comprobada a `nefijj_db`, los datos de demostración y la situación pendiente del firewall. La IP `192.168.1.18` es el valor observado durante la última sesión y puede cambiar; verificarla antes de usarla. `DEBUG=True` y `runserver` son exclusivamente para desarrollo local, nunca para producción.

## 8. Multiempresa y migraciones
El backend ya incluye modelos de organización/membresía/invitación, endpoints organizacionales y aislamiento para recursos operativos. Ejecutar las pruebas con la configuración aislada:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.test_settings"
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

La suite usa SQLite en memoria; no reemplaza el ensayo de migración en MariaDB. El backfill asigna sedes `DEMO-*` a la organización DEMO y el resto a Universidad de La Guajira, y la prueba automatizada incluye reversión. Antes de aplicar migraciones a `nefijj_db`, obtener un respaldo verificable, restaurarlo en una base aislada, conciliar datos y revisar la reversión. No ejecutar el seed DEMO en producción.
