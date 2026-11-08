param([switch]$Once)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($Once) { python -m scripts.container_metrics --once }
else { python -m scripts.container_metrics }
