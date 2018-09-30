# Copyright 2016, 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

import argparse
import getpass
import logging
import os
import sys
import traceback
import pkg_resources

from colorlog import ColoredFormatter

from sawtooth_intkey.client_cli.generate import add_generate_parser
from sawtooth_intkey.client_cli.generate import do_generate
from sawtooth_intkey.client_cli.populate import add_populate_parser
from sawtooth_intkey.client_cli.populate import do_populate
from sawtooth_intkey.client_cli.create_batch import add_create_batch_parser
from sawtooth_intkey.client_cli.create_batch import do_create_batch
from sawtooth_intkey.client_cli.load import add_load_parser
from sawtooth_intkey.client_cli.load import do_load
from sawtooth_intkey.client_cli.intkey_workload import add_workload_parser
from sawtooth_intkey.client_cli.intkey_workload import do_workload

from sawtooth_intkey.client_cli.intkey_client import IntkeyClient
from sawtooth_intkey.client_cli.exceptions import IntKeyCliException
from sawtooth_intkey.client_cli.exceptions import IntkeyClientException
from sawtooth_intkey.client_cli.exceptions import IntkeyKeyNotFoundException
# from sawtooth_cli.keygen import do_keygen


from aiohttp import web
import logging
import asyncio
import json
from zmq.asyncio import ZMQEventLoop
LOGGER = logging.getLogger(__name__)

DISTRIBUTION_NAME = 'sawtooth-intkey'

global_args = None
DEFAULT_URL = 'http://127.0.0.1:8008'
WILL_PREFIX = 'WILL_'
WILL_LIST_PREFIX = 'WILL_LIST_'

KEY_NEED_REVIEW = 'KEY_NEED_REVIEW'

def create_console_handler(verbose_level):
    clog = logging.StreamHandler()
    formatter = ColoredFormatter(
        "%(log_color)s[%(asctime)s %(levelname)-8s%(module)s]%(reset)s "
        "%(white)s%(message)s",
        datefmt="%H:%M:%S",
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        })

    clog.setFormatter(formatter)

    if verbose_level == 0:
        clog.setLevel(logging.WARN)
    elif verbose_level == 1:
        clog.setLevel(logging.INFO)
    else:
        clog.setLevel(logging.DEBUG)

    return clog


def setup_loggers(verbose_level):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(create_console_handler(verbose_level))


def create_parent_parser(prog_name):
    parent_parser = argparse.ArgumentParser(prog=prog_name, add_help=False)
    parent_parser.add_argument(
        '-v', '--verbose',
        action='count',
        help='enable more verbose output')

    try:
        version = pkg_resources.get_distribution(DISTRIBUTION_NAME).version
    except pkg_resources.DistributionNotFound:
        version = 'UNKNOWN'

    parent_parser.add_argument(
        '-V', '--version',
        action='version',
        version=(DISTRIBUTION_NAME + ' (Hyperledger Sawtooth) version {}')
        .format(version),
        help='display version information')

    return parent_parser


