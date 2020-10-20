#!/usr/bin/env python3
"""
make_jwk.py

Create a JWK from a PEM Public Key

Usage:
  make_jwk.py --pk-file=<pem_file> --kid=<key_id>
  make_jwk.py (-h | --help)

Options:
  -h --help                        Show this screen
  --pk-file=<pem_file>             Path to public key file
  --kid=<key_id>                   KID Value
"""
import json
from docopt import docopt
from authlib.jose import jwk


if __name__ == "__main__":
    args = docopt(__doc__)

    with open(args['--pk-file'], 'r') as f:
        public_key = f.read()

    j = jwk.dumps(public_key, kty='RSA', crv_or_size=4096, alg='RS512')
    j['kid'] = args['--kid']
    j['use'] = 'sig'
    print(json.dumps(j, indent=2))
