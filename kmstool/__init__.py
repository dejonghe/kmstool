#!/usr/bin/env python
from optparse import OptionParser
from ConfigParser import ConfigParser

from kmstool import kmstool

__version__ = '1.3.0'

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
    parser.add_option('-t','--temp', help='Temp work dir, optional', default='/var/tmp/')
    (opts, args) = parser.parse_args()


    options_broken = False
    if hasattr(opts, 'encrypt'):
        options_broken = True
    if not opts.file and not opts.output: 
        options_broken = True
    if options_broken:
        parser.print_help()
        exit(1)

    temp_dir = opts.temp + 'kmstool_temp/'
    # init kms
    tool = kmstool(input_file=opts.file,
                      output_file=opts.output,
                      key_id=opts.key_id,
                      key_spec=opts.key_spec,
                      temp_dir=temp_dir,
                      profile=opts.profile,
                      region=opts.region)

    if opts.encrypt:
        tool.encrypt()
    elif not opts.encrypt:
        tool.decrypt()

if __name__ == '__main__':
    try: main()
    except: raise

