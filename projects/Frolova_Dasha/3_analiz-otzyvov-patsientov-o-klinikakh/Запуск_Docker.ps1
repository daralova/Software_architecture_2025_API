param([ValidateRange(1024,65535)][int]$Port = 18013)
$ErrorActionPreference = 'Stop'
$sourceDir = $PSScriptRoot
$stageDir = Join-Path $env:TEMP ('clinic_reviews_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stageDir | Out-Null
Get-ChildItem -LiteralPath $sourceDir -Force | Where-Object { $_.Name -ne '__pycache__' -and $_.Extension -notin @('.docx','.db','.pyc') } | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $stageDir -Recurse -Force
}
$configPath = Join-Path $stageDir 'services.yml'
$config = [IO.File]::ReadAllText($configPath,[Text.Encoding]::UTF8).Replace('"8013:8013"', ('"{0}:8013"' -f $Port))
[IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($false))
Push-Location $stageDir
try {
    docker compose -p clinicreviews-lab -f services.yml up --build -d --wait
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose failed; see output above.' }
    Write-Host "API: http://127.0.0.1:$Port/docs"
    Write-Host "Staging: $stageDir"
    Write-Host "Stop: docker compose -p clinicreviews-lab -f `"$configPath`" down"
} finally { Pop-Location }
