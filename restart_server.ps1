# Swagger ERR_EMPTY_RESPONSE 해결 스크립트
# 포트 8000을 사용하는 모든 프로세스를 종료하고 서버를 재시작합니다

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Swagger ERR_EMPTY_RESPONSE Fix" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 포트 8000을 사용하는 프로세스 찾기
Write-Host "`n1. Finding processes on port 8000..." -ForegroundColor Yellow
$processes = netstat -ano | Select-String ":8000" | Select-String "LISTENING"

if ($processes) {
    Write-Host "Found processes:" -ForegroundColor Yellow
    $pids = @()
    foreach ($line in $processes) {
        $pid = ($line -split '\s+')[-1]
        if ($pid -and $pid -ne "0") {
            $pids += $pid
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "  PID: $pid - $($proc.ProcessName)" -ForegroundColor Red
            }
        }
    }
    
    # 프로세스 종료
    if ($pids.Count -gt 0) {
        Write-Host "`n2. Killing processes..." -ForegroundColor Yellow
        foreach ($pid in $pids) {
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  [OK] Killed PID: $pid" -ForegroundColor Green
            } catch {
                Write-Host "  [WARNING] Could not kill PID: $pid" -ForegroundColor Yellow
            }
        }
        Start-Sleep -Seconds 2
    }
} else {
    Write-Host "[OK] No processes found on port 8000" -ForegroundColor Green
}

# 서버 재시작
Write-Host "`n3. Starting Django server..." -ForegroundColor Yellow
Write-Host "   Run: python manage.py runserver" -ForegroundColor Cyan
Write-Host "`n4. Then access Swagger at:" -ForegroundColor Yellow
Write-Host "   http://localhost:8000/swagger/" -ForegroundColor Cyan

Write-Host "`n==========================================" -ForegroundColor Cyan
