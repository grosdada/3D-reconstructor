Option Explicit
Dim shell, fso, root, blend
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
blend = root & "\output\cockpit-photo-modulaire-v3\cockpit-usure-lumiere.blend"
shell.Run Chr(34) & "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" & Chr(34) & " " & Chr(34) & blend & Chr(34) & " --python " & Chr(34) & root & "\launch_photo_cockpit.py" & Chr(34), 1, False
