@echo off
title Simulador 3D - Rover Frugal 4WD/4WS (Three.js)
color 0A

echo ================================================================
echo       INICIANDO SIMULADOR 3D INTERATIVO - ROVER FRUGAL
echo ================================================================
echo.
echo Abrindo o prototipo 3D no navegador...
echo.

start "" "%~dp0prototipo_3d_standalone.html"

echo Pressione qualquer tecla para fechar esta janela.
pause >nul
