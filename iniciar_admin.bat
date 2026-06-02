@echo off
title Lanzador - Control de Stock Administrador
:: Cambia la ruta de abajo por la carpeta real donde tenés guardado tu app.py
cd /d "%~dp0"
streamlit run stockapp.py
pause