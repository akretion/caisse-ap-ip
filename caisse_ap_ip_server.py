#! /usr/bin/python3

#############################################################################
#   Caisse-AP over IP server simulator.                                     #
#   Copyright (C) 2023  Rémi de Lattre  <remi _at_ miluni dot fr>           #
#                                                                           #
#   This program is free software: you can redistribute it and/or modify    #
#   it under the terms of the GNU General Public License as published by    #
#   the Free Software Foundation, either version 3 of the License, or       #
#   (at your option) any later version.                                     #
#                                                                           #
#   This program is distributed in the hope that it will be useful,         #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the            #
#   GNU General Public License for more details.                            #
#                                                                           #
#   You should have received a copy of the GNU General Public License       #
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.  #
#############################################################################

import argparse
import sys
import logging
import random
import time
from twisted.internet import protocol, reactor, endpoints
from pprint import pprint

__author__ = "Rémi de Lattre <remi@miluni.fr>"
__date__ = "April 2023"
__version__ = "0.1"

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
logging.basicConfig(format=FORMAT)

payment_type_CC_dict = {
    'cbcontact': '001',
    'cbcontactless': '00B',
    'amexcontact': '002',
    'amexcontactless': '00D',
}
failure_type_AF_dict = {
    'abandon': '11',
    'timeout': '08',
    'refused': '04',
    'forbidden': '05',
}


class CaisseAP(protocol.Protocol):
    def __init__(self, args):
        self.args = args

    def dataReceived(self, data_bytes):
        data_str = data_bytes.decode('ascii')
        logger.info('Received raw data: %s', data_str)
        data_dict = {}
        i = 0
        while i < len(data_str):
            tag = data_str[i:i + 2]
            i += 2
            size_str = data_str[i:i + 3]
            size = int(size_str)
            i += 3
            value = data_str[i:i + size]
            data_dict[tag] = value
            i += size
        logger.info('Received parsed data:')
        pprint(data_dict)

        immediate = False

        check = data_dict.get('CC') == '00C'
        logger.debug('check=%s', check)
        answer_dict = dict(data_dict)

        mandatory_tags = ["CZ", "CJ", "CA", "CB", "CD", "CE"]
        if any([x not in data_dict for x in mandatory_tags]):
            answer_dict['AE'] = '01'
            answer_dict['AF'] = '09'
            immediate = True

        ba_tag = data_dict.get('BA', '0')
        if ba_tag == '1':
            immediate = True
            answer_dict['AE'] = '11'  # AE = 11(request took into account) => no 'AF'
        elif args.failure:
            answer_dict['AE'] = '01'  # AE = 01(operation not done)
            # AF = Complement of action status (AE). Only present on failures
            if check:
                # From our experience, for checks, Ingenico always answers 04
                # (press on red button or check inserted wrong side)
                answer_dict['AF'] = '04'
            else:
                answer_dict['AF'] = failure_type_AF_dict[args.failure_type]

        else:
            answer_dict['AE'] = '10'  # AE = 10(operation done)

        if not immediate:
            time.sleep(args.duration)

        if not args.failure and not immediate:

            # CC = Payment mode
            # Set by client only if it's a check
            # otherwise, only present in the answer
            if not check:
                answer_dict['CC'] = payment_type_CC_dict[args.payment_type]
                CI_dict = {
                    'cbcontact': '1',
                    'cbcontactless': '2',
                    'amexcontact': '1',
                    'amexcontactless': '2',
                }
                answer_dict['CI'] = CI_dict[args.payment_type]

                # AC = authorisation number
                answer_dict['AC'] = str(random.randint(100000, 999999))

                # AA = payment card number
                nb1 = random.randint(100000, 999999)
                nb2 = random.randint(1000, 9999)
                answer_dict['AA'] = '%s######%s' % (nb1, nb2)
                # AI = AID of the payment card
                answer_dict['AI'] = 'A00000000%s' % random.randint(10000, 999999999999)
                # AB = expiry date of the payment card (format YYMM)
                next_year = str(time.gmtime().tm_year + 1)[2:]
                month = str(random.randint(1, 12)).zfill(2)
                answer_dict['AB'] = '%s%s' % (next_year, month)

                # CF = private data
                answer_dict['CF'] = '1010000000'

                # CG = seller contract number
                answer_dict['CG'] = args.seller_contract

        logger.info('Answer structured data:')
        pprint(answer_dict)
        for tag, value in answer_dict.items():
            assert isinstance(tag, str)
            assert len(tag) == 2
            assert isinstance(value, str)
            assert len(value) >= 1
            assert len(value) <= 999
        answer_list = []
        # Always start with a CZ tag
        # The order of the other tags is not significant
        if 'CZ' in answer_dict:
            version = answer_dict.pop('CZ')
            answer_list.append(('CZ', version))

        answer_list += list(answer_dict.items())
        answer_str = ''.join(
            ['%s%s%s' % (tag, str(len(value)).zfill(3), value) for (tag, value) in answer_list])
        answer_bytes = answer_str.encode('ascii')
        logger.info('Answer raw data: %s', answer_str)
        self.transport.write(answer_bytes)


