# NEFIJJ

Sistema móvil y API para reportar y gestionar incidencias institucionales por sede y organización.

## Estado actual

- Backend en Django REST Framework con JWT, roles por membresía y alcance por organización.
- El superadministrador de plataforma se identifica mediante `is_superuser`; puede listar, crear, activar y suspender organizaciones.
- Administradores organizacionales, técnicos y usuarios finales operan dentro de su membresía activa. La API valida el tenant; no confía en un `organization_id` enviado como dato de autorización.
- App React Native con Expo para autenticación, incidencias, protocolos y navegación inicial por rol.
- Proyecto en desarrollo local. No está desplegado en producción ni se ha validado completamente en un teléfono.
- Siguen pendientes la UI móvil de invitaciones/QR empresarial, métricas globales y la administración móvil completa. El QR de Expo Go solo carga la app de desarrollo.

El estado y los límites funcionales están en [docs/01_propuesta.md](docs/01_propuesta.md), [docs/09_pruebas.md](docs/09_pruebas.md) y [docs/10_bitacora_desarrollo.md](docs/10_bitacora_desarrollo.md).

## Requisitos

- Python compatible con Django 5.2.
- MySQL/MariaDB local para la ejecución normal del backend.
- Node.js y npm para la app móvil.
- PowerShell y Git en Windows.

Las dependencias Python están fijadas en [backend/requirements.txt](backend/requirements.txt). No reemplazar ese archivo con la salida completa de `pip freeze`.

## Backend local

Desde PowerShell, en la raíz del repositorio:

```powershell
Set-Location .\backend
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edita `backend/.env` localmente. Sustituye el secreto de ejemplo por uno aleatorio, configura usuario/contraseña/puerto de MySQL y limita `DJANGO_ALLOWED_HOSTS` a los hosts de desarrollo que realmente usarás. No subas `.env`, contraseñas ni copias de bases de datos.

Antes de operar sobre una base existente, revisa su historial y esquema siguiendo [docs/07_desarrollo_backend.md](docs/07_desarrollo_backend.md). No ejecutes migraciones ni el seed DEMO contra `nefijj_db` sin respaldo y autorización.

Para validar cambios sin usar MySQL:

```powershell
.\.venv\Scripts\python.exe manage.py test accounts.tests incidents.tests --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py check --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.test_settings
```

Las pruebas usan SQLite en memoria y no certifican el esquema ni la conexión de MariaDB. Consulta [docs/09_pruebas.md](docs/09_pruebas.md) para el estado actualizado.

## Aplicación móvil

Instala dependencias dentro de `mobile/`, configura `mobile/.env.local` con la URL de la API y sigue [docs/08_desarrollo_mobile.md](docs/08_desarrollo_mobile.md). Para Expo Go, el teléfono y el computador deben compartir una red local confiable.

## Fase de despliegue

El código se aloja en GitHub, pero el backend aún no está desplegado en PythonAnywhere ni en otro servicio de producción. Antes de publicarlo se deben validar permisos, credenciales MySQL, HTTPS, hosts permitidos y almacenamiento persistente para evidencia.
