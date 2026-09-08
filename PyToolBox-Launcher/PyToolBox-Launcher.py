# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
#                                              Boot's ToolBox Script                                                      #
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
# Hi :3
# Welcome to my code

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
# Imports
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#

import importlib
import io
import json
import os
import re
import shutil
import site
import subprocess
import sys
import time

import xml.etree.ElementTree as ET
import zipfile
import webbrowser
import threading
import ctypes

def install_if_missing(package, import_name=None):
    if import_name is None:
        import_name = package.split("==")[0].replace("-", "_")

    try:
        importlib.import_module(import_name)
    except ImportError:
        print(f"Installing {package}...")

        install_attempts = [
            [sys.executable, "-m", "pip", "install", package],
        ]
        if sys.platform != "win32":
            install_attempts.append([sys.executable, "-m", "pip", "install", package, "--break-system-packages"])
            install_attempts.append([sys.executable, "-m", "pip", "install", package, "--user"])

        last_error = None
        for cmd in install_attempts:
            try:
                subprocess.check_call(cmd)
                last_error = None
                break
            except subprocess.CalledProcessError as e:
                last_error = e

        if last_error is not None:
            raise last_error

        if sys.platform != "win32":
            user_site = site.getusersitepackages()
            if user_site and user_site not in sys.path:
                sys.path.insert(0, user_site)


install_if_missing("requests==2.32.5", "requests")
install_if_missing("PySide6", "PySide6")

import requests

from PySide6.QtCore import Qt, QObject, Signal, Slot, QPointF, QTimer, QThread, QRectF
from PySide6.QtGui import QPainter, QColor, QPolygonF, QFont, QFontDatabase, QIcon, QTextCursor, QPen, QFontMetrics
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QWidget, QLabel, QPushButton,
    QLineEdit, QComboBox, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QMessageBox, QFileDialog, QSizePolicy, QTextEdit, QStackedWidget,
)

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
# CONFIGURATION & GLOBAL VARIABLES
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#

# ─── App metadata / runtime state ──────────────────────────────────────────
VERSION = "1.0.8"
UPDATE_BRANCH = "main"           # Default selected update branch
BETA_POPUP_SHOWN = False

# Python interpreter used to launch tool scripts. Empty string = use the same
# interpreter the ToolBox itself is running on (sys.executable).
PYTHON_INTERPRETER = ""

# ─── Statically declared theme variables to satisfy code analysis / IDE inspectors ───
BG = ""
PANEL = ""
BORDER = ""
ACCENT = ""
ACCENT2 = ""
TEXT = ""
TEXT2 = ""
SUBTEXT = ""
RED = ""
STRIPE_COLOURS = []

# ─── Filesystem layout ──────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CENTRAL_CONFIG_DIR = os.path.join(os.getenv("LOCALAPPDATA", ""), "")
CENTRAL_CONFIG_FILE = os.path.join(CENTRAL_CONFIG_DIR, "toolbox_config.json")
TOOLS_PATH_POINTER = os.path.join(CENTRAL_CONFIG_DIR, "tools_path.txt")
INSTALL_PATH_POINTER = os.path.join(CENTRAL_CONFIG_DIR, "install_path.txt")

# These will be updated dynamically during bootstrap:
TOOLS_ROOT_DIR = os.path.join(SCRIPT_DIR, "../Nova-Tools")
TOOLBOX_CONFIG_DIR = os.path.join(TOOLS_ROOT_DIR, "configs")
TOOLBOX_CONFIG_FILE = os.path.join(TOOLBOX_CONFIG_DIR, "toolbox_config.json")
BACKUP_DIR = os.path.join(TOOLBOX_CONFIG_DIR, "ToolBox Backup")
LEGACY_TOOLBOX_CONFIG_FILES = [
    os.path.join(TOOLS_ROOT_DIR, "osc_config.json"),
    os.path.join(TOOLS_ROOT_DIR, "chatbox_config.json"),
    os.path.join(TOOLS_ROOT_DIR, "toolbox_config.json"),
]

def update_layout_paths(tools_root: str):
    global TOOLS_ROOT_DIR, TOOLBOX_CONFIG_DIR, TOOLBOX_CONFIG_FILE, BACKUP_DIR, LEGACY_TOOLBOX_CONFIG_FILES
    TOOLS_ROOT_DIR = os.path.abspath(tools_root)
    TOOLBOX_CONFIG_DIR = os.path.join(TOOLS_ROOT_DIR, "configs")
    TOOLBOX_CONFIG_FILE = os.path.join(TOOLBOX_CONFIG_DIR, "toolbox_config.json")
    BACKUP_DIR = os.path.join(TOOLBOX_CONFIG_DIR, "ToolBox Backup")
    LEGACY_TOOLBOX_CONFIG_FILES = [
        os.path.join(TOOLS_ROOT_DIR, "osc_config.json"),
        os.path.join(TOOLS_ROOT_DIR, "chatbox_config.json"),
        os.path.join(TOOLS_ROOT_DIR, "toolbox_config.json"),
    ]

# Per-tool config files to wipe on update (paths relative to TOOLS_ROOT_DIR).
# This ensures users always get a clean config after a breaking update.
TOOL_CONFIG_WIPE_MAP: dict[str, list[str]] = {
    "OSC-Chatbox/main.py": [
        os.path.join("OSC-Chatbox", "chatbox_config.json"),
    ],
}

# NOTE: tool file layout itself is no longer hardcoded here. Every managed
# tool is assumed to live at "<ToolFolder>/<main file>" (e.g.
# "OSC-Chatbox/main.py"), and its full folder contents are discovered
# dynamically from GitHub at download/update time (see get_repo_tree() /
# ensure_tool_folder() further down). That means adding a new file to a tool
# on GitHub "just works" without ever having to touch this file.

# ─── GitHub URLs ─────────────────────────────────────────────────────────────
GITHUB_EXE_RELEASE_BASE_URL = "https://github.com/CaptainBoots/Project-Proto/releases/latest/download/"


def get_github_raw_url():
    return f"https://raw.githubusercontent.com/CaptainBoots/Project-Proto/{UPDATE_BRANCH}/PyToolBox-Launcher/PyToolBox-Launcher.py"


def get_github_base_url():
    return f"https://raw.githubusercontent.com/CaptainBoots/Nova-Tools/{UPDATE_BRANCH}/"


def get_active_python() -> str:
    """Returns the interpreter path to use for launching tool scripts.

    Falls back to a discovered system Python interpreter if no custom interpreter is configured,
    or if the configured one no longer exists on disk.
    """
    if PYTHON_INTERPRETER and os.path.isfile(PYTHON_INTERPRETER):
        return PYTHON_INTERPRETER

    # If frozen, sys.executable is the compiled .exe itself, which cannot run .py scripts!
    if getattr(sys, 'frozen', False):
        # Let's search for python on the system PATH
        for py_cmd in ["pythonw", "python", "python3"]:
            py_path = shutil.which(py_cmd)
            if py_path:
                return py_path
        # If no python is found in PATH, fallback to 'pythonw' and let OS resolve it
        return "pythonw"

    return sys.executable


# ─── Libre Hardware Monitor (EXE tool, downloaded from GitHub Releases) ───────
LHM_FOLDER = "LibreHardwareMonitor"
LHM_EXE_NAME = "LibreHardwareMonitor.exe"
LHM_FILENAME = f"{LHM_FOLDER}/{LHM_EXE_NAME}"
LHM_RELEASE_URL = "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/latest/download/LibreHardwareMonitor.zip"

# ─── Tool state tracking (drives "Download" / "Update" / "Run" button labels) ─
TOOL_STATE_MISSING = "missing"
TOOL_STATE_UPDATE = "update"
TOOL_STATE_CURRENT = "current"

# filename -> one of the TOOL_STATE_* constants above. Populated by the
# lightweight background scan on boot, and updated immediately after any
# download/update triggered by a click.
tool_states: dict[str, str] = {}

_tool_label_cache = {}

def _get_cached_tool_label(filename: str) -> str | None:
    return _tool_label_cache.get(filename)

def _cache_tool_label(filename: str, label: str):
    _tool_label_cache[filename] = label
    # Save cache to config file
    save_managed_scripts(MANAGED_SCRIPTS)

