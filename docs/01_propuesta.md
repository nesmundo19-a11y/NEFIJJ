# 01. Propuesta del Proyecto - NEFIJJ

## 1. Nombre
**NEFIJJ** - Sistema multisedes para la gestión de incidencias institucionales.

## 2. Descripción y alcance
NEFIJJ centraliza el reporte, seguimiento y resolución de incidencias de infraestructura y operación universitaria, inicialmente para la Universidad de La Guajira. Incluye una aplicación móvil, una API REST y una base de datos relacional compartida, con separación lógica de la información por sede.

El sistema permite que los usuarios reporten problemas y consulten sus propios casos; los técnicos atiendan los casos asignados dentro de su sede; y los administradores generales administren usuarios, catálogos, sedes y operaciones de todas las sedes. También ofrece protocolos y contactos de emergencia asociados a cada sede.

La versión actual no implementa asignación automática, chat en tiempo real, seguimiento GPS, notificaciones push ni registro público de cuentas. Como evolución se acordaron avisos informativos de sismos ya publicados por el SGC; esa integración sigue pendiente de identificar un feed/API oficial verificable. Las cuentas son creadas por un administrador.

## 3. Objetivos
### Objetivo general
Desarrollar una solución segura, mantenible y multiplataforma para registrar y dar seguimiento a incidencias institucionales.

### Objetivos específicos
1. Implementar una API con Django y Django REST Framework.
2. Aislar el acceso a la información por sede y por rol en cada operación del servidor.
3. Permitir reportar incidencias, asignarlas, actualizar su estado y consultar su historial.
4. Construir una aplicación móvil con React Native y Expo.
5. Hacer accesibles desde el móvil los protocolos y contactos de emergencia de la sede.

## 4. Usuarios y valor
- **Usuario/estudiante:** registra incidencias de su sede y consulta el estado de las que reportó.
- **Técnico:** consulta incidencias de su sede y gestiona las que le fueron asignadas.
- **Administrador general:** administra el sistema y puede operar en todas las sedes.

La centralización y el historial de cambios mejoran la trazabilidad y ayudan a priorizar el trabajo de soporte sin exponer información de otras sedes a usuarios no autorizados.

## 5. Criterios de éxito
- Los permisos se aplican en el backend, no solo en la interfaz móvil.
- Un usuario no puede consultar ni modificar incidencias ajenas a su alcance.
- Cada incidencia conserva su sede, reportante, estado y fechas; los cambios relevantes quedan auditados.
- Los flujos principales funcionan en Android con Expo Go durante desarrollo y contra un servidor accesible desde el dispositivo.

## 6. Estado de implementación
- Backend Django REST Framework conectado a MariaDB local de XAMPP mediante el backend compatible con MySQL, con cuentas, sedes, incidencias, categorías, protocolos, JWT y control multisedes.
- Aplicación Expo con inicio de sesión, consulta y reporte de incidencias, protocolos y un panel operativo para administradores.
- Los datos `DEMO` son ficticios y sirven exclusivamente para pruebas; no son información institucional ni protocolos de emergencia reales.
- La administración móvil de categorías está implementada; la gestión de usuarios y sedes sigue en Django Admin o la API administrativa.
- La app ya permite adjuntar fotos a reportes y se mejoraron formularios/tarjetas. Falta validación en teléfono y una prueba de persistencia de imágenes en MySQL. Los protocolos existentes son información estática. Los avisos informativos de sismos del SGC se acordaron como trabajo futuro, pero no se implementarán hasta verificar una fuente oficial de datos.
- Las pruebas automatizadas de backend usan SQLite en memoria. Las pruebas manuales de todos los flujos en un teléfono aún deben completarse.

La bitácora técnica, los comandos que se ejecutaron y los pendientes están en [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md).

## 7. Evolución a una plataforma multiempresa
El backend ya incorpora organizaciones, membresías con rol y sede, aislamiento de incidencias/categorías, invitaciones de un uso y selección de organización. La app móvil envía el tenant activo y tiene navegación inicial por rol, selector de organización y gestión básica de organizaciones para superadministradores.

La entrega sigue parcial: faltan la prueba de la migración con una copia representativa de MariaDB, una revisión manual en teléfono y varias pantallas de administración organizacional. La interfaz móvil de invitaciones/vinculación QR ya está implementada; su validación en dispositivo sigue pendiente. El estado verificado y los límites están en [09_pruebas.md](./09_pruebas.md) y [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md).

Decisión de cliente: una sola app operativa para administradores de empresa, técnicos/responsables y usuarios; usar Django Admin como consola web separada del superadministrador en el MVP. No se requieren dos APKs. El QR de Expo Go solo carga la app de desarrollo y no crea ni vincula una empresa.

El trabajo de invitación QR, el contador/listado global de empresas, el flujo
móvil de empleado y las alertas de emergencia están organizados por fases en
[11_hoja_de_ruta_funcional.md](./11_hoja_de_ruta_funcional.md). Las fases 0 a 6 están implementadas en código; las fases 3 a 6 requieren
validación en dispositivo. Para la Fase 6 se definieron administradores
organizacionales como emisores, destinatarios activos del tenant, sin acuse,
tres intentos progresivos, caducidad push de 15 minutos y cancelación dirigida
a todos. Su operación requiere EAS, un development build y un worker programado.
