param(
    [string]$ReleaseTag = "",
    [switch]$SkipDependencySync
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-PathExists {
    param(
        [string]$Path,
        [string]$Description
    )

    if (-not (Test-Path $Path)) {
        throw "$Description was not found at '$Path'."
    }
}

function Get-AppVersion {
    $version = python -c 'import pathlib, tomllib; print(tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])'
    if (-not $version) {
        throw "Unable to read project version from pyproject.toml."
    }

    return $version.Trim()
}

function Get-UvExecutable {
    $uvCommand = Get-Command uv -ErrorAction SilentlyContinue
    if ($uvCommand) {
        return $uvCommand.Source
    }

    $scriptPaths = @(
        (python -c "import sysconfig; print(sysconfig.get_path('scripts'))"),
        (python -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))")
    )

    foreach ($scriptPath in $scriptPaths) {
        if (-not $scriptPath) {
            continue
        }

        $candidate = Join-Path $scriptPath.Trim() "uv.exe"
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "uv executable was not found. Install uv or add it to PATH before building."
}

function Get-BundledFilePath {
    param(
        [string]$BundleDirectory,
        [string]$RelativePath
    )

    $candidatePaths = @(
        (Join-Path $BundleDirectory $RelativePath),
        (Join-Path (Join-Path $BundleDirectory "_internal") $RelativePath)
    )

    foreach ($candidatePath in $candidatePaths) {
        if (Test-Path $candidatePath) {
            return $candidatePath
        }
    }

    throw "Bundled file '$RelativePath' was not found under '$BundleDirectory'."
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$specPath = Join-Path $projectRoot "RePKG_GUI.spec"
$repkgExecutablePath = Join-Path $projectRoot "RePKG.exe"
$aboutImagePath = Join-Path $projectRoot "nekomusume.png"

Assert-PathExists $specPath "PyInstaller spec"
Assert-PathExists $repkgExecutablePath "Bundled RePKG executable"
Assert-PathExists $aboutImagePath "Bundled about-page image"

$uvExecutable = Get-UvExecutable
$appVersion = Get-AppVersion
if (-not $ReleaseTag) {
    $ReleaseTag = "v$appVersion"
}

if ($ReleaseTag -ne "v$appVersion") {
    throw ("Release tag '{0}' does not match project version '{1}'." -f $ReleaseTag, $appVersion)
}

$distDir = Join-Path $PSScriptRoot "..\dist"
$bundleDir = Join-Path $distDir "RePKG_GUI"
$zipPath = Join-Path $distDir "RePKG_GUI-$ReleaseTag-windows.zip"

if (-not $SkipDependencySync) {
    $syncArgs = @("sync", "--extra", "build")
    if (Test-Path (Join-Path $PSScriptRoot "..\uv.lock")) {
        $syncArgs += "--frozen"
    }

    & $uvExecutable @syncArgs
    if ($LASTEXITCODE -ne 0) {
        throw "uv sync failed."
    }
}

if (Test-Path (Join-Path $PSScriptRoot "..\build")) {
    Remove-Item (Join-Path $PSScriptRoot "..\build") -Recurse -Force
}

if (Test-Path $bundleDir) {
    Remove-Item $bundleDir -Recurse -Force
}

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Push-Location $projectRoot
try {
    & $uvExecutable run pyinstaller RePKG_GUI.spec --noconfirm --clean
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }
}
finally {
    Pop-Location
}

Assert-PathExists (Join-Path $bundleDir "RePKG_GUI.exe") "Built executable"
$bundledRepkgPath = Get-BundledFilePath -BundleDirectory $bundleDir -RelativePath "RePKG.exe"
$bundledAboutImagePath = Get-BundledFilePath -BundleDirectory $bundleDir -RelativePath "nekomusume.png"

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $bundleDir,
    $zipPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $true
)

Write-Output "Verified bundled resources:"
Write-Output " - $bundledRepkgPath"
Write-Output " - $bundledAboutImagePath"
Write-Output "Created $zipPath"