def discover_managed_scripts() -> list[dict]:
    """Dynamically auto-detects all tools inside the Nova-Tools folder and GitHub.

    Looks for subdirectories containing 'main.py'. Parsed tool names are extracted
    from the 'NAME' variable, and unique 6-digit IDs are parsed from 'TOOL_ID'.
    """

    # 1. Always include LibreHardwareMonitor as a static default helper tool
    detected = [{
        "filename": "LibreHardwareMonitor/LibreHardwareMonitor.exe",
        "label": "Libre Hardware Monitor",
        "id": "999801"
    }]

    # Keep track of folders we have already discovered
    seen_folders = set()
    local_tools_by_id = {}

    # 2. Local Discovery: Scan the local TOOLS_ROOT_DIR subfolders
    if os.path.isdir(TOOLS_ROOT_DIR):
        try:
            for item in os.listdir(TOOLS_ROOT_DIR):
                folder_path = os.path.join(TOOLS_ROOT_DIR, item)
                if os.path.isdir(folder_path) and item != "LibreHardwareMonitor" and item != "configs" and item != "ToolBox Backup":
                    main_py_path = os.path.join(folder_path, "main.py")
                    if os.path.isfile(main_py_path):
                        # Read and parse NAME and TOOL_ID
                        try:
                            with open(main_py_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                        except Exception:
                            content = ""
                        
                        label = _extract_name_from_source(content) or item
                        tool_id = _extract_id_from_source(content) or "000000"
                        filename = f"{item}/main.py"
                        
                        tool_entry = {"filename": filename, "label": label, "id": tool_id}
                        detected.append(tool_entry)
                        seen_folders.add(item)
                        if tool_id != "000000":
                            local_tools_by_id[tool_id] = tool_entry
        except Exception as e:
            print(f"[Discovery] Local tools scan failed: {e}")

    # 3. Remote Discovery: Find missing folders that have main.py on GitHub and handle renames
    paths = get_repo_tree()
    if paths:
        for p in paths:
            # We look for paths like '<FolderName>/main.py'
            parts = p.split("/")
            if len(parts) == 2 and parts[1] == "main.py":
                folder_name = parts[0]
                if folder_name != "LibreHardwareMonitor":
                    filename = f"{folder_name}/main.py"
                    
                    # Fetch raw main.py content and parse NAME and TOOL_ID
                    remote_text, _, _ = _fetch_remote_script(f"{get_github_base_url()}{filename}", timeout=5)
                    remote_text = remote_text or ""
                    
                    remote_id = _extract_id_from_source(remote_text) or "000000"
                    remote_label = _extract_name_from_source(remote_text) or folder_name

                    # SELF-HEALING RENAME CHECK:
                    # If this remote ID matches an already discovered local tool, but the folder name has changed!
                    if remote_id != "000000" and remote_id in local_tools_by_id:
                        local_entry = local_tools_by_id[remote_id]
                        old_filename = local_entry["filename"]
                        if old_filename != filename:
                            # Folder renamed on GitHub! Let's rename locally
                            old_folder = old_filename.split("/")[0]
                            old_folder_path = os.path.join(TOOLS_ROOT_DIR, old_folder)
                            new_folder_path = os.path.join(TOOLS_ROOT_DIR, folder_name)
                            if os.path.isdir(old_folder_path):
                                try:
                                    if os.path.isdir(new_folder_path):
                                        shutil.rmtree(new_folder_path, ignore_errors=True)
                                    os.rename(old_folder_path, new_folder_path)
                                    print(f"[Self-Healing] Renamed local directory '{old_folder}' -> '{folder_name}' to match remote rename!")

                                except Exception as ex:
                                    print(f"[Self-Healing] Failed to rename directory: {ex}")
                            
                            # Update local entry with the new folder path
                            local_entry["filename"] = filename
                            local_entry["label"] = remote_label
                            seen_folders.add(folder_name)
                            if old_folder in seen_folders:
                                seen_folders.remove(old_folder)
                    else:
                        # Standard discovery of a new tool
                        if folder_name not in seen_folders:
                            _cache_tool_label(filename, remote_label)
                            detected.append({"filename": filename, "label": remote_label, "id": remote_id})
                            seen_folders.add(folder_name)

    return detected


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
# THEME SYSTEM (embedded — same palette/stripe engine used across the rest of
# Nova-Tools, normally split into ui/theme.py, kept inline here since this
# tool has to stay a single file). Colours are plain module globals exactly
# like the tool already used (BG, PANEL, ACCENT, ...) — set_theme() just
# reassigns them, and every widget is rebuilt from scratch on a theme change
# (see ToolBoxWindow._rebuild_ui), so nothing ever holds a stale colour.
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#

colour_mode = "rich_purple"

FONT = "Consolas"
TITLE_PREFIX = "◈"

THEMES: dict[str, dict] = {
    "dark": {
        "BG": "#0f0f13", "PANEL": "#17171f", "BORDER": "#2a2a38", "ACCENT": "#7c5cfc",
        "ACCENT2": "#a78bfa", "TAB": "#4ade80", "TEXT": "#e2e0f0", "TEXT2": "#E0E0E0",
        "SUBTEXT": "#7e7b9a", "GREEN": "#4ade80", "RED": "#f87171", "YELLOW": "#facc15",
        "CYAN": "#67e8f9", "ORANGE": "#fb923c", "STRIPE_COLOURS": None,
    },
    "rich_purple": {
        "BG": "#0f0f13", "PANEL": "#1f102a", "BORDER": "#2a2a38", "ACCENT": "#9D00FF",
        "ACCENT2": "#b44bff", "TAB": "#4ade80", "TEXT": "#e2e0f0", "TEXT2": "#E0E0E0",
        "SUBTEXT": "#7e7b9a", "GREEN": "#00ffcc", "RED": "#ff4b72", "YELLOW": "#facc15",
        "CYAN": "#67e8f9", "ORANGE": "#fb923c", "STRIPE_COLOURS": None,
    },
    "dark_sand": {
        "BG": "#1C1D26", "PANEL": "#1f232d", "BORDER": "#353333", "ACCENT": "#FFAC8B",
        "ACCENT2": "#FFC695", "TAB": "#FFC695", "TEXT": "#F5EFE9", "TEXT2": "#E3D8D0",
        "SUBTEXT": "#AE9281", "GREEN": "#4ade80", "RED": "#f87171", "YELLOW": "#facc15",
        "CYAN": "#67e8f9", "ORANGE": "#FFAC8B", "STRIPE_COLOURS": None,
    },
    "absolute_zero": {
        "BG": "#000D21", "PANEL": "#002154", "BORDER": "#003487", "ACCENT": "#005CED",
        "ACCENT2": "#5496FF", "TAB": "#2177FF", "TEXT": "#EAF3FF", "TEXT2": "#D6E8FF",
        "SUBTEXT": "#A8C4F2", "GREEN": "#4ade80", "RED": "#f87171", "YELLOW": "#facc15",
        "CYAN": "#67e8f9", "ORANGE": "#fb923c", "STRIPE_COLOURS": None,
    },
    "light_purple": {
        "BG": "#F6E6FA", "PANEL": "#ffffff", "BORDER": "#DDCAE3", "ACCENT": "#9D00FF",
        "ACCENT2": "#b44bff", "TAB": "#000000", "TEXT": "#1a1829", "TEXT2": "#1a1829",
        "SUBTEXT": "#1a1829", "GREEN": "#4ade80", "RED": "#f87171", "YELLOW": "#facc15",
        "CYAN": "#67e8f9", "ORANGE": "#fb923c", "STRIPE_COLOURS": None,
    },
    "light_sand": {
        "BG": "#fdfbf7", "PANEL": "#f4f1ea", "BORDER": "#e4dfd3", "ACCENT": "#2b5c43",
        "ACCENT2": "#3d7a5a", "TAB": "#000000", "TEXT": "#1c1b18", "TEXT2": "#383630",
        "SUBTEXT": "#706e64", "GREEN": "#15803d", "RED": "#b91c1c", "YELLOW": "#b45309",
        "CYAN": "#0369a1", "ORANGE": "#c2410c", "STRIPE_COLOURS": None,
    },
    "mint": {
        "BG": "#F5FFFA", "PANEL": "#FFFFFF", "BORDER": "#D6F0E4", "ACCENT": "#2EC4B6",
        "ACCENT2": "#6EE7D8", "TAB": "#1F2937", "TEXT": "#1A2A2A", "TEXT2": "#334155",
        "SUBTEXT": "#64748B", "GREEN": "#22C55E", "RED": "#EF4444", "YELLOW": "#EAB308",
        "CYAN": "#06B6D4", "ORANGE": "#F97316", "STRIPE_COLOURS": None,
    },
    "dark_mint": {
        "BG": "#0F1C18", "PANEL": "#163129", "BORDER": "#295247", "ACCENT": "#2EC4B6",
        "ACCENT2": "#6EE7D8", "TAB": "#6EE7D8", "TEXT": "#E8FFF9", "TEXT2": "#D3F5EE",
        "SUBTEXT": "#8AB5AB", "GREEN": "#4ADE80", "RED": "#F87171", "YELLOW": "#FACC15",
        "CYAN": "#67E8F9", "ORANGE": "#FB923C", "STRIPE_COLOURS": None,
    },
    "dark_red": {
        "BG": "#1A0B0B", "PANEL": "#2C1111", "BORDER": "#512121", "ACCENT": "#DC2626",
        "ACCENT2": "#F87171", "TAB": "#F87171", "TEXT": "#FFF1F1", "TEXT2": "#F8DADA",
        "SUBTEXT": "#B48D8D", "GREEN": "#4ADE80", "RED": "#F87171", "YELLOW": "#FACC15",
        "CYAN": "#67E8F9", "ORANGE": "#FB923C", "STRIPE_COLOURS": None,
    },
    "light_red": {
        "BG": "#FFF5F5", "PANEL": "#FFFFFF", "BORDER": "#F4CACA", "ACCENT": "#DC2626",
        "ACCENT2": "#F87171", "TAB": "#000000", "TEXT": "#2A1111", "TEXT2": "#472020",
        "SUBTEXT": "#735353", "GREEN": "#16A34A", "RED": "#DC2626", "YELLOW": "#CA8A04",
        "CYAN": "#0284C7", "ORANGE": "#EA580C", "STRIPE_COLOURS": None,
    },
    "light_blue": {
        "BG": "#F2F9FF", "PANEL": "#FFFFFF", "BORDER": "#D2E8F8", "ACCENT": "#3B82F6",
        "ACCENT2": "#60A5FA", "TAB": "#000000", "TEXT": "#172033", "TEXT2": "#2E4468",
        "SUBTEXT": "#6A82A8", "GREEN": "#22C55E", "RED": "#EF4444", "YELLOW": "#EAB308",
        "CYAN": "#06B6D4", "ORANGE": "#F97316", "STRIPE_COLOURS": None,
    },
    "dark_rainbow": {
        "BG": "#1A1A1A", "PANEL": "#252525", "BORDER": "#444444", "ACCENT": "#E40303",
        "ACCENT2": "#FF8C00", "TAB": "#732982", "TEXT": "#FFFFFF", "TEXT2": "#F0F0F0",
        "SUBTEXT": "#BBBBBB", "GREEN": "#008026", "RED": "#E40303", "YELLOW": "#FFED00",
        "CYAN": "#004DFF", "ORANGE": "#FF8C00",
        "STRIPE_COLOURS": ["#FF0000", "#FF4400", "#FF8900", "#FFCE00", "#F9FF00", "#ADFF00",
                           "#60FF00", "#14FF00", "#00FF38", "#00FF84", "#00FFD1", "#00E8FF",
                           "#00AAFF", "#0056FF", "#0002FF", "#4900FF", "#9600FF", "#E200FF",
                           "#FF00DD", "#FF0089", "#FF0035"],
    },
    "light_rainbow": {
        "BG": "#FFF5F5", "PANEL": "#FFFFFF", "BORDER": "#F4CACA", "ACCENT": "#E40303",
        "ACCENT2": "#FF8C00", "TAB": "#732982", "TEXT": "#2A1111", "TEXT2": "#472020",
        "SUBTEXT": "#757575", "GREEN": "#008026", "RED": "#E40303", "YELLOW": "#FFED00",
        "CYAN": "#004DFF", "ORANGE": "#FF8C00",
        "STRIPE_COLOURS": ["#FF0000", "#FF4400", "#FF8900", "#FFCE00", "#F9FF00", "#ADFF00",
                           "#60FF00", "#14FF00", "#00FF38", "#00FF84", "#00FFD1", "#00E8FF",
                           "#00AAFF", "#0056FF", "#0002FF", "#4900FF", "#9600FF", "#E200FF",
                           "#FF00DD", "#FF0089", "#FF0035"],
    },
    "pride_flag": {
        "BG": "#1A1A1A", "PANEL": "#1c1c1c", "BORDER": "#333333", "ACCENT": "#FFED00",
        "ACCENT2": "#FF8C00", "TAB": "#FFED00", "TEXT": "#FFFFFF", "TEXT2": "#F0F0F0",
        "SUBTEXT": "#CCCCCC", "GREEN": "#008026", "RED": "#E40303", "YELLOW": "#FFED00",
        "CYAN": "#004DFF", "ORANGE": "#FF8C00",
        "STRIPE_COLOURS": ["#E40303", "#FF8C00", "#FFED00", "#008026", "#004DFF", "#750787"],
    },
    "trans_flag": {
        "BG": "#0d1f28", "PANEL": "#1a2e36", "BORDER": "#5BCEFA", "ACCENT": "#F5A9B8",
        "ACCENT2": "#5BCEFA", "TAB": "#F5A9B8", "TEXT": "#FFFFFF", "TEXT2": "#e0f4ff",
        "SUBTEXT": "#a8d4e8", "GREEN": "#5BCEFA", "RED": "#F5A9B8", "YELLOW": "#FFFFFF",
        "CYAN": "#5BCEFA", "ORANGE": "#F5A9B8",
        "STRIPE_COLOURS": ["#5BCEFA", "#F5A9B8", "#FFFFFF", "#F5A9B8", "#5BCEFA"],
    },
    "nonbinary_flag": {
        "BG": "#1e1230", "PANEL": "#1e1230", "BORDER": "#9C59D1", "ACCENT": "#FFF430",
        "ACCENT2": "#9C59D1", "TAB": "#FFF430", "TEXT": "#FFFFFF", "TEXT2": "#F0F0F0",
        "SUBTEXT": "#DDDDDD", "GREEN": "#9C59D1", "RED": "#FFF430", "YELLOW": "#FFF430",
        "CYAN": "#FFFFFF", "ORANGE": "#FFF430",
        "STRIPE_COLOURS": ["#FFF430", "#FFFFFF", "#9C59D1", "#2C2C2C"],
    },
    "ace_flag": {
        "BG": "#161616", "PANEL": "#2a002a", "BORDER": "#800080", "ACCENT": "#B05ACD",
        "ACCENT2": "#CC88EE", "TAB": "#B05ACD", "TEXT": "#FFFFFF", "TEXT2": "#F2F2F2",
        "SUBTEXT": "#CFCFCF", "GREEN": "#B05ACD", "RED": "#f87171", "YELLOW": "#FFFFFF",
        "CYAN": "#B05ACD", "ORANGE": "#B05ACD",
        "STRIPE_COLOURS": ["#161616", "#808080", "#FFFFFF", "#800080"],
    },
    "bi_flag": {
        "BG": "#1a0d1a", "PANEL": "#2b1028", "BORDER": "#9B4F96", "ACCENT": "#D60270",
        "ACCENT2": "#9B4F96", "TAB": "#D60270", "TEXT": "#FFFFFF", "TEXT2": "#F5E6F5",
        "SUBTEXT": "#C8A0C8", "GREEN": "#9B4F96", "RED": "#D60270", "YELLOW": "#FFFFFF",
        "CYAN": "#0038A8", "ORANGE": "#D60270",
        "STRIPE_COLOURS": ["#D60270", "#D60270", "#9B4F96", "#0038A8", "#0038A8"],
    },
    "gay_flag": {
        "BG": "#00150f", "PANEL": "#002018", "BORDER": "#3D9970", "ACCENT": "#3D9970",
        "ACCENT2": "#70C9A0", "TAB": "#3D9970", "TEXT": "#FFFFFF", "TEXT2": "#E0FFF5",
        "SUBTEXT": "#7ABBA0", "GREEN": "#3D9970", "RED": "#006B54", "YELLOW": "#FFFFFF",
        "CYAN": "#7BADE2", "ORANGE": "#3D9970",
        "STRIPE_COLOURS": ["#078D70", "#26CEA8", "#98E8C1", "#FFFFFF", "#7BADE2", "#5049CC", "#3D1A8E"],
    },
    "lesbian_flag": {
        "BG": "#1f0d00", "PANEL": "#2e1500", "BORDER": "#D52D00", "ACCENT": "#FF9A56",
        "ACCENT2": "#FF6D4A", "TAB": "#FF9A56", "TEXT": "#FFFFFF", "TEXT2": "#FFE8DC",
        "SUBTEXT": "#D4907A", "GREEN": "#FF9A56", "RED": "#D52D00", "YELLOW": "#FF9A56",
        "CYAN": "#A50062", "ORANGE": "#FF9A56",
        "STRIPE_COLOURS": ["#D52D00", "#FF9A56", "#FFFFFF", "#D362A4", "#A50062"],
    },
    "pan_flag": {
        "BG": "#0f0f1a", "PANEL": "#1a1a2e", "BORDER": "#FFD800", "ACCENT": "#FF218C",
        "ACCENT2": "#FFD800", "TAB": "#FF218C", "TEXT": "#FFFFFF", "TEXT2": "#F5F5FF",
        "SUBTEXT": "#BBBBDD", "GREEN": "#21B1FF", "RED": "#FF218C", "YELLOW": "#FFD800",
        "CYAN": "#21B1FF", "ORANGE": "#FF218C",
        "STRIPE_COLOURS": ["#FF218C", "#FF218C", "#FFD800", "#FFD800", "#21B1FF", "#21B1FF"],
    },
    "genderqueer_flag": {
        "BG": "#141020", "PANEL": "#1e1630", "BORDER": "#B57EDC", "ACCENT": "#B57EDC",
        "ACCENT2": "#CCAAEE", "TAB": "#B57EDC", "TEXT": "#FFFFFF", "TEXT2": "#F0EAFF",
        "SUBTEXT": "#BBA8D8", "GREEN": "#498019", "RED": "#B57EDC", "YELLOW": "#FFFFFF",
        "CYAN": "#498019", "ORANGE": "#B57EDC",
        "STRIPE_COLOURS": ["#B57EDC", "#B57EDC", "#FFFFFF", "#FFFFFF", "#498019", "#498019"],
    },
    "aro_flag": {
        "BG": "#0a120a", "PANEL": "#101e10", "BORDER": "#3DA542", "ACCENT": "#3DA542",
        "ACCENT2": "#A8D379", "TAB": "#3DA542", "TEXT": "#FFFFFF", "TEXT2": "#E8F5E8",
        "SUBTEXT": "#8CB88C", "GREEN": "#3DA542", "RED": "#A8D379", "YELLOW": "#FFFFFF",
        "CYAN": "#3DA542", "ORANGE": "#A8D379",
        "STRIPE_COLOURS": ["#3DA542", "#A8D379", "#FFFFFF", "#A9A9A9", "#000000"],
    },
    "genderfluid_flag": {
        "BG": "#0d0014", "PANEL": "#170020", "BORDER": "#BE18D6", "ACCENT": "#FF76A4",
        "ACCENT2": "#BE18D6", "TAB": "#FF76A4", "TEXT": "#FFFFFF", "TEXT2": "#F8E8FF",
        "SUBTEXT": "#C099CC", "GREEN": "#BE18D6", "RED": "#FF76A4", "YELLOW": "#FFFFFF",
        "CYAN": "#3300BE", "ORANGE": "#FF76A4",
        "STRIPE_COLOURS": ["#FF76A4", "#FFFFFF", "#BE18D6", "#000000", "#3300BE"],
    },
    "intersex_flag": {
        "BG": "#1a1400", "PANEL": "#2b2200", "BORDER": "#FFD800", "ACCENT": "#FFD800",
        "ACCENT2": "#FFE84D", "TAB": "#FFD800", "TEXT": "#FFFFFF", "TEXT2": "#FFF8CC",
        "SUBTEXT": "#CCAA00", "GREEN": "#FFD800", "RED": "#7A00C8", "YELLOW": "#FFD800",
        "CYAN": "#7A00C8", "ORANGE": "#FFD800",
        "STRIPE_COLOURS": ["#FFD800", "#FFD800", "#FFD800", "#7A00C8", "#7A00C8", "#FFD800", "#FFD800", "#FFD800"],
    },
    "demi_flag": {
        "BG": "#121212", "PANEL": "#1e1e1e", "BORDER": "#7A7A7A", "ACCENT": "#9966CC",
        "ACCENT2": "#BB99EE", "TAB": "#9966CC", "TEXT": "#FFFFFF", "TEXT2": "#F0F0F0",
        "SUBTEXT": "#AAAAAA", "GREEN": "#9966CC", "RED": "#7A7A7A", "YELLOW": "#FFFFFF",
        "CYAN": "#9966CC", "ORANGE": "#9966CC",
        "STRIPE_COLOURS": ["#000000", "#7A7A7A", "#FFFFFF", "#9966CC", "#FFFFFF", "#7A7A7A"],
    },
}

THEME_LABELS = {
    "dark": "Dark", "rich_purple": "Rich Purple", "dark_sand": "Dark Sand",
    "absolute_zero": "Absolute Zero", "light_purple": "Light Purple", "light_sand": "Light Sand",
    "mint": "Mint", "dark_mint": "Dark Mint", "dark_red": "Dark Red", "light_red": "Light Red",
    "light_blue": "Light Blue", "dark_rainbow": "Dark Rainbow", "light_rainbow": "Light Rainbow",
    "pride_flag": "Pride Flag", "trans_flag": "Trans Flag", "nonbinary_flag": "Nonbinary Flag",
    "ace_flag": "Ace Flag", "bi_flag": "Bi Flag", "gay_flag": "Gay Flag", "lesbian_flag": "Lesbian Flag",
    "pan_flag": "Pan Flag", "genderqueer_flag": "Genderqueer Flag", "aro_flag": "Aro Flag",
    "genderfluid_flag": "Genderfluid Flag", "intersex_flag": "Intersex Flag", "demi_flag": "Demi Flag",
}

STRIPE_COLOURS = None
STRIPE_WIDTH = 28  # px, same tiling width as the old Tk draw_stripes()


def set_theme(mode: str):
    global colour_mode
    palette = THEMES.get(mode, THEMES["rich_purple"])
    colour_mode = mode if mode in THEMES else "rich_purple"
    g = globals()
    for key, value in palette.items():
        g[key] = value
    if "STRIPE_COLOURS" not in palette:
        g["STRIPE_COLOURS"] = None


set_theme(colour_mode)


def qt_font(size: int, bold: bool = False) -> QFont:
    families = QFontDatabase.families()
    if FONT in families:
        f = QFont(FONT, size)
    else:
        f = QFont()  # Consolas unavailable — use the OS/Qt default UI font instead
        f.setPointSize(size)
    if bold:
        f.setBold(True)
    return f


def accent_button_qss() -> str:
    return (
        f"QPushButton {{ background-color: {ACCENT}; color: {BG}; "
        f"border: none; border-radius: 3px; padding: 6px 14px; font-weight: bold; }}"
        f"QPushButton:hover {{ background-color: {ACCENT2}; }}"
        f"QPushButton:disabled {{ background-color: {BORDER}; color: {SUBTEXT}; }}"
    )


def subtle_button_qss() -> str:
    return (
        f"QPushButton {{ background-color: {PANEL}; color: {SUBTEXT}; "
        f"border: none; border-radius: 3px; padding: 6px 14px; }}"
        f"QPushButton:hover {{ background-color: {BORDER}; color: {TEXT}; }}"
    )


def line_edit_qss() -> str:
    return (
        f"QLineEdit {{ background-color: {PANEL}; color: {TEXT}; "
        f"border: 1px solid {BORDER}; border-radius: 2px; padding: 3px 6px; "
        f"selection-background-color: {ACCENT}; }}"
        f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
    )


def qss() -> str:
    return f"""
    QWidget {{
        background-color: {BG};
        color: {TEXT};
        font-family: "{FONT}";
        border: none;
    }}
    QMainWindow, QDialog {{ background-color: {BG}; }}
    QPushButton {{
        background-color: {PANEL}; color: {ACCENT}; border: none;
        border-radius: 3px; padding: 6px 14px; font-weight: bold;
    }}
    QPushButton:hover {{ background-color: {BORDER}; color: {TEXT}; }}
    QPushButton:disabled {{ color: {SUBTEXT}; }}
    QLineEdit {{
        background-color: {PANEL}; color: {TEXT}; border: 1px solid {BORDER};
        border-radius: 2px; padding: 3px 6px; selection-background-color: {ACCENT};
    }}
    QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
    QComboBox {{
        background-color: {PANEL}; color: {TEXT}; border: 1px solid {BORDER};
        border-radius: 2px; padding: 3px 6px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {PANEL}; color: {TEXT}; selection-background-color: {ACCENT};
        border: 1px solid {BORDER};
    }}
    QScrollBar:vertical {{ background: {BG}; width: 12px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 24px; border-radius: 4px; }}
    QScrollBar::handle:vertical:hover {{ background: {ACCENT2}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QToolTip {{ background-color: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; }}
    """


class TextChip(QLabel):
    """QLabel with an opaque background chip painted behind its text —
    keeps labels readable when they sit directly on a StripeBackground
    rather than inside an opaque PANEL frame."""

    def __init__(self, text="", *, fg=None, bg=None, radius=3, padding="3px 10px", parent=None):
        super().__init__(text, parent)
        self._chip_bg = QColor(bg or PANEL)
        self._radius = radius
        self.setStyleSheet(f"color: {fg or ACCENT2}; background: transparent; padding: {padding}; border: none;")

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(self._chip_bg)

        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), self._radius, self._radius)
        painter.end()
        super().paintEvent(event)


