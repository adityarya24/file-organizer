Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

On Error Resume Next
WshShell.Run "pythonw """ & scriptDir & "\organizer.py"" --watch", 0, False
If Err.Number <> 0 Then
    Err.Clear
    WshShell.Run "python """ & scriptDir & "\organizer.py"" --watch", 0, False
End If
On Error GoTo 0
