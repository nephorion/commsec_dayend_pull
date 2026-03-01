## Call the service 

```
export REGION=australia-southeast1
export PROJECT_ID=stocks-427911
export SERVICE_NAME=commsec-dayend-pull

export SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format "value(status.url)")
export IDENTITY_TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer ${IDENTITY_TOKEN}" ${SERVICE_URL}
```