## Set the ENV variables
```
export REGION=australia-southeast1
export PROJECT_ID=stocks-427911
export SERVICE_NAME=commsec-dayend-pull
gcloud config unset auth/access_token_file
gcloud auth application-default set-quota-project ${PROJECT_ID} 
gcloud auth application-default login
gcloud config set project ${PROJECT_ID}
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
gcloud iam service-accounts create ${SERVICE_NAME}-sa \
  --display-name="${SERVICE_NAME} Service Account"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor" 

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser" 
  
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer" 

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectCreator" 

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectUser" 


gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" 

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker" 

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter" 
  
  

```



### Create the topic and allow the sa to publish to it
```
gcloud pubsub topics create ${SERVICE_NAME}-done
gcloud pubsub topics add-iam-policy-binding ${SERVICE_NAME}-done \
  --member=serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/pubsub.publisher
```

### Create the docker repository
```
gcloud services enable artifactregistry.googleapis.com
gcloud artifacts repositories create ${PROJECT_ID} \
    --repository-format=docker \
    --location=${REGION} \
    --description="Docker repository for ${PROJECT_ID}"
```

### Build the service
```
docker build . --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${PROJECT_ID}/${SERVICE_NAME}
gcloud auth configure-docker ${REGION}-docker.pkg.dev
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${PROJECT_ID}/${SERVICE_NAME}
```

### Deploy Service
```
gcloud run deploy ${SERVICE_NAME} \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${PROJECT_ID}/${SERVICE_NAME} \
  --platform=managed \
  --region=${REGION} \
  --no-allow-unauthenticated \
  --service-account=${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-env-vars=BUCKET=stocks-427911,TOPIC=commsec-dayend-pull-done,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},TZ=Australia/Sydney
```

### Get Service URL
```
export SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')
```

### Schedule the service
```
gcloud services enable cloudscheduler.googleapis.com
gcloud scheduler jobs create http ${SERVICE_NAME}-job \
    --schedule="0 20 * * *" \
    --time-zone="Australia/Sydney" \
    --http-method=GET \
    --uri=${SERVICE_URL}/backfill/at/today \
    --oidc-service-account-email=${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --location=${REGION}
```


