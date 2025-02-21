gzdoom.exe ^
  -stdout ^
  -config TobyConfig.ini ^
  -altdeath ^
  +Toby_NarrationOutputType 2 ^
  +fraglimit 20 ^
  +map map01 ^
  +dmflags 16384 ^
  +dmflags 128 ^
  +dmflags 4096 ^
  -file TobyAccMod_V8-0.pk3 ^
  -file "./Addons/DOOM/TobyV8_Guns.pk3" ^
  -file "./Addons/DOOM/TobyV7_Monsters.pk3" ^
  -file "./Addons/DOOM/TobyV8_Pickups.pk3" ^
  -file "./Addons/DOOM/TobyV8_Decorations.pk3" ^
  -file "./Addons/MENU/TobyV7_SimpleMenu.pk3" ^
  -file "./Addons/MAPS/TobyDeathArena_V1-5.wad" ^
  | powershell -ExecutionPolicy Bypass -File DoomTTS.ps1