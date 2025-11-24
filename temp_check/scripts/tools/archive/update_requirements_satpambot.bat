@echo off
cd /d G:\ProjectDiscord
call venv\Scripts\activate
pip install --upgrade pip setuptools
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt
git add requirements.txt
git commit -m "⬆️ Auto update dependencies to latest versions"
git push
pause
