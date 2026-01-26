Dim WinScriptHost
Set WinScriptHost = CreateObject("WScript.Shell")
WinScriptHost.Run "pythonw -m flow.flow_auto_v2", 0
Set WinScriptHost = Nothing
