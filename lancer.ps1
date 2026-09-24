# Lance l'interface web Negolux (Windows / PowerShell 7)
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
    Write-Host "Création de l'environnement virtuel..." -ForegroundColor Cyan
    python -m venv .venv
    .\.venv\Scripts\python -m pip install -q --upgrade pip
}
# (Ré)installe les dépendances à la création du .venv et chaque fois que requirements.txt change
$installe = ".venv\requirements.installe.txt"
if (-not (Test-Path $installe) -or (Get-FileHash requirements.txt).Hash -ne (Get-FileHash $installe).Hash) {
    Write-Host "Installation des dépendances..." -ForegroundColor Cyan
    .\.venv\Scripts\python -m pip install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Échec de l'installation des dépendances." -ForegroundColor Red
        exit 1
    }
    Copy-Item requirements.txt $installe
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
