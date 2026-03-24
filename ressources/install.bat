@echo off
echo Installation des dependances...

python -m pip install --upgrade pip

pip install -r librairies.txt

echo.
echo Installation terminee !
pause