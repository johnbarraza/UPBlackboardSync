# NSIS BlackboardSync Installer
# Copyright {{ copyright }}

# Include Modern UI
!include "MUI2.nsh"

# Installer File and Name
Name "{{ title }}"
Outfile "..\dist\BlackboardSync-${VERSION}-Setup.exe"
Unicode True

# Installation Dir
InstallDir "$LOCALAPPDATA\Programs\BlackboardSync"
InstallDirRegKey HKCU "Software\{{ title }}" "InstallDir"
# Request Privileges
RequestExecutionLevel user

!define SYNC_FILE "..\dist\BlackboardSync\*"
!define SYNC_EXE "$INSTDIR\BlackboardSync.exe"
!define SYNC_ICON "$INSTDIR\icon.ico"
!define APP_DATA_DIR "$APPDATA\BlackboardSync"

!define SYNC_LNK "$SMPROGRAMS\{{ title }}.lnk"

# MUI Settings
!define MUI_LICENSEPAGE_TEXT_BOTTOM "You are now aware of your rights. Click next to continue."
!define MUI_LICENSEPAGE_BUTTON "Next"
!define MUI_FINISHPAGE_LINK "{{ homepage }}"
!define MUI_FINISHPAGE_RUN "${SYNC_EXE}"
!define MUI_ICON ".\icon.ico"
!define MUI_UNICON ".\icon.ico"

# Installer Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE ".\LICENSE"
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

# Uninstaller Pages
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

# Languages
!insertmacro MUI_LANGUAGE "English"

# Uninstall Settings
!define BASE_REGKEY "Software\Microsoft\Windows\CurrentVersion"
!define AUTORUN_REGKEY '"${BASE_REGKEY}\Run"'
!define UNINSTALL_REGKEY '"${BASE_REGKEY}\Uninstall\{{ title }}"'


# default section start; every NSIS script has at least one section.
Section "Installation" SecInstall
    SetOutPath "$INSTDIR"
    File /r ${SYNC_FILE}
    File "icon.ico"

    ; Install Directory
    WriteRegStr HKCU 'Software\{{ title }}' "InstallDir" $INSTDIR

    ; Run on Startup
    WriteRegStr HKCU ${AUTORUN_REGKEY} "{{ title }}" '"${SYNC_EXE}"'

    ; Shortcut
    CreateShortCut "${SYNC_LNK}" "${SYNC_EXE}"

    ; Uninstall Menu
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "DisplayName" "{{ title }}"
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "InstallLocation" $INSTDIR
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "DisplayIcon" "${SYNC_ICON}"
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "Publisher" "{{ publisher }}"
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "HelpLink" "{{ repository }}"
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "DisplayVersion" "${VERSION}"

    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd


Section "Uninstall"
  ; Remove app-owned config, Drive token, and diagnostic logs.
  RMDir /r "${APP_DATA_DIR}"

  ; Remove Application
  RMDir /r $INSTDIR

  ; Run on Startup
  DeleteRegValue HKCU ${AUTORUN_REGKEY} '{{ title }}'

  ; Install Directory
  DeleteRegKey HKCU 'Software\{{ title }}'

  ; Uninstall Menu Entry
  DeleteRegKey HKCU ${UNINSTALL_REGKEY}

  ; Delete Shortcut
  Delete "${SYNC_LNK}"
SectionEnd