def create_parser(prog_name):
    parent_parser = create_parent_parser(prog_name)

    parser = argparse.ArgumentParser(
        parents=[parent_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter)

    subparsers = parser.add_subparsers(title='subcommands', dest='command')

    add_set_parser(subparsers, parent_parser)
    add_inc_parser(subparsers, parent_parser)
    add_dec_parser(subparsers, parent_parser)
    add_mul_parser(subparsers, parent_parser)
    add_show_parser(subparsers, parent_parser)
    add_start_parser(subparsers, parent_parser)

    add_generate_parser(subparsers, parent_parser)
    add_load_parser(subparsers, parent_parser)
    add_populate_parser(subparsers, parent_parser)
    add_create_batch_parser(subparsers, parent_parser)
    add_workload_parser(subparsers, parent_parser)

    return parser


def add_set_parser(subparsers, parent_parser):
    message = 'Sends an intkey transaction to set <name> to <value>.'

    parser = subparsers.add_parser(
        'set',
        parents=[parent_parser],
        description=message,
        help='Sets an intkey value')

    parser.add_argument(
        'name',
        type=str,
        help='name of key to set')

    parser.add_argument(
        'value',
        type=int,
        help='amount to set')

    parser.add_argument(
        '--url',
        type=str,
        default='rest-api:8008',
        help='specify URL of REST API')

    parser.add_argument(
        '--keyfile',
        type=str,
        help="identify file containing user's private key")

    parser.add_argument(
        '--wait',
        nargs='?',
        const=sys.maxsize,
        type=int,
        help='set time, in seconds, to wait for transaction to commit')


def do_set(args):
    name, value, wait = args.name, args.value, args.wait
    client = _get_client(args)
    response = client.set(name, value, wait)
    print(response)


def add_inc_parser(subparsers, parent_parser):
    message = 'Sends an intkey transaction to increment <name> by <value>.'

    parser = subparsers.add_parser(
        'inc',
        parents=[parent_parser],
        description=message,
        help='Increments an intkey value')

    parser.add_argument(
        'name',
        type=str,
        help='identify name of key to increment')

    parser.add_argument(
        'value',
        type=int,
        help='specify amount to increment')

    parser.add_argument(
        '--url',
        type=str,
        default='rest-api:8008',
        help='specify URL of REST API')

    parser.add_argument(
        '--keyfile',
        type=str,
        help="identify file containing user's private key")

    parser.add_argument(
        '--wait',
        nargs='?',
        const=sys.maxsize,
        type=int,
        help='set time, in seconds, to wait for transaction to commit')


def do_inc(args):
    name, value, wait = args.name, args.value, args.wait
    client = _get_client(args)
    response = client.inc(name, value, wait)
    print(response)


def add_dec_parser(subparsers, parent_parser):
    message = 'Sends an intkey transaction to decrement <name> by <value>.'

    parser = subparsers.add_parser(
        'dec',
        parents=[parent_parser],
        description=message,
        help='Decrements an intkey value')

    parser.add_argument(
        'name',
        type=str,
        help='identify name of key to decrement')

    parser.add_argument(
        'value',
        type=int,
        help='amount to decrement')

    parser.add_argument(
        '--url',
        type=str,
        default='rest-api:8008',
        help='specify URL of REST API')

    parser.add_argument(
        '--keyfile',
        type=str,
        help="identify file containing user's private key")

    parser.add_argument(
        '--wait',
        nargs='?',
        const=sys.maxsize,
        type=int,
        help='set time, in seconds, to wait for transaction to commit')


def do_dec(args):
    name, value, wait = args.name, args.value, args.wait
    client = _get_client(args)
    response = client.dec(name, value, wait)
    print(response)


def add_mul_parser(subparsers, parent_parser):
    message = 'Sends an intkey transaction to decrement <name> by <value>.'

    parser = subparsers.add_parser(
        'mul',
        parents=[parent_parser],
        description=message,
        help='Multiply an intkey value')

    parser.add_argument(
        'name',
        type=str,
        help='identify name of key to decrement')

    parser.add_argument(
        'value',
        type=int,
        help='amount to decrement')

    parser.add_argument(
        '--url',
        type=str,
        default='rest-api:8008',
        help='specify URL of REST API')

    parser.add_argument(
        '--keyfile',
        type=str,
        help="identify file containing user's private key")

    parser.add_argument(
        '--wait',
        nargs='?',
        const=sys.maxsize,
        type=int,
        help='set time, in seconds, to wait for transaction to commit')


def do_mul(args):
    name, value, wait = args.name, args.value, args.wait
    client = _get_client(args)
    response = client.mul(name, value, wait)
    print(response)


def add_show_parser(subparsers, parent_parser):
    message = 'Shows the value of the key <name>.'

    parser = subparsers.add_parser(
        'show',
        parents=[parent_parser],
        description=message,
        help='Displays the specified intkey value')

    parser.add_argument(
        'name',
        type=str,
        help='name of key to show')

    parser.add_argument(
        '--url',
        type=str,
        default='rest-api:8008',
        help='specify URL of REST API')


def do_show(args):
    name = args.name
    client = _get_client(args)
    value = client.show(name)
    print('{}: {}'.format(name, value))

def get_value(args, pubkey):
    client = _get_client(args)
    value = client.show(pubkey)
    print('{}: {}'.format(pubkey, value))
    return value


def add_list_parser(subparsers, parent_parser):
    message = 'Shows the values of all keys in intkey state.'

    parser = subparsers.add_parser(
        'list',
        parents=[parent_parser],
        description=message,
        help='Displays all intkey values')

    parser.add_argument(
        '--url',
        type=str,
        default='rest-api:8008',
        help='specify URL of REST API')


def add_start_parser(subparsers, parent_parser):
    message = 'Start REST-API'

    parser = subparsers.add_parser(
        'start',
        parents=[parent_parser],
        description=message,
        help='Start REST-API')

    parser.add_argument(
        '--url',
        type=str,
        default='rest-api:8008',
        help='specify URL of REST API')

    parser.add_argument(
        '--keyfile',
        type=str,
        help="identify file containing user's private key")

    parser.add_argument(
        '--wait',
        nargs='?',
        const=sys.maxsize,
        type=int,
        help='set time, in seconds, to wait for transaction to commit')


def do_list(args):
    client = _get_client(args)
    results = client.list()
    for pair in results:
        for name, value in pair.items():
            print('{}: {}'.format(name, value))


def _get_client(args):
    return IntkeyClient(
        url=DEFAULT_URL if args.url is None else args.url,
        keyfile=_get_keyfile(args))


def _get_keyfile(args):
    try:
        if args.keyfile is not None:
            return args.keyfile
    except AttributeError:
        return None

    real_user = getpass.getuser()
    home = os.path.expanduser("~")
    key_dir = os.path.join(home, ".sawtooth", "keys")

    return '{}/{}.priv'.format(key_dir, real_user)


def main(prog_name=os.path.basename(sys.argv[0]), args=None):
    if args is None:
        args = sys.argv[1:]
    parser = create_parser(prog_name)
    args = parser.parse_args(args)

    if args.verbose is None:
        verbose_level = 0
    else:
        verbose_level = args.verbose
    setup_loggers(verbose_level=verbose_level)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'set':
        do_set(args)
    elif args.command == 'inc':
        do_inc(args)
    elif args.command == 'dec':
        do_dec(args)
    elif args.command == 'mul':
        do_mul(args)
    elif args.command == 'show':
        do_show(args)
    elif args.command == 'list':
        do_list(args)
    elif args.command == 'start':
        start_rest_api(args, 'shell', 8888)
    elif args.command == 'generate':
        do_generate(args)
    elif args.command == 'populate':
        do_populate(args)
    elif args.command == 'load':
        do_load(args)
    elif args.command == 'create_batch':
        do_create_batch(args)
    elif args.command == 'workload':
        do_workload(args)

    else:
        raise IntKeyCliException("invalid command: {}".format(args.command))


def start_rest_api(args, host, port, connection=None, timeout=300, registry=None,
                   client_max_size=10485760):
    """Builds the web app, adds route handlers, and finally starts the app.
    """
    global global_args

    global_args = args
    loop = ZMQEventLoop()
    asyncio.set_event_loop(loop)

    init_console_logging()
    LOGGER.info('Starting CLINET REST API on %s:%s', host, port)
    loop = asyncio.get_event_loop()
    # connection.open()
    app = web.Application(loop=loop, client_max_size=client_max_size)
    # app.on_cleanup.append(lambda app: connection.close())

    # Add routes to the web app
    # handler = RouteHandler(loop, connection, timeout, registry)

    # app.router.add_post('/batches', handler.submit_batches)
    # app.router.add_get('/batch_statuses', handler.list_statuses)
    app.router.add_route('*', '/register', register_pubkey)
    app.router.add_route('*', '/user', show_user)
    app.router.add_route('*', '/admin/list', list_need_approve)
    app.router.add_route('*', '/admin/approve', approve_public_key)
    app.router.add_route('*', '/will/create', create_will)
    app.router.add_route('*', '/will', show_will)
    app.router.add_route('*', '/will/list', show_will_list)
    app.router.add_route('*', '/will/witness_sign', witness_sign)
    app.router.add_route('*', '/generate_key', generate_key)

    web.run_app(
        app,
        host=host,
        port=port,
        access_log=LOGGER,
        access_log_format='%r: %s status, %b size, in %Tf s')

def init_console_logging(verbose_level=2):
    """
    Set up the console logging for a transaction processor.
    Args:
        verbose_level (int): The log level that the console should print out
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(create_console_handler(verbose_level))


async def register_pubkey(request):
    '''
    Register public key
    :param request:
    :return:
    '''
    if request.method != 'POST':
        return _wrap_response(
            request,
            data=None)


    global global_args
    body = await request.json()

    if 'public_key' not in body:
        return _wrap_response(
            request,
            data={
                'success': False,
                'error': 'Missing public_key'
            },
            status=400)

    if 'status' not in body:
        body['status'] = 'need_review'

    pubkey = body["public_key"]
    LOGGER.info("Registering public key %s" %pubkey)

    client = _get_client(global_args)
    # Save to pending list
    list_pending = None
    try:
        list_pending = get_value(global_args, KEY_NEED_REVIEW)
    except IntkeyClientException:
        client.set(KEY_NEED_REVIEW, [], global_args.wait)
        pass

    if list_pending is None:
        list_pending = []

    if pubkey not in list_pending:
        list_pending.append(pubkey)
    pending_response = client.set(KEY_NEED_REVIEW, list_pending, global_args.wait)
    LOGGER.info(pending_response)

    # Save user
    response = client.set(pubkey, body, global_args.wait)
    LOGGER.info(response)
    return _wrap_response(
        request,
        data={
            'processing': True
        })


async def show_user(request):
    '''
    Show public key
    :param request:
    :return:
    '''
    if request.method != 'GET':
        return _wrap_response(
            request,
            data=None)

    global global_args
    pubkey = request.url.query.get('public_key', None)

    if pubkey is None:
        return _wrap_response(
            request,
            data={
                'success': False,
                'error': 'Missing public_key'
            },
            status=400)

    client = _get_client(global_args)
    body = get_value(global_args, pubkey)
    LOGGER.info(body)
    return _wrap_response(
        request,
        data=body)

async def list_need_approve(request):
    '''
    Show public key
    :param request:
    :return:
    '''
    if request.method != 'GET':
        return _wrap_response(
            request,
            data=None)

    global global_args
    client = _get_client(global_args)

    pending_list = get_value(global_args, KEY_NEED_REVIEW)
    LOGGER.info(pending_list)

    users = []
    for pubkey in pending_list:
        user = get_value(global_args, pubkey)
        users.append(user)


    return _wrap_response(
        request,
        data=users)


async def approve_public_key(request):
    '''
    Register public key
    :param request:
    :return:
    '''
    if request.method != 'GET':
        return _wrap_response(
            request,
            data=None)

    global global_args
    pubkey = request.url.query.get('public_key', None)

    if pubkey is None:
        return _wrap_response(
            request,
            data={
                'success': False,
                'error': 'Missing public_key'
            },
            status=400)

    client = _get_client(global_args)
    body = get_value(global_args, pubkey)
    body['status']='approved'
    response = client.set(pubkey, body, global_args.wait)

    pending_list = get_value(global_args, KEY_NEED_REVIEW)
    if pubkey in pending_list:
        pending_list.remove(pubkey)

    client.set(KEY_NEED_REVIEW, pending_list, global_args.wait)

    return _wrap_response(
        request,
        data=body)


async def create_will(request):
    '''
    Register public key
    :param request:
    :return:
    '''
    if request.method != 'POST':
        return _wrap_response(
            request,
            data=None)

    global global_args
    body = await request.json()

    if 'public_key' not in body:
        return _wrap_response(
            request,
            data={
                'success': False,
                'error': 'Missing public_key'
            },
            status=400)

    pubkey = body["public_key"]
    LOGGER.info("Creating will with  public key %s" %pubkey)
    client = _get_client(global_args)
    
    # Check witnesses
    if 'witnesses' not in body or len(body['witnesses']) == 0:
        body['status'] = 'valid'
    else:
        for wn in body['witnesses']:
            wn_pubkey = wn['public_key']
            
            will_list = []
            try:
                will_list = get_value(global_args, WILL_LIST_PREFIX + wn_pubkey)
            except IntkeyClientException:
                # client.set(WILL_LIST_PREFIX + wn_pubkey, [], global_args.wait)
                pass

            if pubkey not in will_list:
                will_list.append(pubkey)
                # Save will list for user
                client.set(WILL_LIST_PREFIX + wn_pubkey, will_list, global_args.wait)
    
    response = client.set(WILL_PREFIX + pubkey, body, global_args.wait)
    LOGGER.info(response)
    return _wrap_response(
        request,
        data={
            'processing': True
        })


async def show_will(request):
    '''
    Show public key
    :param request:
    :return:
    '''
    if request.method != 'GET':
        return _wrap_response(
            request,
            data=None)

    global global_args
    pubkey = request.url.query.get('public_key', None)

    if pubkey is None:
        return _wrap_response(
            request,
            data={
                'success': False,
                'error': 'Missing public_key'
            },
            status=400)

    client = _get_client(global_args)
    body = get_value(global_args, WILL_PREFIX + pubkey)
    LOGGER.info(body)
    return _wrap_response(
        request,
        data=body)


async def show_will_list(request):
    '''
    Show public key
    :param request:
    :return:
    '''
    if request.method != 'GET':
        return _wrap_response(
            request,
            data=None)

    global global_args
    pubkey = request.url.query.get('public_key', None)

    if pubkey is None:
        return _wrap_response(
            request,
            data={
                'success': False,
                'error': 'Missing public_key'
            },
            status=400)

    client = _get_client(global_args)
    will_list_pubkey = []
    will_list = []
    try:
        will_list_pubkey = get_value(global_args, WILL_LIST_PREFIX + pubkey)
    except IntkeyClientException:
        pass

    for will_pubkey in will_list_pubkey:
        try:
            will = get_value(global_args, WILL_PREFIX + will_pubkey)
            testator = get_value(global_args, will['public_key'])
            will['testator'] = testator
            will_list.append(will)
        except:
            pass

    LOGGER.info(will_list)
    return _wrap_response(
        request,
        data=will_list)


async def witness_sign(request):
    '''
    Show public key
    :param request:
    :return:
    '''
    if request.method != 'GET':
        return _wrap_response(
            request,
            data=None)


    global global_args
    pubkey = request.url.query.get('public_key', None)
    witness = request.url.query.get('witness', None)

    if pubkey is None or witness is None:
        return _wrap_response(
            request,
            data={
                'success': False,
                'error': 'Missing public_key and/or witness param'
            },
            status=400)

    client = _get_client(global_args)
    body = get_value(global_args, WILL_PREFIX + pubkey)
    witnesses = body["witnesses"]

    found_witness = False
    sign_count=0
    for wn in witnesses:
        if 'status' in wn and wn["status"] == 'signed':
            sign_count += 1

        if wn["public_key"] == witness:
            wn["status"] = 'signed'
            found_witness = True
            sign_count += 1

    # Update will list
    # will_list = []
    # try:
    #     will_list = get_value(global_args, WILL_LIST_PREFIX + witness)
    # except IntkeyKeyNotFoundException:
    #     will_list = []
    #     pass
    #
    # if pubkey in will_list:
    #     will_list.remove(pubkey)
    #
    # client.set(WILL_LIST_PREFIX + witness, will_list, global_args.wait)

    # Not found witness
    if not found_witness:
        return _wrap_response(
            request,
            data={
                'success': False,
                'error': 'Witness is not found in this will'
            },
            status=400)

    # All witnesses signed into will => VALID
    if sign_count == len(body['witnesses']):
        body['status'] = 'valid'

    response = client.set(WILL_PREFIX + pubkey, body, global_args.wait)
    LOGGER.info(response)
    LOGGER.info(body)
    return _wrap_response(
        request,
        data=body)


async def generate_key(request):
    '''
    Show public key
    :param request:
    :return:
    '''
    if request.method != 'GET':
        return _wrap_response(
            request,
            data=None)
    import time

    from subprocess import call
    current_time = str(time.time()).split('.')[0]
    call(["sawtooth", "keygen", current_time])

    key_folder = "/root/.sawtooth/keys/"

    with open(key_folder + current_time + ".priv") as f:
        priv_key = f.read()

    with open(key_folder + current_time + ".pub") as f:
        pub_key = f.read()

    return _wrap_response(
        request,
        data={
            'private_key': priv_key,
            'public_key': pub_key
        })

async def option_pass(request):
    return _wrap_response(
        request,
        data=None)


def _wrap_response(request, data=None, metadata=None, status=200):
    """Creates the JSON response envelope to be sent back to the client.
    """
    envelope = metadata or {}

    if data is not None:
        envelope['data'] = data

    return web.Response(
        status=status,
        content_type='application/json',
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept'},
        text=json.dumps(
            envelope,
            indent=2,
            separators=(',', ': '),
            sort_keys=True))

def main_wrapper():
    # pylint: disable=bare-except
    try:
        main()
    except (IntKeyCliException, IntkeyClientException) as err:
        print("Error: {}".format(err), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    except SystemExit as e:
        raise e
    except:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
