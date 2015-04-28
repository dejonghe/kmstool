# kmstool
Tool for using AWS KMS data keys to encrypt and decrypt larger files. 

# Requirements
Requires: boto3, pycrypto 

```pip install -r requirements.txt```

# Usage
For encrypting must have Key-Id 
Tool will only decrypt things that it has encrypted. 

encrypt: 
```kmstool.py -e --file myfiles.tar --output this.tar.enc --key_id <KMS Key-ID>```

decrypt:
```kmstool.py -d --file this.tar.enc --output myfiles.tar```

