param(
  [ValidateSet('Start','Smoke','Benchmark','Sustained','Verify','Recover','Stop')][string]$Action='Start',
  [ValidateSet('Both','Postgres','RedisQueue')][string]$Mode='RedisQueue',
  [int]$VUs=3000
)
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force artifacts/metrics,artifacts/benchmarks | Out-Null
function DC {
  $previous=$ErrorActionPreference
  $ErrorActionPreference='Continue'
  try {
    & docker compose @args 2>&1 | ForEach-Object { "$_" }
    $code=$LASTEXITCODE
  } finally { $ErrorActionPreference=$previous }
  if ($code -ne 0) { throw "docker compose failed ($code): $args" }
}
function Use-Mode([string]$Selected) {
  $env:REGISTRATION_MODE=$Selected
  DC up -d --wait fastapi-node-1 fastapi-node-2 worker nginx
  DC restart nginx
  DC up -d --wait --no-deps nginx
}
function Trial([string]$Selected,[string]$Run,[int]$Users=500,[int]$Iterations=6) {
  Use-Mode $Selected
  DC exec -T fastapi-node-1 python -m scripts.benchmark prepare --mode $Selected
  DC --profile tools run --rm -e "RUN_ID=$Run" -e "VUS=$Users" -e "ITERATIONS=$Iterations" k6 run --out experimental-prometheus-rw /scripts/scenarios/flash_sale_test.js
  $expected=[Math]::Min(60,$Users*$Iterations)
  DC exec -T fastapi-node-1 python -m scripts.benchmark verify --mode $Selected --run-id $Run --expected $expected
}
switch ($Action) {
  Start {
    DC build
    DC stop nginx fastapi-node-1 fastapi-node-2 worker
    DC up -d --wait postgres redis rabbitmq
    DC run --rm --no-deps fastapi-node-1 python -m scripts.init_db
    DC run --rm --no-deps fastapi-node-1 python -m scripts.warmup_cache
    DC --profile monitoring up -d --wait
    Write-Host 'App http://localhost:8088 | Grafana http://localhost:3001 (admin / lab-admin) | RedisInsight http://localhost:8001'
    Write-Host 'Run scripts/collect_container_metrics.ps1 in another terminal for container CPU/RAM/network.'
  }
  Smoke {
    $selected=if($Mode -eq 'Postgres'){'postgres'}else{'redis_queue'}
    Trial $selected "smoke-$selected" 10 1
  }
  Benchmark {
    $modes=if($Mode -eq 'Both'){@('postgres','redis_queue')}elseif($Mode -eq 'Postgres'){@('postgres')}else{@('redis_queue')}
    foreach($selected in $modes){Trial $selected "warmup-$selected" 10 1}
    for($i=1;$i -le 3;$i++){
      $ordered=if($i % 2 -eq 0){@($modes | Sort-Object -Descending)}else{$modes}
      foreach($selected in $ordered){Trial $selected "$selected-$i"}
    }
    DC exec -T fastapi-node-1 python -m scripts.benchmark report
    docker version --format '{{json .}}' | Set-Content -Encoding utf8 artifacts/benchmarks/docker-version.json
    DC config | Set-Content -Encoding utf8 artifacts/benchmarks/compose-measured.yml
  }
  Sustained {
    $selected=if($Mode -eq 'Postgres'){'postgres'}else{'redis_queue'}
    Use-Mode $selected
    DC exec -T fastapi-node-1 python -m scripts.benchmark prepare --mode $selected
    DC --profile tools run --rm -e "VUS=$VUs" -e "RUN_ID=sustained-$selected" k6 run --out experimental-prometheus-rw /scripts/scenarios/sustained.js
    DC exec -T fastapi-node-1 python -m scripts.benchmark verify --mode $selected --run-id "sustained-$selected"
  }
  Verify { DC exec -T fastapi-node-1 python -m scripts.benchmark verify }
  Recover { DC run --rm --no-deps fastapi-node-1 python -m scripts.recover_operations --limit 1000 }
  Stop { DC --profile monitoring --profile tools stop }
}
