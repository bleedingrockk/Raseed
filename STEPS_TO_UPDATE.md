gcloud builds submit . --tag $env:IMAGE_TAG

gcloud run deploy $env:SERVICE_NAME `
  --image $env:IMAGE_TAG `
  --platform managed `
  --region $env:GCR_REGION `
  --allow-unauthenticated