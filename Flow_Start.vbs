Set WshShell = CreateObject("WScript.Shell")

basePath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
embeddedPyw = """" & basePath & "\runtime\python-embed\pythonw.exe"" -m flow.flow_auto_v2"

If CreateObject("Scripting.FileSystemObject").FileExists(basePath & "\runtime\python-embed\pythonw.exe") Then
    WshShell.Run embeddedPyw, 0
Else
    WshShell.Run "pythonw -m flow.flow_auto_v2", 0
End If

Set WshShell = Nothing
