@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Access Review

set PY=.venv\Scripts\python.exe
if not exist "%PY%" (
  echo [!] Не знайдено .venv. Створіть віртуальне середовище Python у цій папці.
  pause
  exit /b 1
)

rem --- Python-залежності (лише якщо чогось бракує)
"%PY%" -c "import fastapi, uvicorn, pandas, multipart, openpyxl" >nul 2>&1
if errorlevel 1 (
  echo Встановлюю Python-залежності...
  "%PY%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [!] Не вдалося встановити залежності.
    pause
    exit /b 1
  )
)

rem --- Інтерфейс (збирається один раз)
if not exist "frontend\dist\index.html" (
  echo Збираю інтерфейс, це лише перший раз...
  call npm --prefix frontend install
  call npm --prefix frontend run build
  if not exist "frontend\dist\index.html" (
    echo [!] Не вдалося зібрати інтерфейс. Перевірте, що встановлено Node.js.
    pause
    exit /b 1
  )
)

echo.
echo Access Review працює: http://localhost:8000
echo Щоб зупинити, закрийте це вікно або натисніть Ctrl+C.
echo.

rem --- Відкрити браузер за кілька секунд, коли сервер вже піднявся
if not defined NO_BROWSER start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8000"

"%PY%" -X utf8 -m uvicorn server:app --host 127.0.0.1 --port 8000
echo.
echo Сервер зупинено. Якщо він не запустився, можливо, порт 8000 уже зайнятий.
pause
