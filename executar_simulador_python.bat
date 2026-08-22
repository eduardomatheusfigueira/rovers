@echo off
title Simulador Fisico Avancado - Rover Frugal 4WD/4WS (Python)
color 0B

echo ================================================================
echo       INICIANDO SIMULADOR FISICO AVANCADO EM PYTHON
echo ================================================================
echo.
echo Modulos carregados:
echo - Cinematica 4WS/4WD (Siegwart ^& Nourbakhsh, 2004)
echo - Terramecanica e Carga Dinamica (J. Y. Wong, 2022)
echo - Suspensao Complacente Torsional C-STS (Jeong ^& Kim, 2025)
echo - Escada e Colisao de Blondel (NBR 9050: 2E+P=64cm)
echo.
echo Abrindo a interface grafica interativa...
echo.

python -m simulador_python.main

if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro ao iniciar o simulador.
    pause
)
