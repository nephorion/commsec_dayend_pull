$env:REGION = "australia-southeast1"
$env:PROJECT_ID = "stocks-427911"
$env:COMMON_PROJECT_ID = "common-429401"
$env:SERVICE_NAME = "commsec-dayend-pull"

gcloud components update
gcloud config unset auth/access_token_file
gcloud auth application-default set-quota-project $env:PROJECT_ID
gcloud auth application-default login
gcloud auth login
