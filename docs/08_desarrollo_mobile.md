# 08. Guía de Desarrollo Mobile - NEFIJJ

## 1. Requisitos
- Node.js LTS y npm.
- Expo Go instalado en el dispositivo para pruebas de desarrollo.
- Backend NEFIJJ ejecutándose y accesible desde el dispositivo.

El proyecto existente ya incluye `mobile/package.json` y `mobile/package-lock.json`; no generes una app nueva al clonar/descargar el repositorio.

## 2. Descargar e instalar dependencias del proyecto existente
Después de clonar/descargar el repositorio, desde `mobile/` instala las versiones bloqueadas:

```powershell
cd mobile
npm ci
```

En Windows también puedes usar `npm.cmd ci` si PowerShell bloquea `npm.ps1`. Para el backend, crea `.venv` e instala `requirements.txt` siguiendo [07_desarrollo_backend.md](./07_desarrollo_backend.md); Pillow ya está incluido ahí. Se necesita una instancia autorizada de MySQL/MariaDB solo si se va a probar la base operativa. Los archivos `.env` y credenciales son locales, están ignorados por Git y deben configurarse aparte; no compartirlos.

La carpeta `mobile/` solo debe inicializarse si realmente está vacía y no contiene un proyecto existente.

## 3. Inicializar una aplicación vacía (solo si corresponde)
Desde la raíz del repositorio, solo si `mobile/` aún no contiene un proyecto:

```powershell
cd mobile
npx create-expo-app@latest . --template blank
npm install axios @react-navigation/native @react-navigation/native-stack
npx expo install expo-secure-store expo-image-picker react-native-screens react-native-safe-area-context
```

Confirmar en `package.json` las dependencias instaladas y las versiones compatibles. La app debe separar la presentación de las llamadas HTTP, manejar estados de carga/error y no duplicar reglas de autorización que corresponden al backend.

## 4. URL de la API
Configurar `EXPO_PUBLIC_API_URL` en el entorno local, por ejemplo:

```text
EXPO_PUBLIC_API_URL=http://192.168.1.20:8000/api/v1
```

Reemplazar la IP de ejemplo por la IP LAN real del equipo. `localhost` dentro de un teléfono apunta al teléfono, no al computador. Para emulador Android puede utilizarse `10.0.2.2` si el entorno lo admite. Asegurar que ambos dispositivos estén en la misma red y que el firewall permita la conexión. La configuración `EXPO_PUBLIC_*` no debe contener secretos.
Copiar `.env.example` como `.env.local` y configurar también la IP LAN del equipo en `DJANGO_ALLOWED_HOSTS` dentro de `backend/.env`.

Si el teléfono no puede iniciar sesión, comprobar desde su navegador `http://<IP-LAN-DEL-EQUIPO>:8000/api/v1/auth/token/`. Una respuesta HTTP `405 Method Not Allowed` es esperada para GET e indica que Django y la ruta son accesibles. Si no carga, iniciar Django con `python manage.py runserver 0.0.0.0:8000`, confirmar que el teléfono y el computador están en la misma red y permitir TCP 8000 en el firewall. Después de cambiar `.env.local`, reiniciar Expo con `npx expo start --clear`.

La IP LAN se detecta dinámicamente y puede cambiar. Consultar la dirección actual en Windows antes de conectar el teléfono. Si cambia, actualizar `EXPO_PUBLIC_API_URL` y `NEFIJJ_DEMO_ALLOWED_HOSTS`. La regla de firewall debe limitarse a una red privada de confianza y `LocalSubnet`; no cambiar a perfil privado una red pública.

### Conexión a la base operativa MySQL
Para mostrar los registros existentes y guardar reportes en `nefijj_db`, `EXPO_PUBLIC_API_URL` debe apuntar al servidor Django que usa `config.settings` y la conexión `default` de MySQL/MariaDB, normalmente el puerto 8000, por ejemplo `http://<IP-LAN-DEL-COMPUTADOR>:8000/api/v1`. La app no se conecta directamente al puerto 3308 del motor y no debe incluir credenciales de base de datos.

No usar la URL del backend DEMO (puerto 8001 o `config.demo_settings`) para validar integración con MySQL: esa instancia responde desde SQLite. La configuración local apunta a `http://192.168.1.5:8000/api/v1`; comprobar la IP antes de usarla y reiniciar Expo con `npx.cmd expo start --clear --lan --go`. La lectura y escritura API↔MySQL se probaron desde el computador; todavía falta la prueba visual/funcional desde un teléfono. Django debe incluir la IP LAN en `DJANGO_ALLOWED_HOSTS`; sin ella devuelve HTTP 400 `DisallowedHost`. La pantalla Cuenta permite cambiar la contraseña; administradores organizacionales pueden crear usuarios y el superadministrador puede hacerlo desde la organización seleccionada. Nunca guardar contraseñas en SecureStore ni en `.env.local`.

