import os
from flask import Flask, request
from google.cloud import bigquery
from google.cloud import storage
from google.api_core.exceptions import NotFound

app = Flask(__name__)


@app.route("/", methods=["POST","GET"])
def entry():
    # Load the file into BigQuery
    client = bigquery.Client()
    bucket = os.environ.get('BUCKET')
    folder=os.environ.get('FOLDER')
    pattern=os.environ.get('PATTERN')
    delimiter=os.environ.get('DELIMITER')
    dataset=os.environ.get('DATASET')
    table_name=os.environ.get('TABLENAME')
    archive_folder=os.environ.get('ARCHIVEFOLDER')
    ################### values example for envirement variable #################
    print ("display Ingestion Configuration")
    print("bucket Name :", bucket)
    print("folder Name :", folder)
    print("pattern of files :", pattern)
    print("delimiter  :", delimiter)
    print("dataset Name :", dataset)
    print("table Name :",table_name)
    print("archive_folder Name :",archive_folder)
    ########## test if the envirement variables are set correctly: ##########
    if bucket is None:
        print("Error: bucket environment variable is not defined correctly")
        return ("Error bucket environment variable is not defined correctly.", 500)
    if table_name is None or folder is None or pattern is None or delimiter is None or dataset is None or archive_folder is None:
        print("Error:  environments variables are not defined correctly")
        return ("Error  environments variables are not defined correctly.", 500)
    if (len(delimiter)!=1):
        print("Error: Delimiter environment variable is not defined correctly")
        return ("Error: Delimiter environment variable is not defined correctly.", 500)

    #set destination file + uri of csv files
    table=dataset+"."+table_name
    uri="gs://"+bucket+"/"+folder+"/"+pattern+"*.csv"
    # get files from uri
    storage_client = storage.Client()
    bucket_initial = storage_client.get_bucket(bucket)
    blobs = bucket_initial.list_blobs(prefix=folder+'/'+pattern)
    if len(list(blobs))==0:
        print("Warning:  there is No files match the provided pattern")
        return ("Warning  there is No files match the provided pattern.", 200)
    try:
       client.get_dataset(dataset)  # Make an API request.
       print("Dataset {} already exists".format(dataset))
    except NotFound:
       print("Dataset {} is not found".format(dataset))
       return ("Error  there is No Dataset matchs the provided dataset variable.", 500)
    # Setup the job to append to the table if it already exists and to autodetect the schema
    job_config = bigquery.LoadJobConfig(
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    source_format=bigquery.SourceFormat.CSV,
    skip_leading_rows=1,
    autodetect=True
    )

    # Run the load job
    load_job = client.load_table_from_uri(uri, table, job_config=job_config)

    # Run the job synchronously and wait for it to complete
    load_job.result()

    print ("Loaded files located at ",bucket, " /",folder,"/")
    bucket_initial = storage_client.get_bucket(bucket)
    blobs = bucket_initial.list_blobs(prefix=folder+'/'+pattern)
    for i in blobs:
        bucket_initial.rename_blob(i, new_name=i.name.replace(folder+'/', archive_folder+'/archived_'))

    print ("Archives files to ",bucket, " /",archive_folder,"/")
    return (f"Loaded file located at {uri} into BQ table {table}", 200)
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
