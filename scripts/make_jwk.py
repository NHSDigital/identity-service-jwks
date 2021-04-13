#!/usr/bin/env python3
"""
make_jwk.py

Create a JWK from a PEM Public Key

Usage:
  make_jwk.py  PUBLIC_KEY_FILE  KEY_ID  ENV  APP_ID
  make_jwk.py (-h | --help)

Options:
  -h --help                        Show this screen.
"""
import sys
import json
import uuid
import pathlib
from docopt import docopt
from authlib.jose import jwk

ENVIRONMENTS = [
    "internal-dev",
    "internal-dev-sandbox",
    "internal-qa",
    "internal-qa-sandbox",
    "ref",
    "dev",
    "sandbox",
    "int",
    "prod",
]
JWKS_ROOT_DIR = pathlib.Path(__file__).absolute().parent.parent.joinpath("jwks")

if __name__ == "__main__":
    args = docopt(__doc__)

    # Check public key file exists
    pk_file = args["PUBLIC_KEY_FILE"]
    if not pathlib.Path(pk_file).exists():
        print(f"Unable to find PUBLIC_KEY_FILE: {pk_file}", file=sys.stderr)
        sys.exit(1)

    # Validate environment
    env = args["ENV"]
    if env not in ENVIRONMENTS:
        print(f"Invalid ENV: {env}", file=sys.stderr)
        print(f"Must be one of {ENVIRONMENTS}", file=sys.stderr)
        sys.exit(1)

    # Validate app_id
    app_id = args["APP_ID"]
    try:
        uuid.UUID(app_id, version=4)
    except ValueError:
        print(f"Invalid APP_ID: {app_id}, expecting a uuid4", file=sys.stderr)
        sys.exit(1)

    # Build the public key
    with open(pk_file) as f:
        public_key = f.read()
    new_key = jwk.dumps(public_key, kty="RSA", crv_or_size=4096, alg="RS512")
    new_key["kid"] = args["KEY_ID"]
    new_key["use"] = "sig"

    # Create empty keystore
    jwks = {"keys": []}

    jwks_env_dir = JWKS_ROOT_DIR.joinpath(env)

    # If file already exists, load existing keystore
    jwks_file = jwks_env_dir.joinpath(f"{app_id}.json")
    if jwks_file.exists():
        with open(jwks_file) as f:
            try:
                jwks = json.load(f)
            except json.decoder.JSONDecodeError:
                # If the file exists but is empty
                jwks = {"keys":[]}

    # Check if key already present
    for key in jwks["keys"]:
        if key == new_key:
            print(f"Key already present in {jwks_file}", file=sys.stderr)
            print(json.dumps(jwks, indent=2), file=sys.stderr)
            sys.exit(1)

    if not jwks_env_dir.exists():
        jwks_env_dir.mkdir()

    # Add key and write
    jwks["keys"].append(new_key)
    with open(jwks_file, "w") as f:
        json.dump(jwks, f, indent=2)

    print(json.dumps(jwks, indent=2))
