<#
.SYNOPSIS
Show a Windows toast notification.

.DESCRIPTION
Used by scripts/check_new_nikkes.py to surface its result. Uses the WinRT
notification API directly, so no BurntToast module install is required
(verified on this machine 2026-07-21). Toasts are the signal for the daily
scheduled check: silence means nothing was found.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts/notify_toast.ps1 -Title "신규 니케" -Body "Alpha, Bravo"
#>
param(
  [Parameter(Mandatory = $true)][string]$Title,
  [Parameter(Mandatory = $true)][string]$Body
)

$ErrorActionPreference = 'Stop'

[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null

# PowerShell's own AUMID: a registered app id is required, and this one always
# exists on Windows, so the toast needs no shortcut of our own.
$AppId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'

$esc = {
  param($s)
  $s.Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;')
}

$xml = @"
<toast><visual><binding template="ToastGeneric"><text>$(& $esc $Title)</text><text>$(& $esc $Body)</text></binding></visual></toast>
"@

$doc = New-Object Windows.Data.Xml.Dom.XmlDocument
$doc.LoadXml($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId).Show(
  (New-Object Windows.UI.Notifications.ToastNotification $doc)
)
