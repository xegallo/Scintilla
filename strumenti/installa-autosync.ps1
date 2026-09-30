# Installa la sincronizzazione automatica del libro su Windows (da eseguire una sola volta per progetto).
# Il nome dell'attivita' include il nome della cartella, cosi' piu' libri sullo stesso PC
# possono sincronizzarsi in automatico in parallelo senza sovrascriversi a vicenda.
# Uso:  powershell -ExecutionPolicy Bypass -File strumenti\installa-autosync.ps1
$ErrorActionPreference = "Stop"
$libro  = Split-Path -Parent $PSScriptRoot
$nome   = Split-Path -Leaf $libro
$task   = "Libro autosync - $nome"
$script = Join-Path $PSScriptRoot "autosync.py"
$pyw    = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pyw) { $pyw = (Get-Command python.exe).Source }

$azione  = New-ScheduledTaskAction -Execute $pyw -Argument "`"$script`"" -WorkingDirectory $libro
$avvio   = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$opzioni = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
           -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
           -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName $task -Action $azione -Trigger $avvio `
    -Settings $opzioni -Description "Salva i capitoli del libro ($nome) in Git e scarica quelli dall'altro PC" -Force | Out-Null
Start-ScheduledTask -TaskName $task
Start-Sleep -Seconds 3
Get-ScheduledTask -TaskName $task | Get-ScheduledTaskInfo |
    Select-Object TaskName, LastRunTime, LastTaskResult, NumberOfMissedRuns | Format-List

Write-Host ""
Write-Host "Fatto. Registro: $libro\word\.stato\autosync.log"
Write-Host "Per le notifiche sul desktop (facoltativo):  Install-Module BurntToast -Scope CurrentUser"
Write-Host "Per fermarla:   Unregister-ScheduledTask -TaskName '$task' -Confirm:`$false"
