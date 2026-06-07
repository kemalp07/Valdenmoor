@echo off

cd /d "%~dp0"

title FantasyWorld - Baslatiliyor...

color 0A



echo.

echo  ==========================================

echo         FANTASYWORLD - VALDENMOOR

echo  ==========================================

echo.



:: Python check

echo [1/5] Python kontrol ediliyor...

python --version >nul 2>&1

if %errorlevel% neq 0 (

    echo Python bulunamadi. Indiriliyor...

    curl -o python_installer.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe

    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

    del python_installer.exe

    echo Python kuruldu!

) else (

    echo Python mevcut.

)



:: Node check

echo [2/5] Node.js kontrol ediliyor...

node --version >nul 2>&1

if %errorlevel% neq 0 (

    echo Node.js bulunamadi. Indiriliyor...

    curl -o node_installer.msi https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi

    msiexec /i node_installer.msi /quiet /norestart

    del node_installer.msi

    echo Node.js kuruldu!

) else (

    echo Node.js mevcut.

)



:: Backend deps

echo [3/5] Backend bagimliliklari...

if not exist ".venv\Scripts\uvicorn.exe" (

    echo Sanal ortam ve paketler hazirlaniyor...

    if not exist ".venv" python -m venv .venv

    .venv\Scripts\pip install -r backend\requirements.txt --quiet

    echo Backend hazir!

) else (

    echo Backend zaten kurulu, paketler guncelleniyor...

    .venv\Scripts\pip install -r backend\requirements.txt --quiet

)



:: Frontend deps

echo [4/5] Frontend bagimliliklari...

if not exist "frontend\node_modules" (

    echo Paketler yukleniyor...

    pushd frontend

    call npm install --silent

    popd

    echo Frontend hazir!

) else (

    echo Frontend zaten kurulu.

)



:: Port 8001 doluysa eski backend'i kapat
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: Start

echo [5/5] Baslatiliyor...

echo.

echo  Backend:  http://localhost:8001

echo  Frontend: http://localhost:8081

echo.

echo  Ayri pencereler acilacak. Backend loglari "FantasyWorld Backend" penceresinde.

echo.



start "FantasyWorld Backend" cmd /k "cd /d "%~dp0" && .venv\Scripts\uvicorn backend.main:app --reload --port 8001"

timeout /t 4 /nobreak >nul

start "FantasyWorld Frontend" cmd /k "cd /d "%~dp0frontend" && npx expo start --web"

timeout /t 6 /nobreak >nul

start http://localhost:8081



echo  FantasyWorld acildi!

echo  Bu pencereyi kapatabilirsin; servisler ayri pencerelerde calisir.

timeout /t 3 /nobreak >nul

