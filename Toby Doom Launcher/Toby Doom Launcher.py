#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024 Stormux
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., Franklin Street, Fifth Floor,
# Boston MA  02110-1301 USA.


import configparser
import json
import sys
import os
import re
import subprocess
import time
import platform
import shutil
import glob
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from setproctitle import setproctitle
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QComboBox, QPushButton, QLabel, QSpinBox, QMessageBox, QLineEdit, QDialog,
    QDialogButtonBox, QRadioButton)
from PySide6.QtCore import Qt
import webbrowser

# Initialize speech provider based on platform
if platform.system() == "Windows":
    # Set up DLL paths for Windows
    if getattr(sys, 'frozen', False):
        # If running as compiled executable
        dllPath = os.path.join(sys._MEIPASS, 'lib')
        if os.path.exists(dllPath):
            os.add_dll_directory(dllPath)
        # Also add the executable's directory
        os.add_dll_directory(os.path.dirname(sys.executable))

    # Initialize Windows speech provider
    try:
        import accessible_output2.outputs.auto
        s = accessible_output2.outputs.auto.Auto()
        speechProvider = "accessible_output2"
    except ImportError as e:
        print(f"Failed to initialize accessible_output2: {e}")
        sys.exit()
else:
    # Linux/Mac path
    try:
        output = subprocess.check_output(["pgrep", "cthulhu"])
        speechProvider = "cthulhu"
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            import accessible_output2.outputs.auto
            s = accessible_output2.outputs.auto.Auto()
            speechProvider = "accessible_output2"
        except ImportError as e:
            try:
                import speechd
                spd = speechd.Client()
                speechProvider = "speechd"
            except ImportError:
                print("No speech providers found.")
                sys.exit()


