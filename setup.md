List projects
```
gcloud projects list
gcloud config get project
gcloud config set project stocks-427911
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

Ingest Data into BigQuery from Cloud Storage using gcloud
```
```


* Create a COMMSEC_PASSWORD secret
* Give the cloud run service accout access
* Create a cloudrun service account



