import os
import hashlib
import base64
from base64 import b64encode
import time
import requests
import yaml
from docopt import docopt
from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_signing import ParseError
from sawtooth_signing.secp256k1 import Secp256k1PrivateKey

from sawtooth_sdk.protobuf.transaction_pb2 import TransactionHeader
from sawtooth_sdk.protobuf.transaction_pb2 import Transaction
from sawtooth_sdk.protobuf.batch_pb2 import BatchList
from sawtooth_sdk.protobuf.batch_pb2 import BatchHeader
from sawtooth_sdk.protobuf.batch_pb2 import Batch
"""BarCodeReaderCli.

Usage:
  barcode_cli.py create chain (-u <user> | --username <user>)
  barcode_cli.py (-h | --help)
  barcode_cli.py --version
  # naval_fate.py ship new <name>...
  # naval_fate.py ship <name> move <x> <y> [--speed=<kn>]
  # naval_fate.py ship shoot <x> <y>
  # naval_fate.py mine (set|remove) <x> <y> [--moored | --drifting]
  # naval_fate.py (-h | --help)
  # naval_fate.py --version

Options:
  -h --help     Show this screen.
  -u --username username
  --version     display version
  # --speed=<kn>  Speed in knots [default: 10].
  # --moored      Moored (anchored) mine.
  # --drifting    Drifting mine.

"""


DISTRIBUTION_NAME = 'sawtooth-barcode'
DEFAULT_URL = 'http://127.0.0.1:8008'


def _sha512(data):
    return hashlib.sha512(data).hexdigest()


class BarcodeClient:

    def __init__(self, base_url, keyfile=None):

        self._base_url = base_url
        if keyfile is None:
            self._signer = None
            return

        try:
            with open(keyfile) as fd:
                private_key_str = fd.read().strip()
        except OSError as err:
            raise Exception('Failed to read private key {}: {}'.format(keyfile, str(err)))

        try:
            private_key = Secp256k1PrivateKey.from_hex(private_key_str)
        except ParseError as e:
            raise Exception('Unable to load private key: {}'.format(str(e)))

        self._signer = CryptoFactory(create_context('secp256k1')).new_signer(private_key)

    @staticmethod
    def _get_prefix():
        return _sha512('barcode'.encode('utf-8'))[0:6]

    def _get_address(self, name):
        barcode_prefix = self._get_prefix()
        name_address = _sha512(name.encode('utf-8'))[0:64]
        return barcode_prefix + name_address

    def _create_batch_list(self, transactions):
        transaction_signatures = [t.header_signature for t in transactions]

        header = BatchHeader(
            signer_public_key=self._signer.get_public_key().as_hex(),
            transaction_ids=transaction_signatures
        ).SerializeToString()

        signature = self._signer.sign(header)

        batch = Batch(
            header=header,
            transactions=transactions,
            header_signature=signature)
        return BatchList(batches=[batch])

    def _send_request(self, suffix, data=None, content_type=None, name=None, auth_user=None, auth_password=None):
        if self._base_url.startswith("http://"):
            url = "{}/{}".format(self._base_url, suffix)
        else:
            url = "http://{}/{}".format(self._base_url, suffix)

        headers = {}
        if auth_user is not None:
            auth_string = "{}:{}".format(auth_user, auth_password)
            b64_string = b64encode(auth_string.encode()).decode()
            auth_header = 'Basic {}'.format(b64_string)
            headers['Authorization'] = auth_header

        if content_type is not None:
            headers['Content-Type'] = content_type

        try:
            if data is not None:
                result = requests.post(url, headers=headers, data=data)
            else:
                result = requests.get(url, headers=headers)

            if result.status_code == 404:
                raise Exception("No such name: {}".format(name))

            elif not result.ok:
                raise Exception("Error {}: {}".format(result.status_code, result.reason))

        except requests.ConnectionError as err:
            raise Exception('Failed to connect to {}: {}'.format(url, str(err)))

        except BaseException as err:
            raise Exception(err)

        return result.text

    def _get_status(self, batch_id, wait, auth_user=None, auth_password=None):
        try:
            result = self._send_request(
                'batch_statuses?id={}&wait={}'.format(batch_id, wait),
                auth_user=auth_user,
                auth_password=auth_password)
            return yaml.safe_load(result)['data'][0]['status']
        except BaseException as err:
            raise Exception(err)

    def _send_barcode_txn(self, name, action, space="", wait=None, auth_user=None, auth_password=None):
        # Serialization is just a delimited utf-8 encoded string
        payload = ",".join([name, action, str(space)]).encode()

        # Construct the address
        address = self._get_address(name)

        header = TransactionHeader(signer_public_key=self._signer.get_public_key().as_hex(), family_name="barcode",
                                   family_version="1.0", inputs=[address], outputs=[address], dependencies=[],
                                   payload_sha512=_sha512(payload),
                                   batcher_public_key=self._signer.get_public_key().as_hex(),
                                   nonce=time.time().hex().encode()).SerializeToString()
        signature = self._signer.sign(header)
        transaction = Transaction(header=header, payload=payload, header_signature=signature)
        batch_list = self._create_batch_list([transaction])
        batch_id = batch_list.batches[0].header_signature
        if wait and wait > 0:
            wait_time = 0
            start_time = time.time()
            response = self._send_request("batches", batch_list.SerializeToString(), 'application/octet-stream',
                                          auth_user=auth_user, auth_password=auth_password)
            while wait_time < wait:
                status = self._get_status(batch_id, wait - int(wait_time), auth_user=auth_user,
                                          auth_password=auth_password)
                wait_time = time.time() - start_time
                if status != 'PENDING':
                    return response
            return response

        return self._send_request("batches", batch_list.SerializeToString(), 'application/octet-stream',
                                  auth_user=auth_user, auth_password=auth_password)

    def create(self, name, wait=None, auth_user=None, auth_password=None):
        return self._send_barcode_txn(name, "create", wait=wait, auth_user=auth_user, auth_password=auth_password)


class BarcodeOperations(object):

    def __int__(self, user):
        self.user = user

    def _get_key_file(self):
        home = os.path.expanduser("~")
        key_dir = os.path.join(home, ".sawtooth", "keys")

        return '{}/{}.priv'.format(key_dir, self.user)

    def _validate_user(self):
        self.key_file = self._get_key_file()
        try:
            with open(self.key_file) as fd:
                self.private_key_str = fd.read().strip()
        except OSError as err:
            raise Exception('Failed to read private key {}: {}'.format(self.key_file, str(err)))

    def create_chain(self):
        self._validate_user()
        client = BarcodeClient(base_url=DEFAULT_URL, keyfile=self.key_file)
        name = '1234523'
        response = client.create(name)


if __name__ == '__main__':
    args = docopt(__doc__, version='Barcode 1.0')
    # print(arguments)
    if args['--username']:
        username = args['--username']
        # validate user with action
        if args['create']:
            barcode_ops = BarcodeOperations(username)
            barcode_ops.create_chain()