class StripeBackground(QWidget):
    """Paints repeating ~45° diagonal stripes across the whole widget when
    a flag theme is active (STRIPE_COLOURS set); otherwise just fills BG.
    Child widgets sit on top via a normal layout; stripes show through any
    gap not covered by an opaque widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(False)

    def paintEvent(self, _event):
        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, False)
        w, h = self.width(), self.height()

        colours = STRIPE_COLOURS
        if not colours:
            painter.fillRect(self.rect(), QColor(BG))
            return

        painter.fillRect(self.rect(), QColor(BG))
        stripe_w = STRIPE_WIDTH
        cycle = stripe_w * len(colours)
        extent = w + h + cycle * 2

        start = -cycle
        while start < extent:
            for i, colour in enumerate(colours):
                x0 = start + i * stripe_w
                poly = QPolygonF([
                    QPointF(x0, 0), QPointF(x0 + stripe_w, 0),
                    QPointF(x0 + stripe_w + h, h), QPointF(x0 + h, h),
                ])
                painter.setBrush(QColor(colour))

                painter.setPen(Qt.NoPen)
                painter.drawPolygon(poly)
            start += cycle


class CircleToggle(QWidget):
    """Filled circle = ON, outline circle = OFF. Used for the theme picker
    rows in Settings."""

    toggled = Signal(bool)

    def __init__(self, parent=None, *, enabled: bool = True, color=None, size: int = 20, pad: int = 3):
        super().__init__(parent)
        self._enabled = enabled
        self._color = QColor(colour or ACCENT)
        self._size = size
        self._pad = pad
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self._pad, self._pad, self._size - 2 * self._pad, self._size - 2 * self._pad)
        if self._enabled:
            painter.setBrush(self._color)
            painter.setPen(Qt.PenStyle.NoPen)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(self._color, 2))
        painter.drawEllipse(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._enabled = not self._enabled
            self.update()
            self.toggled.emit(self._enabled)

    def set(self, value: bool):
        self._enabled = bool(value)
        self.update()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
# QT THREAD-SAFETY BRIDGE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
# Tkinter tolerated touching widgets from a background thread (fragile, but
# the original code relied on it in a couple of spots — the startup update
# check and the branch-switch resync both run on a daemon thread and call
# straight into footer_label.config(...)/messagebox.*). Qt does not allow
# this at all — it can crash. A QObject's signals are the standard safe
# hand-off: emitting from any thread auto-queues onto the thread that owns
# the receiving QObject (main_window, which lives on the GUI thread). Every
# background-thread call site below emits through this instead of touching
# a widget directly; the actual widget/dialogue code runs in the connected
# slots on ToolBoxWindow, i.e. on the main thread. The underlying decisions
# (what to check, what to compare, when an update is "available") are 100%
# unchanged from the original.

class ConsoleRedirector(object):
    def __init__(self, original_stream, bridge_signal=None):
        self.original_stream = original_stream
        self.bridge_signal = bridge_signal
        self.buffer = []

    def write(self, text):
        if self.original_stream is not None:
            self.original_stream.write(text)
        self.buffer.append(text)
        if len(self.buffer) > 5000:
            self.buffer = self.buffer[-3000:]
        if self.bridge_signal:
            try:
                self.bridge_signal.emit(text)
            except Exception:
                pass

    def flush(self):
        if self.original_stream is not None:
            self.original_stream.flush()

    def get_logs(self):
        return "".join(self.buffer)


class ConsoleWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ToolBox Console Log")
        self.resize(700, 450)
        self.setStyleSheet(f"background-color: {BG}; color: {TEXT};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Title/Header
        title_label = QLabel("Real-Time Application Console Logs")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {ACCENT}; background: transparent; border: none;")
        layout.addWidget(title_label)

        # Text area
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setFont(QFont("Consolas", 9))
        self.text_area.setStyleSheet(
            f"background-color: {PANEL}; color: {TEXT}; "
            f"border: 1px solid {BORDER}; border-radius: 4px; padding: 5px;"
        )
        layout.addWidget(self.text_area)

        # Buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(
            f"QPushButton {{ background-color: {PANEL}; color: {SUBTEXT}; "
            f"border: 1px solid {BORDER}; border-radius: 3px; padding: 5px 15px; }}"
            f"QPushButton:hover {{ background-color: {BORDER}; color: {TEXT}; }}"
        )
        clear_btn.clicked.connect(self.clear_logs)
        btn_layout.addWidget(clear_btn)

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(
            f"QPushButton {{ background-color: {PANEL}; color: {SUBTEXT}; "
            f"border: 1px solid {BORDER}; border-radius: 3px; padding: 5px 15px; }}"
            f"QPushButton:hover {{ background-color: {BORDER}; color: {TEXT}; }}"
        )
        copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(copy_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: {BG}; "
            f"border: none; border-radius: 3px; padding: 5px 20px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {TEXT}; }}"
        )
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Populate with existing logs
        self.text_area.setPlainText(stdout_redirector.get_logs())
        self.text_area.moveCursor(QTextCursor.MoveOperation.End)

        # Connect to stream signal for real-time updates
        bridge.console_log.connect(self.append_log)

    def append_log(self, text):
        self.text_area.insertPlainText(text)
        self.text_area.moveCursor(QTextCursor.MoveOperation.End)

    def clear_logs(self):
        stdout_redirector.buffer.clear()
        stderr_redirector.buffer.clear()
        self.text_area.clear()

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_area.toPlainText())


class SyncWorker(QThread):
    finished_signal = Signal(bool)

    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    def run(self):
        try:
            # Execute the download/update on a safe background thread
            success = ensure_tool_folder(self.filename, show_errors=False)
            self.finished_signal.emit(success)
        except Exception as e:
            print(f"[Worker] Background thread error syncing {self.filename}: {e}")
            self.finished_signal.emit(False)


class OnboardingWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PyToolBox-Launcher Setup Wizard")
        self.setFixedSize(550, 450)
        self.setStyleSheet(f"background-color: {BG}; color: {TEXT};")

        self.tools_dir = os.path.join(os.getenv("LOCALAPPDATA", ""), "")
        self.selected_theme = "rich_purple"

        # Stacked layout for pages
        self.stack = QStackedWidget()

        # Page 1: Welcome
        self.page1 = QWidget()
        p1_layout = QVBoxLayout(self.page1)
        p1_layout.setContentsMargins(30, 30, 30, 30)
        p1_layout.setSpacing(15)

        p1_logo = QLabel()

        icon_path = os.path.join(SCRIPT_DIR, "../Images", "Boot's-ToolBox-256.ico")
        if os.path.exists(icon_path):
            p1_logo.setPixmap(QIcon(icon_path).pixmap(96, 96))
        p1_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p1_layout.addWidget(p1_logo)

        p1_title = QLabel("Welcome to PyToolBox-Launcher! ✨")
        p1_title.setFont(qt_font(14, bold=True))
        p1_title.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
        p1_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p1_layout.addWidget(p1_title)

        p1_desc = QLabel(
            "Hello! I'm Boots. I'm going to help you get your ToolBox set up in "
            "just a few simple steps so it's not scary or confusing at all! :3\n\n"
            "PyToolBox-Launcher lets you easily download, run, and update all of your "
            "favorite companion tools from a single centralized dashboard."
        )
        p1_desc.setFont(qt_font(10))
        p1_desc.setWordWrap(True)
        p1_desc.setStyleSheet(f"color: {TEXT}; background: transparent; border: none; line-height: 140%;")
        p1_layout.addWidget(p1_desc)
        p1_layout.addStretch()

        # Page 2: Installation Path
        self.page2 = QWidget()
        p2_layout = QVBoxLayout(self.page2)
        p2_layout.setContentsMargins(30, 30, 30, 30)
        p2_layout.setSpacing(15)

        p2_title = QLabel("Choose Your Tools Folder 📁")
        p2_title.setFont(qt_font(14, bold=True))
        p2_title.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
        p2_layout.addWidget(p2_title)

        p2_desc = QLabel(
            "Every companion tool is lightweight and modular. We need to choose "
            "where on your system these tools will be downloaded and kept.\n\n"
            "We highly recommend using our safe, default local AppData folder:"
        )
        p2_desc.setFont(qt_font(10))
        p2_desc.setWordWrap(True)
        p2_desc.setStyleSheet("background: transparent; border: none;")
        p2_layout.addWidget(p2_desc)

        self.path_entry = QLineEdit(self.tools_dir)
        self.path_entry.setReadOnly(True)
        self.path_entry.setFont(qt_font(9))
        self.path_entry.setStyleSheet(line_edit_qss())
        p2_layout.addWidget(self.path_entry)

        p2_btn_layout = QHBoxLayout()
        choose_btn = QPushButton("📂 Browse / Choose Folder...")
        choose_btn.setStyleSheet(subtle_button_qss())
        choose_btn.setFont(qt_font(9, bold=True))
        choose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_btn.clicked.connect(self.browse_folder)
        p2_btn_layout.addWidget(choose_btn)

        default_btn = QPushButton("↺ Use Default Path")
        default_btn.setStyleSheet(subtle_button_qss())
        default_btn.setFont(qt_font(9, bold=True))
        default_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        default_btn.clicked.connect(self.use_default_path)
        p2_btn_layout.addWidget(default_btn)
        p2_btn_layout.addStretch()
        p2_layout.addLayout(p2_btn_layout)
        p2_layout.addStretch()

        # Page 3: Theme Selection
        self.page3 = QWidget()
        p3_layout = QVBoxLayout(self.page3)
        p3_layout.setContentsMargins(30, 30, 30, 30)
        p3_layout.setSpacing(15)

        p3_title = QLabel("Pick Your Style 🎨")
        p3_title.setFont(qt_font(14, bold=True))
        p3_title.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
        p3_layout.addWidget(p3_title)

        p3_desc = QLabel(
            "Pick a default colour palette to style your ToolBox dashboard. "
            "You can always customize and change this anytime in Settings!"
        )
        p3_desc.setFont(qt_font(10))
        p3_desc.setWordWrap(True)
        p3_desc.setStyleSheet("background: transparent; border: none;")
        p3_layout.addWidget(p3_desc)

        self.theme_combo = QComboBox()
        for mode, label_text in THEME_LABELS.items():
            self.theme_combo.addItem(label_text, mode)
        self.theme_combo.setCurrentText(THEME_LABELS[self.selected_theme])
        self.theme_combo.setFont(qt_font(10))
        self.theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_combo.currentTextChanged.connect(self.preview_theme)
        p3_layout.addWidget(self.theme_combo)
        p3_layout.addStretch()

        # Page 4: Success / Finish
        self.page4 = QWidget()
        p4_layout = QVBoxLayout(self.page4)
        p4_layout.setContentsMargins(30, 30, 30, 30)
        p4_layout.setSpacing(15)

        p4_logo = QLabel()
        if os.path.exists(icon_path):
            p4_logo.setPixmap(QIcon(icon_path).pixmap(80, 80))
        p4_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p4_layout.addWidget(p4_logo)

        p4_title = QLabel("You're All Set! 🎉")
        p4_title.setFont(qt_font(14, bold=True))
        p4_title.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
        p4_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p4_layout.addWidget(p4_title)

        p4_desc = QLabel(
            "Awesome job! Setup is completely finished.\n\n"
            "When you proceed, the ToolBox dashboard will open. "
            "Simply click 'Download' or 'Run' on any script to instantly deploy "
            "and manage it in a separate, isolated virtual environment.\n\n"
            "Enjoy your experience, and remember we're here on Discord if you ever need help! :3"
        )
        p4_desc.setFont(qt_font(10))
        p4_desc.setWordWrap(True)
        p4_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p4_desc.setStyleSheet("background: transparent; border: none;")
        p4_layout.addWidget(p4_desc)
        p4_layout.addStretch()

        # Add all pages to stacked widget
        self.stack.addWidget(self.page1)
        self.stack.addWidget(self.page2)
        self.stack.addWidget(self.page3)
        self.stack.addWidget(self.page4)

        # Main Layout
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Body area containing stacked widget
        body_panel = QFrame()
        body_panel.setStyleSheet(f"background-color: {PANEL}; border: none;")
        body_panel_layout = QVBoxLayout(body_panel)
        body_panel_layout.setContentsMargins(0, 0, 0, 0)
        body_panel_layout.addWidget(self.stack)
        root_layout.addWidget(body_panel, 1)

        # Divider line
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {BORDER}; border: none;")
        root_layout.addWidget(divider)

        # Action navigation buttons
        nav_panel = QWidget()
        nav_panel.setStyleSheet(f"background-color: {BG};")
        nav_layout = QHBoxLayout(nav_panel)
        nav_layout.setContentsMargins(20, 10, 20, 15)

        self.back_btn = QPushButton("← Back")
        self.back_btn.setStyleSheet(subtle_button_qss())
        self.back_btn.setFont(qt_font(9, bold=True))
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setMinimumWidth(90)
        self.back_btn.clicked.connect(self.go_back)
        nav_layout.addWidget(self.back_btn)

        nav_layout.addStretch(1)

        self.next_btn = QPushButton("Next →")
        self.next_btn.setStyleSheet(accent_button_qss())
        self.next_btn.setFont(qt_font(9, bold=True))
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setMinimumWidth(100)
        self.next_btn.clicked.connect(self.go_next)
        nav_layout.addWidget(self.next_btn)

        root_layout.addWidget(nav_panel)

        self.update_nav_buttons()

    def browse_folder(self):
        chosen = QFileDialog.getExistingDirectory(self, "Choose Tools Folder", self.tools_dir)
        if chosen:
            self.tools_dir = chosen
            self.path_entry.setText(self.tools_dir)

    def use_default_path(self):
        self.tools_dir = os.path.join(os.getenv("LOCALAPPDATA", ""), "")
        self.path_entry.setText(self.tools_dir)

    def preview_theme(self, label_text):
        for mode, name in THEME_LABELS.items():
            if name == label_text:
                self.selected_theme = mode
                set_theme(mode)
                self.setStyleSheet(f"background-color: {BG}; color: {TEXT};")
                self.path_entry.setStyleSheet(line_edit_qss())
                break

    def update_nav_buttons(self):
        idx = self.stack.currentIndex()
        self.back_btn.setEnabled(idx > 0)
        if idx == self.stack.count() - 1:
            self.next_btn.setText("Get Started! 🎉")
        else:
            self.next_btn.setText("Next →")

    def go_back(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self.update_nav_buttons()

    def go_next(self):
        idx = self.stack.currentIndex()
        if idx < self.stack.count() - 1:
            self.stack.setCurrentIndex(idx + 1)
            self.update_nav_buttons()
        else:
            self.accept()


class _Bridge(QObject):
    footer_text = Signal(str)
    refresh_labels = Signal()
    confirm_main_update = Signal(str, str, str)   # prompt, remote_text, remote_url
    show_info = Signal(str, str)
    show_error = Signal(str, str)
    console_log = Signal(str)


bridge = _Bridge()

stdout_redirector = ConsoleRedirector(sys.stdout, bridge.console_log)
stderr_redirector = ConsoleRedirector(sys.stderr, bridge.console_log)
sys.stdout = stdout_redirector
sys.stderr = stderr_redirector

# Set once the main window is constructed (see entry point at the bottom).
# Business-logic functions below reference this by name, resolved at call
# time — same forward-reference pattern the original script already used
# with its module-level `root`/`footer_label` globals.
main_window = None


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
# BOOT: migrate old layouts, load/save config, resolve managed scripts
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#

def _migrate_legacy_config_folder() -> None:
    """One-time migration: older builds stored the ToolBox's own config under
    Nova-Tools/NovaCore-Toolbox/. Newer builds use Nova-Tools/configs/
    instead — move any existing files over so settings (branch, python
    interpreter, managed scripts list) aren't silently lost."""
    legacy_config_dir = os.path.join(TOOLS_ROOT_DIR, "NovaCore-Toolbox")
    # Support migration from legacy "VRChat-Toolbox" name too
    legacy_vrchat_dir = os.path.join(TOOLS_ROOT_DIR, "VRChat-Toolbox")
    for legacy_dir in [legacy_config_dir, legacy_vrchat_dir]:
        if not os.path.isdir(legacy_dir) or os.path.abspath(legacy_dir) == os.path.abspath(TOOLBOX_CONFIG_DIR):
            continue
        try:
            os.makedirs(TOOLBOX_CONFIG_DIR, exist_ok=True)
            for name in os.listdir(legacy_dir):
                src = os.path.join(legacy_dir, name)
                dst = os.path.join(TOOLBOX_CONFIG_DIR, name)
                if os.path.exists(dst):
                    continue
                os.replace(src, dst)
                print(f"[Layout] Moved config item '{name}' from {os.path.basename(legacy_dir)}/ -> configs/")
            if not os.listdir(legacy_dir):
                os.rmdir(legacy_dir)
        except OSError as e:
            print(f"[Layout] Could not migrate legacy config folder: {e}")


