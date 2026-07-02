@echo off
echo Setting up Voice-Based Email System...
python -m venv venv
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

if not exist .env (
    copy .env.example .env
    echo.
    echo IMPORTANT: A .env file was created from .env.example.
    echo Please open .env and set SECRET_KEY and FERNET_KEY before running the app.
    echo See README.md for the exact commands to generate them.
    echo.
)

echo Setup complete. Run run.bat to start the app.
pause
