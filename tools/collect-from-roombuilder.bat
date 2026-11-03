@echo off
rem Copies TinyPC's finished renders and tours back from a Room Builder folder into this project (for git).
rem Library entries are picked by name (folders with "tinypc" in them); tours by file name (tpc*.json).
rem Copy only: nothing is deleted.
rem   collect-from-roombuilder.bat [RoomBuilder folder]     (default: D:\Projects\01_Active\RoomBuilder)
setlocal
set "HERE=%~dp0.."
set "RB=%~1"
if "%RB%"=="" set "RB=D:\Projects\01_Active\RoomBuilder"
if not exist "%RB%\server.py" (
  echo Room Builder not found at %RB%
  exit /b 1
)
for /d %%D in ("%RB%\library\*tinypc*") do (
  echo %%~nxD
  robocopy "%%D" "%HERE%\renders\library\%%~nxD" /E /XO /XF room.blend view_*.png /NFL /NDL /NJH /NJS >nul
)
robocopy "%RB%\tours" "%HERE%\tours" tpc*.json /XO /NFL /NDL /NJH /NJS >nul
echo Done.
endlocal
