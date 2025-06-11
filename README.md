# mosaic-website
This repository contains the frontend and backend code for MOSAIC data downloads and uploads to an Amazon S3 bucket. 

### Envirnment setup
```
conda create -n mosaic-website python=3.11
conda activate mosaic-website
cd /your/path/to/mosaic-website
pip install -r requirements.txt
```

### How to download data
Valid objects from the S3 bucket are listed in the 'download' page. Check the box beside each object to populate a download script for convenience. Copy the download script into a download.sh file and run it on your machine. Make sure you have enough storage.

### How to upload data
WIP

Upload your hdf5 file in the 'upload' page. The backend will run it through a series of checks to make sure it follows the expected data format, safety, and transparency rules.

### Questions?
First check the FAQ page to see if your question is answered. Next, if the question is related to this project page itself (e.g., frontend or backend code, download bugs etc), raise a GitHub issue. If the question is related to the actual data that is downloaded, contact the "owner" for that data object and/or check the object's provided GitHub url.
