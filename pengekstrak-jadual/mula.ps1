$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$appPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $appPython)) {
    $pythonCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        & $pythonCommand.Source -3 -m venv (Join-Path $PSScriptRoot '.venv')
    } else {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if (-not $pythonCommand) { throw 'Pasang Python 3.12 atau lebih baharu dahulu. Rujuk PANDUAN.md.' }
        & $pythonCommand.Source -m venv (Join-Path $PSScriptRoot '.venv')
    }
    if ($LASTEXITCODE -ne 0) { throw 'Persekitaran Python tidak dapat dicipta. Semak pemasangan Python.' }
}
& $appPython -c 'import sys; assert (3,11) <= sys.version_info[:2] < (3,15), "Gunakan Python 3.11 hingga 3.14; 3.12 disyorkan."'
if ($LASTEXITCODE -ne 0) { throw 'Versi Python belum disokong.' }
$requirementsFile = Join-Path $PSScriptRoot 'requirements.txt'
$fingerprint = (Get-FileHash -LiteralPath $requirementsFile -Algorithm SHA256).Hash
$marker = Join-Path $PSScriptRoot '.venv\kebergantungan.txt'
if (-not (Test-Path -LiteralPath $marker) -or (Get-Content -LiteralPath $marker -Raw).Trim() -ne $fingerprint) {
    Write-Host 'Memasang kebergantungan kali pertama. Sambungan Internet diperlukan...'
    & $appPython -m pip install -r $requirementsFile
    if ($LASTEXITCODE -ne 0) { throw 'Pemasangan tidak selesai. Semak Internet dan cuba MULA.bat semula.' }
    Set-Content -LiteralPath $marker -Value $fingerprint
}
$port = 8501
while ($port -lt 8520) {
    $probe = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $port)
    try { $probe.Start(); $probe.Stop(); break } catch { $probe.Stop(); $port++ }
}
if ($port -ge 8520) { throw 'Tiada port setempat tersedia antara 8501 dan 8519.' }
Write-Host "App akan dibuka pada http://127.0.0.1:$port"
Write-Host 'Biarkan tetingkap ini terbuka. Tekan Ctrl+C untuk menghentikan app.'
& $appPython -m streamlit run (Join-Path $PSScriptRoot 'app.py') --server.port $port --server.address 127.0.0.1 --server.headless false --browser.gatherUsageStats false
exit $LASTEXITCODE
