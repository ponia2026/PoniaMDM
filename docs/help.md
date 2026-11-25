# PoniaMDM help

PoniaMDM writes Ponia metadata (`metadata.ponia.txt`) next to the metadata you already have. Your original files,
images, videos and ROMs are never modified.

## The three tabs

| Tab | Reads | Writes |
|---|---|---|
| Pegasus | `metadata.pegasus.txt` in each platform folder | `metadata.ponia.txt` in the same folder |
| EmuELEC | `gamelist.xml` in each platform folder | `metadata.ponia.txt` in the same folder; images are referenced where they are |
| Custom | any folder of ROMs you organised yourself | `metadata.ponia.txt` in each folder that holds games |

## Typical use
1. Pick a tab and choose the data folder (Browse, or type the path).
2. Set the options for that tab (see below).
3. Press **Start**. The Status card shows what was written and anything that needs a look.
4. Press **Convert again** after you change something, or **Delete data** to remove what this tool wrote.

Re-converting overwrites only files this tool wrote. A `metadata.ponia.txt` you wrote yourself is never touched or deleted.

## Options
- **Output as Traditional Chinese** (Chinese interface only): converts names and descriptions from Simplified to Traditional
  Chinese. File names and paths are never changed.
- **Arcade romsets that cannot be identified go to** (Custom tab only): a zip that holds only chip files cannot be
  told apart as MAME or FBNeo; this decides which collection it goes to.

## Status
| Status | Meaning |
|---|---|
| Ready | Nothing has been written yet, or the tab is idle |
| Converted | Ponia metadata written by this tool exists in the folder |
| Data offline | The folder cannot be reached (for example a USB drive that is unplugged). Nothing is modified; the tab recovers when the drive is back |

## Custom tab: files that need checking
Files whose platform could not be decided with confidence are listed in the Status card. Pick the platform (and tick
*Modified version* for hacks), then press **Convert again**. Your choices are remembered for that folder.
Files whose platform is unknown are not written.

## Files and menus
- **File > Save file / Open file** stores the latest folder and options of each tab in one file and reads them back.
- The program also remembers the last folders by itself.
- Settings live in the `_internal` folder next to `PoniaMDM.exe`; delete `PoniaMDM.settings.json` there to reset.
- **Help > Home / Copyright** open the project pages on GitHub.

## Troubleshooting
- *Failed to load Python DLL ... another program is using this file*: security software is scanning the freshly
  unpacked files. Wait a few seconds and start the program again, or add the program folder to the trusted list.
