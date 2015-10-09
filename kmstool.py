#!/usr/bin/env python2.7
from hashlib import md5
from Crypto.Cipher import AES
from Crypto import Random
import base64

from boto3 import client
from boto3.session import Session

from optparse import OptionParser
from ConfigParser import ConfigParser
from os import walk, path, mkdir, rmdir, remove
import tarfile
from os.path import join
# walk a directory structure and remove everything
def rm_rf(path):
    for root, dirs, files in walk(path, topdown=False):
        # if dir is empty skip files
        for name in files:
            remove(join(root, name))
        for name in dirs:
            rmdir(join(root, name))
    rmdir(path)

# get_profile will use the config file for aws cli 
# provide a profile name it will fetch credentials
def get_profile(profile='default'):
    # if profile is not default need prefix profile
    if profile != 'default':
        profile = 'profile %s' % profile
    home = path.expanduser("~")
    aws_creds = ConfigParser()
    aws_creds.read('%s/.aws/config' % home)
    # this is logic for roles, when using role there may only be region
    try:
        return { 'aws_access_key_id': aws_creds.get(profile, 'aws_access_key_id'),
                 'aws_secret_access_key': aws_creds.get(profile, 'aws_secret_access_key'),
                 'region': aws_creds.get(profile, 'region') }
    except:
        return { 'region': aws_creds.get(profile, 'region') }


# connect to kms with boto3
def connect(profile="default"):
    # if using default profile or role we dont need to pass creds 
    if profile == "default":
        kms = client('kms')
    else:
        profile = get_profile(profile)
        session = Session(aws_access_key_id=profile['aws_access_key_id'],
                  aws_secret_access_key=profile['aws_secret_access_key'],
                  region_name=profile['region']) 
        kms = session.client('kms')
    return kms

# make a big messy md5
def derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = ''
    while len(d) < key_length + iv_length:
        d_i = md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]

# encrypt reads and writes files
# password is the kms data key
# key lenght must not be more than 32
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

# decrypt reads and writes files
# password is the kms data key
# key lenght must not be more than 32
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
    # Help file and options
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

    # connect to kms
    kms = connect(opts.profile)
    workingdir = "/var/tmp/kmstool/" # directory for temp files
    try: 
        mkdir(workingdir)
    except:
        rm_rf(workingdir)
        mkdir(workingdir)
    # naming temp files
    enc_file = join(workingdir, 'file.enc')
    cipher_file = join(workingdir, 'key.enc')

    if opts.encrypt:  
        # get a data key from kms
        response = kms.generate_data_key(KeyId=opts.key_id, KeySpec=opts.key_spec)
        # key comes in as binary so we encode it
        key = base64.b64encode(response['Plaintext'])
        # this is the encrypted version we store with the data 
        ciphertext = response['CiphertextBlob']    

        with open(opts.file, 'rb') as in_file, open(enc_file, 'wb') as out_file:
            encrypt(in_file, out_file, key)
        with open(cipher_file, 'wb') as out_file:
            out_file.write(ciphertext)
        # tar up the encrypted file and the ciphertext key
        with tarfile.open(opts.output, "w") as tar:
            for name in [enc_file, cipher_file]:
                tar.add(name,arcname=path.split(name)[1])

    elif not opts.encrypt:
        # unpack tar file
        tar = tarfile.open(opts.file)
        tar.extractall(workingdir)
        tar.close()
        # read ciphertext key  
        with open(cipher_file, 'rb') as open_file:
            ciphertext = open_file.read()
        # decrypt via kms
        response = kms.decrypt(CiphertextBlob=ciphertext)
        # encode the binary key so it's the same as it was for encrypt
        key = base64.b64encode(response['Plaintext']) 
        with open(enc_file, 'rb') as in_file, open(opts.output, 'wb') as out_file:
            decrypt(in_file, out_file, key)
    
    # clean up working directory 
    rm_rf(workingdir)

if __name__ == '__main__':
    try: main()
    except: raise

