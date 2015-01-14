#!/bin/python
from hashlib import md5
from Crypto.Cipher import AES
from Crypto import Random
import base64

import boto3
from boto3.session import Session

import sys
import datetime
import tarfile

from optparse import OptionParser
from ConfigParser import ConfigParser
import os
from os.path import expanduser

def get_profile(profile='default'):
    if profile != 'default':
        profile = 'profile %s' % profile
    home = expanduser("~")
    aws_creds = ConfigParser()
    aws_creds.read('%s/.aws/config' % home)
    try:
        return { 'aws_access_key_id': aws_creds.get(profile, 'aws_access_key_id'),
                 'aws_secret_access_key': aws_creds.get(profile, 'aws_secret_access_key'),
                 'region': aws_creds.get(profile, 'region') }
    except:
        return { 'region': aws_creds.get(profile, 'region') }

def connect(profile="default"):
    if profile == "default":
        kms = boto3.client('kms')
    else:
        profile = get_profile(profile)
        session = Session(aws_access_key_id=profile['aws_access_key_id'],
                  aws_secret_access_key=profile['aws_secret_access_key'],
                  region_name=profile['region']) 
        kms = session.client('kms')
    return kms

def derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = ''
    while len(d) < key_length + iv_length:
        d_i = md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]

def encrypt(in_file, out_file, password, key_length=32):
    bs = AES.block_size
    salt = Random.new().read(bs - len('Salted__'))
    key, iv = derive_key_and_iv(password, salt, key_length, bs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    out_file.write('Salted__' + salt)
    finished = False
    while not finished:
        chunk = in_file.read(1024 * bs)
        if len(chunk) == 0 or len(chunk) % bs != 0:
            padding_length = (bs - len(chunk) % bs) or bs
            chunk += padding_length * chr(padding_length)
            finished = True
        out_file.write(cipher.encrypt(chunk))

def decrypt(in_file, out_file, password, key_length=32):
    bs = AES.block_size
    salt = in_file.read(bs)[len('Salted__'):]
    key, iv = derive_key_and_iv(password, salt, key_length, bs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    next_chunk = ''
    finished = False
    while not finished:
        chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
        if len(next_chunk) == 0:
            padding_length = ord(chunk[-1])
            chunk = chunk[:-padding_length]
            finished = True
        out_file.write(chunk)


def main():
    usage = "usage: %prog [options] \nYou must specify to encrypt or decrypt.\nOutput will always output a tar file."
    parser = OptionParser(usage=usage)
    parser.add_option("-e","--encrypt", help="This encrypts the file", action="store_true", dest="encrypt")
    parser.add_option("-d","--decrypt", help="This decrypts the file", action="store_false", dest="encrypt")
    parser.add_option("-f","--file",  help="File to encrypt or decrypt")
    parser.add_option("-o","--output", help="Path to output file")
    parser.add_option("-k","--key_id", help="KMS Key-id")
    parser.add_option("-s","--key_spec", help="KMS KeySpec", default="AES_256")
    parser.add_option("-p","--profile", help="AWS Profile", default="default")
    (opts, args) = parser.parse_args()

    kms = connect(opts.profile)
    workingdir = "/var/tmp/kmstool/"
    os.mkdir(workingdir)
    enc_file = os.path.join(workingdir, 'file.enc')
    cipher_file = os.path.join(workingdir, 'key.enc')

    if opts.encrypt:  
        response = kms.generate_data_key(KeyId=opts.key_id, KeySpec=opts.key_spec)

        key = base64.b64encode(response['Plaintext'])
        ciphertext = response['CiphertextBlob']    
        with open(opts.file, 'rb') as in_file, open(enc_file, 'wb') as out_file:
            encrypt(in_file, out_file, key)
        with open(cipher_file, 'wb') as out_file:
            out_file.write(ciphertext)
        with tarfile.open(opts.output, "w") as tar:
            for name in [enc_file, cipher_file]:
                tar.add(name,arcname=os.path.split(name)[1])

    elif not opts.encrypt:
        tar = tarfile.open(opts.file)
        tar.extractall(workingdir)
        tar.close()
        with open(cipher_file, 'rb') as open_file:
            ciphertext = open_file.read()
        response = kms.decrypt(CiphertextBlob=ciphertext)
        key = base64.b64encode(response['Plaintext']) 
        with open(enc_file, 'rb') as in_file, open(opts.output, 'wb') as out_file:
            decrypt(in_file, out_file, key)

    for root, dirs, files in os.walk(workingdir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(workingdir)

if __name__ == '__main__':
    try: main()
    except: raise

