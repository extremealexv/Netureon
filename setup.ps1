# Setup script for NetGuard on Windows
Write-Host "🚀 Starting NetGuard setup..." -ForegroundColor Cyan

# Check Python installation
Write-Host "🐍 Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
    if ([version]$pythonVersion -lt [version]"3.8") {
        Write-Host "❌ Python 3.8 or higher is required. Found version $pythonVersion" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Found Python $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python 3 is not installed or not in PATH. Please install Python 3.8 or higher." -ForegroundColor Red
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    try {
        python -m venv venv
    } catch {
        Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Virtual environment exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "🔌 Activating virtual environment..." -ForegroundColor Yellow
try {
    .\venv\Scripts\Activate.ps1
} catch {
    Write-Host "❌ Failed to activate virtual environment" -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "📥 Installing dependencies..." -ForegroundColor Yellow
try {
    python -m pip install --upgrade pip
    pip install -r requirements.txt
} catch {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Database configuration
Write-Host "🗄️ Database configuration..." -ForegroundColor Yellow

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Please enter PostgreSQL database credentials:" -ForegroundColor Cyan
    $dbName = Read-Host "Database name (default: netguard)"
    if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = "netguard" }
    $dbUser = Read-Host "Database user"
    $dbPassword = Read-Host "Database password" -AsSecureString
    $dbHost = Read-Host "Database host (default: localhost)"
    if ([string]::IsNullOrWhiteSpace($dbHost)) { $dbHost = "localhost" }
    $dbPort = Read-Host "Database port (default: 5432)"
    if ([string]::IsNullOrWhiteSpace($dbPort)) { $dbPort = "5432" }
    
    Write-Host "`n� Email notification configuration:" -ForegroundColor Cyan
    $smtpServer = Read-Host "SMTP Server"
    $smtpPort = Read-Host "SMTP Port (default: 587)"
    if ([string]::IsNullOrWhiteSpace($smtpPort)) { $smtpPort = "587" }
    $smtpUser = Read-Host "SMTP User"
    $smtpPassword = Read-Host "SMTP Password" -AsSecureString
    $emailFrom = Read-Host "From Email"
    $emailTo = Read-Host "To Email"
    
    # Convert secure strings to plain text for .env file
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword)
    $dbPasswordPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($smtpPassword)
    $smtpPasswordPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    $flaskSecret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
    @"
# Database Configuration
DB_NAME=$dbName
DB_USER=$dbUser
DB_PASSWORD=$dbPasswordPlain
DB_HOST=$dbHost
DB_PORT=$dbPort

# Email Configuration
SMTP_SERVER=$smtpServer
SMTP_PORT=$smtpPort
SMTP_USER=$smtpUser
SMTP_PASSWORD=$smtpPasswordPlain
EMAIL_FROM=$emailFrom
EMAIL_TO=$emailTo

# Flask Configuration
FLASK_SECRET_KEY=$flaskSecret
"@ | Out-File -FilePath ".env" -Encoding UTF8
} else {
    Write-Host "✅ .env file exists" -ForegroundColor Green
}

# Load environment variables
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#].+)=(.+)$') {
        $varName = $matches[1].Trim()
        $varValue = $matches[2].Trim()
        Set-Item -Path "Env:$varName" -Value $varValue
    }
}

# Test database connection and create schema
Write-Host "🔄 Testing database connection..." -ForegroundColor Yellow
try {
    $env:PGPASSWORD = $Env:DB_PASSWORD
    & psql -h $Env:DB_HOST -p $Env:DB_PORT -U $Env:DB_USER -d $Env:DB_NAME -c "\q" 2>$null
} catch {
    Write-Host "📝 Creating database..." -ForegroundColor Yellow
    try {
        & psql -h $Env:DB_HOST -p $Env:DB_PORT -U $Env:DB_USER -d postgres -c "CREATE DATABASE $Env:DB_NAME" 2>$null
    } catch {
        Write-Host "❌ Failed to create database" -ForegroundColor Red
        exit 1
    }
}

Write-Host "📝 Creating database schema..." -ForegroundColor Yellow
try {
    Get-Content schema.sql | & psql -h $Env:DB_HOST -p $Env:DB_PORT -U $Env:DB_USER -d $Env:DB_NAME
} catch {
    Write-Host "❌ Failed to create schema" -ForegroundColor Red
    exit 1
}

# Create Windows services
Write-Host "🔧 Creating Windows services..." -ForegroundColor Yellow
$currentPath = Get-Location
$pythonPath = "$(Get-Location)\venv\Scripts\python.exe"

# Create NetGuard service
$netguardService = @"
[Unit]
Description=NetGuard Network Monitor

[Service]
ExePath=$pythonPath
WorkingDirectory=$currentPath
Arguments=main.py
"@

# Create Alert Daemon service
$alertService = @"
[Unit]
Description=NetGuard Alert Daemon

[Service]
ExePath=$pythonPath
WorkingDirectory=$currentPath
Arguments=alert_daemon.py
"@

# Save service configurations
$netguardService | Out-File -FilePath "netguard.service" -Encoding UTF8
$alertService | Out-File -FilePath "netguard-alerts.service" -Encoding UTF8

# Create and start services using sc.exe
Write-Host "🔄 Creating and starting services..." -ForegroundColor Yellow
try {
    & sc.exe create "NetGuard" binPath= "$pythonPath $currentPath\main.py" start= auto displayname= "NetGuard Network Monitor"
    & sc.exe description "NetGuard" "NetGuard Network Monitor"
    & sc.exe create "NetGuardAlerts" binPath= "$pythonPath $currentPath\alert_daemon.py" start= auto displayname= "NetGuard Alert Daemon"
    & sc.exe description "NetGuardAlerts" "NetGuard Alert Daemon"
} catch {
    Write-Host "❌ Failed to create Windows services" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

# Test email configuration
Write-Host "📧 Testing email configuration..." -ForegroundColor Yellow
$emailTest = @"
import smtplib
from email.message import EmailMessage

try:
    msg = EmailMessage()
    msg.set_content("This is a test email from NetGuard setup.")
    msg["Subject"] = "NetGuard Setup Test"
    msg["From"] = "$($Env:EMAIL_FROM)"
    msg["To"] = "$($Env:EMAIL_TO)"

    with smtplib.SMTP("$($Env:SMTP_SERVER)", $($Env:SMTP_PORT)) as server:
        server.starttls()
        server.login("$($Env:SMTP_USER)", "$($Env:SMTP_PASSWORD)")
        server.send_message(msg)
    print("✅ Email test successful")
except Exception as e:
    print(f"❌ Email test failed: {str(e)}")
"@

$emailTest | python

Write-Host "`n✨ Setup complete! Services have been created and enabled." -ForegroundColor Green
Write-Host "👉 To start the services, run:" -ForegroundColor Cyan
Write-Host "   Start-Service NetGuard" -ForegroundColor Yellow
Write-Host "   Start-Service NetGuardAlerts" -ForegroundColor Yellow
Write-Host "👉 To view service status, run:" -ForegroundColor Cyan
Write-Host "   Get-Service NetGuard" -ForegroundColor Yellow
Write-Host "   Get-Service NetGuardAlerts" -ForegroundColor Yellow
