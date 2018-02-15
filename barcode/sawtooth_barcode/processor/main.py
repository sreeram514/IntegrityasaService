import hashlib
import sys
import os

from sawtooth_sdk.processor.core import TransactionProcessor
from sawtooth_sdk.processor.log import init_console_logging
from sawtooth_sdk.processor.log import log_configuration
from sawtooth_sdk.processor.config import get_log_dir
from sawtooth_barcode.processor.barcode_handler import BarcodeTransactionHandler

def main():

    try:
        processor = TransactionProcessor(url='tcp://127.0.0.1:4004')
        log_dir = get_log_dir()
        log_configuration(log_dir=log_dir, name="barcode-" + str(processor.zmq_id)[2:-1])
        init_console_logging(verbose_level=2)
        barcode_prefix = hashlib.sha512('barcode'.encode("utf-8")).hexdigest()[0:6]
        handler = BarcodeTransactionHandler(namespace_prefix=barcode_prefix)
        processor.add_handler(handler)
        processor.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:  # pylint: disable=broad-except
        print("Error: {}".format(e))
    finally:
        if processor is not None:
            processor.stop()
