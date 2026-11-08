# 11. Hoja de ruta funcional propuesta - NEFIJJ

## 1. Propósito y estado
Este documento organiza las nuevas ideas del prompt maestro en fases revisables.
La Fase 0 de definición de alcance está completada con las decisiones confirmadas
por el usuario. Las Fases 1 a 5 están implementadas; las pruebas funcionales en
teléfono de las Fases 3 a 5 quedan pendientes.
La Fase 6 requiere decisiones de producto antes de iniciar. No se fijan fechas.

Los números ordenan el tema y sus dependencias sugeridas; no significan que
todas las fases estén aprobadas para implementarse en ese orden. Cada fase
requiere alcance y pruebas de aceptación antes de programarse.

## 2. Estado actual que sirve de base
- El backend ya tiene organizaciones, membresías y aislamiento de recursos por
  tenant. `OrganizationMembership` define el rol y la sede activa; `is_superuser`
  es el acceso global a la plataforma.
- Las categorías ya pertenecen a una organización. El administrador puede
  consultarlas, crearlas, editarlas y desactivarlas desde la app. La eliminación
  física no se propone porque las incidencias históricas pueden referenciarlas.
- La API crea, previsualiza y revoca invitaciones de un uso. Solo conserva el
  hash del código y calcula vencimiento en siete días hábiles de Colombia. La
  app permite generar/mostrar y escanear el QR; falta validación manual en un
  dispositivo.
- La app ya incluye una pantalla para crear, activar y suspender organizaciones
  para el superadministrador, con listado y conteos de registradas, activas y
  suspendidas.
- El técnico actual equivale parcialmente al rol operativo/resolutor del prompt:
  pertenece a una sede y un administrador lo asigna manualmente. El rol
  `resolver`, las áreas y el enrutamiento automático no están implementados.
- Los protocolos actuales son contenido informativo estático. No hay alertas
  operativas en tiempo real ni notificaciones push.
- La app ya permite crear reportes con categoría y evidencia fotográfica. No
  captura ni envía ubicación GPS; esa capacidad requiere definir consentimiento,
  permisos y tratamiento de ubicación.

## 3. Fases propuestas

### Fase 0 - Confirmar alcance y reglas de producto
**Objetivo:** precisar las decisiones que cambian el modelo, la navegación o la
seguridad antes de desarrollar.

**Estado: completada; decisiones confirmadas por el usuario.**

- **Panel superadmin:** conservar Django Admin como consola web y la gestión
  móvil existente. No crear una consola web independiente en este alcance.
- **QR:** representa una invitación a una organización existente. Se reutilizará
  el flujo de invitación seguro ya implementado; escanear no crea empresas ni
  vincula un dispositivo permanentemente.
- **Roles y asignación:** conservar `superadmin`, `organization_admin`,
  `technician` y `user`, así como la asignación manual actual. No agregar ahora
  el rol `resolver` ni el enrutamiento por áreas.
- **Alertas:** la decisión inicial fue diferirlas. Después el usuario aprobó la
  Fase 6 y precisó autoridad, destinatarios, confirmación, reintentos,
  cancelación y vencimiento; el estado actual se registra en esa fase.
- **GPS:** no capturar ubicación GPS en los reportes. La fecha/hora del servidor
  se conserva como hasta ahora.
- **Contador de empresas:** contar organizaciones registradas y mostrar por
  separado las activas y suspendidas. Este número no se describirá como
  actividad reciente ni como cantidad de empresas con usuarios activos.

Esta definición de alcance es documental y no requiere ni autoriza migraciones,
cambios de código o modificaciones a la base operativa.

### Fase 1 - Categorías propias por organización
**Objetivo:** asegurar que cada administrador personalice el catálogo de
incidencias de su organización (por ejemplo, escuela: Infraestructura, Aseo y
Disciplina; seguridad: Acceso, Cámaras e Intrusión).

**Estado: completada.** La capacidad principal ya estaba implementada: categorías
asociadas a organización, consulta dinámica en reportes, creación, edición y
desactivación desde la app. Se añadió validación de nombres duplicados dentro
del tenant, con un error de validación claro en vez de dejar que el conflicto
llegue a la base de datos.

**Criterios de aceptación propuestos:**
- El administrador solo lista y administra categorías del tenant activo.
- No se permite usar en un reporte una categoría de otra organización o
  desactivada.
- Un catálogo vacío tiene una respuesta clara para el administrador y para quien
  intenta reportar.
- Desactivar conserva incidencias e historial; la reactivación y la unicidad del
  nombre dentro de la organización se comportan de forma consistente.
- Las pruebas del backend cubren aislamiento por tenant, duplicados al crear y
  editar, visibilidad de categorías inactivas y rechazo de reportes con una
  categoría inactiva o de otro tenant.
- La pantalla móvil existente carga categorías de la organización activa y
  muestra estados vacíos y errores. La interacción móvil no se ejecutó como
  prueba automatizada en esta fase.

**Validación realizada:** las 21 pruebas de `IncidentApiTests` pasaron usando
`config.demo_settings`. No se modificó el esquema de base de datos.

