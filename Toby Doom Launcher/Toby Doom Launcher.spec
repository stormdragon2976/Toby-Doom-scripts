# Toby Doom Launcher.spec

block_cipher = None

# Define asset folders that should exist in current directory
asset_folders = [
    ('TobyCustom', 'TobyCustom'),
    ('DoomTTS.ps1', '.')
]

a = Analysis(['Toby Doom Launcher.py'],
             pathex=[],
             binaries=[],
             datas=asset_folders,  # Include the assets reference
             hiddenimports=['PySide6.QtXml'],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Toby Doom Launcher',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True)
