<#
.SYNOPSIS
Register, remove, or inspect the daily new-nikke check.

.DESCRIPTION
Runs scripts/check_new_nikkes.py every day at 19:00 local time. Patches land
on Thursdays every two to three weeks and finish at 15:00 or 18:00 KST, but
the interval is irregular and maintenance can overrun, so a Thursday-only run
risks missing a release for a whole week. A daily run costs one page load and
stays silent unless something is found.

The task is registered against this repository's path, so run this from the
main checkout - not from a worktree, which is temporary.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts/schedule_new_nikke_check.ps1 -Action register
powershell -ExecutionPolicy Bypass -File scripts/schedule_new_nikke_check.ps1 -Action status
powershell -ExecutionPolicy Bypass -File scripts/schedule_new_nikke_check.ps1 -Action unregister
#>
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('register', 'unregister', 'status')]
  [string]$Action
)

$ErrorActionPreference = 'Stop'

$TaskName = 'NikkeDeckBuilder-NewNikkeCheck'
$Repo = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $Repo 'scripts\check_new_nikkes.py'

if (-not (Test-Path $Script)) { throw "not found: $Script" }

switch ($Action) {
  'register' {
    # check_new_nikkes.py imports only the standard library, so any Python
    # would run it; python3.exe (anaconda) is used because bare `python` on
    # this machine is a different install and may not exist on PATH for a
    # task run outside an interactive shell.
    $python = (Get-Command python3).Source
    # Named $taskAction, not $action: PowerShell variable names are
    # case-insensitive, so $action would alias the -Action parameter above
    # (which carries [ValidateSet]) and the attribute re-validates on
    # assignment, throwing "not a valid value for the Action variable".
    $taskAction = New-ScheduledTaskAction -Execute $python -Argument "`"$Script`"" -WorkingDirectory $Repo
    $trigger = New-ScheduledTaskTrigger -Daily -At 19:00
    # No -RestartCount/-RestartInterval here, so the scheduler's default
    # (RestartCount = 0) applies: it never retries on any exit code, including
    # 1, which check_new_nikkes.py uses for "new nikke found", not failure.
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
    Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $trigger `
      -Settings $settings -Description 'Daily check for newly released NIKKEs' -Force | Out-Null
    "registered '$TaskName': daily 19:00, repo $Repo"
  }
  'unregister' {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    "removed '$TaskName'"
  }
  'status' {
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $t) { "'$TaskName' is not registered"; break }
    $i = Get-ScheduledTaskInfo -TaskName $TaskName
    "state      : $($t.State)"
    "last run   : $($i.LastRunTime)  result=$($i.LastTaskResult)"
    "next run   : $($i.NextRunTime)"
    "(LastTaskResult 0 = nothing new, 1 = new SSR found, 2 = the check failed)"
  }
}
