# 08. Guía de Desarrollo Mobile - NEFIJJ

## 1. Requisitos
- Node.js LTS y npm.
- Expo Go instalado en el dispositivo para pruebas de desarrollo.
- Backend NEFIJJ ejecutándose y accesible desde el dispositivo.

La carpeta `mobile/` puede estar vacía al iniciar. Crear el proyecto Expo una sola vez; no ejecutar el generador encima de una aplicación existente.

## 2. Inicializar la aplicación
Desde la raíz del repositorio, solo si `mobile/` aún no contiene un proyecto:

```powershell
cd mobile
npx create-expo-app@latest . --template blank
npm install axios @react-navigation/native @react-navigation/native-stack
npx expo install expo-secure-store react-native-screens react-native-safe-area-context
```

Confirmar en `package.json` las dependencias instaladas y las versiones compatibles. La app debe separar la presentación de las llamadas HTTP, manejar estados de carga/error y no duplicar reglas de autorización que corresponden al backend.

## 3. URL de la API
Configurar `EXPO_PUBLIC_API_URL` en el entorno local, por ejemplo:

```text
EXPO_PUBLIC_API_URL=http://192.168.1.20:8000/api/v1
```

Reemplazar la IP de ejemplo por la IP LAN real del equipo. `localhost` dentro de un teléfono apunta al teléfono, no al computador. Para emulador Android puede utilizarse `10.0.2.2` si el entorno lo admite. Asegurar que ambos dispositivos estén en la misma red y que el firewall permita la conexión. La configuración `EXPO_PUBLIC_*` no debe contener secretos.
Copiar `.env.example` como `.env.local` y configurar también la IP LAN del equipo en `DJANGO_ALLOWED_HOSTS` dentro de `backend/.env`.

Si el teléfono no puede iniciar sesión, comprobar desde su navegador `http://<IP-LAN-DEL-EQUIPO>:8000/api/v1/auth/token/`. Una respuesta HTTP `405 Method Not Allowed` es esperada para GET e indica que Django y la ruta son accesibles. Si no carga, iniciar Django con `python manage.py runserver 0.0.0.0:8000`, confirmar que el teléfono y el computador están en la misma red y permitir TCP 8000 en el firewall. Después de cambiar `.env.local`, reiniciar Expo con `npx expo start --clear`.

La IP LAN se detecta dinámicamente y puede cambiar. Consultar la dirección actual en Windows antes de conectar el teléfono. Si cambia, actualizar `EXPO_PUBLIC_API_URL` y `NEFIJJ_DEMO_ALLOWED_HOSTS`. La regla de firewall debe limitarse a una red privada de confianza y `LocalSubnet`; no cambiar a perfil privado una red pública.

## 4. Ejecutar y probar
Desde `mobile/`:

```powershell
npx.cmd expo start --lan --go
```

Usar `npx.cmd` en PowerShell si la política de ejecución bloquea `npx.ps1`. Ejecutar en una terminal interactiva para que Expo CLI muestre el QR. El QR que imprime Expo CLI es el **QR de desarrollo**: abre el bundle en Expo Go y no vincula una empresa. El **QR de invitación empresarial** es otro flujo; todavía no hay una pantalla que lo genere o escanee en la app. Teléfono y computador deben compartir una red Wi-Fi; no usar `localhost` en la URL de API del teléfono. Probar inicio/cierre de sesión, listado/reporte, filtros, asignación, estados y protocolos.

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

La navegación depende del rol devuelto por la API: el superadministrador abre gestión básica de organizaciones; el administrador organizacional abre el panel de incidencias; técnico y usuario final tienen flujos operativos distintos. Si la cuenta pertenece a varias organizaciones, debe elegir una antes de consultar datos y puede cambiarla desde la navegación. El cliente envía `X-Organization-ID`; el servidor valida la membresía.

El administrador organizacional puede filtrar incidencias por sede/estado, asignar o retirar un técnico activo de su sede, cerrar incidencias resueltas y reabrir cerradas. El usuario final crea reportes propios; el técnico atiende los que tiene asignados. Las pantallas móviles completas para usuarios, sedes, categorías y protocolos siguen pendientes.

Los registros que empiezan por `DEMO -` son ficticios y no representan protocolos reales. Para probar con credenciales, usar solamente el entorno separado `config.demo_settings` y la contraseña aleatoria temporal que imprime el comando DEMO. Las cuentas demo del MariaDB histórico siguen sin contraseña utilizable.

Si la app conserva el bundle anterior, detener Expo y arrancar desde `mobile/` con:

```powershell
npx.cmd expo start --clear
```

Esto recarga la configuración local y limpia la caché del bundler. La app actual usa Expo SDK 58, React Native 0.88 y navegación nativa; comprobar compatibilidad de dependencias con `npx expo install --check`.

## 5. Sesión y seguridad
- Guardar los tokens mediante `expo-secure-store`.
- Enviar el token de acceso en `Authorization: Bearer <access_token>`.
- Renovar la sesión según el endpoint de refresh y limpiar credenciales si la renovación falla o el usuario cierra sesión.
- No persistir contraseñas, no imprimir tokens y no permitir que datos del cliente establezcan rol, sede, reportante o estado inicial.
- Usar HTTPS en entornos compartidos o de producción. HTTP solo para desarrollo local controlado.

## 6. Estado de validación
El bundle Android se exportó correctamente después de los cambios de navegación multiempresa. La exportación genera un bundle, no un APK. La interacción visual en teléfono, selección de organización, cambio de tenant, asignación, estados, sesión expirada y pérdida de red aún requiere validación manual. Consultar [09_pruebas.md](./09_pruebas.md) y la bitácora [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md).

## 7. Roles, invitaciones y entrega instalable
Los roles móviles son `superadmin`, `organization_admin`, `technician`, `user` y `member` (selector pendiente de elección). El selector de organización y el header de tenant están implementados. La vinculación al tenant solo está disponible actualmente por API autenticada; no hay pantalla para introducir el código ni escanear un QR, ni carga de fotos/videos, captura GPS o wizard de tres pasos. La pantalla superadmin crea organizaciones y cambia su estado, pero no presenta analíticas globales. Los límites completos están en la sección 7 de [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md).

`expo export --platform android` genera un bundle exportado, no un APK instalable. La generación y firma de un APK requieren un flujo de compilación Android (por ejemplo, EAS Build o Gradle local), configuración de credenciales de firma y validación en dispositivo. No se garantiza que un servicio de compilación alojado sea gratuito; no se ha generado ni validado un APK en este proyecto.
