from beaker.client import ApplicationClient, LogicException
from beaker import sandbox

from contracts.counter.counter import CounterApp

def demo():
    client = sandbox.get_algod_client()

    accts = sandbox.get_accounts()
    acct = accts.pop()

    # Create an Application client containing both an algod client and my app
    app_client = ApplicationClient(client, CounterApp(), signer=acct.signer)

    # Create the applicatiion on chain, set the app id for the app client
    app_id, app_addr, txid = app_client.create()
    print(f"Created App with id: {app_id} and address addr: {app_addr} in tx: {txid}")

    app_client.call(CounterApp.increment)
    app_client.call(CounterApp.increment)
    app_client.call(CounterApp.increment)
    result = app_client.call(CounterApp.increment)
    print(f"Currrent counter value: {result.return_value}")

    result = app_client.call(CounterApp.decrement)
    print(f"Currrent counter value: {result.return_value}")

    try:
        # Try to call the increment method with a different signer, it should fail
        # since we have the auth check
        other_acct = accts.pop()
        other_client = app_client.prepare(signer=other_acct.signer)
        other_client.call(CounterApp.increment)
    except LogicException as e:
        print("App call failed as expected.")
        print(e)


if __name__ == "__main__":
    ca = CounterApp()
    demo()