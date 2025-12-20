Param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "Creating virtual environment..."
& $PythonExe -m venv .venv
& .\.venv\Scripts\Activate.ps1

Write-Host "Installing PyInstaller..."
python -m pip install --upgrade pip
python -m pip install pyinstaller

Write-Host "Building Windows app..."
pyinstaller --noconsole --windowed --name InternetConnectionTestingApp win_app_main.py

Write-Host "Packaging build output..."
if (Test-Path ".\dist\InternetConnectionTestingApp.zip") {
    Remove-Item ".\dist\InternetConnectionTestingApp.zip"
}
Compress-Archive -Path ".\dist\InternetConnectionTestingApp\*" -DestinationPath ".\dist\InternetConnectionTestingApp.zip"

Write-Host "Done. Zip created at dist\\InternetConnectionTestingApp.zip"
