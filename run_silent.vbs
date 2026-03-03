Dim WinScriptHost
Set WinScriptHost = CreateObject("WScript.Shell")

Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")
basePath = fso.GetParentFolderName(WScript.ScriptFullName)
localPyw = WinScriptHost.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Autoupload\runtime\python-embed\pythonw.exe"
legacyPyw = basePath & "\runtime\python-embed\pythonw.exe"
fallbackBat = basePath & "\Autoupload_실행.bat"

WinScriptHost.CurrentDirectory = basePath

checkSystem = WinScriptHost.Run("cmd /c python -c ""import tkinter,playwright,pystray,PIL""", 0, True)

If checkSystem = 0 Then
    WinScriptHost.Run "pythonw -m flow.flow_auto_v2", 0
ElseIf fso.FileExists(localPyw) Then
    WinScriptHost.Run """" & localPyw & """ -m flow.flow_auto_v2", 0
ElseIf fso.FileExists(legacyPyw) Then
    WinScriptHost.Run """" & legacyPyw & """ -m flow.flow_auto_v2", 0
ElseIf fso.FileExists(fallbackBat) Then
    WinScriptHost.Run """" & fallbackBat & """", 1
Else
    MsgBox "실행 파일을 찾지 못했습니다." & vbCrLf & _
           "Autoupload_실행.bat을 먼저 실행해주세요.", vbExclamation, "Autoupload"
End If

Set fso = Nothing
Set WinScriptHost = Nothing
