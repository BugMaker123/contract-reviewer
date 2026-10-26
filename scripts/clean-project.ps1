[CmdletBinding(SupportsShouldProcess = $true)]
param([switch]$Execute)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$prefix = $projectRoot + [IO.Path]::DirectorySeparatorChar

function Assert-SafePath([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path outside project: $full"
    }
    $current = $full
    while ($current -and $current -ne $projectRoot) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Refusing symbolic link or junction: $current"
            }
        }
        $current = Split-Path $current -Parent
    }
}

# Require Git so tracked files are always protected, including local edits.
$tracked = @{}
Push-Location $projectRoot
try {
    $gitFiles = @(& git -c core.quotepath=false ls-files)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read tracked files; cleanup aborted.' }
    foreach ($path in $gitFiles) { $tracked[$path.Replace('\', '/')] = $true }
} finally { Pop-Location }

$candidates = [Collections.Generic.List[object]]::new()
function Add-Candidate([IO.FileInfo]$File) {
    Assert-SafePath $File.FullName
    $relative = $File.FullName.Substring($prefix.Length).Replace('\', '/')
    if (-not $tracked.ContainsKey($relative)) {
        $candidates.Add([pscustomobject]@{
            Path = $relative
            Bytes = $File.Length
            FullName = $File.FullName
        })
    }
}

# Only these disposable caches and packaging intermediates are scanned.
$cacheDirs = @('.pytest_cache', 'backend/__pycache__', 'tests/__pycache__',
    'scripts/__pycache__', 'frontend/.vite', 'artifacts/pyinstaller')
$artifactRoot = Join-Path $projectRoot 'artifacts'
if (Test-Path -LiteralPath $artifactRoot) {
    Assert-SafePath $artifactRoot
    foreach ($dir in Get-ChildItem -LiteralPath $artifactRoot -Directory) {
        if ($dir.Name -match '^word-.*(render|verified|approved|final|ready)$') {
            $cacheDirs += 'artifacts/' + $dir.Name
        }
    }
}
function Add-Tree([string]$Directory, [string[]]$Extensions = @()) {
    Assert-SafePath $Directory
    if (-not (Test-Path -LiteralPath $Directory)) { return }
    foreach ($item in Get-ChildItem -LiteralPath $Directory -Force) {
        Assert-SafePath $item.FullName
        if ($item.PSIsContainer) {
            Add-Tree $item.FullName $Extensions
        } elseif ($Extensions.Count -eq 0 -or $item.Extension -in $Extensions) {
            Add-Candidate $item
        }
    }
}
foreach ($relative in $cacheDirs) { Add-Tree (Join-Path $projectRoot $relative) }
if (Test-Path -LiteralPath $artifactRoot) {
    foreach ($file in Get-ChildItem -LiteralPath $artifactRoot -File) {
        if ($file.Extension -in @('.png', '.jpg', '.pdf', '.docx', '.log', '.txt')) {
            Add-Candidate $file
        }
    }
    Add-Tree (Join-Path $artifactRoot 'prototypes') @('.png', '.jpg', '.pdf')
}

$plan = @($candidates | Sort-Object Path -Unique)
$plan | Select-Object Path, Bytes | Format-Table -AutoSize -Wrap | Out-Host
$total = ($plan | Measure-Object Bytes -Sum).Sum
Write-Host ('Files: {0}; Size: {1:N2} MiB' -f $plan.Count, ($total / 1MB))
Write-Host 'Preserved: tracked files, data, .venv, node_modules, frontend/dist, release packages, temporary scripts and databases.'
if (-not $Execute) {
    Write-Host 'Preview only. Review the list, stop running tests/builds, then rerun with -Execute to delete.'
    return
}

$removed = 0
$failed = 0
foreach ($file in $plan) {
    Assert-SafePath $file.FullName
    if ($PSCmdlet.ShouldProcess($file.Path, 'Delete generated file')) {
        try {
            Remove-Item -LiteralPath $file.FullName -Force -ErrorAction Stop
            $removed++
        } catch {
            $failed++
            Write-Warning ('Could not delete {0}: {1}' -f $file.Path, $_.Exception.Message)
        }
    }
}
Write-Host "Deleted: $removed; Failed: $failed. Empty directories are retained."
if ($failed -gt 0) { throw 'Some files could not be deleted; see warnings above.' }
