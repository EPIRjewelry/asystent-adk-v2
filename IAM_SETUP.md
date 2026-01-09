# IAM Setup & Security for ADK Agent

Zgodnie z Fazą 2 Mapy Drogowej, wdrożenie dedykowanego Service Account (SA) jest kluczowe dla bezpieczeństwa.

## 1. Tworzenie Service Account

```bash
gcloud iam service-accounts create sa-adk-agent \
    --description="Service Account for ADK Agent v2 (Gemini + BigQuery)" \
    --display-name="ADK Agent Service Account"
```

## 2. Nadawanie Uprawnień (Least Privilege)

Należy nadać uprawnienia TYLKO do odczytu konkretnego datasetu BigQuery oraz uprawnienia do uruchamiania Jobów (zapytań).

### BigQuery Job User (na poziomie projektu)
Pozwala na uruchamianie zapytań (koszt obliczeniowy).

```bash
gcloud projects add-iam-policy-binding epir-adk-agent-v2-48a86e6f \
    --member="serviceAccount:sa-adk-agent@epir-adk-agent-v2-48a86e6f.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"
```

### BigQuery Data Viewer (na poziomie datasetu)
Pozwala tylko na odczyt danych z datasetu analitycznego. NIE pozwala na dostęp do innych datasetów w projekcie.

```bash
# Uwaga: To polecenie wymaga bq command-line tool lub wykonania przez Console
bq add-iam-policy-binding \
    --member="serviceAccount:sa-adk-agent@epir-adk-agent-v2-48a86e6f.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataViewer" \
    epir-adk-agent-v2-48a86e6f:analytics_435783047
```

### Vertex AI User
Pozwala na korzystanie z modeli Gemini.

```bash
gcloud projects add-iam-policy-binding epir-adk-agent-v2-48a86e6f \
    --member="serviceAccount:sa-adk-agent@epir-adk-agent-v2-48a86e6f.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

## 3. Implementacja w Cloud Run

Podczas wdrażania serwisu do Cloud Run, należy wskazać ten konkretny SA:

```bash
gcloud run deploy adk-agent-v2 \
    --image gcr.io/epir-adk-agent-v2-48a86e6f/app-image \
    --service-account sa-adk-agent@epir-adk-agent-v2-48a86e6f.iam.gserviceaccount.com \
    --region europe-west1
```
