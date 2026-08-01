<#
.SYNOPSIS
Run RapiLab in development mode, where a saved file shows up in the browser
right away.

.DESCRIPTION
The packaged app (dist\RapiLab\RapiLab.exe) is a snapshot: it carries the
frontend that was bundled at build time, so seeing a UI change there means
rebuilding - and a running app cannot overwrite its own exe. Use this instead
while working on the UI.

It starts the two servers the app is made of, each in its own window:

  - FastAPI (backend)   http://127.0.0.1:8000
  - Vite    (frontend)  http://localhost:5173   <- open this one

Both must be up: Vite serves the page and forwards /api/* to the backend, so
with the backend down every request fails with ECONNREFUSED. Saving a frontend
file updates the open page by itself; backend files are picked up by uvicorn's
reloader.

The packaged app can stay open at the same time - it listens on 41573+, not on
these ports.

To stop: close the two windows, or press Ctrl+C in each.

Messages here are English on purpose: this console is cp949, which mangles
Korean written in a UTF-8 script file.

.PARAMETER NoBrowser
Skip opening the browser.

.PARAMETER BackendPort
Backend port. Defaults to 8000, which is what the Vite proxy and the sync
bookmarklet both expect - change it only if something else already holds it,
and expect the bookmarklet not to find a dev app on another port.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 -NoBrowser
#>
param(
  [switch]$NoBrowser,
  [int]$BackendPort = 8000
)

$ErrorActionPreference = 'Stop'

$Repo = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Repo 'backend'
$Frontend = Join-Path $Repo 'frontend'

# Anaconda, not whatever `python` resolves to: the bare 3.14 on PATH has none
# of the project's dependencies.
$Python = 'C:\Users\fienn\anaconda3\python.exe'
$VitePort = 5173

function Assert-Path($Path, $What) {
  if (-not (Test-Path $Path)) {
    Write-Host "Missing: $What" -ForegroundColor Red
    Write-Host "  looked for: $Path"
    exit 1
  }
}

function Get-PortOwner($Port) {
  $conn = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
  if (-not $conn) { return $null }
  $ownerPid = $conn[0].OwningProcess
  $proc = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
  if ($proc) {
    return @{ Name = $proc.ProcessName; Pid = $ownerPid; Alive = $true }
  }
  # A listening socket whose process is gone: the backend spawns simulation
  # workers with multiprocessing, and a worker that outlives its parent keeps
  # the inherited socket handle open. taskkill on the reported PID reports
  # "process not found" while the port stays busy - the worker is what has to
  # go.
  return @{ Name = 'a process that no longer exists'; Pid = $ownerPid; Alive = $false }
}

Assert-Path $Python 'Python (anaconda)'
Assert-Path $Backend 'backend folder'
Assert-Path (Join-Path $Frontend 'node_modules') 'frontend deps (run npm install in frontend first)'

foreach ($p in @($BackendPort, $VitePort)) {
  $owner = Get-PortOwner $p
  if ($owner) {
    Write-Host "Port $p is held by $($owner.Name) (PID $($owner.Pid))." -ForegroundColor Yellow
    if (-not $owner.Alive) {
      Write-Host "  An orphaned worker from an earlier run is still holding the socket."
      Write-Host "  Find it and stop it:"
      Write-Host "    Get-CimInstance Win32_Process -Filter `"Name LIKE '%python%'`" | Select ProcessId, CommandLine"
      Write-Host "    Stop-Process -Id <that id> -Force"
    } elseif ($owner.Name -like '*python*' -or $owner.Name -like '*node*') {
      Write-Host "  That looks like this script already running. Close its window and retry."
    }
    exit 1
  }
}

# Separate windows so the two logs stay apart and either server can be
# restarted without touching the other.
Write-Host "Starting backend on $BackendPort..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location '$Backend'; & '$Python' -m uvicorn app.api:app --port $BackendPort --reload"
)

Write-Host "Starting frontend on $VitePort..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location '$Frontend'; npm run dev"
)

if (-not $NoBrowser) {
  # Opening before Vite has the port gives a blank page, so wait for a reply.
  Write-Host "Waiting for the servers to answer..." -ForegroundColor Cyan
  $deadline = (Get-Date).AddSeconds(30)
  $ready = $false
  while ((Get-Date) -lt $deadline) {
    try {
      Invoke-WebRequest -Uri "http://localhost:$VitePort/" -UseBasicParsing -TimeoutSec 2 | Out-Null
      $ready = $true
      break
    } catch {
      Start-Sleep -Milliseconds 400
    }
  }
  if ($ready) {
    Start-Process "http://localhost:$VitePort/"
  } else {
    Write-Host "Nothing answered within 30s - check the two windows that just opened." -ForegroundColor Yellow
    Write-Host "  Open it yourself once it is up: http://localhost:$VitePort/"
  }
}

Write-Host ""
Write-Host "Open http://localhost:$VitePort/ in your browser." -ForegroundColor Green
Write-Host "Saving a file refreshes the page. To stop, close the two windows."
