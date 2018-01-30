#!/usr/bin/env python
import argparse
from kmstool import KmsTool

__version__ = '1.3.2'

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
    args = parser.parse_args()


    options_broken = False
    if not hasattr(args, 'encrypt'):
        options_broken = True
    if not args.file and not args.output: 
        options_broken = True
    if options_broken:
        parser.print_help()
        exit(1)

    temp_dir = args.temp + 'kmstool_temp/'
    # init kms
    tool = KmsTool(input_file=args.file,
                      output_file=args.output,
                      key_id=args.key_id,
                      key_spec=args.key_spec,
                      temp_dir=temp_dir,
                      profile=args.profile,
                      region=args.region)

    if args.encrypt:
        tool.encrypt()
    elif not args.encrypt:
        tool.decrypt()

if __name__ == '__main__':
    try: main()
    except: raise