## 5. Ejecutar y probar
Desde `mobile/`:

```powershell
$env:REACT_NATIVE_PACKAGER_HOSTNAME = "192.168.1.5"
npx.cmd expo start --clear --lan --go
```

> **Importante para Windows con Hyper-V / WSL / Adaptadores virtuales:** Windows suele tener adaptadores `vEthernet` (por ejemplo `172.19.x.x`). Si no defines `$env:REACT_NATIVE_PACKAGER_HOSTNAME`, Expo puede publicar la IP virtual en lugar de la Wi-Fi real (`192.168.1.5`), causando que Expo Go en el teléfono falle al conectar (`Network response was not ok` o `Could not connect`). Configurar `REACT_NATIVE_PACKAGER_HOSTNAME` fuerza a Metro a usar la IP Wi-Fi correcta.

Usar `npx.cmd` en PowerShell si la política de ejecución bloquea `npx.ps1`. Ejecutar en una terminal interactiva para que Expo CLI muestre el QR. El QR que imprime Expo CLI es el **QR de desarrollo**: abre el bundle en Expo Go y no vincula una empresa. El **QR de invitación empresarial** es otro flujo y ya tiene pantallas para generarlo o escanearlo. Teléfono y computador deben compartir una red Wi-Fi; no usar `localhost` en la URL de API del teléfono. Probar inicio/cierre de sesión, listado/reporte, filtros, asignación, estados, protocolos y alertas.

### Entorno aislado de demostración
Desde `backend/`, inicializar un SQLite exclusivo de demostración (no conecta a `nefijj_db` ni a MariaDB):

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.demo_settings"
$env:NEFIJJ_DEMO_ALLOWED_HOSTS = "127.0.0.1,localhost,<IP-LAN-DEL-COMPUTADOR>"
python manage.py migrate
python manage.py seed_demo --enable-login
python manage.py runserver 0.0.0.0:8000
```

`seed_demo --enable-login` genera una contraseña aleatoria compartida por las cuentas de prueba y la imprime una sola vez en la terminal. No copiarla a documentos, repositorio ni cuentas reales. Repetir el comando rota esa contraseña. Usuarios disponibles: `demo_superadmin`, `demo_admin`, `demo_estudiante_a`, `demo_estudiante_b`, `demo_tecnico_a`, `demo_tecnico_b`. Datos de muestra: organización/sedes DEMO, una categoría, dos protocolos y cinco incidencias ficticias. La base está en `backend/nefijj-demo.sqlite3` (ignorada por Git).

En `mobile/.env.local`, asignar `EXPO_PUBLIC_API_URL=http://<IP-LAN-DEL-COMPUTADOR>:8000/api/v1`; desde `mobile/`, ejecutar `npx.cmd expo start --clear --lan --go` en una terminal interactiva y escanear el QR de desarrollo. Requiere que el firewall permita TCP 8000/8081 solo en una red privada de confianza. No utilizar túnel público ni el servidor de desarrollo en producción. Para detener ambos procesos, usar `Ctrl+C` en sus terminales.

Si el puerto 8000 ya está ocupado por otro backend, iniciar el backend DEMO aislado en 8001 y usar `EXPO_PUBLIC_API_URL=http://<IP-LAN-DEL-COMPUTADOR>:8001/api/v1`; Expo Go obtiene la interfaz desde Metro (8081) y los datos desde ese API. El servidor MySQL y el backend DEMO usan puertos/configuraciones separados; la prueba con Expo debe usar `config.demo_settings`, no `nefijj_db`.

La navegación depende del rol devuelto por la API: el superadministrador abre gestión básica de organizaciones; el administrador organizacional abre el panel de incidencias; técnico y usuario final tienen flujos operativos distintos. Si la cuenta pertenece a varias organizaciones, debe elegir una antes de consultar datos y puede cambiarla desde la navegación. El cliente envía `X-Organization-ID`; el servidor valida la membresía.

El administrador organizacional puede filtrar incidencias por sede/estado/prioridad/categoría, cargar páginas, asignar o retirar un técnico activo de su sede, cerrar incidencias resueltas y reabrir cerradas, además de gestionar categorías y alertas de emergencia. El usuario final crea reportes propios y puede adjuntar evidencia; el técnico atiende las que tiene asignadas. El usuario y el técnico pueden consultar alertas y protocolos.

