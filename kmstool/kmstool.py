#!/usr/bin/env python2.7
from hashlib import md5
from Crypto.Cipher import AES
from Crypto import Random
import base64

import boto3
from boto3 import client
from boto3.session import Session

from os import walk, path, mkdir, rmdir, remove
import tarfile
from os.path import join

class kmstool(object):
    def __init__(self,
                 input_file=None,
                 output_file=None,
                 key_id=None,
                 key_spec='AES_256',
                 temp_dir='/var/tmp/kmstool',
                 profile='default',
                 region=None,
                 key_length=32):
        self.input_file = input_file
        self.output_file = output_file
        self.key_id=key_id
        self.key_spec=key_spec
        self.key_length=key_length
        self.bs = AES.block_size
        self.temp_dir = temp_dir
        self.profile=profile
        self.region=region
        try: 
            mkdir(self.temp_dir)
        except:
            self.rm_rf(self.temp_dir)
            mkdir(self.temp_dir)
        self.enc_file = join(self.temp_dir, 'file.enc')
        self.cipher_file = join(self.temp_dir, 'key.enc')
        self.session = self.connect()
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
    
    # create a session with profile optional region
    def connect(self):
        if self.region == None: 
            session = Session(profile_name=self.profile) 
        else:
            session = Session(profile_name=self.profile,region_name=self.region) 
        return session
    
    # make a big messy md5
    def derive_key_and_iv(self, salt, iv_length):
        d = d_i = ''
        while len(d) < self.key_length + iv_length:
            d_i = md5(d_i + self.key + salt).digest()
            d += d_i
        return d[:self.key_length], d[self.key_length:self.key_length+iv_length]
    
    # encrypt reads and writes files
    # password is the kms data key
    # key lenght must not be more than 32
    def encrypt_file(self,in_file,out_file):
        salt = Random.new().read(self.bs - len('Salted__'))
        key, iv = self.derive_key_and_iv(salt, self.bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        out_file.write('Salted__' + salt)
        finished = False
        while not finished:
            chunk = in_file.read(1024 * self.bs)
            if len(chunk) == 0 or len(chunk) % self.bs != 0:
                padding_length = (self.bs - len(chunk) % self.bs) or self.bs
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
                padding_length = ord(chunk[-1])
                chunk = chunk[:-padding_length]
                finished = True
            out_file.write(chunk)

    def encrypt(self):
        # get a data key from kms
        response = self.kms.generate_data_key(KeyId=self.key_id, KeySpec=self.key_spec)
        # key comes in as binary so we encode it
        self.key = base64.b64encode(response['Plaintext'])
        # this is the encrypted version we store with the data 
        self.ciphertext = response['CiphertextBlob']    
        if 's3://' in self.input_file:
            local_path = self.temp_dir + 'temp_file'
            self.s3_download(self.input_file, local_path)
        else:
            local_path = self.input_file
        with open(local_path, 'rb') as in_file, open(self.enc_file, 'wb') as out_file:
            self.encrypt_file(in_file, out_file)
        with open(self.cipher_file, 'wb') as out_file:
            out_file.write(self.ciphertext)
        # tar up the encrypted file and the ciphertext key
        if 's3://' in self.output_file:
            output_path = self.temp_dir + 'temp_output'
            self.tar_file(output_path)
            self.s3_upload(output_path, self.output_file)
        else:
            self.tar_file(self.output_file)
        self.rm_rf(self.temp_dir)

    def decrypt(self):
        if 's3://' in self.input_file:
            local_path = self.temp_dir + 'temp_file'
            self.s3_download(self.input_file, local_path)
        else:
            local_path = self.input_file
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
        if 's3://' in self.output_file:
            output_path = self.temp_dir + 'temp_output'
            with open(self.enc_file, 'rb') as in_file, open(output_path, 'wb') as out_file:
                self.decrypt_file(in_file, out_file)
            self.s3_upload(output_path, self.output_file)
        else:
            with open(self.enc_file, 'rb') as in_file, open(self.output_file, 'wb') as out_file:
                self.decrypt_file(in_file, out_file)
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

