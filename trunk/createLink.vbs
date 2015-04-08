set WSHShell = CreateObject("WScript.Shell")
set objFso = CreateObject("Scripting.FileSystemObject")

sShortcut = WSHShell.ExpandEnvironmentStrings(WScript.Arguments.Item(0))
sTargetPath = WSHShell.ExpandEnvironmentStrings(WScript.Arguments.Item(1))
sWorkingDirectory = objFso.GetAbsolutePathName(sShortcut)

set objSC = WSHShell.CreateShortcut(sShortcut)

objSC.TargetPath = sTargetPath
objSC.WorkingDirectory = sWorkingDirectory

objSC.Save