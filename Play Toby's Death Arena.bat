@echo off
setlocal enabledelayedexpansion

:: Default values
set "ipAddress=127.0.0.1"
set "fraglimit=20"
set "map=map01"
set "skill=3"
set "players=2"

:: Parse command line arguments
:parse_args
if "%1"=="" goto :end_parse_args
if /i "%1"=="-host" set "host_mode=true" & set "players=%2" & shift & shift & goto :parse_args
if /i "%1"=="-join" set "join_mode=true" & set "ip_address=%2" & shift & shift & goto :parse_args
if /i "%1"=="-fraglimit" set "fraglimit=%2" & shift & shift & goto :parse_args
if /i "%1"=="-map" set "map=%2" & shift & shift & goto :parse_args
if /i "%1"=="-skill" set "skill=%2" & shift & shift & goto :parse_args
shift
goto :parse_args
:end_parse_args

:: Set up the command
set "cmd=gzdoom.exe -stdout -config TobyConfig.ini -altdeath"
if defined host_mode (
    set "cmd=!cmd! -host %players% -skill %skill%"
) else if defined join_mode (
    set "cmd=!cmd! -join %ip_address%"
)
set "cmd=!cmd! +fraglimit %fraglimit%"
set "cmd=!cmd! +map %map%"
set "cmd=!cmd! +dmflags 16384 +dmflags 128 +dmflags 4096"
set "cmd=!cmd! -file TobyAccMod_V7-5.pk3"
set "cmd=!cmd! "./Addons/DOOM/TobyV7_Guns.pk3""
set "cmd=!cmd! "./Addons/DOOM/TobyV7_Monsters.pk3""
set "cmd=!cmd! "./Addons/DOOM/TobyV7_Pickups.pk3""
set "cmd=!cmd! "./Addons/DOOM/TobyV7_Decorations.pk3""
set "cmd=!cmd! "./Addons/DOOM/TobyV7_Proximity-Prototype.pk3""
set "cmd=!cmd! "./Addons/MENU/TobyV7_SimpleMenu.pk3""
set "cmd=!cmd! TobyDeathArena_V1-0.wad"
set "cmd=!cmd! -deathmatch"
set "cmd=!cmd! +set sv_cheats 1"
set "cmd=!cmd! +dmflags2 512 +dmflags2 1024"
set "cmd=!cmd! -extratic -dup 3"

:: Execute the command
%cmd% | powershell -ExecutionPolicy Bypass -File DoomTTS.ps1

endlocal
