# Propuesta
# 01. Propuesta del Proyecto - NEFIJJ

## 1. Nombre del Sistema
**NEFIJJ** - Sistema Multitenant de Gestión de Incidencias Institucionales.

## 2. Descripción General y Alcance
NEFIJJ es una plataforma web y móvil diseñada para centralizar, automatizar y gestionar el reporte y resolución de incidencias en infraestructuras institucionales (enfocado inicialmente en el entorno universitario de la Universidad de La Guajira). El sistema permite segmentar la operación por sedes y departamentos (arquitectura multitenant) para garantizar que cada administrador gestione únicamente los reportes de su área correspondiente.

## 3. Objetivos del Proyecto
* **Objetivo General:** Desarrollar un sistema software robusto y escalable para el registro y seguimiento de incidencias operativas y de infraestructura.
* **Objetivos Específicos:**
  1. Implementar una arquitectura multitenant basada en MySQL para aislar los datos por sedes institucionales.
  2. Proveer una API REST segura mediante Django Framework.
  3. Desarrollar una interfaz móvil multiplataforma con React Native y Expo para facilitar la reportería rápida en campo.
  4. Incorporar un módulo de protocolos de emergencia accesible de forma rápida.

## 4. Justificación
La gestión manual de incidencias genera retrasos operativos y pérdida de trazabilidad. NEFIJJ optimiza los tiempos de respuesta de los equipos técnicos mediante notificaciones centralizadas y un control estricto de roles y permisos.