from platform import platform
from webbrowser import get
from algosdk.v2client.algod import AlgodClient
from algosdk.kmd import KMDClient
from algosdk.future import transaction
from algosdk import account

from contracts.crowdfunding.crowdfundingCampaign import compile

algod_address = 'http://localhost:4001'
algod_token = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'

def main():
    # initialize an AlgodClient
    algod_client = AlgodClient(algod_token, algod_address)

    # retrieve useful addreses
    private_keys = get_keys_from_wallet(get_kmd_client())
    
    private_key_founder = private_keys[0]
    founder = account.address_from_private_key(private_key_founder)
    print('Founder account: {}\n'.format(founder))
    
    private_key_user = private_keys[1]
    user = account.address_from_private_key(private_key_user)
    print('User account: {}\n'.format(user))
    
    private_key_platform = private_keys[2]
    platform = account.address_from_private_key(private_key_platform)
    print('Platform account: {}\n'.format(platform))

    # compile pyteal to TEAL
    approval_source, clear_source, contract = compile()

    # compile and encode (64 bytes) the TEAL
    approval_compiled = compile_program(algod_client, approval_source)
    clear_compiled = compile_program(algod_client, clear_source)
    
    # create new application
    print('-----------------------')
    print('Creating new application...')
    # declare application state storage (immutable)
    local_ints = 0
    local_bytes = 1
    global_ints = 3
    global_bytes = 2

    # define schema
    global_schema = transaction.StateSchema(global_ints, global_bytes)
    local_schema = transaction.StateSchema(local_ints, local_bytes)

    # deploy new application
    app_id = create_app(algod_client, private_key_founder, approval_compiled, clear_compiled, global_schema, local_schema)
    assert(app_id > 0)

    # call increment method
    print('-----------------------')
    #print('Call increment method...')
    #call_app(algod_client, private_key_founder, app_id, contract, 'increment', [])

    # read global state of application
    print('Global state:', read_global_state(algod_client, app_id))
    # TODO: implement correctly read_local_state
    # print('Local state of {}:\n{}'.format(founder, read_local_state(algod_client, app_id, '')))



# TODO: move to helpers.py
import base64
from algosdk.future import transaction
# helper function to compile program source (TEAL)
def compile_program(client, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])

# create new application
def create_app(client, private_key, compiled_approval_program, compiled_clear_program, global_schema, local_schema):
    # define sender as creator
    sender = account.address_from_private_key(private_key)

    # declare on_complete as NoOp
    on_complete = transaction.OnComplete.NoOpOC.real

    # get node suggested parameters
    params = client.suggested_params()

    # create unsigned transaction
    txn = transaction.ApplicationCreateTxn(sender, params, on_complete, \
                                            compiled_approval_program, compiled_clear_program, \
                                            global_schema, local_schema)

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # wait for confirmation
    try:
        transaction_response = transaction.wait_for_confirmation(client, tx_id, 4)
        print('TXID: ', tx_id)
        print('Result confirmed in round: {}'.format(transaction_response['confirmed-round']))

    except Exception as err:
        print(err)
        return

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response['application-index']
    print('Created new app-id:', app_id)

    return app_id

from algosdk.atomic_transaction_composer import *
# call application
def call_app(client, private_key, app_id, contract, method, method_args=[]):
    # get sender address
    sender = account.address_from_private_key(private_key)
    # create a Signer object 
    signer = AccountTransactionSigner(private_key)

    # get node suggested parameters
    sp = client.suggested_params()

    # Create an instance of AtomicTransactionComposer
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=app_id,
        method=contract.get_method_by_name(method),
        sender=sender,
        sp=sp,
        signer=signer,
        method_args=method_args,
    )

    # send transaction
    results = atc.execute(client, 2)

    # wait for confirmation
    print('TXID: ', results.tx_ids[0])
    print('Result confirmed in round: {}'.format(results.confirmed_round))

# helper function that formats global state for printing
def format_state(state):
    formatted = {}
    for item in state:
        key = item['key']
        value = item['value']
        formatted_key = base64.b64decode(key).decode('utf-8')
        if value['type'] == 1:
            # byte string
            if formatted_key == 'voted':
                formatted_value = base64.b64decode(value['bytes']).decode('utf-8')
            else:
                formatted_value = value['bytes']
            formatted[formatted_key] = formatted_value
        else:
            # integer
            formatted[formatted_key] = value['uint']
    return formatted

# helper function to read app global state
def read_global_state(client, app_id):
    app = client.application_info(app_id)
    global_state = app['params']['global-state'] if 'global-state' in app['params'] else []
    return format_state(global_state)

# helper function to read app local state
def read_local_state(client, app_id, account):
    results = client.account_info(account)
    for local_state in results["apps-local-state"]:
        if local_state["id"] == app_id:
            if "key-value" not in local_state:
                return {}
            return format_state(local_state["key-value"])
    return {}


# TODO: move to utils.py

def get_kmd_client(address='http://localhost:4002', token='a' * 64) -> KMDClient:
    return KMDClient(token, address)


def get_keys_from_wallet(
    kmd_client: KMDClient, wallet_name='unencrypted-default-wallet', wallet_password=''
) -> list[str] | None:
    wallets = kmd_client.list_wallets()

    handle = None
    for wallet in wallets:
        if wallet['name'] == wallet_name:
            handle = kmd_client.init_wallet_handle(wallet['id'], wallet_password)
            break

    if handle is None:
        raise Exception('Could not find wallet')

    private_keys = None
    try:
        addresses = kmd_client.list_keys(handle)
        private_keys = [
            kmd_client.export_key(handle, wallet_password, address)
            for address in addresses
        ]
    finally:
        kmd_client.release_wallet_handle(handle)

    return private_keys
if __name__ == '__main__':
    main()