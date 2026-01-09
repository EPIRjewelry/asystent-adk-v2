# Skrypt konfiguracyjny deploymentu dla Google Cloud Run
# Uruchom w terminalu PowerShell: .\deploy.ps1

$PROJECT_ID = "epir-adk-agent-v2-48a86e6f"
$REGION = "europe-west1"
$SERVICE_NAME = "asystent-adk-v2"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"
$SERVICE_ACCOUNT = "adk-vertex-agent@$PROJECT_ID.iam.gserviceaccount.com"

Write-Host "--- ROZPOCZYNANIE DEPLOYMENTU ADK AGENT V2 ---" -ForegroundColor Cyan
Write-Host "Projekt: $PROJECT_ID"
Write-Host "Region: $REGION"
Write-Host "Service: $SERVICE_NAME"
Write-Host "Service Account: $SERVICE_ACCOUNT"
Write-Host "----------------------------------------------"

# 1. Konfiguracja projektu
Write-Host "Konfigurowanie projektu gcloud..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID

# 2. Budowanie obrazu (Cloud Build)
Write-Host "Budowanie obrazu Dockera w Cloud Build..." -ForegroundColor Yellow
gcloud builds submit --tag $IMAGE_NAME .

if ($LASTEXITCODE -ne 0) {
    Write-Error "Błąd podczas budowania obrazu. Przerywam."
    exit 1
}

# 3. Deployment do Cloud Run
Write-Host "Deployowanie do Cloud Run..." -ForegroundColor Yellow
# Uwaga: --allow-unauthenticated pozwala na publiczny dostęp (dla demo). 
# W produkcji usuń tę flagę lub skonfiguruj IAP.
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_NAME `
    --platform managed `
    --region $REGION `
    --service-account $SERVICE_ACCOUNT `
    --allow-unauthenticated `
    --memory 1Gi `
    --concurrency 80

if ($LASTEXITCODE -eq 0) {
    Write-Host "--- SUKCES! Aplikacja wdrożona. ---" -ForegroundColor Green
    gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)'
} else {
    Write-Error "Błąd podczas deploymentu."
}
