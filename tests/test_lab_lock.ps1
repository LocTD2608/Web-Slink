$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$mutex=[System.Threading.Mutex]::new($false,'Local\CourseRegistrationLabRunner')
if (-not $mutex.WaitOne(0)) { throw 'Test requires an idle lab runner' }
try {
  $ErrorActionPreference='Continue'
  $output=& powershell.exe -NoProfile -File "$root/scripts/lab.ps1" -Action Verify 2>&1
  $code=$LASTEXITCODE
  $ErrorActionPreference='Stop'
  if ($code -eq 0 -or ($output -join ' ') -notmatch 'Another lab command is running') {
    throw 'Concurrent invocation was not rejected by the whole-run lock'
  }
  Write-Output 'PASS: concurrent lab command rejected before Docker access'
} finally {
  $mutex.ReleaseMutex()
  $mutex.Dispose()
}
