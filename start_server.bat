@echo off

cd /d C:\data\git\Jewelry-Working-Flow-System

call venv\Scripts\activate.bat

waitress-serve --host=0.0.0.0 --port=8000 config.wsgi:application

pause