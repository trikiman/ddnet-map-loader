@echo off
cd /d "%~dp0"
echo Starting DDNet Map Manager Server...
start /min python server.py
exit
