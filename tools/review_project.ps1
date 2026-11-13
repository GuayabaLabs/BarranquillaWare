param([switch]$RunTests)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Output "=== BarranquillaWare: auditoria rapida ==="
Write-Output "Raiz: $root"
Write-Output "`n--- Estado de cambios ---"
git status --short

Write-Output "`n--- Modulos principales ---"
foreach ($folder in @("core", "scenes", "microgames", "ui", "effects", "tests")) {
    $count = @(Get-ChildItem $folder -Recurse -Filter *.py -File -ErrorAction SilentlyContinue).Count
    Write-Output ("{0,-12} {1} archivos Python" -f $folder, $count)
}

Write-Output "`n--- Dependencias importadas ---"
Get-ChildItem core,scenes,microgames,ui,effects -Recurse -Filter *.py -File -ErrorAction SilentlyContinue |
    Select-String -Pattern '^\s*(from|import)\s+(pygame|numpy|PIL|moderngl|cv2|mediapipe)' |
    ForEach-Object { $_.Matches.Value.Trim() } | Sort-Object -Unique

Write-Output "`n--- Rutas absolutas sospechosas ---"
$absolute = Get-ChildItem *.py,core,scenes,microgames,ui,effects,tests,tools -Recurse -Filter *.py -File -ErrorAction SilentlyContinue |
    Select-String -Pattern '[A-Za-z]:\\|/Users/|/home/|\.gemini|\.codex' -ErrorAction SilentlyContinue
if ($absolute) { $absolute | Select-Object Path,LineNumber,Line } else { Write-Output "No se encontraron rutas sospechosas." }

Write-Output "`n--- Assets ---"
$assetCount = @(Get-ChildItem assets -Recurse -File -ErrorAction SilentlyContinue).Count
Write-Output "Assets encontrados: $assetCount"

Write-Output "`n--- Importacion principal ---"
python -c "import core.engine, scenes.main_menu, scenes.story_map, scenes.arcade_mode, scenes.free_play; print('Imports principales: OK')"

if ($RunTests) {
    Write-Output "`n--- Pruebas ---"
    $env:SDL_VIDEODRIVER = "dummy"
    $env:SDL_AUDIODRIVER = "dummy"
    python -m pytest -q
}

Write-Output "`nAuditoria terminada."
