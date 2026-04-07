@echo off
set PY=F:\Visual2022\Python39_64\python.exe
if not exist .venv\Scripts\python.exe (
  %PY% -m venv .venv
)
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --prefer-binary
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
