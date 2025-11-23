!define APPNAME "TranscribeFlow"
!define APPVER "1.0.0"
!define EXE "..\\..\\dist\\TranscribeFlow.exe"

OutFile "..\\..\\dist\\TranscribeFlow-Setup.exe"
InstallDir "$PROGRAMFILES\\${APPNAME}"
RequestExecutionLevel admin

Page directory
Page instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File "${EXE}"
  CreateShortCut "$DESKTOP\\${APPNAME}.lnk" "$INSTDIR\\TranscribeFlow.exe"
SectionEnd
