# PyToolBox & CToolBox

<img src="Images/Boot%27s-ToolBox.svg" alt="Boot's ToolBox" width="200" />

Hello people! I hope you like the Project. I spent quite a while making this project to make managing and launching companion tools as easy and seamless as possible. Since this is a solo project, some bugs are expected so please report any issues or feedback in my Discord server!

### [**The Discord Server**](https://discord.gg/YDXpQPF6g9)


---


##  Installation & Usage

### Windows
1. Go to the **Releases** tab on GitHub.
2. Download the latest **`CToolBox-Launcher-Portable.zip`** (for high-performance C++ launcher) or **`PyToolBox-Launcher.exe`** (for Python-compiled launcher).
3. Run the executable and enjoy!

*( I have made this unbelievably simple, I believe you can do it! )*

### Linux
To run the ToolBox directly from source on Linux:
```bash
# Clone the repository
git clone https://github.com/CaptainBoots/Project-Proto.git
cd Project-Proto/PyToolBox-Launcher

# Run with Python
python3 PyToolBox-Launcher.py
```

*( If you would like to run the c++ version (CToolBox) have fun its untested but it might work )*

---

##  Troubleshooting

### Antivirus False Positives
PyInstaller executables are sometimes flagged as false positives by Windows Defender or other security scanners. If the executable is blocked or cannot be deleted/compiled, add the installation or workspace folder to your antivirus exclusion list.

### Locked Executables
If compiling with PyInstaller fails with a `PermissionError` (Access Denied), ensure that any background instances of `ToolBox.exe` are completely closed so they release their locks.

---

##  Tools & Subprojects
Project Proto is a project for updating and running a set of tools made by me and a few others
you can even join the project in the [**discord**](https://discord.gg/YDXpQPF6g9) and help make new tools!

### Tool IDs
Tools IDs are used by the Project to make managing the tools easier and fix issues from renaming tools if you want to make a tool you will get given a ID range if you ask in the discord server

The ID ranges:
- 000000 - Blank / Non Applicable / No ID
- 000001-000100 - Launcher ( PyToolBox and CToolBox )
- 000101-001100 - Nova Tools
- 001101-999800 - Unreserved
- 999801-999900 - Special Helpers
- 999901-999999 - Top End Buffer
---

i hope you all like the project and if you wana make a tool join the discord above.

*Made with <3 by:*
1. Boots @CaptainBoots
