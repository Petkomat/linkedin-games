<#
.SYNOPSIS
Starts the agent team's orchestrator at every logon, in the background.

.DESCRIPTION
Registers a Windows scheduled task that runs `uv run python -m team run` in
this repo when you log on, restarts it if it crashes, and starts it right
away. The board is then on http://127.0.0.1:8765 and the orchestrator's own
log is ~/.linkedin-games/team/orchestrator.log.

.EXAMPLE
.\team\install.ps1
Register the task and start the team.

.EXAMPLE
.\team\install.ps1 -Remove
Stop the team and remove the task.
#>
param([switch] $Remove)

$name = 'LinkedIn games team'
$repo = Split-Path -Parent $PSScriptRoot

if ($Remove) {
    & uv --directory $repo run python -m team stop
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
    Write-Host "Removed '$name'."
    return
}

$uv = (Get-Command uv -ErrorAction Stop).Source
$command = "`$env:PYTHONIOENCODING = 'utf-8'; & '$uv' run python -m team run"
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -WorkingDirectory $repo `
    -Argument "-NoProfile -WindowStyle Hidden -Command `"$command`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew -Hidden
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings `
    -Description 'The orchestrator of the LinkedIn games agent team (team/README.md)' -Force | Out-Null
Start-ScheduledTask -TaskName $name
Write-Host "Registered '$name' and started it. Board: http://127.0.0.1:8765"
