# kmstool
Tool for using AWS KMS data keys to encrypt and decrypt larger files. Input and Output file can be local or s3 file paths.
# Requirements
Requires: boto3, pycrypto 

```pip install -r requirements.txt```

# Usage
For encrypting must have Key-Id 
Tool will only decrypt things that it has encrypted. 

encrypt: 
```kmstool.py -e --file myfiles.tar --output this.tar.enc --key_id <KMS Key-ID>```
```kmstool.py -e --file myfiles.tar --output s3://mybucket/my/key/path/this.tar.enc --key_id <KMS Key-ID>```
```kmstool.py -e --file s3://bucket/myfiles.tar --output s3://encrypted_bucket/my/key/path/this.tar.enc --key_id <KMS Key-ID>```

decrypt:
```kmstool.py -d --file this.tar.enc --output myfiles.tar```
```kmstool.py -d --file s3://mybucket/my/key/path/this.tar.enc --output myfiles.tar```
```kmstool.py -d --file s3://encrypted_bucket/my/key/path/this.tar.enc --output s3://mybucket/myfiles.tar```
