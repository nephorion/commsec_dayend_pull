List projects
```
gcloud projects list
gcloud config get project
gcloud config set project stocks-427911
gcloud config set region australia-southeast1
```

For local dev
```
gcloud auth application-default set-quota-project stocks-427911
```

Create a bucket
```
gcloud storage buckets create gs://stocks-427911-dayend --location=AUSTRALIA-SOUTHEAST1
```

Copy Data
```
gsutil -m cp ..\..\data\dayend\*.txt gs://stocks-427911-dayend
gsutil -m rsync ..\..\data\dayend gs://stocks-427911-dayend
```

Create service account
```
gcloud iam service-accounts create commsec_dayend_pull_sa \
    --display-name="commsec_dayend_pull_sa"
```

Give the SA access to create objects
```
gcloud projects add-iam-policy-binding stocks-427911 \
    --member="serviceAccount:commsec_dayend_pull_sa@stocks-427911.iam.gserviceaccount.com" \
    --role="roles/storage.objectCreator"
```

Give the SA access to read secrets
```
gcloud projects add-iam-policy-binding stocks-427911 \
    --member="serviceAccount:commsec_dayend_pull_sa@stocks-427911.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```


Docker Build and Push
```
gcloud builds submit --tag gcr.io/stocks-427911/commsec_dayend_pull:v1.0 .
```

Deploy the service
```
gcloud run deploy commsec_dayend_pull \
    --image gcr.io/stocks-427911/commsec_dayend_pull:v1.0 \
    --service-account commsec_dayend_pull_sa@stocks-427911.iam.gserviceaccount.com \
    --platform managed \
    --region australia-southeast1 \
    --set-env-vars COMMSEC_USER=,BUCKET=stocks-427911-dayend
```

Get the service url
```
gcloud run services describe my-service \
    --platform managed \
    --region australia-southeast1 \
    --format 'value(status.url)'
```

Give the SA access to run cloud run job 
```
gcloud run services add-iam-policy-binding commsec-dayend-pull \
    --member="serviceAccount:commsec_dayend_pull_sa@stocks-427911.iam.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --region="australia-southeast1" \
    --platform managed
```

Setup the scheduler
```
gcloud scheduler jobs create http commsec-dayend-pull-schedule \
    --schedule="0 20 * * *" \
    --time-zone="Australia/Sydney" \
    --uri=<url>/today \
    --http-method=GET \
    --oidc-service-account-email=commsec_dayend_pull_sa@stocks-427911.iam.gserviceaccount.com
```

