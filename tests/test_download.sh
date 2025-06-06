#!/bin/bash
# Download script for selected files
# Total files: 1

BUCKET=mosaic-fmri
FILES=(
    "sub-01_hw_20250605_173046.hdf5"
)

echo "Downloading 1 files from S3..."

for file in "${FILES[@]}"; do
    echo "Downloading $file..."
    aws s3 cp "s3://$BUCKET/$file" "./$file"
    if [ $? -eq 0 ]; then
        echo "✓ Successfully downloaded $file"
    else
        echo "✗ Failed to download $file"
    fi
done

echo "Download complete!"