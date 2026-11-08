# 02. Requisitos del Sistema - NEFIJJ

## 1. Roles y reglas generales
- **Superadministrador (`superadmin`):** acceso global; puede crear organizaciones y activar o suspenderlas. La app tiene una pantalla básica para esta gestión.
- **Administrador organizacional (`organization_admin`):** administra incidencias y recursos únicamente dentro de la organización activa a la que pertenece.
- **Técnico (`technician`):** pertenece a una organización y sede, consulta incidencias de su sede y actualiza las que tiene asignadas.
- **Usuario final (`user`):** puede pertenecer a varias organizaciones, selecciona el contexto activo y reporta/consulta sus propias incidencias.
- Las cuentas se crean o habilitan por administración; no existe registro público en la primera versión.
- El servidor obtiene rol, organización y sede de las membresías; no confía en valores enviados por la app. Para cuentas con varias organizaciones, la API usa `X-Organization-ID` y verifica la membresía.

## 2. Requisitos funcionales (RF)
- **RF01 - Cuentas y autenticación:** autenticar usuarios y emitir/renovar tokens JWT. Administradores gestionan cuentas, membresías, roles y sede asignada dentro de su organización.
- **RF02 - Reportar incidencia:** un usuario autenticado crea una incidencia con título, descripción, categoría y prioridad. El servidor asigna el reportante, la sede y el estado inicial `pendiente`.
- **RF03 - Consultar incidencias:** el usuario ve sus propios reportes; el técnico ve los de su sede; el administrador consulta las sedes de su organización y filtra por sede, estado, prioridad y categoría. El superadministrador tiene alcance global autorizado.
- **RF04 - Asignar y atender:** el administrador asigna un técnico de la misma organización y sede. El técnico asignado actualiza el estado permitido de la incidencia. Cada asignación y cambio de estado registra actor, fecha y valores anterior/nuevo.
- **RF05 - Flujo de estados:** `pendiente` → `en_proceso` → `resuelta` → `cerrada`. El técnico asignado puede pasar de pendiente a en proceso y de en proceso a resuelta. El administrador puede cerrar una incidencia resuelta y reabrir una cerrada en estado `en_proceso`, dejando registro de auditoría.
- **RF06 - Categorías y prioridades:** clasificar incidencias con categorías administrables y prioridad `baja`, `media`, `alta` o `critica`; si no se indica prioridad, usar `media`.
- **RF07 - Emergencias:** consultar protocolos y contactos activos correspondientes a la sede del usuario. El administrador gestiona estos datos por sede, dentro de su organización.
- **RF08 - Historial:** consultar el historial de cambios únicamente dentro del mismo alcance de acceso que la incidencia.
- **RF09 - Áreas y enrutamiento automático (pendiente):** el usuario elegirá un área operativa independiente de la categoría; el backend asignará la incidencia a un responsable activo configurado para esa área y sede. No se debe confundir con el `assigned_to` manual actual.
- **RF10 - Vigencia de invitaciones:** los códigos nuevos vencen tras siete días hábiles de Colombia: lunes a viernes, excluyendo festivos nacionales oficiales, calculados en `America/Bogota`. El conteo empieza el día hábil posterior a la emisión y conserva la hora local de emisión.
- **RF11 - Evidencia fotográfica:** desde el formulario móvil, el usuario puede tomar o seleccionar una foto JPG/PNG de hasta 10 MB y adjuntarla opcionalmente a una incidencia. El archivo se valida y almacena fuera de MySQL; la base conserva su ruta relativa. Su consulta requiere acceso autorizado a la incidencia. Falta validar el flujo en un teléfono y probar persistencia con la instancia MySQL operativa.
- **RF12 - Avisos de sismos del SGC (pendiente de integración):** el alcance acordado es enviar por push a todos los dispositivos registrados avisos informativos sobre sismos que el SGC ya haya registrado; no son alertas tempranas ni se requiere acuse. La entrega requiere internet y un development build de Expo, no Expo Go. La sede/área indicada se mostrará como la publique la fuente; no se filtrará por geografía local. Solo se proporcionó la página principal del SGC, no una API/feed verificable, por lo que la integración permanece pendiente. Se autorizó generar código de modelos/migración para las tablas necesarias, pero no ejecutar ni aplicar cambios en MySQL. La app no sustituye los canales oficiales de emergencia ni garantiza la entrega.
- **RF13 - Administración móvil de categorías:** los administradores autorizados pueden consultar, crear, editar y desactivar categorías de su organización desde la app. Falta validar el flujo por rol/tenant en un teléfono. Las categorías describen el tipo de incidencia y no sustituyen áreas/responsables.
- **RF14 - Alertas operativas de emergencia:** solo un administrador de organización activa puede emitir o cancelar una alerta para todos los miembros activos de su organización con dispositivo push registrado. No hay acuse de recepción/lectura. Se reintenta hasta tres veces con esperas progresivas; cada notificación caduca a los 15 minutos. Cancelar detiene reintentos pendientes y programa un aviso de cancelación para todos los dispositivos activos. La aceptación del servicio Expo no confirma que el dispositivo la haya mostrado; la entrega no está garantizada y no reemplaza los canales oficiales. Requiere development build y configuración EAS; no funciona en Expo Go.

