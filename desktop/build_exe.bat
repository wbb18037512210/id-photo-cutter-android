@echo off
chcp 65001 >nul
setlocal
set VENV_PY=C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe
if not exist "%VENV_PY%" (
  echo 未找到受管 Python 环境，请先运行依赖安装。
  pause
  exit /b 1
)
set U2NET_HOME=%APPDATA%\.u2net_idcutter
"%VENV_PY%" -m PyInstaller --onedir --windowed --name 头像抠图 ^
  --hidden-import rembg --hidden-import onnxruntime --hidden-import cv2 ^
  --copy-metadata pymatting ^
  --add-data "models;models" main.py
echo.
echo 打包完成，程序位于 dist\头像抠图\头像抠图.exe
pause
