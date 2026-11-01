# Seguridad
# 06. Políticas de Seguridad - NEFIJJ

## 1. Introducción
La seguridad en **NEFIJJ** es un pilar fundamental para proteger los datos institucionales, la privacidad de los usuarios y garantizar que solo el personal autorizado manipule o resuelva incidencias.

## 2. Seguridad en el Backend (Django)
* **Hashing de Contraseñas:** Las contraseñas de los usuarios nunca se guardan en texto plano. Se utilizará el algoritmo predeterminado de Django (PBKDF2 con SHA256 o Argon2) para transformar las credenciales en hashes seguros en la base de datos MySQL.
* **Autenticación por Tokens (JWT):** Las sesiones de usuario se manejan mediante JSON Web Tokens (JWT). Al iniciar sesión correctamente, el servidor emite un token de acceso de corta duración que debe enviarse en cada petición protegida.
* **Protección contra CSRF y XSS:** Django incluye protección nativa contra falsificación de peticiones en sitios cruzados (CSRF) y inyecciones de código malicioso.

## 3. Seguridad en la Aplicación Móvil (React Native / Expo)
* **Almacenamiento de Tokens:** Los tokens de acceso JWT y datos sensibles de sesión no se guardarán en almacenamiento plano (`AsyncStorage` inseguro). Se utilizará **Expo SecureStore** para cifrarlos dentro del llavero de seguridad nativo del dispositivo móvil (Android/iOS).
* **Comunicaciones Cifradas:** Todas las peticiones HTTP realizadas desde la app móvil hacia el servidor Django deben realizarse bajo protocolos seguros (HTTPS en producción).

## 4. Control de Acceso por Roles (RBAC)
El sistema valida en cada endpoint que el usuario tenga los permisos necesarios:
* **Estudiante/Usuario:** Solo puede crear incidencias y ver el estado de sus propios reportes.
* **Técnico:** Puede visualizar y cambiar el estado de las incidencias asignadas a su sede (`location_id`).
* **Administrador:** Control total sobre usuarios, sedes y catálogos de la plataforma.