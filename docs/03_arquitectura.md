# Arquitectura
# 03. Arquitectura del Sistema - NEFIJJ

## 1. Patrón Arquitectónico General
El sistema **NEFIJJ** implementa una **Arquitectura en Capas orientada a Servicios (Client-Server)**, separando completamente la interfaz de usuario (Frontend Móvil) de la lógica de negocio (Backend API) y del almacenamiento persistente (Base de Datos Relacional).

## 2. Componentes de la Arquitectura

### A. Capa de Presentación (Frontend Móvil)
* **Tecnología:** React Native con Expo.
* **Función:** Interfaz gráfica para dispositivos móviles. Se encarga de capturar las acciones del usuario (registrar incidencias, consultar estados, visualizar protocolos) y comunicarse con el backend mediante peticiones HTTP asíncronas (Axios).

### B. Capa de Lógica de Negocio (Backend API)
* **Tecnología:** Django 5.x / Django REST Framework (DRF).
* **Función:** Cerebro del sistema. Procesa las reglas de negocio, valida los permisos de usuario mediante autenticación JWT, filtra la información según la sede (*multitenant*) y gestiona las respuestas en formato JSON.

### C. Capa de Persistencia (Base de Datos)
* **Tecnología:** MySQL 8.0 (administrada localmente mediante XAMPP).
* **Función:** Almacena de forma estructurada y relacional la información de usuarios, roles, sedes, categorías, incidencias y registros de auditoría.

## 3. Flujo de Comunicación (Multitenant)
1. El usuario inicia sesión desde la app móvil enviando sus credenciales.
2. Django valida la información y devuelve un token de acceso junto con el identificador de su sede (`sede_id`).
3. Cada vez que el usuario reporta o consulta una incidencia, la app móvil envía el token y el sistema filtra automáticamente las consultas a MySQL para mostrar solo los datos correspondientes a esa sede.