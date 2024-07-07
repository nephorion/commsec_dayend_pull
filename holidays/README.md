## Download the public holidays dataset
https://data.gov.au/data/dataset/australian-holidays-machine-readable-dataset

Note: Some of the data is not in the correct format or the filename is in a weird format.
Note: 2019 had an extra column which had to be removed.

## Set the ENV variables
```
export REGION=australia-southeast1
export PROJECT_ID=stocks-427911
export SERVICE_NAME=commsec_dayend_pull
```

### Copy holiday files
```
gcloud storage cp -r ./holidays/*.csv gs://${PROJECT_ID}/holidays
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