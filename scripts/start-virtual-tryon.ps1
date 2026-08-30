$ErrorActionPreference = "Stop"

$catVtonRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..\..\..\CatVTON-local")
)
$pythonPath = Join-Path $catVtonRoot ".venv\Scripts\python.exe"
$appPath = Join-Path $catVtonRoot "api_server.py"
$outputPath = Join-Path $catVtonRoot "resource\demo\output-local"
$cachePath = "D:\arena\.cache\huggingface-catvton"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Khong tim thay CatVTON local tai $catVtonRoot"
}

$env:HF_HOME = $cachePath
Set-Location -LiteralPath $catVtonRoot

& $pythonPath $appPath `
    --width 384 `
    --height 512 `
    --mixed_precision fp16 `
    --output_dir $outputPath
