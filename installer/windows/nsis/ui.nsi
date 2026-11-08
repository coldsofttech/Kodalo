; NSIS installer for the desktop app (kodalo-ui). Windows only; see
; common.nsh for the options.
;
;   makensis /DAPP_NAME="Kodalo" /DAPP_VERSION=0.1.0 /DSOURCE_DIR=..\..\build\installer\kodalo-ui \
;            /DOUT_FILE=..\..\dist\kodalo-0.1.0.setup.exe installer\nsis\ui.nsi
; scripts/build_installer.py does this from the project's own metadata.

; Stable id of this product: keep it for the life of the project, so a newer setup replaces an
; older install. Generate a new one for your project (python -c "import uuid; print(uuid.uuid4())").
!define GUID "{522F0731-6C8B-4F27-922D-E7F7701FFA99}"
!define INSTALL_SUBDIR "UI"
!define MAIN_EXE "kodalo-ui.exe"
!define HAS_DESKTOP

!include "common.nsh"
