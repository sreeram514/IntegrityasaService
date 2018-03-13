import hashlib
import logging
import psycopg2
import re

from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError

LOGGER = logging.getLogger(__name__)


class BarcodeTransactionHandler(TransactionHandler):
    def __init__(self, namespace_prefix):
        self._namespace_prefix = namespace_prefix

    @property
    def family_name(self):
        return 'barcode'

    @property
    def family_versions(self):
        return ['1.0']

    @property
    def namespaces(self):
        return [self._namespace_prefix]

    def apply(self, transaction, context):

        # 1. Deserialize the transaction and verify it is valid
        b_id, action, upd_location, signer = _unpack_transaction(transaction)

        if action == 'add':
            _add_priv_key(context, name=b_id, tag=upd_location.split(':')[0], priv_key=upd_location.split(':')[1],
                          namespace=self._namespace_prefix)
            return

        # 2. Retrieve the game data from state storage
        product_name, mfg_date, location, barcode_list = _get_state_data(context, self._namespace_prefix, b_id)

        # 3. Validate the game data
        # _validate_game_data(
        #     action, space, signer,
        #     board, state, player1, player2)
        #
        # 4. Apply the transaction
        if action == 'create':
            barcode_list = _get_barcode_details(b_id)

        if action == 'update':
            product_name, mfg_date, location, barcode_list = _get_state_data(context, self._namespace_prefix, b_id,
                                                                             upd_location)
        # if action == 'delete':
        #     _delete_game(context, name, self._namespace_prefix)
        #     return
        #

        # upd_board, upd_state, upd_player1, upd_player2 = _play_xo(
        #     action, space, signer,
        #     board, state,
        #     player1, player2)
        #
        # # 5. Log for tutorial usage
        # if action == "create":
        #     _display("Player {} created a game.".format(signer[:6]))
        #
        # elif action == "take":
        #     _display(
        #         "Player {} takes space: {}\n\n".format(signer[:6], space) +
        #         _game_data_to_str(
        #             upd_board, upd_state, upd_player1, upd_player2, name))

        # 6. Put the game data back in state storage
        _store_state_data(context, barcode_list, self._namespace_prefix, b_id)


def _get_barcode_details(barcode):
    barcode_list = {}
    try:
        conn = psycopg2.connect("dbname=barcode user=barcode_user password=shroot12")
        cur = conn.cursor()
        cur.execute('select * from barcode_details where barcode_id={}'.format(barcode))
        barcode_details = cur.fetchone()
        barcode_list = {barcode_details[0]: (barcode_details[1], barcode_details[2], barcode_details[3])}
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        cur.close()
    return barcode_list


def _add_priv_key(context, name, tag, priv_key, namespace):
    state_data = '|'.join([str(name), str(tag), str(priv_key), ]).encode()
    addresses = context.set_state(
        {_make_xo_address(namespace, name): state_data})

    if len(addresses) < 1:
        raise InternalError("State Error")


def _unpack_transaction(transaction):
    header = transaction.header

    # The transaction signer is the player
    signer = header.signer_public_key

    try:
        # The payload is csv utf-8 encoded string
        name, action, location = transaction.payload.decode().split(",")
    except ValueError:
        raise InvalidTransaction("Invalid payload serialization")

    _validate_transaction(name, action, location)

    return name, action, location, signer


def _validate_transaction(name, action, location):
    if not name:
        raise InvalidTransaction('Name is required')

    if '|' in name:
        raise InvalidTransaction('Name cannot contain "|"')

    if not action:
        raise InvalidTransaction('Action is required')

    if action not in ('create', 'update', 'show', 'add'):
        raise InvalidTransaction('Invalid action: {}'.format(action))

    if action == 'update':
        try:
            assert location is not None
        except (ValueError, AssertionError):
            raise InvalidTransaction('location should not be empty during update action')


def _make_xo_address(namespace_prefix, b_id):
    return namespace_prefix + hashlib.sha512(b_id.encode('utf-8')).hexdigest()[:64]


def _get_state_data(context, namespace_prefix, b_id, upd_location=None):
    # Get data from address
    state_entries = context.get_state([_make_xo_address(namespace_prefix, b_id)])
    append_location = ''
    if upd_location is not None:
        append_location = '-> {}'.format(upd_location)
    # context.get_state() returns a list. If no data has been stored yet
    # at the given address, it will be empty.
    if state_entries:
        try:
            state_data = state_entries[0].data

            barcode_list = {b_id: (product_name, mfg_date, location + append_location) for
                            b_id, product_name, mfg_date, location in
                            [barcode.split(',') for barcode in state_data.decode().split('|')]}

            (product_name, mfg_date, location) = barcode_list[re.sub("^0+", "", b_id)]

        except ValueError:
            raise InternalError("Failed to deserialize game data.")

    else:
        barcode_list = {}
        product_name = mfg_date = location = None

    return product_name, mfg_date, location, barcode_list


def _store_state_data(context, barcode_list, namespace_prefix, b_id):

    # barcode_list[b_id] = product_name, mfg_date, location
    # game_list[name] = board, state, player1, player2

    state_data = '|'.join(sorted(
        [','.join([str(idd), str(product_name), str(mfg_date), location]) for idd, (product_name, mfg_date, location) in
         barcode_list.items()])).encode()
    tate_data = '|'.join([str(name), str(tag), str(priv_key), ]).encode()
    addresses = context.set_state(
        {_make_xo_address(namespace_prefix, b_id): state_data})

    if len(addresses) < 1:
        raise InternalError("State Error")
