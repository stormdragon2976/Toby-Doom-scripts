gzdoom.exe ^
  -stdout ^
  -config TobyConfig.ini ^
  +Toby_NarrationOutputType 2 ^
  -file TobyAccMod_V8-0.pk3 ^
  -file "./Addons/DOOM/TobyV8_Guns.pk3" ^
  -file "./Addons/DOOM/TobyV7_Monsters.pk3" ^
  -file "./Addons/DOOM/TobyV8_Pickups.pk3" ^
  -file "./Addons/DOOM/TobyV8_Decorations.pk3" ^
  -file "./Addons/MENU/TobyV7_SimpleMenu.pk3" ^
  -file "./Addons/MAPS/TobyDoomLevels.wad" ^
  | powershell -ExecutionPolicy Bypass -File DoomTTS.ps1