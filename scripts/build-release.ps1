param(
    [string]$ReleaseTag = "",
    [switch]$SkipDependencySync
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AppVersion {
    $version = python -c 'import ast, pathlib; module = ast.parse(pathlib.Path("main.py").read_text(encoding="utf-8")); print(next(node.value.value for node in module.body if isinstance(node, ast.Assign) and any(getattr(target, "id", None) == "APP_VERSION" for target in node.targets)))'
    if (-not $version) {
        throw "Unable to read APP_VERSION from main.py."
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

$uvExecutable = Get-UvExecutable
$appVersion = Get-AppVersion
if (-not $ReleaseTag) {
    $ReleaseTag = "v$appVersion"
}

if ($ReleaseTag -ne "v$appVersion") {
    throw ("Release tag '{0}' does not match APP_VERSION '{1}'." -f $ReleaseTag, $appVersion)
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

Push-Location (Join-Path $PSScriptRoot "..")
try {
    & $uvExecutable run pyinstaller RePKG_GUI.spec --noconfirm --clean
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }
}
finally {
    Pop-Location
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $bundleDir,
    $zipPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $true
)

Write-Output "Created $zipPath"
