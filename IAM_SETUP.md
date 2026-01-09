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

## Co zrobić jeśli utworzono inny Service Account przez pomyłkę?

Jeżeli podczas wcześniejszego procesu wdrożenia został utworzony lub użyty inny Service Account (np. `sa-adk-agent@...` zamiast oczekiwanego `sa-original@...`), masz dwie bezpieczne opcje:

1) Przełączyć Cloud Run na pierwotny (oczekiwany) Service Account — rekomendowane, jeśli masz katalog z właściwymi uprawnieniami.

W Cloud Shell wykonaj:

```bash
# Sprawdź aktualny Service Account używany przez usługę Cloud Run
gcloud run services describe <SERVICE_NAME> --region <REGION> --format 'value(spec.template.spec.serviceAccountName)'

# Przełącz serwis na oryginalny Service Account
gcloud run services update <SERVICE_NAME> \
    --region <REGION> \
    --service-account "sa-original@<PROJECT_ID>.iam.gserviceaccount.com"
```

2) Nadać brakujące uprawnienia nowemu (już utworzonemu) Service Account, jeśli wolisz go zatrzymać:

```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
    --member="serviceAccount:sa-adk-agent@<PROJECT_ID>.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"

bq add-iam-policy-binding \
    --member="serviceAccount:sa-adk-agent@<PROJECT_ID>.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataViewer" \
    <PROJECT_ID>:analytics_435783047
```

Jeżeli chcesz usunąć błędny Service Account po migracji:

```bash
gcloud iam service-accounts delete sa-adk-agent@<PROJECT_ID>.iam.gserviceaccount.com
```

## Deploy z Cloud Shell (zalecane)

Umieściłem w repo skrypt `cloudshell_deploy.sh` — uruchom go z Cloud Shell, podając oryginalny Service Account, aby deployment wykonywał się z użyciem właściwego identity i uprawnień.

Przykład w Cloud Shell:

```bash
chmod +x cloudshell_deploy.sh
./cloudshell_deploy.sh epir-adk-agent-v2-48a86e6f europe-west1 asystent-adk-v2 sa-original@epir-adk-agent-v2-48a86e6f.iam.gserviceaccount.com
```

Po uruchomieniu skryptu Cloud Build zbuduje obraz i wdroży usługę Cloud Run z podanym Service Account.

---
Jeżeli chcesz, mogę:
- przygotować polecenia, aby zamienić Service Account w Cloud Run na wskazany przez Ciebie (wykonam to z Twojego Cloud Shell lub wskażesz oryginalny email SA),
- lub przygotować instrukcję usuwania błędnego SA po potwierdzeniu, że wszystko działa.

