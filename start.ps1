# Start API (uvicorn) and Streamlit dashboard in parallel.
# Run from the project root:  .\start.ps1

$api = Start-Process -NoNewWindow -PassThru `
    -FilePath "uvicorn" `
    -ArgumentList "src.api.main:app", "--reload", "--port", "8000"

$dashboard = Start-Process -NoNewWindow -PassThru `
    -FilePath "streamlit" `
    -ArgumentList "run", "dashboard/app.py", "--server.port", "8501"

Write-Host "API      -> http://localhost:8000  (PID $($api.Id))"
Write-Host "Dashboard -> http://localhost:8501  (PID $($dashboard.Id))"
Write-Host "Ctrl+C para detener ambos procesos."

try {
    Wait-Process -Id $api.Id, $dashboard.Id
} finally {
    Stop-Process -Id $api.Id, $dashboard.Id -Force -ErrorAction SilentlyContinue
}
