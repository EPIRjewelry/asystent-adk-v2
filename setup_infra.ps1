# Skrypt konfiguracji infrastruktury (IAM) dla ADK Agent
# Uruchom w terminalu PowerShell: .\setup_infra.ps1

$PROJECT_ID = "epir-adk-agent-v2-48a86e6f"
$SA_NAME = "sa-adk-agent"
$SA_EMAIL = "$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

Write-Host "--- KONFIGURACJA INFRASTRUKTURY JAM ---" -ForegroundColor Cyan

# 1. Konfiguracja projektu
gcloud config set project $PROJECT_ID

# 2. Tworzenie Service Account
Write-Host "Tworzenie Service Account: $SA_NAME..." -ForegroundColor Yellow
gcloud iam service-accounts create $SA_NAME `
    --description="Service Account for ADK Agent v2" `
    --display-name="ADK Agent Service Account"
# Ignorujemy błędy jeśli już istnieje (nie ma prostej flagi --if-not-exists w gcloud create)
if ($LASTEXITCODE -ne 0) {
    Write-Host "Info: Service Account prawdopodobnie już istnieje." -ForegroundColor Gray
}

# 3. Nadawanie Uprawnień
Write-Host "Nadawanie uprawnień..." -ForegroundColor Yellow

# BigQuery Job User (Project Level)
gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$SA_EMAIL" `
    --role="roles/bigquery.jobUser"

# Vertex AI User (Project Level)
gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$SA_EMAIL" `
    --role="roles/aiplatform.user"

# BigQuery Data Viewer (Dataset Level) - wymaga 'bq'
# Sprawdzamy czy mamy bq
if (Get-Command "bq" -ErrorAction SilentlyContinue) {
    Write-Host "Nadawanie uprawnień do datasetu (bq)..." -ForegroundColor Yellow
    bq add-iam-policy-binding `
        --member="serviceAccount:$SA_EMAIL" `
        --role="roles/bigquery.dataViewer" `
        "$PROJECT_ID`:analytics_435783047"
} else {
    Write-Warning "Brak narzędzia 'bq'. Nie można nadać uprawnień do datasetu automatycznie."
    Write-Warning "Wykonaj ręcznie w Cloud Shell: bq add-iam-policy-binding ..."
}

Write-Host "--- UKOŃCZONO SETUP INFRASTRUKTURY ---" -ForegroundColor Green
