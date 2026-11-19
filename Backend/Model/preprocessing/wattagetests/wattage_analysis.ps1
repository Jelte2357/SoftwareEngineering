$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Push-Location $projectRoot


try {
$monitor = Start-Process -FilePath "nvidia-smi.exe" `
    -ArgumentList "--query-gpu=timestamp,index,power.draw,utilization.gpu,temperature.gpu --format=csv -l 1"  `
    -RedirectStandardOutput "$PSScriptRoot\gpu.csv" `
    -PassThru -NoNewWindow


try {
    python .\train_distilbert.py
}

finally {
    Stop-Process -Id $monitor.Id -ErrorAction SilentlyContinue
}
}
finally {
    Pop-Location
}