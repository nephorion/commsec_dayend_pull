### Copy holiday files
```
gcloud storage cp -r ./holidays gs://${PROJECT_ID}/holidays
```

### Create the dataset
```
bq mk --location=${REGION} lookup
```

### Load 
```
bq load \
    --source_format=CSV \
    --autodetect \
    --replace \
    lookup.holidays \
    gs://${PROJECT_ID}/holidays/*.csv
```