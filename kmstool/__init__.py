#!/usr/bin/env python
import argparse
import base64
import io
import sys
from . import kmstool

__version__ = '1.4.0'


class __encoder(object):
    """
    A basic class for converting to and from base64 when interacting
    with stdin and stdout
    """

    def __init__(self, encrypt):
        self.encrypt = encrypt

    def write(self, data):
        """
        Base64 encode data and write it to stdout
        :param data: A string containing arbitrary data
        :return: None
        """
        sys.stdout.write((base64.b64encode(data) if self.encrypt else data).decode('ascii'))

    def read(self):
        """
        Return base64 decoded data read from stdin
        :return: A string containing the decoded data
        """
        return sys.stdin.read().encode('ascii') if self.encrypt else base64.b64decode(sys.stdin.read())


def main():
    # Help file and options
    parser = argparse.ArgumentParser(description='Envelope encryption with AWS KMS')
    parser.add_argument('-e','--encrypt', help='This encrypts the file', action='store_true', dest='encrypt')
    parser.add_argument('-d','--decrypt', help='This decrypts the file', action='store_false', dest='encrypt')
    parser.add_argument('-f','--file',  help='File to encrypt or decrypt')
    parser.add_argument('-o','--output', help='Path to output file')
    parser.add_argument('-k','--key_id', help='KMS Key-id')
    parser.add_argument('-s','--key_spec', help='KMS KeySpec', default='AES_256')
    parser.add_argument('-p','--profile', help='AWS Profile', default=None)
    parser.add_argument('-r','--region', help='Region', default=None)
    parser.add_argument('-t','--temp', help='Temp work dir, optional', default='/var/tmp/')
    parser.add_argument('-v','--version', help='Print Version', action='store_true', dest='version')
    args = parser.parse_args()


    options_broken = False
    if args.version:
        print(__version__)
        exit(0)
    if not hasattr(args, 'encrypt'):
        options_broken = True
    if not args.file:
        args.file = __encoder(args.encrypt)
    if not args.output:
        args.output = __encoder(args.encrypt)
    if options_broken:
        parser.print_help()
        exit(1)

    temp_dir = args.temp + 'kmstool_temp/'
    # init kms
    tool = kmstool.KmsTool(key_id=args.key_id,
                           key_spec=args.key_spec,
                           temp_dir=temp_dir,
                           profile=args.profile,
                           region=args.region)

    if args.encrypt:
        tool.encrypt(args.file, args.output)
    elif not args.encrypt:
        tool.decrypt(args.file, args.output)

if __name__ == '__main__':
    try: main()
    except: raise

