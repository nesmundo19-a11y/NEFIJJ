# Pruebas
# 09. Plan de Pruebas y Validación - NEFIJJ

## 1. Introducción
El presente plan de pruebas define los casos de uso esenciales que deben validarse para asegurar que el sistema **NEFIJJ** cumple con los requisitos funcionales, de seguridad y de arquitectura multitenant antes de su entrega final.

## 2. Casos de Prueba Funcionales

### CP01 - Autenticación de Usuario (Login)
* **Objetivo:** Verificar que el sistema emita un token JWT válido y devuelva el rol y la sede correcta.
* **Pasos:** 
  1. Enviar credenciales correctas desde la app móvil o Thunder Client.
  2. Evaluar la respuesta del servidor.
* **Resultado Esperado:** Código HTTP 200 OK y entrega exitosa del token de acceso junto con el `location_id`.

### CP02 - Aislamiento por Sede (Multitenant)
* **Objetivo:** Comprobar que un técnico de una sede específica solo visualice los reportes de su área.
* **Pasos:**
  1. Iniciar sesión con un usuario de la "Sede Maicao".
  2. Consultar el listado de incidencias (`GET /api/v1/incidents/`).
* **Resultado Esperado:** El sistema solo debe retornar incidencias cuyo `location_id` coincida con la Sede Maicao, excluyendo las demás.

### CP03 - Registro de Nueva Incidencia
* **Objetivo:** Validar que la app móvil pueda registrar un reporte exitosamente en la base de datos.
* **Pasos:**
  1. Completar el formulario de nueva incidencia en la app móvil.
  2. Enviar la petición.
* **Resultado Esperado:** Código HTTP 201 Created y visualización inmediata del reporte en el panel general.

### CP04 - Consulta de Módulo de Emergencia
* **Objetivo:** Garantizar el acceso rápido a los protocolos de emergencia.
* **Pasos:**
  1. Ingresar a la sección de emergencias desde la app móvil.
* **Resultado Esperado:** Despliegue correcto de los números de contacto y guías de actuación de la sede.

## 3. Criterios de Aceptación Final
* El 100% de los casos de prueba anteriores deben arrojar resultados exitosos.
* No deben existir errores críticos en consola ni en Django ni en React Native durante la ejecución de las pruebas básicas.