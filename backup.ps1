# NetGuard Backup Utility for Windows PowerShell
Write-Output "🛡️ NetGuard Backup Utility"
Write-Output "======================="

# Get current date in YYYYMMDD format
$backupDate = Get-Date -Format "yyyyMMdd"

# Set backup directory
$backupDir = Join-Path $env:USERPROFILE "Documents\NetGuard\backups"
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}

# Load environment variables from .env file
$envContent = Get-Content .env | Where-Object { $_ -notmatch '^#' -and $_.Trim() }
$envVars = @{}
foreach ($line in $envContent) {
    if ($line -match '(.+)=(.+)') {
        $envVars[$Matches[1].Trim()] = $Matches[2].Trim()
    }
}

# Backup database
Write-Output "📦 Creating database backup..."
$dbBackupPath = Join-Path $backupDir "netguard_db_$backupDate.sql"
$env:PGPASSWORD = $envVars['DB_PASSWORD']
try {
    & pg_dump -h $envVars['DB_HOST'] -U $envVars['DB_USER'] -d $envVars['DB_NAME'] -f $dbBackupPath
    if ($LASTEXITCODE -eq 0) {
        Write-Output "Database backup created successfully"
    } else {
        Write-Error "Database backup failed"
    }
} catch {
    Write-Error "Error executing pg_dump: $_"
}

# Backup configuration
Write-Output "📝 Backing up configuration..."
$envBackupPath = Join-Path $backupDir "env_$backupDate.backup"
Copy-Item .env $envBackupPath -Force

# Cleanup old backups (keep last 30 days)
Write-Output "🧹 Cleaning up old backups..."
Get-ChildItem -Path $backupDir -Filter "netguard_db_*.sql" | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | 
    Remove-Item -Force

Get-ChildItem -Path $backupDir -Filter "env_*.backup" | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | 
    Remove-Item -Force

Write-Output "✅ Backup completed successfully!"
Write-Output "Backup location: $backupDir"
