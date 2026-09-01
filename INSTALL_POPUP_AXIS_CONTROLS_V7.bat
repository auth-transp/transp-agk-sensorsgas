@echo off
cd /d "%~dp0"
py -3.13 add_popup_axis_controls_v7.py
if errorlevel 1 py add_popup_axis_controls_v7.py
