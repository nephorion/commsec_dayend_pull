## Download from asx
```
https://www.asx.com.au/markets/market-resources/isin-services
```

## Save as csv
Open with Excel
Save as csv with the name ISIN-YYYYMMDD.csv
The YYYYMMDD is found in the file 
Remove the lines between the data and the header


## Set the ENV variables
```
export REGION=australia-southeast1
export PROJECT_ID=stocks-427911
export SERVICE_NAME=commsec_dayend_pull
```

### Copy isin files
```
gcloud storage cp -r ./isin/*.csv gs://${PROJECT_ID}/isin
```

### Create the dataset
```
bq mk --location=${REGION} lookup
```

### Load 
```
bq load \
    --source_format=CSV \
    --schema=./isin/isin.json \
    --replace \
    --skip_leading_rows=1 \
    lookup.isin \
    gs://${PROJECT_ID}/isin/ISIN-20240705.csv
```