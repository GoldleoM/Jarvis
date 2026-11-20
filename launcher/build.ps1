$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
& $compiler /nologo /target:winexe /optimize+ /reference:System.Windows.Forms.dll "/win32icon:$project\jarvis.ico" "/out:$project\Jarvis.exe" "$PSScriptRoot\Jarvis.cs"
if ($LASTEXITCODE -ne 0) { throw 'Jarvis launcher compilation failed.' }
