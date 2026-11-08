@echo off
title NEFIJJ - Frontend Expo (Mobile)
cd /d "%~dp0mobile"

echo ===================================================
echo     INICIANDO FRONTEND NEFIJJ (Expo Metro LAN)
echo ===================================================
echo.
echo [INFO] Configurando IP Wi-Fi fisica: 192.168.1.5
set REACT_NATIVE_PACKAGER_HOSTNAME=192.168.1.5
set EXPO_NO_TELEMETRY=1

echo.
echo [INFO] Iniciando Metro Bundler con cache limpia para Expo Go...
echo [INFO] Abre Expo Go en tu celular y escanea el codigo QR que saldra abajo.
echo.
npx.cmd expo start --clear --lan --go
pause

