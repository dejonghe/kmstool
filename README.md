# kmstool
Tool for using AWS KMS data keys to encrypt and decrypt larger files. Input and Output file can be local or s3 file paths.
If you were using this tool before May 2016, this was pre tag/release. That version is still available at v1.0.0. 

# Install 
kmstool is now able to be installed via pip. Download the latest release package and pip install it:

```pip install ~/Downloads/kmstool-1.3.2.tar.gz```

# Usage
For encrypting must have Key-Id 
Tool will only decrypt things that it has encrypted. 
Data can be piped to kmstool and input file omitted when encrypting. 
Omitting output file when decrypting with cause the decrypted data to be written to stdout.
Encrypt operations with no output will write the result to stdout as base64 encoded data.
Base64 encoded data can be piped from stdin for decrypt operations with no input file specified.

encrypt: 
```
kmstool.py -e --file myfiles.tar --output this.tar.enc --key_id <KMS Key-ID>
kmstool.py -e --file myfiles.tar --output s3://mybucket/my/key/path/this.tar.enc --key_id <KMS Key-ID>
kmstool.py -e --file s3://bucket/myfiles.tar --output s3://encrypted_bucket/this.tar.enc --key_id <KMS Key-ID>
echo 'password' | kmstool.py -e --output this.tar.enc --key_id <KMS Key-ID>
```

decrypt:
```
kmstool.py -d --file this.tar.enc --output myfiles.tar
kmstool.py -d --file s3://mybucket/my/key/path/this.tar.enc --output myfiles.tar
kmstool.py -d --file s3://encrypted_bucket/my/key/path/this.tar.enc --output s3://mybucket/myfiles.tar
kmstool.py -d --file s3://encrypted_bucket/my/key/path/this.tar.enc
```
help:
```
Usage: kmstool [options] 
You must specify to encrypt or decrypt.
Output will always output a tar file.

Options:
  -h, --help            show this help message and exit
  -e, --encrypt         This encrypts the file
  -d, --decrypt         This decrypts the file
  -f FILE, --file=FILE  File to encrypt or decrypt
  -o OUTPUT, --output=OUTPUT
                        Path to output file
  -k KEY_ID, --key_id=KEY_ID
                        KMS Key-id
  -s KEY_SPEC, --key_spec=KEY_SPEC
                        KMS KeySpec
  -p PROFILE, --profile=PROFILE
                        AWS Profile
  -r REGION, --region=REGION
                        Region
  -t TEMP, --temp=TEMP  Temp work dir, optional
```
