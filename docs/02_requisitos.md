# Requisitos
# 02. Requisitos del Sistema - NEFIJJ

## 1. Requisitos Funcionales (RF)
Los requisitos funcionales describen las acciones y operaciones que el sistema debe realizar:

* **RF01 - Gestión de Usuarios:** El sistema debe permitir el registro, autenticación y control de roles (Administrador General, Técnico de Soporte y Usuario/Estudiante) mediante tokens seguros.
* **RF02 - Reporte de Incidencias:** Los usuarios deben poder registrar una nueva incidencia especificando título, descripción, categoría (eléctrica, red, infraestructura, etc.) y la sede correspondiente.
* **RF03 - Arquitectura Multitenant por Sedes:** El sistema debe aislar o filtrar la información de las incidencias para que los técnicos solo visualicen los reportes asignados a su sede específica.
* **RF04 - Actualización de Estados:** Los técnicos y administradores deben poder cambiar el estado de una incidencia (Pendiente, En Proceso, Resuelta, Cerrada).
* **RF05 - Módulo de Emergencia:** La aplicación móvil debe incluir una sección de acceso rápido con números de contacto y protocolos de actuación ante emergencias.

## 2. Requisitos No Funcionales (RNF)
Los requisitos no funcionales describen las características de calidad, rendimiento y seguridad:

* **RNF01 - Rendimiento:** Las peticiones a la API REST de Django deben responder en un tiempo menor a 2 segundos bajo condiciones normales de red.
* **RNF02 - Seguridad y Encriptación:** Las contraseñas de los usuarios deben almacenarse utilizando algoritmos de encriptación seguros (Argon2 o PBKDF2), y la comunicación móvil debe protegerse mediante HTTPS/Tokens JWT.
* **RNF03 - Disponibilidad:** El entorno local de base de datos MySQL debe mantenerse operativo mediante el servicio de XAMPP durante las pruebas del equipo.
* **RNF04 - Portabilidad:** La aplicación móvil desarrollada en React Native y Expo debe ejecutarse correctamente en dispositivos Android mediante el uso de Expo Go.