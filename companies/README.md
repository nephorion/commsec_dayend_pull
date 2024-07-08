## Download from asx
```
https://www.asx.com.au/markets/trade-our-cash-market/directory
```

## Set the ENV variables
```
export REGION=australia-southeast1
export PROJECT_ID=stocks-427911
export SERVICE_NAME=commsec_dayend_pull
```

### Copy isin files
```
gcloud storage cp -r ./companies/*.csv gs://${PROJECT_ID}/companies
```

### Create the dataset
```
bq mk --location=${REGION} lookup
```

### Load 
```
bq load \
    --source_format=CSV \
    --schema=./companies/companies.json \
    --replace \
    --skip_leading_rows=1 \
    lookup.companies \
    gs://${PROJECT_ID}/companies/ASX_Listed_Companies_08-07-2024_02-38-29_AEST.csv
```
