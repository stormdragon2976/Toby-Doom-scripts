gzdoom.exe ^
  -stdout ^
  -config TobyConfig.ini ^
  +Toby_NarrationOutputType 2 ^
  -file TobyAccMod_V8-0.pk3 ^
  -file "./Addons/HEXEN/TobyHexenWeapons.pk3" ^
  -file "./Addons/HEXEN/TobyHexenMonsters.pk3" ^
  -file "./Addons/HEXEN/TobyHexenItems.pk3" ^
  -file "./Addons/HEXEN/TobyHexenDecorations.pk3" ^
  -file "./Addons/HEXEN/TobyHexenMenu.wad" ^
  -file "./Addons/MENU/TobyV7_SimpleMenu.pk3" ^
  | powershell -ExecutionPolicy Bypass  -File DoomTTS.ps1