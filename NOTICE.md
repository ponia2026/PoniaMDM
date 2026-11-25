# NOTICE

## PoniaMDM (Ponia Metadata Manager)

Copyright (C) 2026 Equuleus Works.

Licensed under the GNU General Public License, version 3 or (at your option) any later version
(`SPDX-License-Identifier: GPL-3.0-or-later`). The full license text is in `LICENSE.md`.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

The name "Ponia" and the Ponia logo (`frontend/public/ponia_mark.svg`, `packaging/ponia_mark.png`,
`packaging/ponia.ico`) are the property of Equuleus Works. All rights reserved. The GPL grants no
trademark rights.

## Relationship to other projects

PoniaMDM is an independent tool. It reads the text metadata format used by Pegasus Frontend
(https://github.com/mmatyas/pegasus-frontend, Copyright (C) 2017-2020 Mátyás Mustoha) and by
EmulationStation / EmuELEC (`gamelist.xml`), and writes the Ponia format. It contains no code from those
projects and is not affiliated with, or endorsed by, their authors. All product, platform and game names
mentioned or produced by the tool belong to their respective owners.

## Third-party components bundled in the Windows executable

| Component | License |
|---|---|
| Python (CPython) | PSF License |
| Vue.js | MIT |
| FastAPI, Starlette, Pydantic | MIT |
| Uvicorn | BSD-3-Clause |
| pywebview | BSD-3-Clause |
| opencc-python-reimplemented and the OpenCC dictionaries | Apache-2.0 |
| py7zr (and its compression back-ends) | LGPL-2.1-or-later (and component licenses) |
| PyInstaller bootloader | GPL-2.0-or-later with the bootloader exception |

Each component keeps its own license; their license texts are available from the upstream projects.
