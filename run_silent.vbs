Dim WinScriptHost
Set WinScriptHost = CreateObject("WScript.Shell")

Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")
basePath = fso.GetParentFolderName(WScript.ScriptFullName)
embeddedPyw = """" & basePath & "\runtime\python-embed\pythonw.exe"" -m flow.flow_auto_v2"

If fso.FileExists(basePath & "\runtime\python-embed\pythonw.exe") Then
    WinScriptHost.Run embeddedPyw, 0
Else
    WinScriptHost.Run "pythonw -m flow.flow_auto_v2", 0
End If

Set WinScriptHost = Nothing
