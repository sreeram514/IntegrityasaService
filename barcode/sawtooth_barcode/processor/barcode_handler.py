import hashlib
import logging


from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError

LOGGER = logging.getLogger(__name__)


class BarcodeTransactionHandler(TransactionHandler):
    def __int__(self,namespace_prefix):
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
        LOGGER.debug("namespace_prefix is : {} and context : ".format(self._namespace_prefix, context))
        name, action, space, signer = _unpack_transaction(transaction)
        LOGGER.debug("name : {}, space: {}, signer: {}".format(name, space, signer))
        # 2. Retrieve the game data from state storage
        board, state, player1, player2, game_list = \
            _get_state_data(context, self._namespace_prefix, name)

        # 3. Validate the game data
        _validate_game_data(
            action, space, signer,
            board, state, player1, player2)

        # 4. Apply the transaction
        if action == 'delete':
            _delete_game(context, name, self._namespace_prefix)
            return

        upd_board, upd_state, upd_player1, upd_player2 = _play_xo(
            action, space, signer,
            board, state,
            player1, player2)

        # 5. Log for tutorial usage
        if action == "create":
            _display("Player {} created a game.".format(signer[:6]))

        elif action == "take":
            _display(
                "Player {} takes space: {}\n\n".format(signer[:6], space) +
                _game_data_to_str(
                    upd_board, upd_state, upd_player1, upd_player2, name))

        # 6. Put the game data back in state storage
        _store_state_data(
            context, game_list,
            self._namespace_prefix, name,
            upd_board, upd_state,
            upd_player1, upd_player2)