_migrate_legacy_config_folder()

def load_managed_scripts():
    global UPDATE_BRANCH, BETA_POPUP_SHOWN, PYTHON_INTERPRETER, colour_mode, MANAGED_SCRIPTS, TOOLS_ROOT_DIR
    
    appdata_toolbox_dir = os.path.join(os.getenv("LOCALAPPDATA", ""), "")
    os.makedirs(appdata_toolbox_dir, exist_ok=True)
    status_file = os.path.join(appdata_toolbox_dir, "run_status.txt")

    # Save the current installation directory so the uninstaller can find it
    try:
        with open(INSTALL_PATH_POINTER, "w", encoding="utf-8") as f_inst:
            f_inst.write(os.path.abspath(SCRIPT_DIR))

    except Exception as ex:
        print(f"[Config] Error saving install path pointer: {ex}")

    tools_root = None
    config_loaded = False
    config = {}

    # 1. Check if the tools path pointer exists in AppData
    if os.path.exists(TOOLS_PATH_POINTER):
        try:
            with open(TOOLS_PATH_POINTER, "r", encoding="utf-8") as f_ptr:
                tools_root = f_ptr.read().strip()
            print(f"[Config] Found tools path pointer: {tools_root}")
        except Exception as e:
            print(f"[Config] Error reading tools path pointer: {e}")

    # If we found a tools root from the pointer, resolve the config file path there
    if tools_root and os.path.isdir(tools_root):
        target_config_file = os.path.join(tools_root, "configs", "toolbox_config.json")
        if os.path.exists(target_config_file):
            try:
                with open(target_config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                config_loaded = True
                print(f"[Config] Loaded configuration from tools directory: {target_config_file}")
            except Exception as e:
                print(f"[Config] Error loading config from tools: {e}")

    # 2. Fallback / Migration: Check if central config exists, or check if default/legacy config file exists in SCRIPT_DIR
    if not config_loaded:
        if os.path.exists(CENTRAL_CONFIG_FILE):
            try:
                with open(CENTRAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                config_loaded = True
                tools_root = config.get("tools_root_dir", os.path.join(SCRIPT_DIR, "../Nova-Tools"))
                print(f"[Config] Migrated central configuration from {CENTRAL_CONFIG_FILE}")
            except Exception as e:
                print(f"[Config] Error loading legacy central config: {e}")
        else:
            default_legacy_file = os.path.join(SCRIPT_DIR, "../Nova-Tools", "configs", "toolbox_config.json")
            if os.path.exists(default_legacy_file):
                try:
                    with open(default_legacy_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    config_loaded = True
                    tools_root = os.path.join(SCRIPT_DIR, "../Nova-Tools")
                    print(f"[Config] Loaded fallback/legacy config: {default_legacy_file}")
                except Exception as e:
                    print(f"[Config] Error loading legacy config: {e}")

    # 3. If no config was loaded, this is a first-time run! Run the Onboarding Wizard
    if not config_loaded:
        wizard = OnboardingWizard()
        if wizard.exec() == QDialog.DialogCode.Accepted:
            chosen_dir = wizard.tools_dir
            chosen_theme = wizard.selected_theme
        else:
            chosen_dir = os.path.join(os.getenv("LOCALAPPDATA", ""), "")
            chosen_theme = "rich_purple"

        # Temporarily apply layout path to discover tools during setup
        update_layout_paths(chosen_dir)
        discovered_scripts = discover_managed_scripts()

        print(f"[Config] First run setup complete. Tools directory: {chosen_dir}, Theme: {chosen_theme}")
        config = {
            "version": VERSION,
            "update_branch": "main",
            "beta_popup_shown": False,
            "python_interpreter": "",
            "theme_mode": chosen_theme,
            "tools_root_dir": chosen_dir,
            "managed_scripts": discovered_scripts
        }
        tools_root = chosen_dir

    # Write the tools path to the pointer file so it's loaded automatically next time
    try:
        with open(TOOLS_PATH_POINTER, "w", encoding="utf-8") as f_ptr:
            f_ptr.write(os.path.abspath(tools_root or ""))

    except Exception as ex:
        print(f"[Config] Error writing tools path pointer: {ex}")

    # Read/apply values from the config
    UPDATE_BRANCH = config.get("update_branch", "main")
    BETA_POPUP_SHOWN = config.get("beta_popup_shown", False)
    PYTHON_INTERPRETER = config.get("python_interpreter", "")
    set_theme(config.get("theme_mode", "rich_purple"))
    
    # Dynamically update global tools path and sub-paths!

    update_layout_paths(tools_root)

    # Verify version matches for upgrade/downgrade detection
    config_version = config.get("version")
    if config_version == VERSION:
        try:
            with open(status_file, "w", encoding="utf-8") as f_status:
                f_status.write(f"New executable v{VERSION} ran successfully.\n")

        except Exception as ex:
            print(f"[Config] Error writing status file: {ex}")
    else:
        # Avoid cleaning AppData on first run (when config_version is None because no config existed)
        if config_version is not None:
            print(f"[Config] Version mismatch (Config: {config_version}, App: {VERSION}). Wiping and regenerating config...")
            try:
                # Wipe old AppData/Local/Project-Proto cache (except our pointer and config files!)
                for item in os.listdir(appdata_toolbox_dir):
                    item_path = os.path.join(appdata_toolbox_dir, item)
                    if item_path in [CENTRAL_CONFIG_FILE, TOOLS_PATH_POINTER, INSTALL_PATH_POINTER]:
                        continue
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)
                    else:
                        os.remove(item_path)
                        
                with open(status_file, "w", encoding="utf-8") as f_status:
                    f_status.write(f"An old executable (v{config_version}) was run previously. Performing clean installation of tools...\n")
                print(f"[Config] Cleaned old AppData cached files in: {appdata_toolbox_dir}")

            except Exception as ex:
                print(f"[Config] Error during AppData clean installation process: {ex}")
            
            QTimer.singleShot(1000, force_update_all_scripts)

    # Load the tool name labels cache
    global _tool_label_cache
    _tool_label_cache = config.get("cached_labels", {})

    # Extract any custom scripts the user manually added
    saved_scripts = config.get("managed_scripts", [])
    custom_scripts = [s for s in saved_scripts if s.get("custom", False)]

    # Dynamically discover all tools instead of relying on a static hardcoded config list!
    discovered_scripts = discover_managed_scripts()
    
    # Combine auto-detected scripts with custom ones
    combined_scripts = discovered_scripts + custom_scripts

    # Save config inside the tools directory
    config["version"] = VERSION
    config["tools_root_dir"] = TOOLS_ROOT_DIR
    config["managed_scripts"] = combined_scripts
    config["cached_labels"] = _tool_label_cache
    try:
        os.makedirs(TOOLBOX_CONFIG_DIR, exist_ok=True)
        with open(TOOLBOX_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[Config] Error saving config inside tools directory: {e}")

    # Enforce beta clean-up
    if UPDATE_BRANCH == "beta":
        if os.path.exists(TOOLBOX_CONFIG_FILE):
            try:
                os.remove(TOOLBOX_CONFIG_FILE)
            except OSError:
                pass

    return combined_scripts


def save_managed_scripts(scripts):
    try:
        os.makedirs(TOOLBOX_CONFIG_DIR, exist_ok=True)
        config = {
            "version": VERSION,
            "update_branch": UPDATE_BRANCH,
            "beta_popup_shown": BETA_POPUP_SHOWN,
            "python_interpreter": PYTHON_INTERPRETER,
            "theme_mode": colour_mode,
            "tools_root_dir": TOOLS_ROOT_DIR,
            "managed_scripts": scripts,
            "cached_labels": _tool_label_cache
        }
        with open(TOOLBOX_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print(f"[Config] Saved {len(scripts)} managed scripts (v{VERSION}) to {TOOLBOX_CONFIG_FILE}")
        
        # Ensure the path pointer file matches
        try:
            os.makedirs(CENTRAL_CONFIG_DIR, exist_ok=True)
            with open(TOOLS_PATH_POINTER, "w", encoding="utf-8") as f_ptr:
                f_ptr.write(os.path.abspath(TOOLS_ROOT_DIR))
        except Exception:
            pass
    except Exception as e:
        print(f"[Config] Error saving config: {e}")


MANAGED_SCRIPTS = []

print("Boot's ToolBox")
print("Made By Boots")
print(f"Version {VERSION}")


def _lhm_exe_path() -> str:
    return os.path.join(TOOLS_ROOT_DIR, LHM_FOLDER, LHM_EXE_NAME)


def ensure_lhm(show_errors: bool = False) -> bool:
    """Download and extract the full LibreHardwareMonitor package if not already present."""
    dest = _lhm_exe_path()
    lhm_dir = os.path.dirname(dest)
    if os.path.isfile(dest):
        return True

    os.makedirs(lhm_dir, exist_ok=True)
    print(f"[LHM] Downloading from {LHM_RELEASE_URL} ...")
    try:
        resp = requests.get(LHM_RELEASE_URL, timeout=60)
        resp.raise_for_status()
        zdata = io.BytesIO(resp.content)
        with zipfile.ZipFile(zdata) as zf:
            members = zf.namelist()

            # Detect whether the ZIP has a single top-level subfolder (common GitHub pattern)
            top_dirs = {m.split("/")[0] for m in members if "/" in m}
            single_root = (
                    len(top_dirs) == 1 and
                    all(m.startswith(next(iter(top_dirs)) + "/") or m == next(iter(top_dirs)) + "/"
                        for m in members)
            )
            strip_prefix = (next(iter(top_dirs)) + "/") if single_root else ""

            exe_members = [m for m in members if m.endswith(LHM_EXE_NAME)]
            if not exe_members:
                raise FileNotFoundError(f"{LHM_EXE_NAME} not found in release ZIP")

            # Extract everything (exe + all DLLs and supporting files) into lhm_dir
            for member in members:
                if member.endswith("/"):
                    continue
                rel_path = member[len(strip_prefix):] if strip_prefix and member.startswith(strip_prefix) else member
                out_path = os.path.join(lhm_dir, rel_path.replace("/", os.sep))
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with zipfile.ZipFile(zdata).open(member) as src, open(out_path, "wb") as dst:
                    dst.write(src.read())
                print(f"[LHM] Extracted: {rel_path}")

        print(f"[LHM] All files extracted to {lhm_dir}")
        return True
    except Exception as e:
        print(f"[LHM] Download failed: {e}")
        if show_errors:
            QMessageBox.critical(
                main_window, "Libre Hardware Monitor",
                f"Could not download LibreHardwareMonitor.\n\nCheck your internet connection and try again.\n\nDetails:\n{e}"
            )
        return False


def _patch_lhm_config() -> None:
    """
    Ensure the LHM .config file has the required keys set before launch.
    Sets:
      runWebServerMenuItem = true   (enables the web API on port 8085)
      startMinMenuItem     = true   (starts minimised to tray)
    Creates the config from scratch if it doesn't exist yet.
    """
    lhm_dir = os.path.dirname(_lhm_exe_path())
    cfg_path = os.path.join(lhm_dir, "LibreHardwareMonitor.config")


    REQUIRED = {
        "runWebServerMenuItem": "true",
        "startMinMenuItem": "true",
    }

    # ── Build / load the XML tree ─────────────────────────────────────────────
    if os.path.isfile(cfg_path):
        try:
            tree = ET.parse(cfg_path)
            root_el = tree.getroot()
        except ET.ParseError as e:
            print(f"[LHM] Config parse error ({e}), will recreate.")
            root_el = ET.Element("configuration")
            tree = ET.ElementTree(root_el)
    else:
        print("[LHM] No config found, creating one.")
        root_el = ET.Element("configuration")
        tree = ET.ElementTree(root_el)

    # ── Find or create <appSettings> ─────────────────────────────────────────
    app_settings = root_el.find("appSettings")
    if app_settings is None:
        app_settings = ET.SubElement(root_el, "appSettings")

    # ── Update / insert each required key ────────────────────────────────────
    for key, value in REQUIRED.items():
        node = app_settings.find(f"./add[@key='{key}']")
        if node is not None:
            if node.get("value") != value:
                print(f"[LHM] Config: setting {key} = {value} (was {node.get('value')})")
                node.set("value", value)
        else:
            print(f"[LHM] Config: inserting {key} = {value}")
            ET.SubElement(app_settings, "add", key=key, value=value)

    # ── Write back ────────────────────────────────────────────────────────────
    try:
        tree.write(cfg_path, encoding="utf-8", xml_declaration=True)
        print(f"[LHM] Config written to {cfg_path}")
    except Exception as e:
        print(f"[LHM] Could not write config: {e}")


def _show_lhm_started_popup() -> None:
    """Small non-blocking confirmation that LHM launched successfully.
    Always called from launch_lhm(), which is only ever invoked from a
    button click (main thread) — no cross-thread hand-off needed here."""
    dlg = QDialog(main_window)
    dlg.setWindowTitle("Libre Hardware Monitor")
    dlg.setStyleSheet(f"background-color: {BG};")

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    hdr = QWidget()
    hdr.setStyleSheet(f"background-color: {PANEL};")
    hdr_layout = QHBoxLayout(hdr)
    hdr_layout.setContentsMargins(14, 8, 14, 8)
    title_lbl = QLabel("Libre Hardware Monitor")
    title_lbl.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
    title_lbl.setFont(qt_font(11, bold=True))
    hdr_layout.addWidget(title_lbl)
    layout.addWidget(hdr)

    divider = QFrame()
    divider.setFixedHeight(1)
    divider.setStyleSheet(f"background-color: {BORDER}; border: none;")
    layout.addWidget(divider)

    body = QWidget()
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(20, 14, 20, 14)
    body_lbl = QLabel(
        "✓  LHM started successfully.\n\nIt will appear in your system tray shortly.\n"
        "The UAC prompt may have appeared behind this window."
    )
    body_lbl.setStyleSheet(f"color: {TEXT}; background: transparent; border: none;")
    body_lbl.setFont(qt_font(9))
    body_layout.addWidget(body_lbl)

    ok_btn = QPushButton("OK")
    ok_btn.setStyleSheet(accent_button_qss())
    ok_btn.setFont(qt_font(9, bold=True))
    ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    ok_btn.clicked.connect(dlg.close)
    body_layout.addWidget(ok_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

    layout.addWidget(body)
    dlg.exec()


def launch_lhm() -> None:
    """Patch the LHM config, launch the exe with admin elevation, confirm success."""

    main_window.footer_label.setText("Starting up Libre Hardware Monitor...")

    QApplication.instance().processEvents()

    if not ensure_lhm(show_errors=True):

        main_window.footer_label.setText("Error preparing Libre Hardware Monitor")
        return

    # Patch config before every launch so the settings are always correct
    _patch_lhm_config()

    dest = _lhm_exe_path()
    try:
        if sys.platform == "win32":
            import ctypes
            shell32 = getattr(ctypes.windll, "shell32")

            ShellExecuteW = getattr(shell32, "ShellExecuteW")
            ret = ShellExecuteW(
                None, "runas", dest, None, os.path.dirname(dest), 1
            )
            if ret <= 32:
                raise OSError(f"ShellExecuteW returned {ret} (elevation may have been denied)")
            print(f"[LHM] Launched with admin elevation via ShellExecuteW")
        else:
            p = subprocess.Popen([dest], cwd=os.path.dirname(dest))
            print(f"[LHM] Launched (PID: {p.pid})")

        _show_lhm_started_popup()

        main_window.footer_label.setText("Ready")
    except Exception as e:
        print(f"[LHM] Launch failed: {e}")

        main_window.footer_label.setText("Error launching Libre Hardware Monitor")
        QMessageBox.critical(main_window, "Launch Error", f"Failed to start LibreHardwareMonitor.\n\nDetails:\n{e}")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
# MANAGED SCRIPT HELPERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#

def _ensure_layout_dirs() -> None:
    os.makedirs(TOOLS_ROOT_DIR, exist_ok=True)
    os.makedirs(TOOLBOX_CONFIG_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _migrate_legacy_layout() -> None:
    pass


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
# TOOL STATE (missing / needs update / current) — drives button labels
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#

def _tool_folder_name(filename: str) -> str:
    """Top-level repo folder for a tool, e.g. 'OSC-Chatbox/main.py' -> 'OSC-Chatbox'."""
    return filename.split("/")[0]


def _tool_local_path(filename: str) -> str:
    """Local disk path to a tool's main file."""
    return os.path.join(TOOLS_ROOT_DIR, filename.replace("/", os.sep))


def get_tool_state(filename: str) -> str:
    """Best-known state for a tool. Falls back to a plain local-existence
    check if the background scan hasn't reached this tool yet."""
    if filename in tool_states:
        return tool_states[filename]
    if filename == LHM_FILENAME:
        return TOOL_STATE_CURRENT if os.path.isfile(_lhm_exe_path()) else TOOL_STATE_MISSING
    return TOOL_STATE_CURRENT if os.path.isfile(_tool_local_path(filename)) else TOOL_STATE_MISSING


def _detect_tool_state(filename: str) -> str:
    """Cheap, download-free check used by the background boot scan: fetches
    only the tool's main file (not the whole folder) purely to compare
    version strings, so we can label the button correctly before the user
    ever clicks it."""
    if filename == LHM_FILENAME:
        return TOOL_STATE_CURRENT if os.path.isfile(_lhm_exe_path()) else TOOL_STATE_MISSING

    dest_path = _tool_local_path(filename)
    if not os.path.isfile(dest_path):
        return TOOL_STATE_MISSING

    remote_text, remote_version, _ = _fetch_remote_script(f"{get_github_base_url()}{filename}", timeout=10)
    if remote_text is None:
        # Can't reach GitHub — don't falsely flag as needing an update
        return TOOL_STATE_CURRENT

    try:
        with open(dest_path, "r", encoding="utf-8") as lf:
            local_text = lf.read()
    except OSError:
        local_text = ""

    local_version = _extract_version_from_source(local_text) or "0.0.0"
    remote_version = remote_version or "0.0.0"
    if _parse_version(remote_version) > _parse_version(local_version):
        return TOOL_STATE_UPDATE
    return TOOL_STATE_CURRENT


def refresh_tool_states_background() -> None:
    """Runs on a background thread at boot. Only ever reads/compares version
    strings — never downloads a tool folder. Missing tools stay TOOL_STATE_MISSING
    (no point checking their remote version yet); present tools get flagged
    TOOL_STATE_UPDATE or TOOL_STATE_CURRENT so the button label is right
    before the user ever clicks anything."""
    for script in MANAGED_SCRIPTS:
        filename = script["filename"]
        tool_states[filename] = _detect_tool_state(filename)
        bridge.refresh_labels.emit()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
# TOOL FOLDER SYNC — auto-discovers every file under a tool's GitHub folder
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#

# Cached recursive file listing of the repo for the current branch, so
# clicking several tools in one session doesn't burn GitHub's unauthenticated
# API rate limit (60 requests/hour). One tree fetch covers every tool.
_repo_tree_cache: dict = {"branch": None, "paths": None}


def get_repo_tree(force: bool = False) -> list[str] | None:
    global _repo_tree_cache
    if not force and _repo_tree_cache["branch"] == UPDATE_BRANCH and _repo_tree_cache["paths"] is not None:
        return _repo_tree_cache["paths"]

    url = f"https://api.github.com/repos/CaptainBoots/Nova-Tools/git/trees/{UPDATE_BRANCH}?recursive=1"
    try:
        resp = requests.get(url, timeout=15, headers={"Accept": "application/vnd.github+json"})
        resp.raise_for_status()
        data = resp.json()
        paths = [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]
        _repo_tree_cache = {"branch": UPDATE_BRANCH, "paths": paths}
        return paths
    except Exception as e:
        print(f"[Tree] Failed to fetch repo file tree: {e}")
        return None


def _tool_remote_files(filename: str) -> list[str] | None:
    """Every file path (relative to the repo's folder, e.g.
    'OSC-Router/ui/app.py') that belongs to this tool's folder, or None if
    the tree couldn't be fetched at all.
    """
    tool_prefix = f"{_tool_folder_name(filename)}/"
    paths = get_repo_tree()
    if paths is None:
        return None
    return [p for p in paths if p.startswith(tool_prefix)]


def ensure_tool_folder(filename: str, show_errors: bool = False) -> bool:
    """Downloads (or re-syncs) every file GitHub currently has under a tool's
    folder. Used for both a first-time download AND an update — it always
    just pulls whatever's on the branch right now, so there's no separate
    'ensure' vs 'update' code path and no dependency list to maintain."""
    if filename == LHM_FILENAME:
        return ensure_lhm(show_errors=show_errors)

    dest_path = _tool_local_path(filename)
    remote_files = _tool_remote_files(filename)

    if remote_files is None:
        # Couldn't reach GitHub at all
        if os.path.isfile(dest_path):
            return True
        if show_errors:
            QMessageBox.critical(
                main_window, f"{filename} Error",
                f"Could not prepare {filename}.\nCheck your internet connection and try again.",
            )
        return False

    if not remote_files:
        print(f"[{filename}] No files found under '{_tool_folder_name(filename)}/' on branch '{UPDATE_BRANCH}'.")
        return os.path.isfile(dest_path)

    success = True
    for rel_path in remote_files:
        file_dest = os.path.join(TOOLS_ROOT_DIR, rel_path.replace("/", os.sep))
        try:
            os.makedirs(os.path.dirname(file_dest), exist_ok=True)
            resp = requests.get(
                f"{get_github_base_url()}{rel_path}", timeout=15, params={"_": int(time.time())},
                headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
            )
            resp.raise_for_status()
            with open(file_dest, "wb") as df:
                df.write(resp.content)
            print(f"[{filename}] Synced: {rel_path}")
        except Exception as e:
            print(f"[{filename}] Failed to sync {rel_path}: {e}")
            success = False

    if not success and show_errors:
        QMessageBox.critical(
            main_window, f"{filename} Error",
            f"Some files for {filename} failed to download.\nCheck your internet connection and try again.",
        )

    return success and os.path.isfile(dest_path)


def launch_script(filename: str) -> None:
    """Downloads/updates the tool's folder if needed (based on its current
    state), then launches it in a separate process. Always called from a
    button click (main thread). Downloads run in background SyncWorker thread."""
    # Route LHM to its dedicated launcher
    if filename == LHM_FILENAME:
        launch_lhm()
        tool_states[filename] = TOOL_STATE_CURRENT if os.path.isfile(_lhm_exe_path()) else TOOL_STATE_MISSING

        main_window.refresh_button_labels()
        return

    state = get_tool_state(filename)
    if state == TOOL_STATE_MISSING:

        main_window.footer_label.setText(f"Downloading {filename}... (please wait)")
    elif state == TOOL_STATE_UPDATE:

        main_window.footer_label.setText(f"Updating {filename}... (please wait)")
    else:

        main_window.footer_label.setText(f"Starting up {filename}...")

    # Disable window to prevent double click while downloading/starting

    main_window.setEnabled(False)

    QApplication.instance().processEvents()

    def on_sync_finished(success: bool):

        main_window.setEnabled(True)
        if not success:

            main_window.footer_label.setText("Error preparing script")
            QMessageBox.critical(
                main_window, f"{filename} Error",
                f"Some files for {filename} failed to download.\nCheck your internet connection and try again.",
            )
            return

        tool_states[filename] = TOOL_STATE_CURRENT

        main_window.refresh_button_labels()

        # Resolve local execution path
        dest_path = _tool_local_path(filename)
        script_dir = os.path.dirname(dest_path)

        try:
            # Launch script via the configured Python interpreter (falls back to
            # the ToolBox's own interpreter if none is set) in a detached environment
            p = subprocess.Popen(
                [get_active_python(), os.path.basename(dest_path)],
                cwd=script_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )

            print(f"[Launcher] Successfully started {filename} (PID: {p.pid})")

            main_window.footer_label.setText("Ready")

        except Exception as e:
            print(f"[Launcher] Failed to execute {filename}: {e}")

            main_window.footer_label.setText("Error launching script")
            QMessageBox.critical(main_window, "Launch Error", f"Failed to start {filename}.\n\nTechnical details:\n{e}")

    # Async download in SyncWorker thread
    if state in (TOOL_STATE_MISSING, TOOL_STATE_UPDATE):
        main_window.sync_worker = SyncWorker(filename)

        main_window.sync_worker.finished_signal.connect(on_sync_finished)

        main_window.sync_worker.start()
    else:
        # Already current, run launch immediately
        on_sync_finished(True)


def _parse_version(v_str: str) -> tuple[int, ...]:
    try:
        return tuple(map(int, v_str.split(".")))
    except ValueError:
        return 0, 0, 0


def _extract_version_from_source(source_text: str) -> str | None:
    for line in source_text.splitlines():
        if line.strip().startswith("VERSION"):
            match = re.search(r'["\']([^"\']+)["\']', line)
            if match:
                return match.group(1)
    return None


def _extract_name_from_source(source_text: str) -> str | None:
    for line in source_text.splitlines():
        if line.strip().startswith("NAME"):
            match = re.search(r'["\']([^"\']+)["\']', line)
            if match:
                return match.group(1)
    return None


def _extract_id_from_source(source_text: str) -> str | None:
    for line in source_text.splitlines():
        strip_line = line.strip()
        if strip_line.startswith("TOOL_ID") or strip_line.startswith("ID"):
            # Match quoted string ID like TOOL_ID = "000101"
            match = re.search(r'["\']([^"\']+)["\']', strip_line)
            if match:
                return match.group(1).zfill(6)
            # Match integer ID like TOOL_ID = 101
            match_num = re.search(r'=\s*(\d+)', strip_line)
            if match_num:
                return match_num.group(1).zfill(6)
    return None


def _fetch_remote_script(url: str, timeout: int = 10) -> tuple[str | None, str | None, str | None]:
    try:
        resp = requests.get(
            url, timeout=timeout, params={"_": int(time.time())},
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
        )
        resp.raise_for_status()
        return resp.text, _extract_version_from_source(resp.text), url
    except requests.RequestException:
        return None, None, None


def get_remote_script_info() -> dict[str, str] | None:
    urls = [get_github_raw_url()]
    errors = []
    best: dict[str, str] | None = None

    for url in urls:
        text, remote_version, used_url = _fetch_remote_script(url, timeout=10)
        if text is None:
            errors.append(url)
            continue

        info: dict[str, str] = {
            "text": text,
            "version": remote_version or "0.0.0",
            "url": used_url or url,
        }

        if best is None:
            best = info
            continue

        best_version: str = best["version"] if best else "0.0.0"
        if _parse_version(info["version"]) > _parse_version(best_version):
            best = info

    if best is not None:
        return best

    print(f"[Updater] Could not reach GitHub URLs: {errors}")
    return None


def perform_update(remote_text=None, source_url=None):
    """Always executed on the main thread — either directly (not currently
    exercised, since silent=False is never actually passed today, but kept
    intact for parity/future use) or via the confirm_main_update bridge
    signal's slot after the person clicks Yes."""
    try:
        is_frozen = getattr(sys, 'frozen', False)
        script_path: str = os.path.abspath(__file__)

        if is_frozen:
            current_exe = sys.executable
            backup_exe = current_exe + ".bak"

            # Ensure we can delete or find a unique name for backup_exe if it already exists
            counter = 1
            while os.path.exists(backup_exe):
                try:
                    os.remove(backup_exe)
                    break
                except Exception:
                    backup_exe = f"{current_exe}.bak.{counter}"
                    counter += 1

            os.rename(current_exe, backup_exe)
            print(f"[Updater] Renamed active executable to backup: {backup_exe}")

            # Try to download the updated executable.
            exe_names_to_try = [os.path.basename(current_exe)]
            for fallback in ["NovaCore-ToolBox.exe", "VRChat-ToolBox.exe", "ToolBox.exe"]:
                if fallback not in exe_names_to_try:
                    exe_names_to_try.append(fallback)

            downloaded = False
            last_error = None

            for exe_name in exe_names_to_try:
                download_url = f"{GITHUB_EXE_RELEASE_BASE_URL}{exe_name}"
                print(f"[Updater] Trying to download update from: {download_url}")
                try:
                    resp = requests.get(download_url, stream=True, timeout=60)
                    if resp.status_code == 200:
                        with open(current_exe, "wb") as f_dst:
                            for chunk in resp.iter_content(chunk_size=8192):
                                f_dst.write(chunk)
                        downloaded = True
                        print(f"[Updater] Successfully downloaded updated executable from: {download_url}")
                        break
                    else:
                        err_msg = f"HTTP {resp.status_code} - File not found or release unavailable"
                        last_error = err_msg
                        print(f"[Updater] {err_msg} for {download_url}")

                except Exception as ex:
                    last_error = ex
                    print(f"[Updater] Error trying to download from {download_url}: {ex}")

            if not downloaded:
                try:
                    if os.path.exists(backup_exe):
                        if os.path.exists(current_exe):
                            try:
                                os.remove(current_exe)
                            except Exception:
                                pass
                        os.rename(backup_exe, current_exe)
                except Exception as restore_ex:
                    print(f"[Updater] Error restoring backup exe: {restore_ex}")
                
                if last_error and "HTTP 404" in str(last_error):
                    raise RuntimeError(
                        f"Could not download the updated executable from GitHub.\n\n"
                        f"Technical Detail: {last_error}\n\n"
                        "This typically means that there is no compiled release asset matching this executable name "
                        "on the latest release on GitHub, or the repository is private.\n\n"
                        "Please verify that the latest release on GitHub has a compiled 'NovaCore-ToolBox.exe', "
                        "'ToolBox.exe', or 'VRChat-ToolBox.exe' uploaded as a release asset, or perform the update manually."
                    )
                else:
                    raise RuntimeError(f"Could not download updated executable from GitHub. (Error: {last_error})")

        else:
            if remote_text is None:
                info = get_remote_script_info()
                if not info:
                    raise RuntimeError("No remote script source available")
                remote_text = info["text"]
                source_url = info["url"]

            script_path = os.path.abspath(__file__)
            os.makedirs(BACKUP_DIR, exist_ok=True)
            script_name = os.path.splitext(os.path.basename(script_path))[0]

            backup_path = os.path.join(BACKUP_DIR, f"{script_name} {VERSION}.bak")

            with open(script_path, "r", encoding="utf-8") as f_src:
                current_code = f_src.read()
            with open(backup_path, "w", encoding="utf-8") as f_dst:
                f_dst.write(current_code)
            print(f"[Updater] Created rollback backup pointing at: {backup_path}")

            with open(script_path, "w", encoding="utf-8") as f_upper:
                f_upper.write(remote_text)
            print(f"[Updater] Main system assembly updated successfully from {source_url}.")

        # Wipe targeted configurations on version shift
        for tool_key, configs_to_wipe in TOOL_CONFIG_WIPE_MAP.items():
            for relative_cfg in configs_to_wipe:
                full_cfg_path = os.path.join(TOOLS_ROOT_DIR, relative_cfg)
                if os.path.exists(full_cfg_path):
                    try:
                        os.remove(full_cfg_path)
                        print(f"[Updater] Wiped breaking config layout targets: {relative_cfg}")

                    except Exception as ex:
                        print(f"[Updater] Error cleaning target configuration profile: {ex}")

        QMessageBox.information(
            main_window, "Update Complete",
            f"ToolBox updated to the latest available software build on branch '{UPDATE_BRANCH}'.\n\nThe system will now restart automatically."
        )


        main_window.close()
        if is_frozen:
            # Clean PyInstaller environment variables so the new process doesn't think it is a child
            for key in list(os.environ.keys()):
                if "MEIPASS" in key or "PYI" in key or key in ("PYTHONHOME", "PYTHONPATH"):
                    os.environ.pop(key, None)
            
            # Spawn a detached, silent background command that:
            # 1. Sleeps for 2 seconds (ping 127.0.0.1 -n 3 > nul) to let this old process fully exit
            # 2. Launches the new executable cleanly (start "" "ToolBox.exe")
            # This completely breaks the parent process chain, letting PyInstaller boot cleanly.
            cmd = f'ping 127.0.0.1 -n 3 > nul && start "" "{sys.executable}"'
            subprocess.Popen(
                cmd,
                shell=True,
                creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
            )
        else:
            subprocess.Popen([sys.executable, script_path], cwd=os.path.dirname(script_path))
        sys.exit(0)

    except Exception as e:
        print(f"[Updater] Self-update failed catastrophically: {e}")
        QMessageBox.critical(main_window, "Update Failed", f"An error occurred during updating processing:\n\n{e}")


@Slot(str, str, str)
def _on_confirm_main_update(prompt: str, remote_text: str, remote_url: str):
    """Slot for bridge.confirm_main_update — runs on the main thread."""
    msg_box = QMessageBox(main_window)
    msg_box.setWindowTitle("Update Available")
    msg_box.setText(prompt)
    msg_box.setInformativeText("Would you like to update automatically now, or open the GitHub releases page to download manually?")
    msg_box.setStyleSheet(qss())
    
    auto_btn = msg_box.addButton("Auto-Update", QMessageBox.ButtonRole.AcceptRole)
    manual_btn = msg_box.addButton("Manual (GitHub)", QMessageBox.ButtonRole.ActionRole)
    cancel_btn = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    
    msg_box.setDefaultButton(auto_btn)
    msg_box.exec()
    
    clicked = msg_box.clickedButton()
    if clicked == auto_btn:
        perform_update(remote_text=remote_text, source_url=remote_url)
    elif clicked == manual_btn:
        webbrowser.open("https://github.com/CaptainBoots/Project-Proto/releases")
    else:
        print(f"[Nova-Tools] Update skipped by user")


def check_for_main_updates(silent: bool = True):
    """Runs on a background daemon thread (see the threading.Thread call at
    the bottom of this file). All network + version-comparison logic below
    is unchanged from the original — only the dialogue/footer touches were
    swapped for bridge.*.emit() so they execute safely on the main thread."""
    if not silent:
        bridge.footer_text.emit("Connecting to repository update server nodes...")

    info = get_remote_script_info()
    if not info:
        if not silent:
            bridge.show_error.emit("Update Connection Fault", "Unable to pull validation info records from GitHub.")
        bridge.footer_text.emit("Ready")
        return

    remote_text = info["text"]
    remote_version = info["version"]
    remote_url = info["url"]

    remote_newer = _parse_version(remote_version) > _parse_version(VERSION)

    if getattr(sys, 'frozen', False):
        content_differs = False
    else:
        try:
            with open(__file__, "r", encoding="utf-8", errors="ignore") as f:
                local_text = f.read()
        except Exception:
            local_text = ""
        local_norm = local_text.replace("\r\n", "\n")
        remote_norm = remote_text.replace("\r\n", "\n")
        content_differs = remote_norm != local_norm

    main_update_available = remote_newer or content_differs

    print(f"[Nova-Tools] Checking... (local: {VERSION} remote: {remote_version}")
    print(f"[Nova-Tools] Tools Branch: {UPDATE_BRANCH})")

    if main_update_available:
        if remote_newer:
            print(f"[Nova-Tools] Update available: {VERSION} -> {remote_version}")
            if os.path.exists(TOOLBOX_CONFIG_FILE):
                try:
                    os.remove(TOOLBOX_CONFIG_FILE)
                except Exception:
                    pass
            prompt = (
                f"New version {remote_version} is available (you have {VERSION}).\n\n"
                "Update and restart now?"
            )
        else:
            print(f"[Nova-Tools] Remote content differs (version string unchanged at {VERSION})")
            prompt = (
                f"A remote script update is available (content changed,\n"
                "but version string may not have been bumped).\n\n"
                "Update and restart now?"
            )

        bridge.confirm_main_update.emit(prompt, remote_text, remote_url)
    else:
        print(f"[Nova-Tools] Up to date ({VERSION})")

    # Tool downloads/updates no longer happen at boot — just re-run the
    # lightweight version scan so button labels stay accurate.
    threading.Thread(target=refresh_tool_states_background, daemon=True).start()

    if not silent and not main_update_available:
        bridge.show_info.emit("Up to Date", f"You're on the latest version ({VERSION}) for branch '{UPDATE_BRANCH}'.")


def force_update_all_scripts():
    """Wipes the cached/downloaded tool folders and force re-downloads them
    fresh from the newly selected branch. This is the one place tools are
    still eagerly re-synced immediately, since switching branches is an
    explicit user action in Settings rather than something happening at boot."""

    def _update_task():
        global MANAGED_SCRIPTS
        bridge.footer_text.emit(f"Switching branch to '{UPDATE_BRANCH}' & updating...")

        # 1. Fetch remote repository tree for the new branch
        remote_paths = get_repo_tree(force=True)  # branch changed — the cached file listing is stale

        # 2. Identify all valid tool folders belonging to the remote target branch
        valid_remote_tool_folders = set()
        if remote_paths:
            for p in remote_paths:
                parts = p.split("/")
                if len(parts) == 2 and parts[1] == "main.py":
                    valid_remote_tool_folders.add(parts[0])

        # 3. Clean up older local tool folders that do not exist on the target branch
        # (This cleanly gets rid of beta-only tools when switching back to main!)
        if os.path.isdir(TOOLS_ROOT_DIR):
            try:
                for item in os.listdir(TOOLS_ROOT_DIR):
                    folder_path = os.path.join(TOOLS_ROOT_DIR, item)
                    if os.path.isdir(folder_path) and item not in ("LibreHardwareMonitor", "configs", "ToolBox Backup"):
                        if item not in valid_remote_tool_folders:
                            print(f"[Branch Sync] Removing branch-specific tool folder: {item}")
                            shutil.rmtree(folder_path, ignore_errors=True)
            except Exception as e:
                print(f"[Branch Sync] Error cleaning up branch-specific folders: {e}")

        # 4. Dynamically re-discover and update MANAGED_SCRIPTS for the target branch
        # This checks for any newly added/available tools on the chosen branch!
        MANAGED_SCRIPTS = load_managed_scripts()

        success = True
        for script in MANAGED_SCRIPTS:
            filename = script["filename"]
            if filename == LHM_FILENAME:
                continue

            # Skip syncing any custom added tools or files not matching the remote tree
            tool_folder = _tool_folder_name(filename)
            if remote_paths and not any(p.startswith(f"{tool_folder}/") for p in remote_paths):
                continue

            folder_path = os.path.join(TOOLS_ROOT_DIR, tool_folder)
            if os.path.isdir(folder_path):
                try:
                    shutil.rmtree(folder_path)
                except Exception as e:
                    print(f"[{filename}] Could not clear old folder before re-sync: {e}")

            if ensure_tool_folder(filename, show_errors=False):
                tool_states[filename] = TOOL_STATE_CURRENT
            else:
                tool_states[filename] = TOOL_STATE_MISSING
                success = False

        bridge.refresh_labels.emit()

        # Safely trigger a main window button reload on the main thread to reflect any newly discovered scripts!
        if main_window:
            QTimer.singleShot(0, main_window.refresh_main_buttons)

        if success:
            bridge.footer_text.emit(f"Successfully switched to branch '{UPDATE_BRANCH}'!")
            bridge.show_info.emit(
                "Branch Updated",
                f"All scripts have been successfully updated to match the '{UPDATE_BRANCH}' branch structure.",
            )
        else:
            bridge.footer_text.emit("Error updating branch assets")
            bridge.show_error.emit(
                "Branch Update Error",
                "Failed to fully re-download some script assets from the chosen branch.",
            )

    threading.Thread(target=_update_task, daemon=True).start()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
# GUI
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#

def square_button(text: str, command, base_size: int = 28) -> QPushButton:
    """Small square icon button (Help/Settings in the footer). The original
    Tk version had a whole DPI-scaling apparatus (register_scalable /
    apply_ui_scaling) wrapped around this, but apply_ui_scaling() was never
    actually called anywhere in that file — dead code — so it's not carried
    over; Qt also handles DPI scaling natively. Visual result is the same
    fixed-size square icon button.

    Deliberately does NOT use qt_font()/the Consolas code font here — a
    monospace code font typically doesn't include glyphs for symbols like
    ⚙ or the full-width ？, so the label would render blank even with
    Consolas installed. The OS/Qt default UI font has full symbol
    coverage."""
    btn = QPushButton(text)
    btn.setFixedSize(base_size, base_size)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    icon_font = QFont()
    icon_font.setPointSize(12)
    btn.setFont(icon_font)
    btn.setStyleSheet(
        f"QPushButton {{ background-color: {PANEL}; color: {SUBTEXT}; "
        f"border: 1px solid {BORDER}; border-radius: 3px; padding: 0px; }}"
        f"QPushButton:hover {{ background-color: {BORDER}; color: {TEXT}; }}"
    )
    btn.clicked.connect(command)
    return btn


def _show_beta_popup():
    win = QDialog(main_window)
    win.setWindowTitle("Beta Branch")
    win.setFixedSize(420, 260)
    win.setStyleSheet(f"background-color: {BG};")

    layout = QVBoxLayout(win)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    hdr = QWidget()
    hdr.setStyleSheet(f"background-color: {PANEL};")
    hdr_layout = QHBoxLayout(hdr)
    hdr_layout.setContentsMargins(16, 10, 16, 10)
    title_lbl = QLabel("◈ Thanks Beta Tester")
    title_lbl.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
    title_lbl.setFont(qt_font(12, bold=True))
    hdr_layout.addWidget(title_lbl)
    layout.addWidget(hdr)

    divider = QFrame()
    divider.setFixedHeight(1)
    divider.setStyleSheet(f"background-color: {BORDER}; border: none;")
    layout.addWidget(divider)

    body = QWidget()
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(20, 16, 20, 16)

    msg = (
        "Thanks for participating in the beta test!\n\n"
        "Your bug reports help optimize these tools for everyone.\n\n"
        "Join our discord server to report issues or suggest modifications!"
    )
    msg_lbl = QLabel(msg)
    msg_lbl.setStyleSheet(f"color: {TEXT}; background: transparent; border: none;")
    msg_lbl.setFont(qt_font(9))
    msg_lbl.setWordWrap(True)
    body_layout.addWidget(msg_lbl)

    btn_row = QHBoxLayout()
    btn_row.setContentsMargins(0, 18, 0, 0)

    def _join_discord():
        webbrowser.open("https://discord.gg/VWeTPh3m8Q")
        win.close()

    join_btn = QPushButton("Join Discord Server")
    join_btn.setStyleSheet(accent_button_qss())
    join_btn.setFont(qt_font(9, bold=True))
    join_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    join_btn.clicked.connect(_join_discord)
    btn_row.addWidget(join_btn)
    btn_row.addStretch(1)

    dismiss_btn = QPushButton("Dismiss")
    dismiss_btn.setStyleSheet(subtle_button_qss())
    dismiss_btn.setFont(qt_font(9, bold=True))
    dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    dismiss_btn.clicked.connect(win.close)
    btn_row.addWidget(dismiss_btn)

    body_layout.addLayout(btn_row)
    layout.addWidget(body)

    win.exec()


HELP_PAGES = [
    {
        "title": "Welcome to ToolBox",
        "content": (
            "This control centre manages and runs various modular optimization tools "
            "tailored for companion OSC network tracking.\n\n"
            "Features include:\n"
            "• Automated system update patches on initialization cycles.\n"
            "• Sandbox virtual execution container environments.\n"
            "• Fast preference configuration overlays."
        ),
    },
    {
        "title": "Status Indicator",
        "content": (
            "The status shelf located across the footer displays active telemetry feedback:\n"
            "• 'Ready' — waiting for action\n"
            "• 'Starting up (ScriptName)' — launching\n"
            "• 'Up to date' — version check complete\n"
            "• 'Error' — something went wrong"
        ),
    },
    {
        "title": "Available Scripts",
        "content": (
            "▶ Router — Manages OSC routing\n"
            " Forwards OSC messages between sources\n"
            " and destinations.\n\n"
            "▶ ChatBox — Sends data over OSC\n"
            " Displays system info, weather, music,\n"
            " and custom messages.\n\n"
            "▶ Face Tracking Controller — Control\n"
            " face tracking features."
        ),
    },
    {
        "title": "Status Bar",
        "content": (
            "The top bar of each script shows:\n\n"
            "Left: Script name and icon\n"
            "Centre: Version number\n"
            "Right: Current status\n\n"
            "Status Examples:\n"
            "• Status: Running — Script is active\n"
            "• Status: Stopped — Script is inactive\n"
            "• Status: Error — Something failed"
        ),
    },
    {
        "title": "Adding a Script",
        "content": (
            "1. Click the ⚙ (gear) button in the footer\n"
            "2. Click '+ Add Script' button\n"
            "3. Enter a label (button text)\n"
            "4. Enter filename or full path\n"
            "5. Click 'Add' to save\n\n"
            "Your new script button appears in\n"
            "'MANAGED SCRIPTS' section immediately!"
        ),
    },
    {
        "title": "Removing a Script",
        "content": (
            "1. Click the ⚙ (gear) button\n"
            "2. Find the script in the list\n"
            "3. Click the '✕ Remove' button\n"
            "4. Script removed from buttons\n\n"
            "Changes save automatically. Close and\n"
            "reopen ToolBox to fully refresh if needed."
        ),
    },
    {
        "title": "Tips",
        "content": (
            "• Always start Router first, then ChatBox\n\n"
            "• Each script remembers its settings\n"
            " between sessions\n\n"
            "• Check your internet connection if\n"
            " scripts fail to start\n\n"
            "• Run scripts from the ToolBox for\n"
            " proper management"
        ),
    },
]


def open_help():
    help_win = QDialog(main_window)
    help_win.setWindowTitle("Documentation & Guide")
    help_win.setFixedSize(520, 460)
    help_win.setStyleSheet(f"background-color: {BG};")

    root_layout = QVBoxLayout(help_win)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    current_page = [0]

    hdr = QWidget()
    hdr.setStyleSheet(f"background-color: {PANEL};")
    hdr_layout = QHBoxLayout(hdr)
    hdr_layout.setContentsMargins(20, 10, 20, 10)
    title_label = QLabel("")
    title_label.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
    title_label.setFont(qt_font(12, bold=True))
    hdr_layout.addWidget(title_label)
    root_layout.addWidget(hdr)

    divider = QFrame()
    divider.setFixedHeight(1)
    divider.setStyleSheet(f"background-color: {BORDER}; border: none;")
    root_layout.addWidget(divider)

    content_panel = QFrame()
    content_panel.setStyleSheet(f"background-color: {PANEL}; border: none;")
    content_layout = QVBoxLayout(content_panel)
    content_layout.setContentsMargins(14, 14, 14, 14)
    content_label = QLabel("")
    content_label.setStyleSheet(f"color: {TEXT}; background: transparent; border: none;")
    content_label.setFont(qt_font(10))
    content_label.setWordWrap(True)
    content_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    content_layout.addWidget(content_label)

    body_wrap = QWidget()
    body_wrap_layout = QVBoxLayout(body_wrap)
    body_wrap_layout.setContentsMargins(20, 16, 20, 0)
    body_wrap_layout.addWidget(content_panel)
    root_layout.addWidget(body_wrap, 1)

    nav_frame = QHBoxLayout()
    nav_frame.setContentsMargins(20, 8, 20, 14)

    prev_btn = QPushButton("← Back")
    prev_btn.setStyleSheet(subtle_button_qss())
    prev_btn.setFont(qt_font(9, bold=True))
    prev_btn.setFixedWidth(100)
    nav_frame.addWidget(prev_btn)
    nav_frame.addStretch(1)

    page_indicator = QLabel("")
    page_indicator.setStyleSheet(f"color: {SUBTEXT}; background: transparent; border: none;")
    page_indicator.setFont(qt_font(9))
    nav_frame.addWidget(page_indicator)
    nav_frame.addStretch(1)

    next_btn = QPushButton("Next →")
    next_btn.setStyleSheet(accent_button_qss())
    next_btn.setFont(qt_font(9, bold=True))
    next_btn.setFixedWidth(100)
    nav_frame.addWidget(next_btn)

    root_layout.addLayout(nav_frame)

    def show_page(idx):
        p = HELP_PAGES[idx]
        title_label.setText(p["title"])
        content_label.setText(p["content"])
        page_indicator.setText(f"Page {idx + 1} of {len(HELP_PAGES)}")
        prev_btn.setEnabled(idx > 0)
        is_last = idx == len(HELP_PAGES) - 1
        next_btn.setText("Finish" if is_last else "Next →")

    def go_back():
        if current_page[0] > 0:
            current_page[0] -= 1
            show_page(current_page[0])

    def next_or_finish():
        if current_page[0] < len(HELP_PAGES) - 1:
            current_page[0] += 1
            show_page(current_page[0])
        else:
            help_win.close()

    prev_btn.clicked.connect(go_back)
    next_btn.clicked.connect(next_or_finish)

    show_page(0)
    help_win.exec()


def open_settings():
    global MANAGED_SCRIPTS, UPDATE_BRANCH, PYTHON_INTERPRETER, BETA_POPUP_SHOWN

    settings_win = QDialog(main_window)
    settings_win.setWindowTitle("Settings")
    settings_win.resize(520, 560)
    settings_win.setStyleSheet(f"background-color: {BG};")

    root_layout = QVBoxLayout(settings_win)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    # ── Header ────────────────────────────────────────────────────────────
    header = QWidget()
    header.setStyleSheet(f"background-color: {PANEL};")
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(20, 10, 20, 10)
    title_label = QLabel(f"Manage Scripts & Settings (v{VERSION})")
    title_label.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
    title_label.setFont(qt_font(12, bold=True))
    header_layout.addWidget(title_label)
    root_layout.addWidget(header)

    divider = QFrame()
    divider.setFixedHeight(1)
    divider.setStyleSheet(f"background-color: {BORDER}; border: none;")
    root_layout.addWidget(divider)

    # ── Scrollable body (everything below the header scrolls as one unit,
    #    matching the collapsible-Themes-section pattern used across the
    #    rest of the suite) ───────────────────────────────────────────────
    outer_scroll = QScrollArea()
    outer_scroll.setWidgetResizable(True)
    outer_scroll.setStyleSheet(f"background-color: {BG}; border: none;")

    body = QWidget()
    body.setStyleSheet(f"background-color: {BG};")
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(20, 14, 20, 14)
    body_layout.setSpacing(10)
    outer_scroll.setWidget(body)
    root_layout.addWidget(outer_scroll, 1)

    # ── Branch selection ─────────────────────────────────────────────────
    branch_row = QHBoxLayout()
    branch_lbl = QLabel("Update Branch Context:")
    branch_lbl.setStyleSheet(f"color: {TEXT}; background: transparent; border: none;")
    branch_lbl.setFont(qt_font(9, bold=True))
    branch_row.addWidget(branch_lbl)

    branch_combo = QComboBox()
    branch_combo.addItems(["main", "beta"])
    branch_combo.setCurrentText(UPDATE_BRANCH)
    branch_combo.setFont(qt_font(9))
    branch_combo.setCursor(Qt.CursorShape.PointingHandCursor)
    branch_row.addWidget(branch_combo)
    branch_row.addStretch(1)
    body_layout.addLayout(branch_row)

    def on_branch_change(new_branch: str):
        global UPDATE_BRANCH, BETA_POPUP_SHOWN
        if new_branch == UPDATE_BRANCH:
            return
        if new_branch == "beta":
            BETA_POPUP_SHOWN = True
            QTimer.singleShot(800, _show_beta_popup)
        else:
            BETA_POPUP_SHOWN = False
        UPDATE_BRANCH = new_branch
        save_managed_scripts(MANAGED_SCRIPTS)  # Commit update_branch string context to storage configurations
        force_update_all_scripts()  # Instantly fire asynchronous live updates swapping code logic branches

    branch_combo.currentTextChanged.connect(on_branch_change)

    # ── Python interpreter ───────────────────────────────────────────────
    python_row = QHBoxLayout()
    python_lbl = QLabel("Python Interpreter:")
    python_lbl.setStyleSheet(f"color: {TEXT}; background: transparent; border: none;")
    python_lbl.setFont(qt_font(9, bold=True))
    python_row.addWidget(python_lbl)

    python_entry = QLineEdit(PYTHON_INTERPRETER if PYTHON_INTERPRETER else f"{sys.executable} (default)")
    python_entry.setReadOnly(True)
    python_entry.setFont(qt_font(8))
    python_entry.setStyleSheet(line_edit_qss())
    python_row.addWidget(python_entry, 1)

    def browse_python():
        global PYTHON_INTERPRETER
        name_filter = "Python executable (*.exe)" if sys.platform == "win32" else "All files (*)"
        chosen, _ = QFileDialog.getOpenFileName(settings_win, "Select Python Interpreter", "", name_filter)
        if not chosen:
            return
        PYTHON_INTERPRETER = chosen
        python_entry.setText(PYTHON_INTERPRETER)
        save_managed_scripts(MANAGED_SCRIPTS)
        print(f"[Config] Python interpreter for launched scripts set to: {PYTHON_INTERPRETER}")

    def reset_python():
        global PYTHON_INTERPRETER
        PYTHON_INTERPRETER = ""
        python_entry.setText(f"{sys.executable} (default)")
        save_managed_scripts(MANAGED_SCRIPTS)
        print("[Config] Python interpreter reset to default (ToolBox's own interpreter).")

    browse_python_btn = QPushButton("Browse...")
    browse_python_btn.setStyleSheet(subtle_button_qss())
    browse_python_btn.setFont(qt_font(8, bold=True))
    browse_python_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    browse_python_btn.clicked.connect(browse_python)
    python_row.addWidget(browse_python_btn)

    reset_python_btn = QPushButton("Reset")
    reset_python_btn.setStyleSheet(subtle_button_qss())
    reset_python_btn.setFont(qt_font(8, bold=True))
    reset_python_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    reset_python_btn.clicked.connect(reset_python)
    python_row.addWidget(reset_python_btn)

    body_layout.addLayout(python_row)

    # ── Tools Installation Folder ───────────────────────────────────────
    tools_row = QHBoxLayout()
    tools_lbl = QLabel("Tools Folder:")
    tools_lbl.setStyleSheet(f"color: {TEXT}; background: transparent; border: none;")
    tools_lbl.setFont(qt_font(9, bold=True))
    tools_row.addWidget(tools_lbl)

    tools_entry = QLineEdit(TOOLS_ROOT_DIR)
    tools_entry.setReadOnly(True)
    tools_entry.setFont(qt_font(8))
    tools_entry.setStyleSheet(line_edit_qss())
    tools_row.addWidget(tools_entry, 1)

    def change_tools_folder():
        global TOOLS_ROOT_DIR
        chosen = QFileDialog.getExistingDirectory(settings_win, "Select Nova-Tools Installation Folder", TOOLS_ROOT_DIR)
        if not chosen or chosen == TOOLS_ROOT_DIR:
            return
        
        # Confirm moving existing files if there are any
        old_tools_dir = TOOLS_ROOT_DIR
        new_tools_dir = chosen
        
        if os.path.exists(old_tools_dir) and any(os.scandir(old_tools_dir)):
            move_confirm = QMessageBox.question(
                settings_win, "Move Existing Tools?",
                f"Would you like to move your existing Nova-Tools files from:\n{old_tools_dir}\n\nto the new directory:\n{new_tools_dir}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if move_confirm == QMessageBox.StandardButton.Cancel:
                return
            elif move_confirm == QMessageBox.StandardButton.Yes:
                # Move files
                try:
                    for item in os.listdir(old_tools_dir):
                        src = os.path.join(old_tools_dir, item)
                        dst = os.path.join(new_tools_dir, item)
                        if os.path.isdir(src):
                            if os.path.exists(dst):
                                shutil.rmtree(dst, ignore_errors=True)
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy(src, dst)
                    print(f"[Config] Successfully copied tools to new folder: {new_tools_dir}")

                except Exception as ex:
                    print(f"[Config] Error copying tools folder: {ex}")
                    QMessageBox.warning(settings_win, "Move Failed", f"Could not move all tools files:\n{ex}\n\nUsing new directory anyway.")

        # Update the global path variable and subpaths
        update_layout_paths(new_tools_dir)
        tools_entry.setText(TOOLS_ROOT_DIR)
        
        # Ensure directories are set up correctly
        _ensure_layout_dirs()
        
        # Save config
        save_managed_scripts(MANAGED_SCRIPTS)
        print(f"[Config] Tools folder set to: {TOOLS_ROOT_DIR}")
        
        # Refresh UI buttons label in case any tools changed their download state

        main_window.refresh_button_labels()

    change_tools_btn = QPushButton("Change...")
    change_tools_btn.setStyleSheet(subtle_button_qss())
    change_tools_btn.setFont(qt_font(8, bold=True))
    change_tools_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    change_tools_btn.clicked.connect(change_tools_folder)
    tools_row.addWidget(change_tools_btn)

    body_layout.addLayout(tools_row)

    # ── Themes (collapsible, collapsed by default — matches the pattern
    #    used in every other Nova-Tools settings dialogue) ────────────────
    theme_header = QWidget()
    theme_header.setCursor(Qt.CursorShape.PointingHandCursor)
    theme_header_layout = QHBoxLayout(theme_header)
    theme_header_layout.setContentsMargins(0, 8, 0, 0)

    arrow_lbl = QLabel("▶")
    arrow_lbl.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
    arrow_lbl.setFont(qt_font(12, bold=True))
    theme_header_layout.addWidget(arrow_lbl)

    themes_lbl = QLabel("  Themes")
    themes_lbl.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
    themes_lbl.setFont(qt_font(12, bold=True))
    theme_header_layout.addWidget(themes_lbl)

    preview_lbl = QLabel(f"({THEME_LABELS.get(colour_mode, colour_mode)})")
    preview_lbl.setStyleSheet(f"color: {SUBTEXT}; background: transparent; border: none;")
    preview_lbl.setFont(qt_font(9))
    theme_header_layout.addWidget(preview_lbl)
    theme_header_layout.addStretch(1)

    body_layout.addWidget(theme_header)

    restart_lbl = QLabel("Applies immediately")
    restart_lbl.setStyleSheet(f"color: {SUBTEXT}; background: transparent; border: none;")
    restart_lbl.setFont(qt_font(8))
    body_layout.addWidget(restart_lbl)
    restart_lbl.hide()

    theme_body = QWidget()
    theme_body_layout = QVBoxLayout(theme_body)
    theme_body_layout.setContentsMargins(20, 4, 0, 0)
    body_layout.addWidget(theme_body)
    theme_body.hide()

    theme_state = {"selected": colour_mode}
    theme_rows = []

    def _refresh_theme_rows():
        for row_data in theme_rows:
            is_sel = row_data["mode"] == theme_state["selected"]
            row_data["toggle"].set(is_sel)
            row_data["label"].setStyleSheet(
                f"color: {ACCENT2 if is_sel else TEXT}; background: transparent; border: none;"
            )


    def _select_theme(mode):
        theme_state["selected"] = mode
        _refresh_theme_rows()
        preview_lbl.setText(f"({THEME_LABELS.get(mode, mode)})")

        main_window.set_theme(mode)

    for mode, label_text in THEME_LABELS.items():
        row = QWidget()
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 3, 0, 3)

        toggle = CircleToggle(enabled=(mode == colour_mode), color=ACCENT)
        row_layout.addWidget(toggle)

        lbl = QLabel(label_text)
        lbl.setFont(qt_font(9))
        row_layout.addWidget(lbl)

        swatch = QWidget()
        swatch_layout = QHBoxLayout(swatch)
        swatch_layout.setContentsMargins(4, 0, 0, 0)
        swatch_layout.setSpacing(1)
        for colour_key in ("BG", "PANEL", "ACCENT", "ACCENT2"):
            sw = QFrame()
            sw.setFixedSize(14, 14)
            sw.setStyleSheet(f"background-color: {THEMES[mode][colour_key]}; border: 1px solid {BORDER};")
            swatch_layout.addWidget(sw)
        row_layout.addWidget(swatch)
        row_layout.addStretch(1)

        def _mk_click(m):
            def _handler(_evt):
                _select_theme(m)
            return _handler

        row.mousePressEvent = _mk_click(mode)
        toggle.toggled.connect(lambda _checked, m=mode: _select_theme(m))

        theme_rows.append({"mode": mode, "toggle": toggle, "label": lbl})
        theme_body_layout.addWidget(row)

    _refresh_theme_rows()

    _theme_open = {"value": False}

    def _toggle_theme_body(_evt=None):
        _theme_open["value"] = not _theme_open["value"]
        if _theme_open["value"]:
            arrow_lbl.setText("▼")
            restart_lbl.show()
            theme_body.show()
        else:
            arrow_lbl.setText("▶")
            restart_lbl.hide()
            theme_body.hide()

    theme_header.mousePressEvent = _toggle_theme_body

    # ── Managed scripts list ─────────────────────────────────────────────
    scripts_lbl = QLabel("Managed Scripts")
    scripts_lbl.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
    scripts_lbl.setFont(qt_font(10, bold=True))
    body_layout.addWidget(scripts_lbl)

    list_panel = QFrame()
    list_panel.setStyleSheet(f"background-color: {PANEL}; border: 1px solid {BORDER};")
    list_panel.setMinimumHeight(200)
    list_panel_layout = QVBoxLayout(list_panel)
    list_panel_layout.setContentsMargins(0, 4, 0, 4)

    list_scroll = QScrollArea()
    list_scroll.setWidgetResizable(True)
    list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    list_scroll.setStyleSheet(f"background-color: {PANEL}; border: none;")
    list_inner = QWidget()
    list_inner.setStyleSheet(f"background-color: {PANEL};")
    list_inner_layout = QVBoxLayout(list_inner)
    list_inner_layout.setContentsMargins(0, 0, 0, 0)
    list_inner_layout.setSpacing(0)
    list_scroll.setWidget(list_inner)
    list_panel_layout.addWidget(list_scroll)

    body_layout.addWidget(list_panel, 1)

    def refresh_script_list():
        while list_inner_layout.count():
            item = list_inner_layout.takeAt(0)

            w = item.widget()
            if w is not None:
                w.deleteLater()

        for idx, script in enumerate(MANAGED_SCRIPTS):
            script_row = QWidget()
            script_row.setStyleSheet(f"background-color: {BG};")

            row_layout = QHBoxLayout(script_row)
            row_layout.setContentsMargins(10, 6, 10, 6)

            name_lbl = QLabel(script["label"])
            name_lbl.setStyleSheet(f"color: {TEXT}; background: transparent; border: none;")
            name_lbl.setFont(qt_font(9, bold=True))
            row_layout.addWidget(name_lbl)
            row_layout.addStretch(1)

            file_font = qt_font(8)
            file_metrics = QFontMetrics(file_font)
            elided = file_metrics.elidedText(f"({script['filename']})", Qt.TextElideMode.ElideMiddle, 170)
            file_lbl = QLabel(elided)
            file_lbl.setToolTip(script["filename"])
            file_lbl.setFixedWidth(170)
            file_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            file_lbl.setStyleSheet(f"color: {SUBTEXT}; background: transparent; border: none;")
            file_lbl.setFont(file_font)
            row_layout.addWidget(file_lbl)

            if script.get("custom", False):
                remove_btn = QPushButton("✕ Remove")
                remove_btn.setStyleSheet(
                    f"QPushButton {{ background-color: {PANEL}; color: {RED}; border: none; "
                    f"border-radius: 3px; padding: 3px 10px; font-weight: bold; }}"
                    f"QPushButton:hover {{ background-color: {BORDER}; }}"
                )
                remove_btn.setFont(qt_font(8, bold=True))
                remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                remove_btn.clicked.connect(lambda _checked=False, i=idx: remove_script(i))
                row_layout.addWidget(remove_btn)
            else:
                core_lbl = QLabel("🔒 Core Tool")
                core_lbl.setStyleSheet(f"color: {SUBTEXT}; background: transparent; border: none; padding-right: 5px;")
                core_lbl.setFont(qt_font(8, bold=True))
                row_layout.addWidget(core_lbl)

            list_inner_layout.addWidget(script_row)

            row_divider = QFrame()
            row_divider.setFixedHeight(1)
            row_divider.setStyleSheet(f"background-color: {BORDER}; border: none;")
            list_inner_layout.addWidget(row_divider)

        list_inner_layout.addStretch(1)

    def remove_script(idx):
        MANAGED_SCRIPTS.pop(idx)
        save_managed_scripts(MANAGED_SCRIPTS)
        refresh_script_list()

        main_window.refresh_main_buttons()

    def add_script():
        add_win = QDialog(settings_win)
        add_win.setWindowTitle("Add Script")
        add_win.setFixedSize(400, 200)
        add_win.setStyleSheet(f"background-color: {BG};")

        grid = QGridLayout(add_win)
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setVerticalSpacing(10)

        label_caption = QLabel("Script Display Label:")
        label_caption.setStyleSheet(f"color: {TEXT}; background: transparent; border: none;")
        label_caption.setFont(qt_font(9))
        grid.addWidget(label_caption, 0, 0)

        label_entry = QLineEdit()
        label_entry.setFont(qt_font(9))
        label_entry.setStyleSheet(line_edit_qss())
        grid.addWidget(label_entry, 0, 1)

        file_caption = QLabel("Filename / Resource Path:")
        file_caption.setStyleSheet(f"color: {TEXT}; background: transparent; border: none;")
        file_caption.setFont(qt_font(9))
        grid.addWidget(file_caption, 1, 0)

        file_entry = QLineEdit()
        file_entry.setFont(qt_font(9))
        file_entry.setStyleSheet(line_edit_qss())
        grid.addWidget(file_entry, 1, 1)

        def save_new_script():

            lbl = label_entry.text().strip()
            flm = file_entry.text().strip()
            if not lbl or not flm:
                QMessageBox.warning(add_win, "Validation Error", "All entry parameters must be populated.")
                return

            MANAGED_SCRIPTS.append({"filename": flm, "label": lbl, "custom": True})
            save_managed_scripts(MANAGED_SCRIPTS)
            refresh_script_list()

            main_window.refresh_main_buttons()
            add_win.close()

        submit_btn = QPushButton("Save Script")
        submit_btn.setStyleSheet(accent_button_qss())
        submit_btn.setFont(qt_font(9, bold=True))
        submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        submit_btn.clicked.connect(save_new_script)
        grid.addWidget(submit_btn, 2, 1, alignment=Qt.AlignmentFlag.AlignRight)

        grid.setColumnStretch(1, 1)
        add_win.exec()

    # ── Bottom action row ─────────────────────────────────────────────────
    nav_frame = QWidget()
    nav_frame.setStyleSheet(f"background-color: {BG};")
    nav_layout = QHBoxLayout(nav_frame)
    nav_layout.setContentsMargins(20, 8, 20, 14)

    add_btn = QPushButton("+ Add Script")
    add_btn.setStyleSheet(accent_button_qss())
    add_btn.setFont(qt_font(9, bold=True))
    add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    add_btn.setMinimumWidth(120)
    add_btn.clicked.connect(add_script)
    nav_layout.addWidget(add_btn)
    nav_layout.addStretch(1)

    def show_console():

        settings_win.console_dialogue = ConsoleWindow(settings_win)

        settings_win.console_dialogue.setWindowModality(Qt.NonModal)
        settings_win.console_dialogue.show()

    console_btn = QPushButton("Console Log")
    console_btn.setStyleSheet(subtle_button_qss())
    console_btn.setFont(qt_font(9, bold=True))
    console_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    console_btn.setMinimumWidth(110)
    console_btn.clicked.connect(show_console)
    nav_layout.addWidget(console_btn)

    close_btn = QPushButton("Close")
    close_btn.setStyleSheet(subtle_button_qss())
    close_btn.setFont(qt_font(9, bold=True))
    close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    close_btn.setMinimumWidth(90)
    close_btn.clicked.connect(settings_win.close)
    nav_layout.addWidget(close_btn)

    root_layout.addWidget(nav_frame)

    refresh_script_list()
    settings_win.exec()


def _tool_button_label(script: dict) -> str:
    base = script["label"]
    state = get_tool_state(script["filename"])
    if state == TOOL_STATE_MISSING:
        return f"Download {base}"
    elif state == TOOL_STATE_UPDATE:
        return f"Update {base}"
    return f"Run {base}"


class ToolBoxWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.script_buttons: dict[int, QPushButton] = {}

        self._build_root()

        # Bridge connections — everything a background thread might trigger
        # routes through these, all running on this (the GUI) thread.
        bridge.footer_text.connect(self.footer_label.setText)
        bridge.refresh_labels.connect(self.refresh_button_labels)
        bridge.confirm_main_update.connect(_on_confirm_main_update)
        bridge.show_info.connect(lambda title, msg: QMessageBox.information(self, title, msg))
        bridge.show_error.connect(lambda title, msg: QMessageBox.critical(self, title, msg))

        self.refresh_main_buttons()

    # ── Root window ───────────────────────────────────────────────────────

    def _build_root(self):
        self.setWindowTitle("PyToolBox-Launcher")
        self.resize(580, 600)
        self.setMinimumSize(480, 380)

        central = StripeBackground()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet(f"background-color: {PANEL};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 12, 20, 12)

        title_lbl = QLabel(f"{TITLE_PREFIX} PyToolBox-Launcher")
        title_lbl.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
        title_lbl.setFont(qt_font(16, bold=True))
        header_layout.addWidget(title_lbl)
        header_layout.addStretch(1)

        version_lbl = QLabel(f"v{VERSION}")
        version_lbl.setStyleSheet(f"color: {SUBTEXT}; background: transparent; border: none;")
        version_lbl.setFont(qt_font(9))
        header_layout.addWidget(version_lbl)

        root_layout.addWidget(header)

        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {BORDER}; border: none;")
        root_layout.addWidget(divider)

        # ── Main content ──────────────────────────────────────────────────
        main_area = QWidget()
        main_area.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(24, 16, 24, 16)
        main_layout.setSpacing(0)

        tools_label = TextChip("MANAGED SCRIPTS", fg=ACCENT, padding="3px 8px")
        tools_label.setFont(qt_font(9, bold=True))
        main_layout.addWidget(tools_label)
        main_layout.addSpacing(10)

        self._buttons_scroll = QScrollArea()
        self._buttons_scroll.setWidgetResizable(True)
        self._buttons_scroll.setStyleSheet("background: transparent; border: none;")

        self._buttons_inner = QWidget()
        self._buttons_inner.setStyleSheet("background: transparent;")
        self._buttons_layout = QVBoxLayout(self._buttons_inner)
        self._buttons_layout.setContentsMargins(0, 0, 4, 0)
        self._buttons_layout.setSpacing(4)
        self._buttons_layout.addStretch(1)

        self._buttons_scroll.setWidget(self._buttons_inner)
        main_layout.addWidget(self._buttons_scroll, 1)

        root_layout.addWidget(main_area, 1)

        # ── Footer ────────────────────────────────────────────────────────
        footer_bar = QWidget()
        footer_bar.setStyleSheet(f"background-color: {PANEL};")
        footer_outer = QVBoxLayout(footer_bar)
        footer_outer.setContentsMargins(0, 6, 0, 4)
        footer_outer.setSpacing(2)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(8, 0, 8, 0)

        help_btn = square_button("?", open_help, base_size=28)
        footer_row.addWidget(help_btn)
        footer_row.addStretch(1)

        settings_btn = square_button("⚙", open_settings, base_size=28)
        footer_row.addWidget(settings_btn)

        footer_outer.addLayout(footer_row)

        self.footer_label = QLabel("Checking for updates on startup...")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_label.setStyleSheet(f"color: {SUBTEXT}; background: transparent; border: none;")
        self.footer_label.setFont(qt_font(8))
        footer_outer.addWidget(self.footer_label)

        root_layout.addWidget(footer_bar)

        self.setCentralWidget(central)

    # ── Tool buttons ──────────────────────────────────────────────────────

    def refresh_main_buttons(self):
        while self._buttons_layout.count():
            item = self._buttons_layout.takeAt(0)

            w = item.widget()
            if w is not None:
                w.deleteLater()

        self.script_buttons.clear()

        for i, script in enumerate(MANAGED_SCRIPTS):
            btn = QPushButton(_tool_button_label(script))
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; "
                f"border-radius: 3px; padding: 8px 20px; font-weight: bold; text-align: left; }}"
                f"QPushButton:hover {{ background-color: {ACCENT}; color: {TEXT2}; }}"
            )
            btn.setFont(qt_font(10, bold=True))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, f=script["filename"]: launch_script(f))
            self._buttons_layout.insertWidget(i, btn)
            self.script_buttons[i] = btn

        self._buttons_layout.addStretch(1)

        btn_count = len(MANAGED_SCRIPTS)
        self.resize(580, min(440 + btn_count * 52, 820))

    def refresh_button_labels(self):
        """Lightweight label-only refresh (no widget rebuild/resize) — used
        whenever a tool's state changes, e.g. after the background version
        scan checks one more tool, so there's no flicker during boot."""
        for i, script in enumerate(MANAGED_SCRIPTS):
            btn = self.script_buttons.get(i)
            if btn is not None:
                btn.setText(_tool_button_label(script))

    # ── Theme ─────────────────────────────────────────────────────────────

    def set_theme(self, mode: str):
        set_theme(mode)
        save_managed_scripts(MANAGED_SCRIPTS)
        app_instance = QApplication.instance()
        if app_instance is not None:

            app_instance.setStyleSheet(qss())
        self._rebuild_ui()

    def _rebuild_ui(self):
        old_central = self.takeCentralWidget()
        if old_central is not None:
            old_central.deleteLater()

        self._build_root()
        self.refresh_main_buttons()

        self.show()
        app_instance = QApplication.instance()
        if app_instance is not None:
            app_instance.processEvents()

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def closeEvent(self, event):
        save_managed_scripts(MANAGED_SCRIPTS)
        super().closeEvent(event)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════#

qt_app = QApplication(sys.argv)

# Initialise process model ID for full-size taskbar icons on Windows
if sys.platform == 'win32':
    try:

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f'CaptainBoots.PyToolBox-Launcher.{VERSION}')
        print(f"[Process] Successfully registered AppUserModelID: CaptainBoots.PyToolBox-Launcher.{VERSION}")
    except Exception as ex:
        print(f"[Process] Error setting AppUserModelID: {ex}")

# Set application-wide icon
icon_path = os.path.join(SCRIPT_DIR, "../Images", "Boot's-ToolBox-256.ico")
if os.path.exists(icon_path):
    qt_app.setWindowIcon(QIcon(icon_path))
    print(f"[Process] Loaded application icon from: {icon_path}")

# Clean up leftover update backup files if running as a frozen executable
if getattr(sys, 'frozen', False):
    try:
        import glob
        for backup_path in glob.glob(sys.executable + ".bak*"):
            try:
                os.remove(backup_path)
                print(f"[Process] Cleaned up update backup: {backup_path}")
            except Exception:
                pass
    except Exception as ex:
        print(f"[Process] Could not clean up update backup: {ex}")

# Bootstrap paths, configurations, and ask if first run
MANAGED_SCRIPTS = load_managed_scripts()

_ensure_layout_dirs()
_migrate_legacy_layout()

qt_app.setStyleSheet(qss())

main_window = ToolBoxWindow()
# Also set window icon explicitly on main window
if os.path.exists(icon_path):
    main_window.setWindowIcon(QIcon(icon_path))
main_window.show()

# Automatically kick off startup network validation threads asynchronously
threading.Thread(target=lambda: check_for_main_updates(silent=True), daemon=True).start()

# Conditional Beta Modal Promotion Injection
if UPDATE_BRANCH == "beta" and not BETA_POPUP_SHOWN:
    BETA_POPUP_SHOWN = True
    save_managed_scripts(MANAGED_SCRIPTS)
    QTimer.singleShot(800, _show_beta_popup)

sys.exit(qt_app.exec())