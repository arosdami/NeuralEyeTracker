@echo off
setlocal

cd /d "%~dp0"

where npm >nul 2>nul
if errorlevel 1 (
    echo HIBA: Az npm nem talalhato. Telepitsd a Node.js-t, majd inditsd ujra.
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo HIBA: A Python nem talalhato. Telepitsd a Python 3-at, majd inditsd ujra.
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo Elso inditas: fuggosegek telepitese...
    call npm install
    if errorlevel 1 (
        echo HIBA: A fuggosegek telepitese nem sikerult.
        pause
        exit /b 1
    )
)

echo Python tracker API inditasa: http://127.0.0.1:8765
start "Neural Eye Tracker API" cmd /k "python backend_server.py"

echo.
echo Neural Eye Tracker klinikai munkaterulet indul...
echo A bongeszoben nyisd meg: http://127.0.0.1:5173/
echo A kamerat a feluleten a Tracker inditasa gombbal lehet megnyitni.
echo A Python API kulon ablakban fut; leallitasahoz zarj be azt az ablakot.
echo.

call npm run dev

if errorlevel 1 (
    echo.
    echo HIBA: A fejlesztoi szerver leallt vagy nem indult el.
    pause
)

endlocal