### Fase 2 - Listado y métricas de empresas para superadmin
**Objetivo:** mostrar un listado global de organizaciones y un contador
comprensible en la consola elegida durante la Fase 0.

**Estado: completada.** El endpoint global de organizaciones entrega, además de
la lista paginada, los conteos de organizaciones registradas, activas y
suspendidas. La gestión móvil muestra esos tres valores y el identificador,
nombre, slug y estado de cada organización. Crear, suspender y reactivar
refresca la lista y los conteos después de que el servidor confirma la
operación.

**Criterios de aceptación propuestos:**
- El total se obtiene del backend y se distingue, como mínimo, entre empresas
  activas y suspendidas.
- La pantalla lista nombre, identificador y estado; los datos usan paginación
  cuando sea necesario.
- Crear, activar y suspender mantiene el comportamiento existente y actualiza
  listado y contadores tras una respuesta exitosa.
- Solo `is_superuser` puede ver o modificar el registro global. Los
  administradores de empresa no acceden a métricas ni a otros tenants.
- La palabra «usando» se acompaña de la definición acordada; no se presenta como
  actividad en tiempo real si no se mide esa actividad.

**Validación realizada:** las pruebas de `OrganizationApiTests` verifican
conteos, cambio de estado y denegación de acceso/actualización para un
administrador de organización. La exportación del bundle Android de Expo
completó correctamente. Los conteos describen organizaciones registradas y
estado administrativo; no miden uso ni actividad reciente.

### Fase 3 - Invitación y vinculación mediante QR
**Objetivo:** facilitar el ingreso a una organización con un QR seguro y un
flujo de aceptación dentro de la app.

**Estado: implementación completada; falta validación manual en teléfono.**

**Base reutilizable:** endpoint de invitaciones existente, código aleatorio de un
uso almacenado como hash, revocación y vencimiento de siete días hábiles de
Colombia. El QR representa directamente el código existente; no se añadieron
campos ni credenciales duplicadas.

**Flujo implementado:** un administrador autorizado genera y muestra el QR, y
puede revocar la invitación. El usuario inicia sesión con una cuenta existente,
escanea el QR o ingresa el código, previsualiza la organización, elige una sede
activa y confirma. El backend valida autenticación, token, vencimiento,
revocación, uso único, estado del tenant y sede antes de crear la membresía.
El QR no crea una cuenta ni vincula un dispositivo de forma permanente.

**Criterios de aceptación:**
- Los códigos no incluyen secretos permanentes ni datos personales innecesarios.
- Un código expirado, revocado o usado no puede volver a vincular usuarios.
- El usuario no puede elegir una sede de otro tenant.
- El QR de desarrollo de Expo Go se distingue del QR de invitación empresarial.
- Pruebas cubren replay, expiración, revocación, cuenta autenticada y aislamiento.
- La vista previa muestra solo sedes activas y no consume el código; los listados
  administrativos no devuelven códigos ni hashes.

**Validación realizada:** 12 pruebas de API cubren creación/hash/vencimiento,
previsualización, sedes activas, rechazo de códigos revocados/expirados,
consumo de un solo uso y listado sin secretos. `expo install --check` y la
exportación Android pasaron. Falta escanear y completar el flujo en un teléfono
real con una cuenta de prueba.

### Fase 4 - Flujo móvil de empleado/usuario
**Objetivo:** simplificar inicio, reporte e historial sin debilitar autenticación
ni permisos.

**Estado: implementación móvil completada; validación manual en teléfono pendiente.**

Alcance implementado:
- Inicio con marca NEFIJJ y acceso a la vinculación mediante el flujo QR aprobado.
- Menú de usuario con «Reportar incidencia» y «Mis reportes».
- Formulario breve con categorías dinámicas del tenant, evidencia opcional y
  estados de envío/error y confirmación de creación.
- Historial propio con estados `pendiente`, `en_proceso`, `resuelta` y `cerrada`,
  fechas presentadas con hora local del dispositivo a partir de la fecha del
  servidor.
- Captura automática de fecha y hora en el servidor. La ubicación GPS es opcional
  y no se añadirá hasta acordar consentimiento, permisos, retención y visibilidad.

**Criterios de aceptación:**
- El usuario solo ve sus reportes; organización, sede y reportante se derivan de
  la membresía autorizada en el servidor. La API existente tiene prueba de
  aislamiento por reportante.
- Fallos de cámara, selección de evidencia o red muestran error y no limpian el
  formulario antes de una respuesta exitosa.
- La UI muestra una confirmación tras crear el reporte y permite abrir el
  historial; la categoría sigue siendo requerida y la evidencia es opcional.
- No se solicita ni captura ubicación GPS.

**Validación realizada:** exportación Android y suite backend aprobadas en
SQLite; la API conserva el filtro de reportes propios. Falta prueba manual de
reporte, cámara/galería, estado de error y consulta en un teléfono real.