Los registros que empiezan por `DEMO -` son ficticios y no representan protocolos reales. Para probar con credenciales, usar solamente el entorno separado `config.demo_settings` y la contraseña aleatoria temporal que imprime el comando DEMO. Las cuentas demo del MariaDB histórico siguen sin contraseña utilizable.

Si la app conserva el bundle anterior, detener Expo y arrancar desde `mobile/` con:

```powershell
npx.cmd expo start --clear
```

Esto recarga la configuración local y limpia la caché del bundler. La app actual usa Expo SDK 58, React Native 0.88 y navegación nativa; comprobar compatibilidad de dependencias con `npx expo install --check`.

## 6. Sesión y seguridad
- Guardar los tokens mediante `expo-secure-store`.
- Enviar el token de acceso en `Authorization: Bearer <access_token>`.
- Renovar la sesión según el endpoint de refresh y limpiar credenciales si la renovación falla o el usuario cierra sesión.
- No persistir contraseñas, no imprimir tokens y no permitir que datos del cliente establezcan rol, sede, reportante o estado inicial.
- Usar HTTPS en entornos compartidos o de producción. HTTP solo para desarrollo local controlado.

## 7. Estado de validación
El bundle Android se exportó correctamente después de los cambios de navegación multiempresa. La exportación genera un bundle, no un APK. La interacción visual en teléfono, selección de organización, cambio de tenant, asignación, estados, sesión expirada y pérdida de red aún requiere validación manual. Consultar [09_pruebas.md](./09_pruebas.md) y la bitácora [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md).

## 8. Roles, invitaciones y entrega instalable
Los roles móviles son `superadmin`, `organization_admin`, `technician`, `user` y `member` (selector pendiente de elección). El selector de organización y el header de tenant están implementados. Administradores organizacionales y superadministradores pueden generar, mostrar y revocar invitaciones QR; el código solo se revela al crearlo y el QR de Expo Go se distingue del QR empresarial. Un usuario con sesión iniciada puede escanear o escribir el código, ver la organización y elegir una sede activa antes de unirse. El backend exige autenticación y valida vigencia, uso único, estado del tenant y sede. El flujo no crea cuentas: el usuario debe tener una cuenta NEFIJJ. La pantalla de inicio del usuario separa «Reportar incidencia» de «Mis reportes». El reporte conserva categorías dinámicas, foto opcional, errores recuperables y confirmación de éxito; la fecha/hora proviene del servidor y no se captura GPS. El usuario puede tomar/seleccionar una foto JPG/PNG de hasta 10 MB, previsualizarla y adjuntarla; el backend protege su descarga por permisos de la incidencia. Administradores organizacionales y superadministradores pueden gestionar categorías desde la app. Se mejoraron los formularios y las tarjetas de estado/prioridad. La prueba en dispositivo real sigue pendiente. Tampoco hay wizard de tres pasos. La pantalla superadmin crea organizaciones y cambia su estado. Los límites completos están en la sección 7 de [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md).

### Validación pendiente y próximo desarrollo
La fase de fotos, categorías y primera mejora visual ya está implementada; verificar permisos de cámara/galería y el flujo de punta a punta en un teléfono Expo Go, además de la persistencia de una imagen en MySQL con autorización y limpieza de prueba.

Las alertas operativas de emergencia de la Fase 6 ya tienen API, cola durable, registros push y pantallas móviles. Para habilitarlas, configurar `EXPO_PUBLIC_EAS_PROJECT_ID` en `mobile/.env.local`, reconstruir un development build y programar `python manage.py send_emergency_alerts` cada minuto. El proceso llama al servicio Expo Push; si se configura `EXPO_ACCESS_TOKEN`, mantenerlo solo en `backend/.env`, nunca en la app. Expo recibe el token y el texto de cada notificación. No enviar datos personales en ese texto. La aceptación del servicio no prueba recepción; la alerta caduca a los 15 minutos y la entrega no se garantiza. No correr el worker en pruebas salvo con mocks.

Expo Go/QR no sirve para probar notificaciones remotas; se requiere proyecto EAS, credenciales de plataforma y development build. Esta implementación no envió notificaciones ni aplicó migraciones a MySQL. La integración de avisos informativos del SGC sigue aparte y pendiente de identificar un feed oficial verificable. Los protocolos existentes siguen siendo información estática; no se debe prometer detección ni entrega garantizada.

`expo export --platform android` genera un bundle exportado, no un APK instalable. La generación y firma de un APK requieren un flujo de compilación Android (por ejemplo, EAS Build o Gradle local), configuración de credenciales de firma y validación en dispositivo. No se garantiza que un servicio de compilación alojado sea gratuito; no se ha generado ni validado un APK en este proyecto.
