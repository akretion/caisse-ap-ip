#! /usr/bin/python3

##############################################################################

#    Caisse-AP IP client server.                                             #
#    Copyright (C) 2023  Alexis de Lattre  alexis _at_ miluni dot fr         #
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
__date__ = "Avril 2023"
__version__ = "0.1"

# VARIABLES that should NOT be changed (or rarely)
BUFFER_SIZE = 1024
TIMEOUT = 180  # in seconds

# CZ version protocole
# CJ identifiant protocole concert
# CA numéro de caisse
# CD Type action
# CB = montant en centimes, longueur variable 2 à 12
# CD = action (0 pour débit ; 1 pour remboursement ; 2 pour annulation)
# CE = devise 978 pour euro
# CH : optionnel : Numéro de référence donné lors de la transaction (En fonction du type d’action demandée par la caisse, ce numéro peut être vérifié par le terminal)

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
        logger.error('Wrong TCP port (%s). Must be between 1 and 65535' % args.port)
        sys.exit(1)
    currency = args.currency.upper()
    # if len(args.amount)>13:
    #     logger.error('Amount too high. (%s). 10 numbers max' % args.amount)
    #     sys.exit(1)
    cur_speed_map = {  # small speed-up, and works even if pycountry not installed
        'EUR': '978',
        'XPF': '953',
    }
    if currency in cur_speed_map:
        cur_num = cur_speed_map[currency]
    else:
        import pycountry
        cur = pycountry.currencies.get(alpha_3=currency.name)
        if not cur:
            logger.error("Currency %s doesn't exist." % currency)
            sys.exit(1)
        cur_num = cur.numeric  # it returns a string
    assert len(cur_num) == 3

    msg_dict = {
        'CZ': '0300',  # Caisse-AP protocol version
        'CJ': '012345678901',  # Identifiant Protocole Concert
        'CA': '01',  # caisse number
        'CE': cur_num,  # EUR
        'BF': '0',  # 0 = partial payment disallowed
        'BA': '0',  # 1 = immediate answer ; 0 = answer at the end of transaction
    }

    logger.debug(type(args.amount))

    amount = args.amount
    if amount > 0:
        msg_dict['CD'] = '0'  # debit
        amount_positive = amount
    elif amount < 0:
        msg_dict['CD'] = '1'  # reimburse
        amount_positive = amount * -1

    if args.check:
        msg_dict['CC'] = '00C'
    if args.decimals < 0 or args.decimals > 4:
        logger.error(
            'Wrong value for the option decimals (%s). Possible values: 0, 1, 2, 3, 4' % args.decimals)
    amount_cent = amount_positive * 10 ** args.decimals
    amount_str = str(int(round(amount_cent)))
    assert len(amount_str) <= 12
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
        print('sent: %s' % msg_str)
        sock.send(msg_str.encode('ascii'))
        data = sock.recv(BUFFER_SIZE)
    print("received: %s" % data.decode('ascii'))


if __name__ == '__main__':
    usage = "caisse_ap_ip_client"
    epilog = "Author: %s - Version: %s" % (__author__, __version__)
    description = "There aren't any description. "\

    parser = argparse.ArgumentParser(
        usage=usage, epilog=epilog, description=description)
    parser.add_argument(
        '-l', '--log-level', dest='log_level', default='info',
        help="Set log level. Possible values: debug, info, warn, error. "
             "Default value: info.")
    parser.add_argument(
        '-d', '--destination', dest='destination', default='127.0.0.1',
        help="Set destination. Default value '127.0.0.1' ")
    parser.add_argument(
        '-p', '--port', dest='port', type=int, default=8888,
        help="Set listening TCP port. Default value : 8888.")
    parser.add_argument(
        '-a', '--amount', dest='amount', type=float, default=112.45,
        help="Set the amount.")
    parser.add_argument(
        '-ck', '--check', dest='check', action='store_true',
        help="If set, you choose to pay by check.")
    parser.add_argument(
        '-c', '--currency', dest='currency', default="EUR",
        help="Set the currency you want to use. Possible values : EUR, XPF. "
             "Default value: EUR.")
    parser.add_argument(
        '-m', '--decimals', dest='decimals', type=int, default=2,
        help="Set the number of decimals of the currency. It can de between 0 and 4. "
             "Default value: 2.")
    args = parser.parse_args()
    main(args)
