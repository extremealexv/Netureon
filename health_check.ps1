# NetGuard Health Check Utility
Write-Output "🛡️ NetGuard Health Check"
Write-Output "====================="

# Check if PostgreSQL is running
function Test-PostgreSQL {
    Write-Output "📊 Checking PostgreSQL connection..."
    
    # Load environment variables from .env file
    $envContent = Get-Content .env | Where-Object { $_ -notmatch '^#' -and $_.Trim() }
    $envVars = @{}
    foreach ($line in $envContent) {
        if ($line -match '(.+)=(.+)') {
            $envVars[$Matches[1].Trim()] = $Matches[2].Trim()
        }
    }

    $env:PGPASSWORD = $envVars['DB_PASSWORD']
    try {
        & psql -h $envVars['DB_HOST'] -U $envVars['DB_USER'] -d $envVars['DB_NAME'] -c "SELECT 1" > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Output "✅ Database connection successful"
            return $true
        } else {
            Write-Output "❌ Database connection failed"
            return $false
        }
    } catch {
        Write-Output "❌ Database connection failed: $_"
        return $false
    }
}

# Check if required services are running
function Test-Services {
    Write-Output "`n🔍 Checking NetGuard services..."
    
    $services = @(
        "NetGuardAlertDaemon",
        "NetGuardWebUI",
        "NetGuardScan"
    )

    $allOk = $true
    foreach ($service in $services) {
        $status = Get-Service -Name $service -ErrorAction SilentlyContinue
        if ($status) {
            if ($status.Status -eq 'Running') {
                Write-Output "✅ $service is running"
            } else {
                Write-Output "❌ $service is not running (Status: $($status.Status))"
                $allOk = $false
            }
        } else {
            Write-Output "❌ $service not found"
            $allOk = $false
        }
    }
    return $allOk
}
# Check disk space
function Test-DiskSpace {
    Write-Output "`n💾 Checking disk space..."
    
    $drive = Get-PSDrive -Name C
    $freeSpaceGB = [math]::Round($drive.Free / 1GB, 2)
    $totalSpaceGB = [math]::Round(($drive.Free + $drive.Used) / 1GB, 2)
    $freeSpacePercent = [math]::Round(($drive.Free / ($drive.Free + $drive.Used)) * 100, 2)
    
    Write-Output "System Drive (C:)"
    Write-Output "Free: ${freeSpaceGB}GB / ${totalSpaceGB}GB (${freeSpacePercent}%)"
    
    if ($freeSpacePercent -lt 10) {
        Write-Output "❌ Critical: Less than 10% disk space remaining"
        return $false
    } elseif ($freeSpacePercent -lt 20) {
        Write-Output "⚠️ Warning: Less than 20% disk space remaining"
        return $true
    } else {
        Write-Output "✅ Disk space is adequate"
        return $true
    }
}

# Check log files
function Test-LogFiles {
    Write-Output "`n📝 Checking log files..."
    
    $logPath = Join-Path $env:ProgramData "NetGuard\logs"
    if (-not (Test-Path $logPath)) {
        Write-Output "❌ Log directory not found at: $logPath"
        return $false
    }

    $recentLogs = Get-ChildItem -Path $logPath -Filter "*.log" | 
        Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-1) }
    
    if ($recentLogs.Count -eq 0) {
        Write-Output "⚠️ Warning: No recent log files found in the last 24 hours"
        return $false
    } else {
        Write-Output "✅ Found $($recentLogs.Count) log files from the last 24 hours"
        return $true
    }
}

# Run all checks
$overallStatus = $true

$dbStatus = Test-PostgreSQL
$overallStatus = $overallStatus -and $dbStatus

$servicesStatus = Test-Services
$overallStatus = $overallStatus -and $servicesStatus

$diskStatus = Test-DiskSpace
$overallStatus = $overallStatus -and $diskStatus

$logStatus = Test-LogFiles
$overallStatus = $overallStatus -and $logStatus

Write-Output "`n====================="
if ($overallStatus) {
    Write-Output "✅ Overall system health: GOOD"
} else {
    Write-Output "❌ Overall system health: ISSUES DETECTED"
    Write-Output "Please review the warnings and errors above."
}
    dir /s /b logs\*.log | find /c "::" > nul
    echo ✅ Log files present
) else (
    echo ⚠️ No log files found
)

endlocal