class AccessibleComboBox(QComboBox):
    """ComboBox with enhanced keyboard navigation"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.pageStep = 5  # Number of items to jump for page up/down

    def keyPressEvent(self, event):
        currentIndex = self.currentIndex()
        itemCount = self.count()
        
        if event.key() == Qt.Key_PageUp:
            newIndex = max(0, currentIndex - self.pageStep)
            self.setCurrentIndex(newIndex)
        elif event.key() == Qt.Key_PageDown:
            newIndex = min(itemCount - 1, currentIndex + self.pageStep)
            self.setCurrentIndex(newIndex)
        elif event.key() == Qt.Key_Home:
            self.setCurrentIndex(0)
            # Force update and focus events
            self.setFocus()
            self.currentIndexChanged.emit(0)
            self.activated.emit(0)
        elif event.key() == Qt.Key_End:
            lastIndex = itemCount - 1
            self.setCurrentIndex(lastIndex)
            # Force update and focus events
            self.setFocus()
            self.currentIndexChanged.emit(lastIndex)
            self.activated.emit(lastIndex)
        else:
            super().keyPressEvent(event)


class SpeechHandler:
    """Handles text-to-speech processing for game output"""
    
    # Class-level constants for patterns
    FILTER_PATTERNS = [
        r'^----+$',
        r'^$',
        r'^[0-9]',
        r'^P_StartScript:',
        r'^(Facing |fluidsynth |INTRO|MAP[0-9]+|Music "|Unknown)',
        r'^(\[Toby Accessibility Mod\] )?READ.*',
        r'^ *TITLEMAP',
        r'^\[Toby Accessibility Mod\] (INTRO|READMe)([0-9]+).*',
        r'key card',
        r'^New PDA Entry:',
        r"^(As |Computer Voice:|Holy|I |I've|Monorail|Sector |Ugh|What|Where)",
        r'Script warning, "',
        r'Tried to define'
    ]
    
    TEXT_REPLACEMENTS = [
        (r'^\[Toby Accessibility Mod\] M_', r'[Toby Accessibility Mod] '),
        (r'^\[Toby Accessibility Mod\] ', r''),
        (r'^MessageBoxMenu$', r'Confirmation menu: Press Y for yes or N for no'),
        (r'^Mainmenu$', r'Main menu'),
        (r'^Skillmenu$', r'Difficulty menu'),
        (r'^Episodemenu$', r'Episode menu'),
        (r'^NGAME$', r'New game'),
        (r'^(LOAD|SAVE|QUIT)G$', r'\1 game'),
        (r'"cl_run" = "true"', r'run'),
        (r'"cl_run" = "false"', r'walk'),
        (r'UAC', r'U A C'),
        (r'^\+', r''),
        (r' ?\*+ ?', r'')
    ]
    
    def __init__(self):
        """Initialize the speech handler"""
        self.platform = platform.system()
        
        # Compile all regex patterns once at initialization
        self.filterPatterns = [re.compile(pattern) for pattern in self.FILTER_PATTERNS]
        self.textReplacements = [(re.compile(pattern), repl) 
                               for pattern, repl in self.TEXT_REPLACEMENTS]

    def speak(self, text: str) -> None:
        """Speak text using available speech method"""
        if not text:
            return
            
        if speechProvider == "speechd":
            spd.cancel()
            spd.speak(text)
        elif speechProvider == "accessible_output2":
            s.speak(text, interrupt=True)
        else:  # Cthulhu
            try:
                process = subprocess.Popen(
                    ["socat", "-", "UNIX-CLIENT:/tmp/cthulhu.sock"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                process.communicate(input=text)
            except Exception as e:
                print(f"Cthulhu error: {e}", file=sys.stderr)

    def process_line(self, line: str) -> Optional[str]:
        """Process a line of game output for speech"""
        # Skip empty lines
        if not line.strip():
            return None
            
        # Check if line should be filtered out
        for pattern in self.filterPatterns:
            if pattern.search(line):
                return None
                
        # Apply replacements
        processedLine = line
        for pattern, repl in self.textReplacements:
            processedLine = pattern.sub(repl, processedLine)
            
        return processedLine.strip() if processedLine.strip() else None

    def speak_thread(self, process: subprocess.Popen):
        """Thread to handle speech processing"""
        startSpeech = False  # Don't start speaking until after initial output
        
        while True:
            try:
                line = process.stdout.readline()
                if not line:
                    break
                
                lineStr = line.strip()
                
                # Wait for the initial separator before starting speech
                if not startSpeech:
                    if lineStr and all(c == '-' for c in lineStr):
                        startSpeech = True
                    continue
                
                processedLine = self.process_line(lineStr)
                if processedLine:
                    self.speak(processedLine)
                        
            except Exception as e:
                print(f"Error processing game output: {e}", file=sys.stderr)
                break


class MenuDialog(QDialog):
    """Dialog for game configuration options"""
    
    def __init__(self, title: str, options: Dict[str, dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.dialogOptions = options
        self.init_dialog_ui()

    def init_dialog_ui(self):
        """Initialize the dialog UI components"""
        dialogLayout = QVBoxLayout(self)
        
        for key, opt in self.dialogOptions.items():
            if opt['type'] == 'radio':
                dialogWidget = QRadioButton(opt['label'])
            elif opt['type'] == 'spinbox':
                # Create label first
                label = QLabel(opt['label'])
                dialogWidget = QSpinBox()
                dialogWidget.setRange(opt['min'], opt['max'])
                dialogWidget.setValue(opt.get('default', opt['min']))
                # Set accessibility label
                dialogWidget.setAccessibleName(opt['label'])
                # Add label to layout first
                dialogLayout.addWidget(label)
            elif opt['type'] == 'text':
                dialogWidget = QLineEdit()
                dialogWidget.setPlaceholderText(opt['placeholder'])
            elif opt['type'] == 'combobox':
                dialogWidget = AccessibleComboBox()
                dialogWidget.addItems(opt['items'])
                dialogLayout.addWidget(QLabel(opt['label']))
            else:
                continue
                
            setattr(self, f"{key}_widget", dialogWidget)
            dialogLayout.addWidget(dialogWidget)

        dialogButtons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialogButtons.accepted.connect(self.accept)
        dialogButtons.rejected.connect(self.reject)
        dialogLayout.addWidget(dialogButtons)

    def get_dialog_values(self) -> dict:
        """Get the current values from all dialog widgets"""
        values = {}
        for key in self.dialogOptions.keys():
            widget = getattr(self, f"{key}_widget")
            if isinstance(widget, QSpinBox):
                values[key] = widget.value()
            elif isinstance(widget, QComboBox):
                values[key] = widget.currentText()
            elif isinstance(widget, QRadioButton):
                values[key] = widget.isChecked()
            else:
                values[key] = widget.text()
        return values


class IWADSelector:
    """Handles IWAD file detection and selection"""
    
    def __init__(self):
        if platform.system() == "Windows":
            self.configFile = Path.cwd() / 'TobyConfig.ini'
        else:
            self.configFile = Path(os.getenv('XDG_CONFIG_HOME', Path.home() / '.config')) / 'gzdoom/gzdoom.ini'
        self.wadPaths = self._get_wad_paths()
        
    def _get_wad_paths(self) -> List[str]:
        """Extract IWAD search paths from GZDoom config"""
        if not self.configFile.exists():
            print("Config file not found")
            return []
            
        try:
            # Read the file directly to handle duplicate keys
            paths = []
            currentSection = None
            with open(self.configFile, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('['):
                        currentSection = line[1:-1]
                    elif currentSection == 'IWADSearch.Directories' and '=' in line:
                        key, value = line.split('=', 1)
                        if key.strip().lower().startswith('path'):
                            value = value.strip()
                            # Handle special paths
                            if value == '$DOOMWADDIR' or value == '$PROGDIR':
                                continue  # Skip these as they're GZDoom internal
                            elif value == '$HOME':
                                value = str(Path.home())
                            paths.append(value)
                
        except Exception as e:
            print(f"Error reading config: {e}", file=sys.stderr)
        
        # Additional paths to check
        if platform.system() == "Windows":
            paths.append(str(Path.cwd()))
        else:
                paths.append(str(Path("/usr/share/doom")))
                paths.append(str(Path("/usr/share/games/doom")))
                paths.append(str(Path.home() / ".local/games/doom"))
                paths.append(str(Path.home() / ".local/share/doom"))
        return paths

    def is_iwad(self, file_path: str) -> bool:
        """Check if a file is an IWAD or IPK3"""
        path = Path(file_path)
        if path.suffix.lower() == '.ipk3':
            return True
            
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return header == b'IWAD'
        except Exception:
            return False
            
    def find_iwads(self) -> Dict[str, str]:
        """Find all available IWADs in configured paths"""
        uniqueWads = {}
        
        for path in self.wadPaths:
            wadDir = Path(path)
            if not wadDir.is_dir():
                continue
                
            # Only look at files directly in the directory, not subdirectories
            for wadFile in wadDir.iterdir():
                if wadFile.is_file():
                    # Check if it's a WAD or IPK3 file
                    if wadFile.suffix.lower() in ['.wad', '.iwad']:
                        if self.is_iwad(str(wadFile)):
                            wadName = wadFile.stem.lower()
                            uniqueWads[wadName] = str(wadFile)
                    elif wadFile.suffix.lower() == '.ipk3':
                        if self.is_iwad(str(wadFile)):
                            wadName = wadFile.stem.lower()
                            uniqueWads[wadName] = str(wadFile)
                    
        return uniqueWads


class CustomGameDialog(QDialog):
    """Dialog for selecting and configuring custom games"""
    def __init__(self, customGames: Dict[str, dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Custom Game Selection")
        self.customGames = customGames

        # Create layout
        layout = QVBoxLayout(self)
        
        # Game selection combobox
        label = QLabel("Select Custom Game:")
        self.gameCombo = QComboBox()
        self.gameCombo.setAccessibleName("Custom Game Selection")
        self.gameCombo.addItems(sorted(customGames.keys()))
        self.gameCombo.setEditable(True)
        self.gameCombo.lineEdit().setReadOnly(True)
        # Connect enter key to accept
        self.gameCombo.lineEdit().returnPressed.connect(self.accept)
        
        layout.addWidget(label)
        layout.addWidget(self.gameCombo)

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.accept()
        else:
            super().keyPressEvent(event)

    def get_selected_game(self) -> Optional[str]:
        """Get the selected game name"""
        if self.result() == QDialog.Accepted:
            return self.gameCombo.currentText()
        return None


class DoomLauncher(QMainWindow):
    """Main launcher window for Toby Doom"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Toby Doom Launcher")
    
        if platform.system() == "Windows":
            self.configFile = Path.cwd() / 'TobyConfig.ini'
            self.gamePath = Path.cwd()
        else:
            self.gamePath = Path.home() / ".local/games/doom"
            self.configFile = Path(os.getenv('XDG_CONFIG_HOME', Path.home() / '.config')) / 'gzdoom/gzdoom.ini'
        
        self.tobyVersion = "8-0"
        self.speechHandler = SpeechHandler()
        self.iwadSelector = IWADSelector()  # Add IWAD selector
        self.init_launcher_ui()

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            self.close()

    def handle_button_keypress(self, event, button):
        """Handle key press events for buttons"""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            button.click()
        # Make sure to call the parent class's key press event
        QPushButton.keyPressEvent(button, event)

    def populate_iwad_list(self):
        """Populate the IWAD selection combo box"""
        iwads = self.iwadSelector.find_iwads()
        for name, path in iwads.items():
            self.iwadCombo.addItem(name, userData=path)

    def init_launcher_ui(self):
        """Initialize the main launcher UI"""
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        mainLayout = QVBoxLayout(centralWidget)
    
        # IWAD Selection
        iwadLabel = QLabel("Select IWAD:")
        self.iwadCombo = AccessibleComboBox(self)
        self.iwadCombo.setAccessibleName("IWAD Selection")
        self.populate_iwad_list()
        mainLayout.addWidget(iwadLabel)
        mainLayout.addWidget(self.iwadCombo)
    
        # Game Selection
        self.gameCombo = AccessibleComboBox(self)
        self.gameCombo.setAccessibleName("Game Selection")
        self.populate_game_list()
        self.gameCombo.lineEdit().returnPressed.connect(self.launch_single_player)
        mainLayout.addWidget(QLabel("Select Game:"))
        mainLayout.addWidget(self.gameCombo)
    
        # Narration style selection
        self.narrationCombo = AccessibleComboBox(self)
        self.narrationCombo.setAccessibleName("Narration Style")
        self.narrationCombo.addItems(["Self-voiced", "Text to Speech"])
        # Set current value based on config
        current = self.get_narration_type()
        self.narrationCombo.setCurrentText(
            "Self-voiced" if current == 0 else "Text to Speech"
        )
        self.narrationCombo.currentTextChanged.connect(self.narration_type_changed)
    
        mainLayout.addWidget(QLabel("Narration Style:"))
        mainLayout.addWidget(self.narrationCombo)

        # Create buttons
        self.singlePlayerBtn = QPushButton("&Single Player")
        self.deathMatchBtn = QPushButton("&Deathmatch")
        self.customDeathMatchBtn = QPushButton("C&ustom Deathmatch")  # Alt+U
        self.coopBtn = QPushButton("&Co-op")

        self.singlePlayerBtn.clicked.connect(self.launch_single_player)
        self.deathMatchBtn.clicked.connect(self.show_deathmatch_dialog)
        self.customDeathMatchBtn.clicked.connect(self.show_custom_deathmatch_dialog)  # New line
        self.coopBtn.clicked.connect(self.show_coop_dialog)

        self.deathMatchBtn.keyPressEvent = lambda e: self.handle_button_keypress(e, self.deathMatchBtn)
        self.customDeathMatchBtn.keyPressEvent = lambda e: self.handle_button_keypress(e, self.customDeathMatchBtn)  # New line
        self.coopBtn.keyPressEvent = lambda e: self.handle_button_keypress(e, self.coopBtn)
        self.singlePlayerBtn.keyPressEvent = lambda e: self.handle_button_keypress(e, self.singlePlayerBtn)

        mainLayout.addWidget(self.singlePlayerBtn)
        mainLayout.addWidget(self.deathMatchBtn)
        mainLayout.addWidget(self.customDeathMatchBtn)  # New line
        mainLayout.addWidget(self.coopBtn)

    def get_narration_type(self) -> int:
        """Get the current narration type from config file"""
        try:
            if not self.configFile.exists():
                return 0  # Default if file doesn't exist
            
            with open(self.configFile, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('Toby_NarrationOutputType='):
                        value = line.split('=')[1].strip()
                        return int(value)
            return 0  # Default to self-voiced if not found
        except Exception as e:
            print(f"Error reading config: {e}", file=sys.stderr)
            return 0

    def set_narration_type(self, value: int) -> bool:
        """Set the narration type in config file
    
        Args:
            value (int): Narration type (0 for self-voiced, 2 for TTS)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.configFile.exists():
                # Create new config with default section
                with open(self.configFile, 'w') as f:
                    f.write('[GlobalSettings]\n')
                    f.write(f'Toby_NarrationOutputType={value}\n')
                return True

            # Read all lines
            with open(self.configFile, 'r') as f:
                lines = f.readlines()

            # Try to find and replace existing setting
            found = False
            for i, line in enumerate(lines):
                if line.strip().startswith('Toby_NarrationOutputType='):
                    lines[i] = f'Toby_NarrationOutputType={value}\n'
                    found = True
                    break

            # If not found, add to end or after [GlobalSettings]
            if not found:
                globalSettingsIndex = -1
                for i, line in enumerate(lines):
                    if line.strip() == '[GlobalSettings]':
                        globalSettingsIndex = i
                        break

                if globalSettingsIndex >= 0:
                    # Insert after [GlobalSettings]
                    lines.insert(globalSettingsIndex + 1, f'Toby_NarrationOutputType={value}\n')
                else:
                    # Add [GlobalSettings] section if it doesn't exist
                    lines.append('\n[GlobalSettings]\n')
                    lines.append(f'Toby_NarrationOutputType={value}\n')

            # Write back the modified content
            with open(self.configFile, 'w') as f:
                f.writelines(lines)
            return True

        except Exception as e:
            print(f"Error writing config: {e}", file=sys.stderr)
            return False

    def narration_type_changed(self, text: str):
        """Handle narration type combobox changes"""
        value = 0 if text == "Self-voiced" else 2
        if not self.set_narration_type(value):
            QMessageBox.warning(
                self,
                "Error",
                "Failed to update narration setting. Check file permissions."
            )
            # Reset combobox to current value
            current = self.get_narration_type()
            self.narrationCombo.setCurrentText(
                "Self-voiced" if current == 0 else "Text to Speech"
            )

    def populate_game_list(self):
        """Populate the game selection combo box"""
        gameList = [
            "Toby Demo Map",
            "Classic Doom",
            "Toby Doom",
            "OperationMDK",
            "Classic Heretic",
            "Toby Heretic",
            "Classic Hexen",
            "Toby Hexen",
            "Custom Game",
            "Audio Manual"
        ]

        for gameName in gameList:
            self.gameCombo.addItem(gameName)

    def find_freedm(self) -> Optional[str]:
        """Find freedm.wad in standard locations"""
        # Check common locations
        locations = [
            self.gamePath / "freedm.wad",
            Path("/usr/share/games/doom/freedm.wad"),
            Path("/usr/share/doom/freedm.wad")
        ]
    
        for loc in locations:
            if loc.exists():
                return str(loc)
            
        return None

    def find_gzdoom(self) -> Optional[str]:
        """Find the GZDoom executable"""
        if platform.system() == "Windows":
            gzdoomPath = Path.cwd() / "gzdoom.exe"
            return str(gzdoomPath) if gzdoomPath.exists() else None
        
        return shutil.which("gzdoom")

    def get_addon_files(self, game_type: str = "DOOM") -> List[str]:
        """Get all addon PK3 files for specified game type"""
        addonFiles = []
        # MENU addons are common to all games
        menuPath = self.gamePath / "Addons" / "MENU"
        if menuPath.exists():
            addonFiles.extend(str(p) for p in menuPath.glob("Toby*.pk3"))

        # Game specific addons
        gamePath = self.gamePath / "Addons" / game_type
        if gamePath.exists():
            if game_type == "HERETIC":
                pattern = "TobyHeretic*.pk3"
            elif game_type == "HEXEN":
                pattern = "TobyHexen*.pk3"
            else:  # DOOM
                pattern = "Toby*.pk3"
            addonFiles.extend(str(p) for p in gamePath.glob(pattern))

        return addonFiles

    def get_selected_game_files(self) -> List[str]:
        tobyMod = self.gamePath / f"TobyAccMod_V{self.tobyVersion}.pk3"
        if not tobyMod.exists():
            QMessageBox.critical(self, "Error", f"Could not find {tobyMod}")
            return []

        baseFiles = [str(tobyMod)]
        selectedGame = self.gameCombo.currentText()

        # Determine game type and get corresponding addons
        if "Heretic" in selectedGame:
            gameType = "HERETIC"
            if "Toby Heretic" in selectedGame:
                baseFiles.append(str(self.gamePath / "Addons/MAPS/TobyHereticLevels.wad"))
        elif "Hexen" in selectedGame:
            gameType = "HEXEN"
            if "Toby Hexen" in selectedGame:
                baseFiles.append(str(self.gamePath / "Addons/MAPS/TobyHexen.pk3"))
        else:  # Doom games
            gameType = "DOOM"
            if "Demo Map" in selectedGame:
                baseFiles.append(str(self.gamePath / "Addons/MAPS/Toby-Demo-Level.wad"))
            elif "Toby Doom" in selectedGame:
                baseFiles.append(str(self.gamePath / "Addons/MAPS/TobyDoomLevels.wad"))
                musicRenamer = self.gamePath / "Toby-Doom-Level-Music-Renamer.pk3"
                if musicRenamer.exists():
                    baseFiles.append(str(musicRenamer))
            elif "OperationMDK" in selectedGame:
                baseFiles.append(str(self.gamePath / "OpMDK.wad"))

            # Add metal music mod if available (Doom only)
            metalV7 = self.gamePath / "DoomMetalVol7.wad"
            metalV6 = self.gamePath / "DoomMetalVol6.wad"
            if metalV7.exists():
                baseFiles.append(str(metalV7))
            elif metalV6.exists():
                baseFiles.append(str(metalV6))

        # Add game-specific addons
        baseFiles.extend(self.get_addon_files(gameType))
        return baseFiles

    def show_custom_deathmatch_dialog(self):
        """Show custom deathmatch configuration dialog"""
        # First find available PK3s for customization
        pk3List = []
        for item in self.gamePath.glob('*.pk3'):
            if item.stat().st_size > 10 * 1024 * 1024:  # >10MB
                pk3List.append(str(item))
    
        # Add Army of Darkness if available
        aodWad = self.gamePath / "aoddoom1.wad"
        if aodWad.exists():
            pk3List.append(str(aodWad))
    
        if not pk3List:
            QMessageBox.warning(self, "Error", "No custom mods found")
            return
        
        # Create mod selection dialog
        modDialog = QDialog(self)
        modDialog.setWindowTitle("Select Customization")
        dialogLayout = QVBoxLayout(modDialog)
    
        modLabel = QLabel("Select Mod:")
        modCombo = AccessibleComboBox(modDialog)
        modCombo.setAccessibleName("Mod Selection")
        for pk3 in pk3List:
            modCombo.addItem(Path(pk3).stem, userData=pk3)
    
        dialogLayout.addWidget(modLabel)
        dialogLayout.addWidget(modCombo)
    
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(modDialog.accept)
        buttons.rejected.connect(modDialog.reject)
        dialogLayout.addWidget(buttons)
    
        if not modDialog.exec():
            return
        
        selectedMod = modCombo.currentData()
    
        # Show map selection dialog (same as regular deathmatch)
        mapOptions = {
            'map': {
                'type': 'combobox',
                'label': 'Select Map',
                'items': [
                    "Com Station (2-4 players)",
                    "Warehouse (2-4 players)",
                    "Sector 3 (2-4 players)",
                    "Dungeon of Doom (2-4 players)",
                    "Ocean Fortress (2-4 players)",
                    "Water Treatment Facility (2-4 players)",
                    "Phobos Base Site 4 (2-4 players)",
                    "Hangar Bay 18 (2-4 players)",
                    "Garden of Demon (2-4 players)",
                    "Outpost 69 (2-4 players)"
                ]
            }
        }

        mapDialog = MenuDialog("Select Map", mapOptions, self)
        if not mapDialog.exec():
            return
    
        selectedMap = mapDialog.get_dialog_values()['map']
        mapIndex = mapOptions['map']['items'].index(selectedMap) + 1  # 1-based index

        # Show game options dialog
        options = {
            'mode': {
                'type': 'combobox',
                'label': 'Game Mode',
                'items': [
                    "Host Game",
                    "Join Game",
                    "Bots Only"
                ]
            },
            'ip': {
                'type': 'text',
                'placeholder': 'Enter IP address to join (required for joining)'
            },
            'fraglimit': {
                'type': 'spinbox',
                'label': 'Frag Limit',
                'min': 1,
                'max': 500,
                'default': 20
            },
            'players': {
                'type': 'spinbox',
                'label': 'Number of Players',
                'min': 2,
                'max': 4,
                'default': 2
            },
            'skill': {
                'type': 'spinbox',
                'label': 'Skill Level',
                'min': 1,
                'max': 5,
                'default': 3
            }
        }
    
        dialog = MenuDialog("Deathmatch Options", options, self)
        if dialog.exec():
            values = dialog.get_dialog_values()
        
            # Set up game files
            gameFiles = [
                str(self.gamePath / f"TobyAccMod_V{self.tobyVersion}.pk3")
            ]
        
            # Add menu addons
            menuPath = self.gamePath / "Addons/MENU"
            if menuPath.exists():
                gameFiles.extend(str(p) for p in menuPath.glob("Toby*.pk3"))
        
            # Add selected mod
            gameFiles.append(selectedMod)
        
            # Add deathmatch map
            deathMatchMap = str(self.gamePath / "Addons/MAPS/TobyDeathArena_V1-5.wad")
            if Path(deathMatchMap).exists():
                gameFiles.append(deathMatchMap)
            
            # Get deathmatch flags and add map selection
            gameFlags = self.get_deathmatch_flags(values)
            gameFlags.extend(["-warp", str(mapIndex)])
        
            # Check/set freedm.wad as IWAD
            freedmPath = self.find_freedm()
            if not freedmPath:
                QMessageBox.critical(self, "Error", "Could not find freedm.wad")
                return
    
            # Force freedm.wad selection
            for i in range(self.iwadCombo.count()):
                if "freedm" in self.iwadCombo.itemText(i).lower():
                    self.iwadCombo.setCurrentIndex(i)
                    break

            # Launch the game
            self.launch_game(gameFiles, gameFlags)

    def load_custom_games(self) -> Dict[str, dict]:
        """Load all custom game configurations"""
        customGames = {}
        if platform.system() == "Windows":
            customDir = Path.cwd() / "TobyCustom"
        else:
            pathList = [
                Path(__file__).parent / "TobyCustom",
                self.gamePath / "TobyCustom",
                Path(os.path.expanduser("~/.local/share/doom/TobyCustom"))
            ]
    
            # Use first existing path or fall back to original
            customDir = next(
                (path for path in pathList if path.exists()),
                Path(__file__).parent / "TobyCustom"
            )

        if not customDir.exists():
            return customGames

        for json_file in customDir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    game_config = json.load(f)
                    customGames[game_config['name']] = game_config
            except Exception as e:
                print(f"Error loading custom game {json_file}: {e}")
                
        return customGames

    def check_dependencies(self, dependencies: List[dict]) -> bool:
        """Check if required files exist and show download info if not"""
        for dep in dependencies:
            file_path = self.gamePath / dep['file']
            if not file_path.exists():
                message = [
                    f"You are missing the \"{dep['file']}\" Package.\n",
                    f"You can get it from \"{dep['url']}\"\n",
                    "The URL has been copied to the clipboard.\n"
                ]
                message.extend(f"{msg}\n" for msg in dep.get('messages', []))
                
                QMessageBox.critical(
                    self,
                    "Missing Dependency",
                    "".join(message)
                )
                
                # Copy URL to clipboard (platform-specific implementation needed)
                # For now, try to open the URL in browser
                try:
                    webbrowser.open(dep['url'])
                except Exception:
                    pass
                    
                return False
        return True

    def show_custom_game_dialog(self):
        """Show dialog for custom game selection"""
        customGames = self.load_custom_games()
        if not customGames:
            QMessageBox.warning(
                self,
                "No Custom Games",
                "No custom game configurations found in TobyCustom directory."
            )
            return

        dialog = CustomGameDialog(customGames, self)
        if not dialog.exec():
            return
        
        selectedGame = dialog.get_selected_game()
        if selectedGame and selectedGame in customGames:
            config = customGames[selectedGame]
        
            # Check dependencies before launching
            if not self.check_dependencies(config.get('dependencies', [])):
                return
            
            gameFiles = []  # We'll build this up as we go
        
            # Always start with TobyAccMod
            tobyMod = self.gamePath / f"TobyAccMod_V{self.tobyVersion}.pk3"
            if not tobyMod.exists():
                QMessageBox.critical(self, "Error", f"Could not find {tobyMod}")
                return
            gameFiles.append(str(tobyMod))
        
            # Handle map selection right after TobyAccMod if specified
            if config.get('use_map_menu', False) and 'submenu' not in config:
                mapFiles = ["None"]  # Start with None option
                mapsDir = self.gamePath / "Addons/MAPS"
                if mapsDir.exists():
                    mapFiles.extend([p.name for p in mapsDir.glob("*.wad") 
                                if p.name != "TobyDeathArena_V1-5.wad"])
            
                # Add Operation MDK as special case
                opMDK = self.gamePath / "OpMDK.wad"
                if opMDK.exists():
                    mapFiles.append("OpMDK.wad")
            
                mapDialog = QDialog(self)
                mapDialog.setWindowTitle("Select Map")
                dialogLayout = QVBoxLayout(mapDialog)
            
                mapLabel = QLabel("Select Map:")
                mapCombo = AccessibleComboBox(mapDialog)
                mapCombo.setAccessibleName("Map Selection")
                mapCombo.addItems(mapFiles)
            
                dialogLayout.addWidget(mapLabel)
                dialogLayout.addWidget(mapCombo)
            
                buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                buttons.accepted.connect(mapDialog.accept)
                buttons.rejected.connect(mapDialog.reject)
                dialogLayout.addWidget(buttons)
            
                if not mapDialog.exec():
                    return
                
                selectedMap = mapCombo.currentText()
                if selectedMap != "None":
                    if selectedMap == "OpMDK.wad":
                        mapPath = str(self.gamePath / selectedMap)
                    else:
                        mapPath = str(self.gamePath / "Addons/MAPS" / selectedMap)
                    if Path(mapPath).exists():
                        gameFiles.append(mapPath)
        
            # Handle submenu if present
            if 'submenu' in config:
                selectedFile = self.show_submenu_dialog(config['submenu'])
                if not selectedFile:
                    return
                gameFiles.append(selectedFile)
            
            # Add remaining files
            tobyBaseVersion = self.tobyVersion.split('-')[0]
            for filePath in config.get('files', []):
                filePath = filePath.format(toby_base_version=tobyBaseVersion)
                # Handle glob patterns
                if '*' in filePath:
                    pathObj = self.gamePath / filePath.split('*')[0]
                    pattern = filePath.split('/')[-1]
                    if pathObj.parent.exists():
                        matches = list(pathObj.parent.glob(pattern))
                        gameFiles.extend(str(p) for p in matches)
                else:
                    fullPath = self.gamePath / filePath
                    if fullPath.exists():
                        gameFiles.append(str(fullPath))
            
            # Add optional files last
            for optFile in config.get('optional_files', []):
                optPath = self.gamePath / optFile
                if optPath.exists():
                    gameFiles.append(str(optPath))
        
            # Get any custom flags
            gameFlags = config.get('flags', [])
        
            # Launch the game if we have files
            if gameFiles:
                iwadIndex = self.iwadCombo.currentIndex()
                if iwadIndex < 0:
                    QMessageBox.critical(self, "Error", "Please select an IWAD first")
                    return
            
                self.launch_game(gameFiles, gameFlags)

    def show_submenu_dialog(self, submenu_config) -> Optional[str]:
        """Show dialog for selecting submenu option"""
        dialog = QDialog(self)
        dialog.setWindowTitle(submenu_config['title'])
        dialogLayout = QVBoxLayout(dialog)
    
        # Game selection combobox
        label = QLabel("Select Version:")
        gameCombo = AccessibleComboBox(dialog)
        gameCombo.setAccessibleName("Game Version Selection")
    
        # Add options and store full file paths as user data
        for option in submenu_config['options']:
            gameCombo.addItem(option['name'], userData=str(self.gamePath / option['file']))
    
        dialogLayout.addWidget(label)
        dialogLayout.addWidget(gameCombo)
    
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dialogLayout.addWidget(buttons)
    
        if dialog.exec():
            return gameCombo.currentData()
        return None

    def launch_single_player(self):
        """Launch single player game"""
        selectedGame = self.gameCombo.currentText()
        if selectedGame == "Custom Game":
            self.show_custom_game_dialog()
        elif selectedGame == "Audio Manual":
            self.show_audio_manual()
        else:
            gameFiles = self.get_selected_game_files()
            if gameFiles:
                # Get selected IWAD
                iwadIndex = self.iwadCombo.currentIndex()
                if iwadIndex < 0:
                    QMessageBox.critical(self, "Error", "Please select an IWAD first")
                    return
            
                iwadPath = self.iwadCombo.itemData(iwadIndex)
                cmdLine = [self.find_gzdoom(), "-iwad", iwadPath] + gameFiles
                if cmdLine[0]:  # If gzdoom was found
                    self.launch_game(gameFiles)

    def show_audio_manual(self):
        """Show and play audio manual"""
        manualPath = self.gamePath / "Manual"
        if not manualPath.exists():
            QMessageBox.warning(self, "Error", "Manual directory not found")
            return
            
        # Get all manual directories and print them for debugging
        manualDirs = sorted([d for d in manualPath.iterdir() if d.is_dir()])
        
        if not manualDirs:
            QMessageBox.warning(self, "Error", "No manuals found")
            return
            
        # Get all tracks for the first manual
        firstManualTracks = sorted(manualDirs[0].glob('*.mp3'))
        
        # Create dialog with proper accessibility names
        dialog = QDialog(self)
        dialog.setWindowTitle("Audio Manual")
        dialogLayout = QVBoxLayout(dialog)
        
        # Manual selection
        manualLabel = QLabel("Select Manual:")
        manualCombo = AccessibleComboBox()
        manualCombo.setAccessibleName("Manual Selection")
        manualCombo.addItems([m.name for m in manualDirs])
        dialogLayout.addWidget(manualLabel)
        dialogLayout.addWidget(manualCombo)
        
        # Track selection
        trackLabel = QLabel("Select Track:")
        trackCombo = AccessibleComboBox()
        trackCombo.setAccessibleName("Track Selection")
        trackCombo.addItem("Play All")
        trackCombo.addItems([t.stem for t in firstManualTracks])
        dialogLayout.addWidget(trackLabel)
        dialogLayout.addWidget(trackCombo)
        
        # Update track list when manual selection changes
        def update_tracks(manualName):
            selectedManual = manualPath / manualName
            tracks = sorted(selectedManual.glob('*.mp3'))
            trackCombo.clear()
            trackCombo.addItem("Play All")
            trackCombo.addItems([t.stem for t in tracks])
        
        manualCombo.currentTextChanged.connect(update_tracks)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dialogLayout.addWidget(buttons)
        
        if dialog.exec():
            selectedManual = manualPath / manualCombo.currentText()
            selectedTrack = trackCombo.currentText()
            
            if selectedTrack == "Play All":
                audioTracks = sorted(selectedManual.glob('*.mp3'))
            else:
                audioTracks = [selectedManual / f"{selectedTrack}.mp3"]
            
            # Platform-specific audio playback
            if platform.system() == "Windows":
                # Use absolute paths for Windows Media Player
                playlistPath = self.gamePath / "temp_playlist.m3u"
                try:
                    with open(playlistPath, 'w', encoding='utf-8') as f:
                        f.write('#EXTM3U\n')  # M3U header
                        for track in audioTracks:
                            abs_path = track.resolve()  # Get absolute path
                            f.write(str(abs_path) + '\n')
                    os.startfile(str(playlistPath))
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to play audio: {e}")
                finally:
                    # Clean up playlist after delay
                    def cleanup():
                        time.sleep(2)
                        try:
                            playlistPath.unlink()
                        except:
                            pass
                    threading.Thread(target=cleanup, daemon=True).start()
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['afplay'] + [str(t) for t in audioTracks])
            else:  # Linux
                if shutil.which('mpv'):
                    subprocess.run(['mpv', '--really-quiet', '--no-video'] + [str(t) for t in audioTracks])
                elif shutil.which('play'):
                    subprocess.run(['play', '-qV0'] + [str(t) for t in audioTracks])
                else:
                    QMessageBox.warning(self, "Error", "No suitable audio player found. Please install mpv or sox.")

    def show_deathmatch_dialog(self):
        """Show deathmatch configuration dialog"""
        # First show map selection
        mapOptions = {
            'map': {
                'type': 'combobox',
                'label': 'Select Map',
                'items': [
                    "Com Station (2-4 players)",
                    "Warehouse (2-4 players)",
                    "Sector 3 (2-4 players)",
                    "Dungeon of Doom (2-4 players)",
                    "Ocean Fortress (2-4 players)",
                    "Water Treatment Facility (2-4 players)",
                    "Phobos Base Site 4 (2-4 players)",
                    "Hangar Bay 18 (2-4 players)",
                    "Garden of Demon (2-4 players)",
                    "Outpost 69 (2-4 players)"
                ]
            }
        }
        
        mapDialog = MenuDialog("Select Map", mapOptions, self)
        if not mapDialog.exec():
            return
        
        selectedMap = mapDialog.get_dialog_values()['map']
        mapIndex = mapOptions['map']['items'].index(selectedMap) + 1  # 1-based index

        # Show game options dialog
        options = {
            'mode': {
                'type': 'combobox',
                'label': 'Game Mode',
                'items': [
                    "Host Game",
                    "Join Game",
                    "Bots Only"
                ]
            },
            'ip': {
                'type': 'text',
                'placeholder': 'Enter IP address to join (required for joining)'
            },
            'fraglimit': {
                'type': 'spinbox',
                'label': 'Frag Limit',
                'min': 1,
                'max': 500,
                'default': 20
            },
            'players': {
                'type': 'spinbox',
                'label': 'Number of Players',
                'min': 2,
                'max': 4,
                'default': 2
            },
            'skill': {
                'type': 'spinbox',
                'label': 'Skill Level',
                'min': 1,
                'max': 5,
                'default': 3
            }
}
        
        dialog = MenuDialog("Deathmatch Options", options, self)
        if dialog.exec():
            values = dialog.get_dialog_values()
            gameFiles = self.get_selected_game_files()
            # Add deathmatch map
            deathMatchMap = str(self.gamePath / "Addons/MAPS/TobyDeathArena_V1-5.wad")
            if Path(deathMatchMap).exists():
                gameFiles.append(deathMatchMap)
            gameFlags = self.get_deathmatch_flags(values)
            # Add map selection flag
            gameFlags.extend(["-warp", str(mapIndex)])

            # Check/set freedm.wad as IWAD
            freedmPath = self.find_freedm()
            if not freedmPath:
                QMessageBox.critical(self, "Error", "Could not find freedm.wad")
                return
    
            # Force freedm.wad selection
            for i in range(self.iwadCombo.count()):
                if "freedm" in self.iwadCombo.itemText(i).lower():
                    self.iwadCombo.setCurrentIndex(i)
                    break

            self.launch_game(gameFiles, gameFlags)

    def show_coop_dialog(self):
        """Show co-op configuration dialog"""
        options = {
            'host': {
                'type': 'radio',
                'label': 'Host Game'
            },
            'ip': {
                'type': 'text',
                'placeholder': 'Enter IP address to join'
            },
            'players': {
                'type': 'spinbox',
                'label': 'Number of Players',
                'min': 2,
                'max': 10,
                'default': 2
            },
            'skill': {
                'type': 'spinbox',
                'label': 'Skill Level',
                'min': 1,
                'max': 5,
                'default': 3
            }
        }
        
        dialog = MenuDialog("Co-op Options", options, self)
        if dialog.exec():
            values = dialog.get_dialog_values()
            gameFiles = self.get_selected_game_files()
            # Add keyshare for co-op
            keyshareFile = str(self.gamePath / "keyshare-universal.pk3")
            if Path(keyshareFile).exists():
                gameFiles.append(keyshareFile)
            gameFlags = self.get_coop_flags(values)
            self.launch_game(gameFiles, gameFlags)

    def get_deathmatch_flags(self, values: dict) -> List[str]:
        """Get command line flags for deathmatch mode"""
        mode = values['mode']
    
        if mode == "Join Game":
            if not values['ip'].strip():
                QMessageBox.warning(self, "Error", "IP address required for joining")
                return []
            return ["-join", values['ip']]
    
        # Handle both Host Game and Bots Only
        if mode == "Bots Only":
            values['players'] = 1
            QMessageBox.information(
                self,
                "Bot Instructions",
                "When the game starts, press ` to open the console.\n"
                "Type addbot and press enter.\n"
                "Repeat addbot for as many bots as you want.\n"
                "Press ` again to close the console."
            )
    
        return [
            "-host", str(values['players']),
            "-skill", str(values['skill']),
            "-deathmatch",
            "+Toby_SnapToTargetTargetingMode", "0",
            "+set", "sv_cheats", "1",
            "+fraglimit", str(values['fraglimit']),
            "+dmflags", "16384",
            "+dmflags", "4",
            "+dmflags", "128",
            "+dmflags", "4096",
            "+dmflags2", "512",
            "+dmflags2", "1024",
            "-extratic",
            "-dup", "3"
        ]

    def get_coop_flags(self, values: dict) -> List[str]:
        """Get command line flags for co-op mode"""
        if not values['host']:
            if not values['ip'].strip():
                QMessageBox.warning(self, "Error", "IP address required for joining")
                return []
            return ["-join", values['ip']]
            
        return [
            "-host", str(values['players']),
            "-skill", str(values['skill']),
            "+set", "sv_cheats", "1",
            "+set", "sv_weaponsstay", "1",
            "+set", "sv_respawnprotect", "1",
            "+set", "sv_respawnsuper", "1",
            "+set", "alwaysapplydmflags", "1",
            "-extratic",
            "-dup", "3"
        ]

    def monitor_game_process(self, process):
        """Monitor game process and exit when it's done"""
        process.wait()  # Wait for the game to finish
        QApplication.instance().quit()  # Quit the application

    def launch_game(self, gameFiles: List[str], gameFlags: List[str] = None):
        """Launch game with speech processing"""
        if not gameFiles:
            return
            
        gzdoomPath = self.find_gzdoom()
        if not gzdoomPath:
            QMessageBox.critical(self, "Error", "GZDoom executable not found")
            return
            
        # Get selected IWAD
        iwadIndex = self.iwadCombo.currentIndex()
        if iwadIndex < 0:
            QMessageBox.critical(self, "Error", "Please select an IWAD first")
            return
            
        iwadPath = self.iwadCombo.itemData(iwadIndex)

        try:
            if platform.system() == "Windows":
                configFile = Path.cwd() / 'TobyConfig.ini'
                # For Windows, pipe directly to PowerShell running DoomTTS.ps1
                cmdLine = [gzdoomPath, "-stdout", "-config", str(configFile), 
                        "-iwad", iwadPath, "-file"] + gameFiles
                if gameFlags:
                    cmdLine.extend(gameFlags)
                
                fullCmd = " ".join(cmdLine) + " | powershell -ExecutionPolicy Bypass -File DoomTTS.ps1"
                process = subprocess.Popen(
                    fullCmd,
                    cwd=str(self.gamePath),
                    shell=True
                )
            
                # Monitor thread only for Windows
                monitorThread = threading.Thread(
                    target=self.monitor_game_process,
                    args=(process,),
                    daemon=True
                )
                monitorThread.start()
            else:
                # For Linux/Mac, use stdbuf to unbuffer output
                cmdLine = ["stdbuf", "-oL", gzdoomPath, "-stdout", 
                        "-iwad", iwadPath, "-file"] + gameFiles
                if gameFlags:
                    cmdLine.extend(gameFlags)
                
                process = subprocess.Popen(
                    cmdLine,
                    cwd=str(self.gamePath),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    text=True,
                    env=dict(os.environ, PYTHONUNBUFFERED="1")
                )
            
                # Start speech processing thread
                speechThread = threading.Thread(
                    target=self.speechHandler.speak_thread,
                    args=(process,),
                    daemon=True
                )
                speechThread.start()
            
                # Start process monitor thread
                monitorThread = threading.Thread(
                    target=self.monitor_game_process,
                    args=(process,),
                    daemon=True
                )
                monitorThread.start()
        
            # Hide the window
            self.hide()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch game: {e}")


if __name__ == "__main__":
    setproctitle("Toby Doom Launcher")
    app = QApplication(sys.argv)
    window = DoomLauncher()
    window.show()
    sys.exit(app.exec())