### Fase 5 - Operación del administrador y del responsable
**Objetivo:** completar la bandeja de control para administrar incidencias en el
tenant y sede autorizados.

**Estado: implementación completada; validación manual en teléfono pendiente.**

Alcance implementado:
- Listar y filtrar incidencias por sede, estado, prioridad y categoría; cargar
  páginas adicionales sin perder los filtros.
- Asignar o desasignar un técnico activo de la misma organización y sede,
  según validación del backend.
- Ejecutar las transiciones permitidas y consultar el historial completo de
  auditoría, incluyendo cambios de estado y asignación.

El rol `resolver`, las áreas y el enrutamiento automático siguen fuera del
alcance implementado. Si se aprueban, deben diseñarse por separado de
`Category`, con migración gradual y reglas explícitas; no cambiar roles
existentes por suposición.

**Validación automatizada:** suite backend aprobada en SQLite; incluye filtros
de prioridad y categoría, sin exponer incidencias al filtrar una categoría de
otra organización. Falta probar en teléfono filtros, paginación, asignación,
cambios de estado e historial.

### Fase 6 - Alertas de emergencia en tiempo real
**Estado: implementación en código completada; preparación EAS y prueba en
dispositivo pendiente.**

Alcance aprobado e implementado:
- Solo un administrador de organización activa puede emitir o cancelar. Los
  destinatarios son todos los miembros activos del tenant seleccionado con un
  dispositivo push activo; el superadministrador no emite estas alertas.
- No se exige acuse. Cada intento registra estado y reintenta hasta tres veces:
  intento inicial, luego esperas de 1 y 5 minutos. Expo no confirma que el
  teléfono haya mostrado el aviso.
- Cada push caduca a los 15 minutos. Cancelar detiene reintentos de la alerta y
  programa un aviso de cancelación para todos los dispositivos activos.
- La app permite habilitar notificaciones con permiso explícito del sistema,
  mostrar historial y administrar alertas. La API registra emisor/cancelador,
  limita destinatarios al tenant y crea una cola durable. El comando
  `send_emergency_alerts` debe ejecutarse periódicamente (se recomienda cada
  minuto, con una sola instancia de worker).
- Requiere `EXPO_PUBLIC_EAS_PROJECT_ID`, un development build con
  `expo-notifications` y conectividad. Expo Go no permite validar la entrega
  push. No se envió ninguna notificación real durante la implementación.

Esta función no es equivalente a los protocolos informativos ni a los avisos
de sismos del SGC. No sustituye a los servicios oficiales y no garantiza la
entrega. No incluir datos personales o sensibles en el texto push.

La interfaz puede reservar el rojo para la alerta de emergencia como se propone,
pero primero debe acordarse cómo representar la prioridad `critica` de una
incidencia, que actualmente también usa un indicador rojo. No cambiar el
significado de colores sin actualizar accesibilidad y diseño completo.

**Pendiente de aceptación operativa:** configurar EAS y proveedor, programar el
worker, probar permiso/recepción/cancelación y fallos en dispositivos
autorizados; validar que ninguna alerta se presente como entrega garantizada.

### Fase 7 - Revisión visual y accesibilidad final
**Objetivo:** consolidar el estilo visual después de aprobar los flujos y reglas
funcionales.

Alcance propuesto: tipografía legible, paleta azul/neutral para navegación,
verde para éxito, rojo crítico solo según la regla de emergencia finalmente
aprobada, estados de carga/vacío/error, botones completos y usables en pantallas
pequeñas, accesibilidad y prueba manual por rol en un dispositivo real.

**Criterios de aceptación propuestos:** ninguna etiqueta ni control queda
recortado, los estados se distinguen sin depender solo del color y las acciones
siguen siendo accesibles con lector de pantalla.

## 4. Reglas técnicas y de seguridad transversales
- Mantener una sola fuente de verdad para rol, organización y sede: las
  membresías validadas por el backend. No confiar en `organization_id` enviado
  por el cliente para autorizar consultas.
- Usar los roles existentes mientras no se apruebe una migración explícita:
  `superadmin` por `is_superuser`, `organization_admin`, `technician` y `user`.
- No eliminar categorías con incidencias relacionadas; desactivar para
  conservar el historial.
- No guardar tokens de invitación en claro en la base de datos, bitácoras o
  documentos.
- Toda nueva migración debe tener respaldo, ensayo sobre copia representativa
  de MySQL/MariaDB y plan de reversión. No ejecutar cambios de esquema de
  producción sin autorización.
- No registrar contraseñas, JWT, códigos QR secretos, archivos `.env` ni datos
  sensibles en bitácoras.
- La lógica de permisos, alcance y validación siempre se aplica en el backend;
  ocultar botones en móvil no sustituye la autorización del servidor.

## 5. Aprobación y próximo paso
Las Fases 0 a 6 están implementadas en código; las Fases 3 a 6 requieren
validación manual en dispositivo. Para operar la Fase 6 se debe configurar el
proyecto EAS, compilar un development build y programar el worker de entregas.
La Fase 7 se mantiene posterior a la validación de los flujos.
