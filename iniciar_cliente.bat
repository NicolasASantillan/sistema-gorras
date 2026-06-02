@echo off
title Lanzador - Catálogo Clientes
:: Cambia la ruta de abajo por la carpeta real donde tenés guardado tu cliente_app.py
cd /d "%~dp0"
streamlit run cliente_app.py --server.port 8502
pause