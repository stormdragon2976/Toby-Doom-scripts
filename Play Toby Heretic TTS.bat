gzdoom.exe ^
  -stdout ^
  -config TobyConfig.ini ^
  +Toby_NarrationOutputType 2 ^
  -file TobyAccMod_V8-0.pk3 ^
  -file "./Addons/HERETIC/TobyHereticWeaponsV8.pk3" ^
  -file "./Addons/HERETIC/TobyHereticMonsters.pk3" ^
  -file "./Addons/HERETIC/TobyHereticItemsV8.pk3" ^
  -file "./Addons/HERETIC/TobyHereticDecorations.pk3" ^
  -file "./Addons/HERETIC/TobyHereticBeacons.pk3" ^
  -file "./Addons/HERETIC/TobyHereticMenu.wad" ^
  -file "./Addons/MENU/TobyV7_SimpleMenu.pk3" ^
  -file "./Addons/MAPS/TobyHereticLevels.wad" ^
  | powershell -ExecutionPolicy Bypass -File DoomTTS.ps1
