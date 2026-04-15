@echo off
cd /d "%~dp0"

echo ============================================
echo   Product Recommend App - Starting...
echo ============================================
echo.

if exist env\Scripts\activate.bat (
    call env\Scripts\activate.bat
    streamlit run main.py
) else (
    echo [ERROR] Virtual environment "env" is missing or broken.
    echo ---------------------------------------------------------
    echo  Please follow these steps to fix:
    echo  1. Delete "env" folder.
    echo  2. Run: python -m venv env
    echo  3. Run: env\Scripts\activate.bat
    echo  4. Run: pip install -r requirements.txt
    echo ---------------------------------------------------------
    pause
    exit /b 1
)

pause
