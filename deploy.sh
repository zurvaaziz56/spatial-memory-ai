#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "  Spatial Memory AI - 1-Command Google Cloud Run Deployer"
echo "=========================================================="

if [ -z "$GEMINI_API_KEY" ]; then
  read -p "Enter your GEMINI_API_KEY (from Google AI Studio): " GEMINI_API_KEY
fi

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
  echo "No active GCP project found. Listing available projects:"
  gcloud projects list
  read -p "Enter your Google Cloud Project ID: " PROJECT_ID
  gcloud config set project "$PROJECT_ID"
fi

echo "Enabling Cloud Run and Cloud Build APIs on project: $PROJECT_ID..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

echo "Deploying spatial-memory-ai to Google Cloud Run..."
gcloud run deploy spatial-memory-ai \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GEMINI_API_KEY=${GEMINI_API_KEY}"

echo "✅ Deployment complete! Copy the Service URL above into your Hack2skill submission."
