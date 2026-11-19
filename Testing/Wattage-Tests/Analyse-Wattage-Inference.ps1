$projectRoot = (Resolve-Path "$PSScriptRoot\..\..\Backend\Backend (Flask Server)").Path
Push-Location $projectRoot


try {
    $monitor = Start-Process -FilePath "nvidia-smi.exe" `
        -ArgumentList "--query-gpu=timestamp,index,power.draw,utilization.gpu,temperature.gpu --format=csv -l 1"  `
        -RedirectStandardOutput "$PSScriptRoot\Inference-Session.csv" `
        -PassThru -NoNewWindow

    $server = Start-Process -FilePath "python" `
        -ArgumentList ".\app.py" `
        -PassThru -NoNewWindow

    try {
        python ./TEST_FLASK_SERVER.py
    }

    finally {
        Stop-Process -Id $monitor.Id -ErrorAction SilentlyContinue
        Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
    }
}
finally {
    Pop-Location
}