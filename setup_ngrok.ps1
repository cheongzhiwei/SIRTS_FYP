# ngrok Setup Script for Windows
# This script downloads and sets up ngrok

Write-Host "Setting up ngrok..." -ForegroundColor Green

# Create ngrok directory in user's folder
$ngrokDir = "$env:USERPROFILE\ngrok"
if (-not (Test-Path $ngrokDir)) {
    New-Item -ItemType Directory -Path $ngrokDir | Out-Null
    Write-Host "Created directory: $ngrokDir" -ForegroundColor Yellow
}

# Download ngrok
$ngrokZip = "$ngrokDir\ngrok.zip"
$ngrokExe = "$ngrokDir\ngrok.exe"

if (-not (Test-Path $ngrokExe)) {
    Write-Host "Downloading ngrok..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip" -OutFile $ngrokZip
        Write-Host "Extracting ngrok..." -ForegroundColor Yellow
        Expand-Archive -Path $ngrokZip -DestinationPath $ngrokDir -Force
        Remove-Item $ngrokZip -Force
        Write-Host "ngrok installed successfully!" -ForegroundColor Green
    } catch {
        Write-Host "Error downloading ngrok: $_" -ForegroundColor Red
        Write-Host "Please download manually from: https://ngrok.com/download" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "ngrok already exists at: $ngrokExe" -ForegroundColor Green
}

# Run ngrok
Write-Host "`nStarting ngrok on port 5678..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop ngrok`n" -ForegroundColor Yellow
& $ngrokExe http 5678
