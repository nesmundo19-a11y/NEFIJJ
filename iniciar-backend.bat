@echo off
title NEFIJJ - Backend Django
cd /d "%~dp0backend"

echo ===================================================
echo     INICIANDO BACKEND NEFIJJ (Django REST API)
echo ===================================================
echo.
echo 1) Modo DEMO  (SQLite - No requiere XAMPP ni MySQL)
echo 2) Modo REAL  (MySQL / MariaDB en XAMPP puerto 3308)
echo.
set /p MODO="Selecciona una opcion [1 o 2, por defecto 1]: "

if "%MODO%"=="2" (
    echo.
    echo [INFO] Iniciando backend con MySQL en puerto 8000...
    echo [INFO] Recuerda tener MySQL de XAMPP encendido en puerto 3308.
    echo.
    .\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
) else (
    echo.
    echo [INFO] Iniciando backend DEMO con SQLite en puerto 8000...
    echo [INFO] Conectando a nefijj-demo.sqlite3...
    echo.
    .\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000 --settings=config.demo_settings
)
pause