## 3. Requisitos no funcionales (RNF)
- **RNF01 - Rendimiento:** objetivo de respuesta inferior a 2 segundos para operaciones habituales bajo carga normal, excluyendo latencia de red externa. Medir con datos y entorno representativos.
- **RNF02 - Seguridad:** almacenar contraseñas mediante los hashers de Django; usar JWT y HTTPS en producción; aplicar autorización en cada consulta y operación.
- **RNF03 - Aislamiento:** filtrar por organización y sede en el servidor y comprobar también el acceso al objeto solicitado por ID. No depender de filtros enviados por el cliente para limitar permisos.
- **RNF04 - Integridad:** validar referencias, transiciones de estado y coincidencia de organización/sede entre técnicos e incidencias; registrar cambios sensibles.
- **RNF05 - Portabilidad:** desarrollar la app con React Native y Expo; probar en Android con Expo Go. La API debe ser accesible desde la red del dispositivo.
- **RNF06 - Configuración:** credenciales, claves y direcciones sensibles se configuran mediante variables de entorno; no se suben al repositorio.
- **RNF07 - Disponibilidad de desarrollo:** MySQL o MariaDB local puede ejecutarse mediante XAMPP; el sistema no debe depender de XAMPP en producción. La instancia comprobada ejecuta MariaDB 10.11.16.
- **RNF08 - Experiencia visual y accesibilidad:** mantener navegación, jerarquía visual, formularios, estados de carga/vacío/error y accesibilidad coherentes, conservando permisos y validando los flujos por rol en un dispositivo real. La primera pasada visual está implementada; falta su validación manual.

## 4. Validación de aceptación
La versión se acepta cuando las pruebas del documento [09_pruebas.md](./09_pruebas.md) verifican autenticación, permisos por rol y sede, creación y flujo de incidencias, protocolos de emergencia y respuestas de error coherentes.

## 5. Estado y límites conocidos
- El backend implementa organizaciones, membresías, invitaciones, selección de tenant, filtros por organización y permisos para incidencias, sedes, usuarios, categorías y protocolos. La migración de datos tiene una prueba aislada de asignación y reversión.
- La app Expo implementa selección de organización, encabezado `X-Organization-ID`, gestión básica de organizaciones para superadministradores, panel de incidencias organizacional y flujos existentes de usuarios/técnicos.
- La app ya permite generar/revocar invitaciones QR y aceptarlas con una cuenta autenticada, eligiendo sede. La validación manual del escáner en teléfono sigue pendiente. Métricas/gráficas y pantallas completas para administrar personal, sedes y protocolos continúan pendientes.
- El inicio móvil de usuario separa el reporte del historial propio. El formulario mantiene categorías dinámicas, evidencia opcional, mensajes de envío/error y confirmación; fecha y hora las registra el servidor. No se captura GPS. Validación manual en dispositivo pendiente.
- Áreas/departamentos y enrutamiento automático por responsable no están implementados; actualmente se clasifica por categoría y la asignación del técnico la realiza un administrador.
- La API y app permiten adjuntar fotos, administrar categorías y emitir/cancelar alertas operativas. La Fase 6 está implementada en código, pero requiere configurar EAS, programar el worker, validar en development build y probar en teléfono. Los protocolos siguen siendo contenido informativo y separado de las alertas.
- El contrato inicial de avisos del SGC está definido; falta identificar y verificar un endpoint/feed oficial para integrar eventos reales. Los avisos del SGC y las alertas operativas de RF14 son funciones distintas. Los protocolos estáticos siguen siendo informativos. Los criterios están en [09_pruebas.md](./09_pruebas.md).
- El objetivo de rendimiento RNF01 no se ha medido bajo carga y no debe considerarse certificado.
- La exportación Android aprobada es un bundle, no un APK; se requiere comprobación manual de la UI y roles en dispositivo.
- Para el estado real de pruebas y red local, consultar [09_pruebas.md](./09_pruebas.md) y [10_bitacora_desarrollo.md](./10_bitacora_desarrollo.md).

## 6. Evolución pendiente de priorización
Las fases de flujo móvil de empleado, alertas push de emergencia y revisión
visual final están organizadas en [11_hoja_de_ruta_funcional.md](./11_hoja_de_ruta_funcional.md).
La Fase 3 de invitaciones QR está implementada, pendiente de validación manual
en teléfono. Las decisiones generales de alcance, roles, consola superadmin,
privacidad de ubicación y alertas están registradas en la Fase 0; cada fase
futura requiere priorización y autorización explícita antes de implementarse.
