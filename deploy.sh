#!/bin/bash

gcloud app deploy app.yaml --version current
gcloud storage rm -r $(gcloud storage buckets list --uri | rev | cut -d / -f 1 | rev | sed 's|^|gs://|')
