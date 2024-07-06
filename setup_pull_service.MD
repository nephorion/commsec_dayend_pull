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

## Create the service account
```
gcloud iam service-accounts create ${SERVICE_NAME}_sa \
  --display-name="${SERVICE_NAME}_sa"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_NAME}_sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectCreator" \
  --role="roles/secretmanager.secretAccessor" \
  --role="roles/run.invoker" 
```

### Create the topic and allow the sa to publish to it
```
gcloud pubsub topics create ${SERVICE_NAME}_done
gcloud pubsub topics add-iam-policy-binding ${SERVICE_NAME}-done \
  --member=serviceAccount:=${SERVICE_NAME}_sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/pubsub.publisher
```


