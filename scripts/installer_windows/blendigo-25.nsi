;--------------------------------

; Use Modern UI
!include "MUI2.nsh"

;--------------------------------

; Setup Blendigo parameters
!define BLENDIGO_VERSION $%BLENDIGO_VERSION%
!define BLENDER_VERSION $%BLENDER_VERSION%

; The name of the installer
Name "Blendigo-2.6 ${BLENDIGO_VERSION} for Blender ${BLENDER_VERSION}"

; The file to write
OutFile "blendigo-2.6-${BLENDIGO_VERSION}-installer.exe"

;--------------------------------
; New style GUI setup

; Colors and images
!define MUI_ICON "indigo.ico"
!define MUI_UNICON "indigo.ico"

!define MUI_PAGE_HEADER_TEXT "Blendigo Installation"
!define MUI_PAGE_HEADER_SUBTEXT "Version ${BLENDIGO_VERSION} for Blender ${BLENDER_VERSION}"

LangString MUI_TEXT_DIRECTORY_TITLE ${LANG_ENGLISH} "Blendigo Installation"
LangString MUI_TEXT_DIRECTORY_SUBTITLE ${LANG_ENGLISH} "Version ${BLENDIGO_VERSION} for Blender ${BLENDER_VERSION}"

LangString MUI_TEXT_INSTALLING_TITLE ${LANG_ENGLISH} "Blendigo Installation"
LangString MUI_TEXT_INSTALLING_SUBTITLE ${LANG_ENGLISH} "Version ${BLENDIGO_VERSION} for Blender ${BLENDER_VERSION}"

!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "indigo_logo_150_57.bmp"
!define MUI_HEADERIMAGE_BITMAP_NOSTRETCH
!define MUI_HEADERIMAGE_UNBITMAP "indigo_logo_150_57.bmp"
!define MUI_HEADERIMAGE_UNBITMAP_NOSTRETCH

!define MUI_BGCOLOR "333333"
!define MUI_HEADER_TRANSPARENT_TEXT
!define MUI_LICENSEPAGE_BGCOLOR  "FFFFFF 333333"
!define MUI_INSTFILESPAGE_COLORS "FFFFFF 333333"

; These functions are called prior to the page macros below
Function "changeWelcomeTextColor"
	FindWindow $1 "#32770" "" $HWNDPARENT
	GetDlgItem $2 $1 1201
	SetCtlColors $2 0xFFFFFF 0x333333
	GetDlgItem $2 $1 1202
	SetCtlColors $2 0xFFFFFF 0x333333
FunctionEnd

Function "changeTitleColor"
	GetDlgItem $r3 $HWNDPARENT 1037
	SetCtlColors $r3 0xFFFFFF 0x333333
	GetDlgItem $r3 $HWNDPARENT 1038
	SetCtlColors $r3 0xFFFFFF 0x333333
FunctionEnd

; Installer behaviour
!define MUI_ABORTWARNING
!define MUI_UNABORTWARNING

; Welcome page
!define MUI_WELCOMEFINISHPAGE_BITMAP "indigo_logo_163_314.bmp"
!define MUI_WELCOMEFINISHPAGE_BITMAP_NOSTRETCH
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "indigo_logo_163_314.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP_NOSTRETCH
!define MUI_WELCOMEPAGE_TITLE "Blendigo ${BLENDIGO_VERSION} for Blender ${BLENDER_VERSION}"
!define MUI_WELCOMEPAGE_TEXT "This installer will first attempt to auto-locate your Blender installation folder. If the folder is not found, you will be asked to locate Blender yourself."

; License page
!define MUI_LICENSEPAGE_RADIOBUTTONS

; Directory page
!define MUI_DIRECTORYPAGE_TEXT_TOP "Choose Blender ${BLENDER_VERSION} Installation Folder"

; Installation page
!define MUI_INSTFILESPAGE_FINISHHEADER_TEXT "Blendigo ${BLENDIGO_VERSION} for Blender ${BLENDER_VERSION} Installation Complete"
!define MUI_INSTFILESPAGE_ABORTHEADER_TEXT "Blendigo ${BLENDIGO_VERSION} for Blender ${BLENDER_VERSION} Installation Aborted"

;--------------------------------

