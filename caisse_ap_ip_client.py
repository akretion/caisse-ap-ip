#! /usr/bin/python3

##############################################################################
#    Caisse-AP IP client                                                     #
#    Copyright (C) 2023 Alexis de Lattre <alexis.delattre@akretion.com>      #
#    Copyright (C) 2023 Rémi de Lattre <remi _at_ miluni dot fr>             #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU General Public License as published by    #
#    the Free Software Foundation, either version 3 of the License, or       #
#    (at your option) any later version.                                     #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU General Public License for more details.                            #
#                                                                            #
#    You should have received a copy of the GNU General Public License       #
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.  #

##############################################################################

import logging
import argparse
import sys
import socket
from pprint import pprint

__author__ = "Rémi de Lattre <remi@miluni.fr>"
__date__ = "April 2023"
__version__ = "0.1"

BUFFER_SIZE = 1024
TIMEOUT = 180  # in seconds

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
logging.basicConfig(format=FORMAT)


def main(args):
    if args.log_level:
        log_level = args.log_level.lower()
        log_map = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warn': logging.WARN,
            'error': logging.ERROR,
        }
        if log_level in log_map:
            logger.setLevel(log_map[log_level])
    if args.port < 1 or args.port > 65535:
        logger.error('Wrong TCP port (%s). Must be between 1 and 65535', args.port)
        sys.exit(1)
    currency = args.currency.upper()
    if currency == 'EUR':
        cur_num = '978'
        decimals = 2
    else:
        from iso4217 import Currency
        cur = Currency(currency)
        cur_num = str(cur.number)
        decimals = cur.exponent
    assert len(cur_num) == 3

    msg_dict = {
        'CZ': '0300',  # Caisse-AP protocol version
        'CJ': '012345678901',  # Identifiant Protocole Concert
        'CA': '01',  # caisse number
        'CE': cur_num,  # Currency ISO number
        'BA': '0',  # 1 = immediate answer ; 0 = answer at the end of transaction
    }

    amount = args.amount
    if amount > 0:
        msg_dict['CD'] = '0'  # debit
        amount_positive = amount
    elif amount < 0:
        msg_dict['CD'] = '1'  # reimburse
        amount_positive = amount * -1

    if args.check:
        msg_dict['CC'] = '00C'
    amount_cent = amount_positive * 10 ** decimals
    amount_str = str(int(round(amount_cent)))
    if len(amount_str) > 12:
        logger.error(
            'Amount is too big (%s): 12 numbers (including cents) maximum.', args.amount)
        sys.exit(1)
    if len(amount_str) < 2:
        amount_str = amount_str.zfill(2)
    msg_dict['CB'] = amount_str

    # START to build request
    pprint(msg_dict)

    for tag, value in msg_dict.items():
        assert isinstance(tag, str)
        assert len(tag) == 2
        assert isinstance(value, str)
        assert len(value) >= 1
        assert len(value) <= 999
    msg_list = []
    # Always start with tag CZ
    # the order of the other tags is unrelevant
    if 'CZ' in msg_dict:
        version = msg_dict.pop('CZ')
        msg_list.append(('CZ', version))
    msg_list += list(msg_dict.items())
    msg_str = ''.join(['%s%s%s' % (tag, str(len(value)).zfill(3), value) for (tag, value) in msg_list])

    with socket.create_connection((args.destination, args.port), timeout=TIMEOUT) as sock:
        logger.info('sent: %s', msg_str)
        sock.send(msg_str.encode('ascii'))
        data = sock.recv(BUFFER_SIZE)
        logger.info("received: %s", data.decode('ascii'))


if __name__ == '__main__':
    usage = "caisse_ap_ip_client.py"
    epilog = "Author: %s - Version: %s" % (__author__, __version__)
    description = "Caisse-AP IP client. Can simulate a point of sale."

    parser = argparse.ArgumentParser(
        usage=usage, epilog=epilog, description=description)
    parser.add_argument(
        '-l', '--log-level', dest='log_level', default='info',
        help="Log level. Possible values: debug, info, warn, error. "
             "Default value: info.")
    parser.add_argument(
        '-d', '--destination', dest='destination', default='127.0.0.1',
        help="Destination IP address or DNS. Default value: 127.0.0.1.")
    parser.add_argument(
        '-p', '--port', dest='port', type=int, default=8888,
        help="TCP port. Default value: 8888.")
    parser.add_argument(
        '-a', '--amount', dest='amount', type=float, default=112.45,
        help="Amount as float. Use dot as decimal separator. Default value: 112.45")
    parser.add_argument(
        '-ck', '--check', dest='check', action='store_true',
        help="If set, use the check printing feature of the payment terminal.")
    parser.add_argument(
        '-c', '--currency', dest='currency', default="EUR",
        help="Currency ISO code (3 letters). Default value: EUR.")
    args = parser.parse_args()
    main(args)
