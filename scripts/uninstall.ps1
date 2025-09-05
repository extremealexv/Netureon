# NetGuard Uninstall Script for Windows
Write-Host "🗑️ NetGuard Uninstallation Script" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan

# Function to print status messages
function Write-Status {
    param($Message, $Type = "Info")
    
    switch ($Type) {
        "Info" { 
            Write-Host "ℹ️ $Message" -ForegroundColor Cyan 
        }
        "Success" { 
            Write-Host "✅ $Message" -ForegroundColor Green 
        }
        "Warning" { 
            Write-Host "⚠️ $Message" -ForegroundColor Yellow 
        }
        "Error" { 
            Write-Host "❌ $Message" -ForegroundColor Red 
        }
    }
}

# Check if running as administrator
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Status "This script must be run as Administrator" -Type "Error"
    exit 1
}

# Ask for confirmation
Write-Host
Write-Status "WARNING: This will remove all NetGuard services and their data" -Type "Warning"
Write-Host "The following actions will be performed:"
Write-Host "1. Stop all NetGuard services"
Write-Host "2. Remove Windows services"
Write-Host "3. Remove service configurations"
Write-Host "4. Clean up program data"
Write-Host
$confirm = Read-Host "Do you want to proceed? (y/N)"
if ($confirm -notmatch "^[yY]") {
    Write-Status "Uninstallation cancelled" -Type "Info"
    exit 0
}

# Stop services
Write-Status "Stopping NetGuard services..."
$services = @(
    "NetGuard",
    "NetGuardAlerts",
    "NetGuardScan"
)

foreach ($service in $services) {
    if (Get-Service -Name $service -ErrorAction SilentlyContinue) {
        try {
            Stop-Service -Name $service -Force -ErrorAction Stop
            Write-Status "$service service stopped" -Type "Success"
        } catch {
            Write-Status "Failed to stop $service service: $_" -Type "Warning"
        }
    }
}

# Remove services
Write-Status "Removing services..."
foreach ($service in $services) {
    if (Get-Service -Name $service -ErrorAction SilentlyContinue) {
        try {
            & sc.exe delete $service
            Write-Status "$service service removed" -Type "Success"
        } catch {
            Write-Status "Failed to remove $service service: $_" -Type "Warning"
        }
    }
}

# Clean up program data
$programData = Join-Path $env:ProgramData "NetGuard"
if (Test-Path $programData) {
    Write-Status "Removing program data..."
    try {
        Remove-Item -Path $programData -Recurse -Force
        Write-Status "Program data removed" -Type "Success"
    } catch {
        Write-Status "Failed to remove program data: $_" -Type "Warning"
    }
}

# Clean up logs
$logPath = Join-Path $env:ProgramData "NetGuard\logs"
if (Test-Path $logPath) {
    Write-Status "Removing log files..."
    try {
        Remove-Item -Path $logPath -Recurse -Force
        Write-Status "Log files removed" -Type "Success"
    } catch {
        Write-Status "Failed to remove log files: $_" -Type "Warning"
    }
}

Write-Host
Write-Status "Uninstallation complete!" -Type "Success"
Write-Host "To complete the removal:"
Write-Host "1. Delete the NetGuard directory"
Write-Host "2. Remove the virtual environment if created"
Write-Host "3. Optionally remove the PostgreSQL database"
Write-Host
Write-Host "Database can be removed using:"
Write-Host "psql -h <host> -U <user> -c 'DROP DATABASE netguard;'"
