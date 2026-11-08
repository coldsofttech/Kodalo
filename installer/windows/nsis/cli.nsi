; NSIS installer for the command line (kodalo). Windows; see common.nsh for the options.
;
;   makensis /DAPP_NAME="Example CLI" /DAPP_VERSION=0.1.0 /DSOURCE_DIR=..\..\build\installer\kodalo \
;            /DOUT_FILE=..\..\dist\kodalo-cli-0.1.0.setup.exe installer\nsis\cli.nsi
; scripts/build_installer.py does this from the project's own metadata.

; Stable id of this product: keep it for the life of the project, so a newer setup replaces an
; older install. Generate a new one for your project (python -c "import uuid; print(uuid.uuid4())").
!define GUID "{1DA45AD5-1231-419B-B274-3FB82A30440E}"
!define INSTALL_SUBDIR "CLI"
!define MAIN_EXE "kodalo.exe"
!define HAS_PATH

!include "common.nsh"
