## Set the ENV variables
```
export REGION=australia-southeast1
export PROJECT_ID=stocks-427911
export SERVICE_NAME=commsec_dayend_pull
```

## Create the bucket
```
gcloud storage buckets create gs://${PROJECT_ID} \
  --location=${REGION} \
  --soft-delete-duration=0
```

## Create the bq dataset and tables
```
bq mk --location=${REGION} data
bq mk --table data.raw_eod raw_eod_schema.json
```

## Create the service account
```
gcloud iam service-accounts create ${SERVICE_NAME}_sa \
  --display-name="${SERVICE_NAME} Service Account"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_NAME}_sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectCreator" \
  --role="roles/secretmanager.secretAccessor" \
  --role="roles/run.invoker"  \
  --role="roles/bigquery.dataViewer" \
  --role="roles/bigquery.dataEditor" 
```

### Create the topic and allow the sa to publish to it
```
gcloud pubsub topics create ${SERVICE_NAME}_done
gcloud pubsub topics add-iam-policy-binding ${SERVICE_NAME}-done \
  --member=serviceAccount:=${SERVICE_NAME}_sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/pubsub.publisher
```

### Create the docker repository
```
gcloud services enable artifactregistry.googleapis.com
gcloud artifacts repositories create ${PROJECT_ID} \
    --repository-format=docker \
    --description="Docker repository for ${PROJECT_ID}"
```

### Build the service
```
gcloud auth configure-docker ${REGION}.pkg.dev
gcloud builds submit --tag gcr.io/${PROJECT-ID}/${SERVICE_NAME}
```

### Deploy Service
```
gcloud run deploy ${SERVICE_NAME} \ 
  --image gcr.io/${PROJECT-ID}/${SERVICE_NAME} \
  --platform managed \ 
  --region ${REGION} \ 
  --allow-unauthenticated \
  --service-account ${SERVICE_NAME}_sa@${PROJECT_ID}.iam.gserviceaccount.com
```

### Deploy Service
```
export SERVICE_URL=gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)'
```

### Schedule the service
```
gcloud scheduler jobs create http ${SERVICE_NAME} \
    --schedule="0 20 * * *" \
    --time-zone="Australia/Sydney" \
    --http-method=GET \
    --uri=${SERVICE_URL} \
    --oidc-service-account-email=${SERVICE_NAME}_sa@${PROJECT_ID}.iam.gserviceaccount.com
```


