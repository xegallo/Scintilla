# Installa la sincronizzazione automatica del libro su Windows (da eseguire una sola volta).
# Uso:  powershell -ExecutionPolicy Bypass -File strumenti\installa-autosync.ps1
$ErrorActionPreference = "Stop"
$libro  = Split-Path -Parent $PSScriptRoot
$script = Join-Path $PSScriptRoot "autosync.py"
$pyw    = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pyw) { $pyw = (Get-Command python.exe).Source }

$azione  = New-ScheduledTaskAction -Execute $pyw -Argument "`"$script`"" -WorkingDirectory $libro
$avvio   = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$opzioni = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
           -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
           -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName "Libro autosync" -Action $azione -Trigger $avvio `
    -Settings $opzioni -Description "Salva i capitoli del libro in Git e scarica quelli dall'altro PC" -Force | Out-Null
Start-ScheduledTask -TaskName "Libro autosync"
Start-Sleep -Seconds 3
Get-ScheduledTask -TaskName "Libro autosync" | Get-ScheduledTaskInfo |
    Select-Object TaskName, LastRunTime, LastTaskResult, NumberOfMissedRuns | Format-List

Write-Host ""
Write-Host "Fatto. Registro: $libro\word\.stato\autosync.log"
Write-Host "Per le notifiche sul desktop (facoltativo):  Install-Module BurntToast -Scope CurrentUser"
Write-Host "Per fermarla:   Unregister-ScheduledTask -TaskName 'Libro autosync' -Confirm:`$false"
