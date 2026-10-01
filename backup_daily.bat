@echo off

cd /d C:\data\git\Jewelry-Working-Flow-System

venv\Scripts\python.exe manage.py backup_db
if errorlevel 1 exit /b %errorlevel%

venv\Scripts\python.exe manage.py cleanup_photos
if errorlevel 1 exit /b %errorlevel%

exit /b 0