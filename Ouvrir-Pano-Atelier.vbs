Option Explicit
Dim shell, fso, root, blender, scene, args
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
scene = root & "\output\cockpit-lowpoly-v2\cockpit-lowpoly-v2.blend"
If Not fso.FileExists(scene) Then scene = root & "\output\cockpit-lowpoly-v1\cockpit-lowpoly-v1.blend"
If Not fso.FileExists(scene) Then scene = root & "\output\cockpit\cockpit.blend"
If Not fso.FileExists(scene) Then scene = root & "\test-output\demo.blend"
If Not fso.FileExists(blender) Then
  MsgBox "Blender 5.2 est introuvable. Installer le ZIP de l'add-on dans votre version de Blender.", 48, "Pano Atelier"
  WScript.Quit 1
End If
args = """" & blender & """ """ & scene & """ --python """ & root & "\launch.py"""
shell.Run args, 1, False
