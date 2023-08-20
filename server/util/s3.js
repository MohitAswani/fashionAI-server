const fs = require('fs');

const S3 = require('aws-sdk/clients/s3');

const region = process.env.AWS_BUCKET_REGION;

const bucketName = process.env.AWS_BUCKET_NAME;

const accessKey = process.env.AWS_ACCESS_KEY_ID;

const secretAccessKey = process.env.AWS_SECRET_ACCESS_KEY;

const s3 = new S3({
    region,
    accessKey,
    secretAccessKey
});

// Download a file

exports.getFileStream = (fileKey) => {
    const downloadParams = {
        Key: fileKey,
        Bucket: bucketName
    }

    console.log(fileKey);

    return s3.getObject(downloadParams).createReadStream();
}