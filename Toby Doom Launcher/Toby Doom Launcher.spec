# Toby Doom Launcher.spec
block_cipher = None

# Import to help locate files
from pathlib import Path
import accessible_output2

# Get the accessible_output2 installation directory
ao2_path = Path(accessible_output2.__file__).parent

# Define asset folders and files that should exist
asset_folders = [
    ('TobyCustom', 'TobyCustom'),
]

# Add DLLs needed by accessible_output2
dlls = [
    (str(ao2_path / 'lib/dolapi.dll'), '.'),
    (str(ao2_path / 'lib/nvdaControllerClient32.dll'), '.'),
    (str(ao2_path / 'lib/nvdaControllerClient64.dll'), '.'),
    (str(ao2_path / 'lib/ZDSRAPI_x64.dll'), '.'),
    (str(ao2_path / 'lib/PCTKUSR64.dll'), '.'),
    (str(ao2_path / 'lib/PCTKUSR.dll'), '.'),
    (str(ao2_path / 'lib/SAAPI32.dll'), '.'),
    (str(ao2_path / 'lib/ZDSRAPI.dll'), '.')
]

# Combine all data files
all_datas = asset_folders + dlls

a = Analysis(['Toby Doom Launcher.py'],
             pathex=[],
             binaries=[],
             datas=all_datas,
             hiddenimports=['accessible_output2.outputs.nvda',
                           'accessible_output2.outputs.jaws',
                           'accessible_output2.outputs.window_eyes',
                           'accessible_output2.outputs.system_access',
                           'accessible_output2.outputs.dolphin',
                           'accessible_output2.outputs.sapi5'],
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
