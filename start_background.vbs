Set WshShell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
pythonExe = "C:\Python314\pythonw.exe"
If Not CreateObject("Scripting.FileSystemObject").FileExists(pythonExe) Then
    pythonExe = "pythonw.exe"
End If
WshShell.Run """" & pythonExe & """ """ & scriptDir & "\organizer.py"" --watch", 0, False
