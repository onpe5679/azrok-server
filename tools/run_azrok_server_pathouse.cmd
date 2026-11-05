@echo off
setlocal

set "ROOT=<home>\Documents\<project-dir>\Azrok_Plaza"
set "AZROK_SPACE_NAME=PatHouse"
set "AZROK_USE_BINARY_0010_DEFAULTS=1"
set "AZROK_LEGACY_FORCE_PLAZA_ON_LOBBY="

cd /d "%ROOT%"
"C:\Python314\python.exe" azrok_server.py

