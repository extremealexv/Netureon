# Setup script for NetGuard on Windows
Write-Host "🚀 Setting up NetGuard environment..." -ForegroundColor Cyan

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
} else {
    Write-Host "✅ Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "🔌 Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Install requirements
Write-Host "📥 Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "🔑 Creating .env file..." -ForegroundColor Yellow
    @"
DB_NAME=netguard
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "⚠️ Please update the database credentials in .env file" -ForegroundColor Red
} else {
    Write-Host "✅ .env file already exists" -ForegroundColor Green
}

Write-Host "`n✨ Setup complete! You can now run NetGuard using 'python main.py'" -ForegroundColor Green
