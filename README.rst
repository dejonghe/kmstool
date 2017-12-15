kmstool
=======

Tool for using AWS KMS data keys to encrypt and decrypt larger files.
Input and Output file can be local or s3 file paths. If you were using
this tool before May 2016, this was pre tag/release. That version is
still available at v1.0.0. # Requirements Requires: boto3, pycrypto

``pip install -r requirements.txt``

Usage
=====

For encrypting must have Key-Id Tool will only decrypt things that it
has encrypted.

encrypt:

::

    kmstool.py -e --file myfiles.tar --output this.tar.enc --key_id <KMS Key-ID>
    kmstool.py -e --file myfiles.tar --output s3://mybucket/my/key/path/this.tar.enc --key_id <KMS Key-ID>
    kmstool.py -e --file s3://bucket/myfiles.tar --output s3://encrypted_bucket/this.tar.enc --key_id <KMS Key-ID>

decrypt:

::

    kmstool.py -d --file this.tar.enc --output myfiles.tar
    kmstool.py -d --file s3://mybucket/my/key/path/this.tar.enc --output myfiles.tar
    kmstool.py -d --file s3://encrypted_bucket/my/key/path/this.tar.enc --output s3://mybucket/myfiles.tar

help:

::

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
