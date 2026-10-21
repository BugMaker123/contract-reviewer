$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
Push-Location frontend
try {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
} finally { Pop-Location }
& .venv/Scripts/python.exe -m PyInstaller --noconfirm --distpath artifacts/windows --workpath artifacts/pyinstaller LexisGraph.spec
if ($LASTEXITCODE -ne 0) { throw 'EXE build failed' }
Copy-Item docs/windows-readme.txt artifacts/windows/LexisGraph/README.txt
Copy-Item LICENSE artifacts/windows/LexisGraph/LICENSE.txt
Compress-Archive -Path artifacts/windows/LexisGraph -DestinationPath artifacts/LexisGraph-Windows-x64.zip -Force
Write-Output 'Created artifacts/LexisGraph-Windows-x64.zip'