class CaisseAPFactory(protocol.Factory):
    def __init__(self, args):
        self.args = args

    def buildProtocol(self, addr):
        return CaisseAP(self.args)


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
        else:
            logger.error(
                'Wrong value for log level (%s). Possible values: %s',
                log_level, ', '.join(log_map.keys()))
            sys.exit(1)
    if args.port < 1 or args.port > 65535:
        logger.error('Wrong TCP port (%s). Must be between 1 and 65535', args.port)
        sys.exit(1)
    if args.failure_type:
        failure_type = args.failure_type.lower()
        if failure_type not in failure_type_AF_dict:
            logger.error(
                'Wrong value for failure type (%s). Possible values : %s',
                args.failure_type, ', '.join(failure_type_AF_dict.keys()))
            sys.exit(1)
        if args.failure_type != 'abandon' and not args.failure:
            logger.warning(
                'Failure type option is ignored because the failure option is not set.')
        payment_type = args.payment_type.lower()
        if payment_type not in payment_type_CC_dict:
            logger.error(
                'Wrong value for payment type (%s). Possible values: %s',
                args.payment_type, ', '.join(payment_type_CC_dict.keys()))
            sys.exit(1)
    if args.failure:
        logger.info(
            "Start in failure mode: all payment requests will fail with type '%s'.",
            args.failure_type)
    else:
        logger.info('Start in success mode: all payment requests will succeed.')

    if len(args.seller_contract) > 10:
        logger.error('Wrong seller contract (%s): 10 characters max.' % args.seller_contract)
        sys.exit(1)

    endpoints.serverFromString(reactor, "tcp:%s" % args.port).listen(CaisseAPFactory(args))
    logger.info('Listening on TCP port %s', args.port)
    reactor.run()


if __name__ == '__main__':
    usage = "caisse_ap_ip_simulator.py"
    epilog = "Author: %s - Version: %s" % (__author__, __version__)
    description = "This script is a server for Caisse-AP over IP protocol. "
    "It simulates a payment terminal."

    parser = argparse.ArgumentParser(
        usage=usage, epilog=epilog, description=description)
    parser.add_argument(
        '-l', '--log-level', dest='log_level', default='info',
        help="Log level. Possible values: debug, info, warn, error. "
        "Default value: info.")
    parser.add_argument(
        '-p', '--port', dest='port', type=int, default=8888,
        help="Listening TCP port. Default value : 8888.")
    parser.add_argument(
        '-f', '--failure', dest='failure',
        action='store_true', help="If set, the simulator will return all payment "
        "requests as failures (otherwise all payment requests will be returned "
        "as success).")
    parser.add_argument(
        '-ft', '--failure-type', dest='failure_type', default='abandon',
        help="Failure type. Possible values : abandon, timeout, "
        "refused, forbidden. Default value: abandon.")
    parser.add_argument(
        '-d', '--duration', dest='duration', type=int, default=3,
        help="Delay in seconds between the payment request and the return message. "
        "Ignored if the immediate option is set by the client (BA = 1). "
        "Default timeout: 3 seconds.")
    parser.add_argument(
        '-pt', '--payment-type', dest='payment_type', default='cbcontact',
        help="Payment type for payment card transactions (unrelevant for payment by check). "
        "Possible values : cbcontact, cbcontactless, amexcontact, amexcontactless. "
        "Default value : cbcontact.")
    parser.add_argument(
        '-sc', '--seller-contract', dest='seller_contract', default="424242",
        help="Seller contract reference (10 characters max).")

    args = parser.parse_args()
    main(args)
