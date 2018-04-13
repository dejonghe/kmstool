#!/usr/bin/env python
from hashlib import md5
from Crypto.Cipher import AES
from Crypto import Random
from builtins import str
import sys
import six
import uuid
import base64

import boto3
from boto3 import client
from boto3.session import Session

from os import walk, path, makedirs, rmdir, remove
import tarfile
from os.path import join


class KmsTool(object):
    def __init__(self,
                 key_id=None,
                 key_spec='AES_256',
                 temp_dir='/var/tmp/kmstool',
                 profile=None,
                 region=None,
                 key_length=32,):
        self.key_id=key_id
        self.key_spec=key_spec
        self.key_length=key_length
        self.bs = AES.block_size
        self.temp_dir = '{}/{}/'.format(temp_dir.rstrip('/\\'), uuid.uuid4())
        try: 
            makedirs(self.temp_dir)
        except:
            self.rm_rf(self.temp_dir)
            makedirs(self.temp_dir)
        self.enc_file = join(self.temp_dir, 'file.enc')
        self.cipher_file = join(self.temp_dir, 'key.enc')
        self.session =  Session(profile_name=profile,region_name=region) 
        self.kms = self.session.client('kms')
        self.s3 = self.session.client('s3')


    # walk a directory structure and remove everything
    def rm_rf(self, path):
        for root, dirs, files in walk(path, topdown=False):
            # if dir is empty skip files
            for name in files:
                remove(join(root, name))
            for name in dirs:
                rmdir(join(root, name))
        rmdir(path)
    
    # make a big messy md5
    def derive_key_and_iv(self, salt, iv_length):
        d = d_i = b''
        while len(d) < self.key_length + iv_length:
            pre_hash = d_i + self.key + salt
            d_i = md5(pre_hash).digest()
            d += d_i
        return d[:self.key_length], d[self.key_length:self.key_length+iv_length]
    
    # encrypt reads and writes files
    # password is the kms data key
    # key lenght must not be more than 32
    def encrypt_file(self,in_file,out_file):
        salt = Random.new().read(self.bs - len('Salted__'))
        key, iv = self.derive_key_and_iv(salt, self.bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        salt_stash = b'Salted__' + salt
        if isinstance(salt_stash,str):
            salt_stash = bytes(salt_stash,'ascii')
        out_file.write(salt_stash)
        finished = False
        while not finished:
            chunk = in_file.read(1024 * self.bs)
            if len(chunk) == 0 or len(chunk) % self.bs != 0:
                padding_length = (self.bs - len(chunk) % self.bs) or self.bs
                if (sys.version_info > (3, 0)):
                    chunk += bytes([padding_length]) * padding_length
                else:
                    chunk += padding_length * chr(padding_length)
                finished = True
            out_file.write(cipher.encrypt(chunk))
    
    # decrypt reads and writes files
    # password is the kms data key
    # key lenght must not be more than 32
    def decrypt_file(self, in_file, out_file):
        salt = in_file.read(self.bs)[len('Salted__'):]
        key, iv = self.derive_key_and_iv(salt, self.bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        next_chunk = ''
        finished = False
        while not finished:
            chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * self.bs))
            if len(next_chunk) == 0:
                # Python 3 does not need the ord() its redundant and no reverse compatability 
                if (sys.version_info > (3, 0)):
                    padding_length = chunk[-1]
                else:
                    padding_length = ord(chunk[-1])
                chunk = chunk[:-padding_length]
                finished = True
            if isinstance(chunk,str):
                chunk = bytes(chunk,'ascii')
            out_file.write(chunk)

    def encrypt(self, source, dest):
        # get a data key from kms
        response = self.kms.generate_data_key(KeyId=self.key_id, KeySpec=self.key_spec)
        # key comes in as binary so we encode it
        self.key = base64.b64encode(response['Plaintext'])
        # this is the encrypted version we store with the data 
        self.ciphertext = response['CiphertextBlob']    
        if isinstance(source, six.string_types) and 's3://' in source:
            local_path = self.temp_dir + 'temp_file'
            self.s3_download(source, local_path)
        elif isinstance(source, six.string_types):
            local_path = source
        else:
            local_path = self.temp_dir + 'temp_file'
            with open(local_path, 'wb') as archive:
                archive.write(source.read())

        with open(local_path, 'rb') as in_file, open(self.enc_file, 'wb') as out_file:
            self.encrypt_file(in_file, out_file)
        with open(self.cipher_file, 'wb') as out_file:
            out_file.write(self.ciphertext)

        # tar up the encrypted file and the cipher text key
        if isinstance(dest, six.string_types) and 's3://' in dest:
            output_path = self.temp_dir + 'temp_output'
            self.tar_file(output_path)
            self.s3_upload(output_path, dest)
        elif isinstance(dest, six.string_types):
            self.tar_file(dest)
        else:
            output_path = self.temp_dir + 'temp_output'
            with open(self.enc_file, 'rb') as in_file, open(output_path, 'wb') as out_file:
                self.tar_file(output_path)
            with open(output_path, 'rb') as in_file:
                dest.write(in_file.read())

        self.rm_rf(self.temp_dir)

    def decrypt(self, source, dest):
        # Set local archive
        if isinstance(source, six.string_types) and 's3://' in source:
            local_path = self.temp_dir + 'temp_file'
            self.s3_download(source, local_path)
        elif isinstance(source, six.string_types):
            local_path = source
        else:
            local_path = self.temp_dir + 'temp_file'
            with open(local_path, 'wb') as archive:
                archive.write(source.read())

        # unpack tar file
        tar = tarfile.open(local_path)
        tar.extractall(self.temp_dir)
        tar.close()
        # read ciphertext key  
        with open(self.cipher_file, 'rb') as open_file:
            ciphertext = open_file.read()
        # decrypt via kms
        response = self.kms.decrypt(CiphertextBlob=ciphertext)
        # encode the binary key so it's the same as it was for encrypt
        self.key = base64.b64encode(response['Plaintext'])

        # open input file for reading, open an output file for s3 or file IO or a memory stream for memory IO
        if isinstance(dest, six.string_types) and 's3://' in dest:
            output_path = self.temp_dir + 'temp_output'
            with open(self.enc_file, 'rb') as in_file, open(output_path, 'wb') as out_file:
                self.decrypt_file(in_file, out_file)
            self.s3_upload(output_path, dest)
        elif isinstance(dest, six.string_types):
            with open(self.enc_file, 'rb') as in_file, open(dest, 'wb') as out_file:
                self.decrypt_file(in_file, out_file)
        else:
            with open(self.enc_file, 'rb') as in_file:
                self.decrypt_file(in_file, dest)

        self.rm_rf(self.temp_dir)

    def tar_file(self, output_file):
        with tarfile.open(output_file, "w") as tar:
            for name in [self.enc_file, self.cipher_file]:
                tar.add(name,arcname=path.split(name)[1])

    def s3_upload(self, orig, dest):
        dest_bucket = dest.split('/')[2]
        dest_key = '/'.join(dest.split('/')[3:])
        self.s3.upload_file(orig, dest_bucket, dest_key)

    def s3_download(self, orig, dest):
        orig_bucket = orig.split('/')[2]
        orig_key = '/'.join(orig.split('/')[3:])
        self.s3.download_file(orig_bucket, orig_key, dest)

