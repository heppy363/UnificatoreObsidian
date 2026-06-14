param(
    [string]$OutputDir = "dist\portable-cli",
    [string]$ExeName = "unificatore-obsidian",
    [string]$PandocSource,
    [string]$PdfEngineSource,
    [string]$PdfEngineName = "tectonic",
    [switch]$SkipZip
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pyInstallerRoot = Join-Path $projectRoot "build\pyinstaller-portable"
$releaseRoot = Join-Path $projectRoot $OutputDir
$pyInstallerDist = Join-Path $pyInstallerRoot "dist"
$pyInstallerBuild = Join-Path $pyInstallerRoot "build"
$zipPath = Join-Path $projectRoot ("dist\{0}-portable-win64.zip" -f $ExeName)

function Remove-IfExists {
    param([string]$PathToRemove)

    if (-not (Test-Path -LiteralPath $PathToRemove)) {
        return
    }

    $resolved = (Resolve-Path -LiteralPath $PathToRemove).Path
    $projectResolved = (Resolve-Path -LiteralPath $projectRoot).Path
    if (-not $resolved.StartsWith($projectResolved, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Rifiuto di rimuovere un percorso fuori dal progetto: $resolved"
    }

    Remove-Item -LiteralPath $resolved -Recurse -Force
}

function Ensure-Directory {
    param([string]$PathToCreate)

    New-Item -ItemType Directory -Force -Path $PathToCreate | Out-Null
}

function Copy-ToolBundle {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$ToolName
    )

    $resolvedSource = (Resolve-Path -LiteralPath $Source).Path
    if ((Get-Item -LiteralPath $resolvedSource) -is [System.IO.FileInfo]) {
        $bundleRoot = Split-Path -Parent $resolvedSource
    }
    else {
        $bundleRoot = $resolvedSource
    }

    $targetRoot = Join-Path $releaseRoot ("external\{0}" -f $ToolName)
    Ensure-Directory $targetRoot
    Copy-Item -Path (Join-Path $bundleRoot "*") -Destination $targetRoot -Recurse -Force
}

function Write-PortableReadme {
    $content = @"
Questa cartella contiene una build portabile della CLI.

Uso rapido:
  .\${ExeName}.exe "D:\Vault\indice.md"

Diagnostica:
  .\${ExeName}.exe --diagnose

Dipendenze locali:
  Se `external\pandoc\` e `external\${PdfEngineName}\` sono presenti, la CLI li rileva automaticamente.

Percorsi supportati:
  - external\pandoc\
  - external\${PdfEngineName}\

Note:
  - L'eseguibile resta una utility da riga di comando.
  - Puoi comunque usare `--pandoc-path` e `--pdf-engine-path` per puntare a binari diversi.
"@

    Set-Content -LiteralPath (Join-Path $releaseRoot "PORTABLE.txt") -Value $content -Encoding UTF8
}

Push-Location $projectRoot
try {
    Remove-IfExists $pyInstallerRoot
    Remove-IfExists $releaseRoot
    Remove-IfExists $zipPath

    Ensure-Directory $pyInstallerDist
    Ensure-Directory $pyInstallerBuild
    Ensure-Directory $releaseRoot
    Ensure-Directory (Join-Path $releaseRoot "external")

    $pyInstallerArgs = @(
        "run",
        "--extra", "portable",
        "pyinstaller",
        "--onefile",
        "--console",
        "--clean",
        "--name", $ExeName,
        "--paths", "src",
        "--distpath", $pyInstallerDist,
        "--workpath", $pyInstallerBuild,
        "--specpath", $pyInstallerRoot,
        "src\unificatore_obsidian\__main__.py"
    )

    & uv @pyInstallerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller ha restituito codice $LASTEXITCODE"
    }

    $builtExe = Join-Path $pyInstallerDist ("{0}.exe" -f $ExeName)
    if (-not (Test-Path -LiteralPath $builtExe)) {
        throw "Eseguibile non trovato dopo la build: $builtExe"
    }

    Copy-Item -LiteralPath $builtExe -Destination (Join-Path $releaseRoot ("{0}.exe" -f $ExeName)) -Force
    Copy-Item -LiteralPath "README.md" -Destination (Join-Path $releaseRoot "README.md") -Force
    Copy-Item -LiteralPath "LICENSE" -Destination (Join-Path $releaseRoot "LICENSE") -Force
    Write-PortableReadme

    if ($PandocSource) {
        Copy-ToolBundle -Source $PandocSource -ToolName "pandoc"
    }

    if ($PdfEngineSource) {
        Copy-ToolBundle -Source $PdfEngineSource -ToolName $PdfEngineName
    }

    if (-not $SkipZip) {
        Compress-Archive -Path (Join-Path $releaseRoot "*") -DestinationPath $zipPath -Force
    }

    Write-Host "Build portabile pronta in: $releaseRoot"
    if (-not $SkipZip) {
        Write-Host "Archivio ZIP creato in: $zipPath"
    }
}
finally {
    Pop-Location
}
