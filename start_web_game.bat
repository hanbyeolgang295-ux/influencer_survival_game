@echo off
cd /d "%~dp0"

echo 백만유튜버 나락 탈출 웹게임을 시작합니다.
echo 주소: http://127.0.0.1:8020/
echo.
echo 이 창을 닫으면 웹게임 주소 연결도 끊길 수 있습니다.
echo 시연이 끝날 때까지 이 창을 켜두세요.
echo.

start "" "http://127.0.0.1:8020/"
py -3 -m http.server 8020 --bind 127.0.0.1 --directory web
if errorlevel 1 (
  python -m http.server 8020 --bind 127.0.0.1 --directory web
)

pause
