[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot 'portable'),
    [switch]$SkipDependencyInstall,
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed (exit code $LASTEXITCODE)."
    }
}

if ($env:OS -ne 'Windows_NT') {
    throw 'The portable EXE build requires Windows x64.'
}

# Import the installed Visual C++ environment, including preview installations.
# This changes only this script process; it never installs or changes system tools.
if (-not (Get-Command cl.exe -ErrorAction SilentlyContinue)) {
    $vswherePath = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    if (-not (Test-Path -LiteralPath $vswherePath)) {
        throw 'Visual Studio C++ Build Tools and Windows SDK are required.'
    }
    $vsPath = & $vswherePath -latest -prerelease -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if (-not $vsPath) {
        throw 'Install the Desktop development with C++ workload and Windows SDK.'
    }
    $devCmdPath = Join-Path $vsPath 'Common7/Tools/VsDevCmd.bat'
    $devEnvironment = & $env:ComSpec /d /s /c "`"$devCmdPath`" -no_logo -arch=x64 -host_arch=x64 >nul && set"
    if ($LASTEXITCODE -ne 0) { throw 'Could not load the Visual C++ build environment.' }
    foreach ($entry in $devEnvironment) {
        if ($entry -match '^([^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
        }
    }
}

Push-Location $PSScriptRoot
$oldRustFlags = $env:RUSTFLAGS
try {
    $env:RUSTFLAGS = (@($oldRustFlags, '-C target-feature=+crt-static') | Where-Object { $_ }) -join ' '
    if (-not $SkipDependencyInstall) {
        Invoke-Checked 'npm.cmd' @('ci', '--no-audit', '--no-fund')
    }
    if (-not $SkipTests) {
        Invoke-Checked 'npm.cmd' @('test')
        Invoke-Checked 'cargo.exe' @('test', '--manifest-path', 'src-tauri/Cargo.toml', '--target', 'x86_64-pc-windows-msvc', '--locked')
    }
    # `--no-bundle` produces the application itself, not an installer.
    Invoke-Checked 'npm.cmd' @('run', 'tauri', '--', 'build', '--no-bundle', '--target', 'x86_64-pc-windows-msvc', '--', '--locked')
    $version = (Get-Content -Raw -LiteralPath 'package.json' | ConvertFrom-Json).version
    $buildRoot = if ($env:CARGO_TARGET_DIR) { $env:CARGO_TARGET_DIR } else { 'src-tauri/target' }
    $builtExe = Join-Path $buildRoot 'x86_64-pc-windows-msvc/release/humidi-tauri.exe'
    if (-not (Test-Path -LiteralPath $builtExe)) { throw "Missing build output: $builtExe" }
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    $outputExe = Join-Path $OutputDirectory "HuMidi-Xingkong-Edition-$version-Windows-x64.exe"
    Copy-Item -LiteralPath $builtExe -Destination $outputExe -Force
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $outputExe).Hash.ToLowerInvariant()
    [IO.File]::WriteAllText("$outputExe.sha256", "$hash  $([IO.Path]::GetFileName($outputExe))`n")
    Write-Host "Built: $outputExe"
    Write-Host "SHA256: $hash"
} finally {
    $env:RUSTFLAGS = $oldRustFlags
    Pop-Location
}
