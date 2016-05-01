#!/usr/bin/env python2.7
from hashlib import md5
from Crypto.Cipher import AES
from Crypto import Random
import base64

import boto3
from boto3 import client
from boto3.session import Session

from optparse import OptionParser
from ConfigParser import ConfigParser
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
        with open(self.input_file, 'rb') as in_file, open(self.enc_file, 'wb') as out_file:
            self.encrypt_file(in_file, out_file)
        with open(self.cipher_file, 'wb') as out_file:
            out_file.write(self.ciphertext)
        # tar up the encrypted file and the ciphertext key
        with tarfile.open(self.output_file, "w") as tar:
            for name in [self.enc_file, self.cipher_file]:
                tar.add(name,arcname=path.split(name)[1])
        self.rm_rf(self.temp_dir)

    def decrypt(self):
        # unpack tar file
        tar = tarfile.open(self.input_file)
        tar.extractall(self.temp_dir)
        tar.close()
        # read ciphertext key  
        with open(self.cipher_file, 'rb') as open_file:
            ciphertext = open_file.read()
        # decrypt via kms
        response = self.kms.decrypt(CiphertextBlob=ciphertext)
        # encode the binary key so it's the same as it was for encrypt
        self.key = base64.b64encode(response['Plaintext']) 
        with open(self.enc_file, 'rb') as in_file, open(self.output_file, 'wb') as out_file:
            self.decrypt_file(in_file, out_file)
        self.rm_rf(self.temp_dir)

def main():
    # Help file and options
    usage = "usage: %prog [options] \nYou must specify to encrypt or decrypt.\nOutput will always output a tar file."
    parser = OptionParser(usage=usage)
    parser.add_option('-e','--encrypt', help='This encrypts the file', action='store_true', dest='encrypt')
    parser.add_option('-d','--decrypt', help='This decrypts the file', action='store_false', dest='encrypt')
    parser.add_option('-f','--file',  help='File to encrypt or decrypt')
    parser.add_option('-o','--output', help='Path to output file')
    parser.add_option('-k','--key_id', help='KMS Key-id')
    parser.add_option('-s','--key_spec', help='KMS KeySpec', default='AES_256')
    parser.add_option('-p','--profile', help='AWS Profile', default='default')
    parser.add_option('-r','--region', help='Region', default=None)
    parser.add_option('-t','--temp', help='Temp work dir, optional', default='/var/tmp/kmstool/')
    (opts, args) = parser.parse_args()

    # init kms
    tool = kmstool(input_file=opts.file,
                      output_file=opts.output,
                      key_id=opts.key_id,
                      key_spec=opts.key_spec,
                      temp_dir=opts.temp,
                      profile=opts.profile,
                      region=opts.region)

    if opts.encrypt:  
        tool.encrypt()
    elif not opts.encrypt:
        tool.decrypt()

if __name__ == '__main__':
    try: main()
    except: raise
