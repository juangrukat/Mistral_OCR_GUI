import boto3
from botocore.exceptions import NoCredentialsError
import os
from datetime import datetime, timedelta

class FileUploader:
    def __init__(self, aws_access_key, aws_secret_key, bucket_name):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        self.bucket_name = bucket_name
    
    def upload_file(self, file_path):
        """Upload file to S3 and return a pre-signed URL"""
        try:
            file_name = os.path.basename(file_path)
            object_name = f"temp/{datetime.now().strftime('%Y%m%d%H%M%S')}/{file_name}"
            
            # Upload the file
            self.s3_client.upload_file(file_path, self.bucket_name, object_name)
            
            # Generate a pre-signed URL that expires in 1 hour
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=3600
            )
            
            return url
        except NoCredentialsError:
            print("AWS credentials not available")
            return None
        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            return None