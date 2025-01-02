# Toby Doom Launcher.spec
import os
from PyInstaller.utils.hooks import collect_dynamic_libs

block_cipher = None

# Define asset folders that should exist in current directory
asset_folders = [
    ('TobyCustom', 'TobyCustom'),
]

# Collect NVDA DLL files
nvda_dlls = []
accessible_output2_path = None

try:
    import accessible_output2
    accessible_output2_path = os.path.dirname(accessible_output2.__file__)
    
    # Add both 32-bit and 64-bit DLLs
    nvda_dlls.extend([
        (os.path.join(accessible_output2_path, 'lib', 'nvdaControllerClient32.dll'), '.'),
        (os.path.join(accessible_output2_path, 'lib', 'nvdaControllerClient64.dll'), '.'),
    ])
except ImportError:
    print("Warning: accessible_output2 not found")

a = Analysis(['Toby Doom Launcher.py'],
             pathex=[],
             binaries=nvda_dlls,  # Add the NVDA DLLs to binaries
             datas=asset_folders,
             hiddenimports=[
                 'PySide6.QtXml',
                 'accessible_output2.outputs.auto',
                 'accessible_output2.outputs.nvda',  # Add explicit NVDA import
                 'speechd',
                 'setproctitle'
             ],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# Add accessible_output2 lib directory to search paths
if accessible_output2_path:
    a.datas += [(f'lib/{os.path.basename(f)}', os.path.join(accessible_output2_path, 'lib', f), 'DATA')
                for f in os.listdir(os.path.join(accessible_output2_path, 'lib'))
                if f.endswith('.dll')]

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
          console=True,
          disable_windowed_traceback=False,
          argv_emulation=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None)
