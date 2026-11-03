@echo off
rem Copies TinyPC's output into a Room Builder folder so its renders, tours and models can be used there.
rem Copy only: nothing in Room Builder is deleted or overwritten with older files.
rem   sync-to-roombuilder.bat [RoomBuilder folder]     (default: D:\Projects\01_Active\RoomBuilder)
setlocal
set "HERE=%~dp0.."
set "RB=%~1"
if "%RB%"=="" set "RB=D:\Projects\01_Active\RoomBuilder"
if not exist "%RB%\server.py" (
  echo Room Builder not found at %RB%
  exit /b 1
)
echo Models   -^> %RB%\catalogue\models
for /d %%D in ("%HERE%\models\tpc_*") do robocopy "%%D" "%RB%\catalogue\models\%%~nxD" /E /XO /NFL /NDL /NJH /NJS >nul
echo Library  -^> %RB%\library
for /d %%D in ("%HERE%\renders\library\*") do robocopy "%%D" "%RB%\library\%%~nxD" /E /XO /NFL /NDL /NJH /NJS >nul
echo Tours    -^> %RB%\tours
robocopy "%HERE%\tours" "%RB%\tours" /E /XO /XF .gitkeep /NFL /NDL /NJH /NJS >nul
echo Done.
endlocal