; Request application privileges for Windows Vista
; We will request admin level privileges, so that we can write to the Program Files dir if needed.
RequestExecutionLevel admin

;--------------------------------

Function DetectInstallPath
	TryProgFiles32:
	IfFileExists "$PROGRAMFILES32\Blender Foundation\Blender\${BLENDER_VERSION}" 0 TryProgFiles64
		CreateDirectory "$PROGRAMFILES32\Blender Foundation\Blender\${BLENDER_VERSION}\scripts\addons"
		StrCpy $INSTDIR "$PROGRAMFILES32\Blender Foundation\Blender"
		Return
		
	TryProgFiles64:
	IfFileExists "$PROGRAMFILES64\Blender Foundation\Blender\${BLENDER_VERSION}" 0 TryRegistry
		CreateDirectory "$PROGRAMFILES64\Blender Foundation\Blender\${BLENDER_VERSION}\scripts\addons"
		StrCpy $INSTDIR "$PROGRAMFILES64\Blender Foundation\Blender"
		Return
		
	TryRegistry:
	ReadRegStr $0 HKCR blendfile\shell\open\command ""
	StrCmp $0 "" TryAppData
		; "D:\PATH\blender.exe" "%1" => D:\PATH
		StrLen $1 $0
		IntOp $3 $0 - 18
		StrCpy $INSTDIR $0 $3 1
		Return
	
	TryAppData:
	IfFileExists "$APPDATA\Blender Foundation\Blender\${BLENDER_VERSION}" 0 AutoFindFailed
		CreateDirectory "$APPDATA\Blender Foundation\Blender\${BLENDER_VERSION}\scripts\addons"
		StrCpy $INSTDIR "$APPDATA\Blender Foundation\Blender"
		Return

	AutoFindFailed:
	MessageBox MB_OK "Could not find the Blender ${BLENDER_VERSION} installation. Choose your Blender install folder on the next page."
FunctionEnd

;--------------------------------

; Old-style Pages
;Page directory
;Page instfiles
;UninstPage uninstConfirm
;UninstPage instfiles

;--------------------------------

; Modern style pages
!define MUI_PAGE_CUSTOMFUNCTION_SHOW "changeWelcomeTextColor"
!insertmacro MUI_PAGE_WELCOME

; Language setting has to be after welcome page otherwise the welcome image doesn't show
!insertmacro MUI_LANGUAGE "English"
!define MUI_PAGE_CUSTOMFUNCTION_PRE "changeTitleColor"
!insertmacro MUI_PAGE_LICENSE "License.rtf"
Page custom DetectInstallPath
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------

; The stuff to install
Section "" ;No components page, name is not important
  ; Set output path to the installation directory.
  SetOutPath $INSTDIR\${BLENDER_VERSION}\scripts\addons\indigo
  
  ; Put files there recursively
  File /r ..\..\sources\indigo\*.py
  
  ; Write the uninstall keys for Windows
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Blendigo-2.6" "DisplayName" "Blendigo-2.6"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Blendigo-2.6" "BlenderVersion" "${BLENDER_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Blendigo-2.6" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Blendigo-2.6" "UninstallString" '"$INSTDIR\${BLENDER_VERSION}\scripts\addons\Blendigo_uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Blendigo-2.6" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Blendigo-2.6" "NoRepair" 1
  WriteUninstaller "$INSTDIR\${BLENDER_VERSION}\scripts\addons\Blendigo_uninstall.exe"
  
SectionEnd ; end the section

Section "Uninstall"
  
  Var /GLOBAL BLENDER_VERSION
  ReadRegStr $BLENDER_VERSION HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Blendigo-2.6" "BlenderVersion"
  
  Var /GLOBAL INSTALL_DIR
  ReadRegStr $INSTALL_DIR HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Blendigo-2.6" "InstallDir"
  
  ; Remove files and uninstaller
  Delete $INSTALL_DIR\$BLENDER_VERSION\scripts\addons\Blendigo_uninstall.exe
  rmdir /r $INSTALL_DIR\$BLENDER_VERSION\scripts\addons\indigo
  rmdir $INSTALL_DIR\$BLENDER_VERSION\scripts\addons\indigo

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Blendigo-2.6"

SectionEnd
