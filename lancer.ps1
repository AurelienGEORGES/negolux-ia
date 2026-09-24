# Lance l'interface web Negolux (Windows / PowerShell 7)
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
    Write-Host "Création de l'environnement virtuel..." -ForegroundColor Cyan
    python -m venv .venv
    .\.venv\Scripts\python -m pip install -q --upgrade pip
    .\.venv\Scripts\python -m pip install -q -r requirements.txt
}
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Fichier .env créé : renseigne MCP_API_KEY puis relance." -ForegroundColor Yellow
    exit 1
}
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "CLI Claude Code introuvable : l'onglet Assistant ne fonctionnera pas (l'explorateur MCP oui)." -ForegroundColor Yellow
}
.\.venv\Scripts\python -m streamlit run app.py --server.address 127.0.0.1
