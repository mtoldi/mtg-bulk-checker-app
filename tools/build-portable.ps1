<#
Builds the portable Windows version: the app + embedded Python + Streamlit in one ZIP.
Users unzip it, double-click start.bat and that's it (no Python install needed).

    powershell -ExecutionPolicy Bypass -File tools\build-portable.ps1

Output: dist\BulkChecker-windows.zip
#>
param(
    [string]$PythonVersion = "3.13.1"
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # Invoke-WebRequest is very slow otherwise

$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist"
$out  = Join-Path $dist "BulkChecker"
$py   = Join-Path $out "python"
$zip  = Join-Path $dist "BulkChecker-windows.zip"

if (Test-Path $out) { Remove-Item -Recurse -Force $out }
if (Test-Path $zip) { Remove-Item -Force $zip }
New-Item -ItemType Directory -Force $py | Out-Null

# 1) embeddable Python from python.org
$embedZip = Join-Path $dist "python-$PythonVersion-embed-amd64.zip"
if (-not (Test-Path $embedZip)) {
    Write-Host "Downloading Python $PythonVersion..."
    Invoke-WebRequest "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip" -OutFile $embedZip
}
Expand-Archive $embedZip -DestinationPath $py

# 2) ._pth: enable site-packages and the app folder (..)
$pth = Get-ChildItem $py -Filter "python*._pth" | Select-Object -First 1
$lines = (Get-Content $pth.FullName) -replace '^#\s*import site', 'import site'
$lines = @($lines) + @('Lib\site-packages', '..')
Set-Content -Path $pth.FullName -Value $lines -Encoding ascii

# 3) dependencies, prebuilt Windows wheels for exactly this Python version
$short = ($PythonVersion -split '\.')[0..1] -join ''
Write-Host "Installing dependencies..."
python -m pip install --disable-pip-version-check -q `
    --target (Join-Path $py "Lib\site-packages") `
    --only-binary=:all: --platform win_amd64 --python-version $short --implementation cp `
    -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# 4) the app itself
foreach ($f in "app.py", "parser.py", "matcher.py", "storage.py", "config.toml", "start.bat", "README.md", "requirements.txt") {
    Copy-Item (Join-Path $root $f) $out
}
Copy-Item -Recurse (Join-Path $root ".streamlit") $out
Copy-Item -Recurse (Join-Path $root "decks") $out
New-Item -ItemType Directory -Force (Join-Path $out "bulks") | Out-Null
# only the example bulks tracked by git, never your local ones
foreach ($f in (git -C $root ls-files bulks)) { Copy-Item (Join-Path $root $f) (Join-Path $out "bulks") }

# 5) ZIP – tar (built into Windows 10+) makes a proper ZIP; Compress-Archive in PS 5.1 writes "\" paths
Write-Host "Packing..."
tar.exe -a -c -f $zip -C $dist BulkChecker
if ($LASTEXITCODE -ne 0) { throw "packing failed" }
$mb = [math]::Round((Get-Item $zip).Length / 1MB)
Write-Host "Done: $zip ($mb MB)"
