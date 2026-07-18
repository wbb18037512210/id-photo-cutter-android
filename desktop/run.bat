@echo off
chcp 65001 >nul
setlocal
REM 优先使用本项目对应的受管虚拟环境
set VENV_PY=C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe
if exist "%VENV_PY%" (
  "%VENV_PY%" "%~dp0main.py"
) else (
  echo 未找到受管 Python 环境，请先安装依赖或运行 build_exe.bat 生成的 exe。
  pause
)
