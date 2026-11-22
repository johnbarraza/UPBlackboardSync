# NSIS BlackboardSync Installer
# Copyright {{ copyright }}

# Include Modern UI
!include "MUI2.nsh"

# Installer File and Name
Name "{{ title }}"
; Fixed name so README can link releases/latest/download/BlackboardSync-Setup.exe
Outfile "..\dist\BlackboardSync-Setup.exe"
Unicode True

# Installation Dir
InstallDir "$LOCALAPPDATA\Programs\BlackboardSync"
InstallDirRegKey HKCU "Software\{{ title }}" "InstallDir"
# Request Privileges
RequestExecutionLevel user

!define SYNC_FILE "..\dist\BlackboardSync.exe"
!define SYNC_EXE "$INSTDIR\BlackboardSync.exe"
!define SYNC_ICON "$INSTDIR\icon.ico"
!define APP_DATA_DIR "$APPDATA\BlackboardSync"

!define SYNC_LNK "$SMPROGRAMS\{{ title }}.lnk"
!define UNINSTALL_LNK "$SMPROGRAMS\Uninstall {{ title }}.lnk"

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
!define MUI_COMPONENTSPAGE_TEXT_TOP "Choose what to remove. Downloaded course files are never deleted."
!insertmacro MUI_UNPAGE_COMPONENTS
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
    ; Update in place: close a running copy so its exe can be replaced.
    ; Settings (%APPDATA%\BlackboardSync), downloads and saved login are kept.
    nsExec::Exec 'taskkill /F /IM BlackboardSync.exe'
    Pop $0
    Sleep 1500

    SetOutPath "$INSTDIR"
    File /r ${SYNC_FILE}
    File "icon.ico"

    ; Install Directory
    WriteRegStr HKCU 'Software\{{ title }}' "InstallDir" $INSTDIR

    ; Run on Startup
    WriteRegStr HKCU ${AUTORUN_REGKEY} "{{ title }}" '"${SYNC_EXE}"'

    ; Shortcut
    CreateShortCut "${SYNC_LNK}" "${SYNC_EXE}"
    CreateShortCut "${UNINSTALL_LNK}" "$INSTDIR\Uninstall.exe"

    ; Uninstall Menu
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "DisplayName" "{{ title }}"
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "InstallLocation" $INSTDIR
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "DisplayIcon" "${SYNC_ICON}"
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "Publisher" "{{ publisher }}"
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "HelpLink" "{{ repository }}"
    WriteRegStr HKCU ${UNINSTALL_REGKEY} "DisplayVersion" "${VERSION}"

    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; In-app update runs us with /S (no finish page): relaunch the app.
    IfSilent 0 +2
        Exec '"${SYNC_EXE}"'
SectionEnd


Section "un.Blackboard Sync (app)" SecUnApp
  SectionIn RO

  ; A running copy would keep its files locked.
  nsExec::Exec 'taskkill /F /IM BlackboardSync.exe'
  Pop $0
  Sleep 1500

  ; Remove Application
  RMDir /r $INSTDIR

  ; Run on Startup
  DeleteRegValue HKCU ${AUTORUN_REGKEY} '{{ title }}'

  ; Install Directory
  DeleteRegKey HKCU 'Software\{{ title }}'

  ; Uninstall Menu Entry
  DeleteRegKey HKCU ${UNINSTALL_REGKEY}

  ; Delete Shortcuts
  Delete "${SYNC_LNK}"
  Delete "${UNINSTALL_LNK}"
SectionEnd


; Checked by default (also what /S does). Unchecked = keep settings and
; login for a later reinstall. Downloads are never touched: the folder may
; be synced elsewhere (Syncthing, Drive) and a delete would propagate.
Section "un.Settings, saved login and app data" SecUnData
  ; Config, Drive token and diagnostic logs.
  RMDir /r "${APP_DATA_DIR}"

  ; Login browser profile (session cookies) and its cache live under the
  ; Qt app name, outside APP_DATA_DIR.
  RMDir /r "$APPDATA\{{ title }}"
  RMDir /r "$LOCALAPPDATA\{{ title }}"

  ; Saved login in Windows Credential Manager (keyring service name;
  ; keyring may store it as "<user>@<service>").
  nsExec::Exec 'cmdkey /delete:BlackboardSync'
  Pop $0
  nsExec::Exec 'cmdkey /delete:login@BlackboardSync'
  Pop $0
SectionEnd
