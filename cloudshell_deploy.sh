#!/bin/bash
# Skrypt do uruchomienia w Google Cloud Shell
# Użycie: ./cloudshell_deploy.sh
# Automatycznie używa konta serwisowego: adk-vertex-agent@epir-adk-agent-v2-48a86e6f.iam.gserviceaccount.com

set -euo pipefail

PROJECT_ID="epir-adk-agent-v2-48a86e6f"
REGION="europe-west1"
SERVICE_NAME="asystent-adk-v2"
SA_EMAIL="adk-vertex-agent@epir-adk-agent-v2-48a86e6f.iam.gserviceaccount.com"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo "Service account to use: $SA_EMAIL"

# 1. Sync repo (pull latest changes from main)
echo "Pulling latest changes from origin/main..."
git pull origin main

# 2. Build image via Cloud Build
echo "Building container image via Cloud Build..."
gcloud config set project "$PROJECT_ID"
gcloud builds submit --tag "$IMAGE_NAME" .

# 3. Deploy to Cloud Run using the ORIGINAL service account
echo "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_NAME" \
  --platform managed \
  --region "$REGION" \
  --service-account "$SA_EMAIL" \
  --allow-unauthenticated --memory 1Gi --concurrency 80

# 4. Print service URL
echo ""
echo "Deployment successful!"
gcloud run services describe "$SERVICE_NAME" --region "$REGION" --platform managed --format 'value(status.url)'

echo ""
echo "If you need to grant BigQuery dataset access, run:"
echo "bq add-iam-policy-binding --member=\"serviceAccount:$SA_EMAIL\" --role=\"roles/bigquery.dataViewer\" $PROJECT_ID:analytics_435783047"