from beaker.client import ApplicationClient
from beaker import sandbox

from contracts.crowdfunding.crowdfundingCampaign import CrowdfundingCampaignApp

def demo():
    client = sandbox.get_algod_client()

    accts = sandbox.get_accounts()
    creator_acct = accts[0]
    user_acct = accts[1]

    # Create the Application client containing both an algod client and CrowdfundingCampaignApp
    creator_app_client = ApplicationClient(client, CrowdfundingCampaignApp(), signer=creator_acct.signer)

    # Create the applicatiion on chain, set the app id for the app client
    app_id, app_addr, txid = creator_app_client.create()
    print(f"Created App with id: {app_id} and address addr: {app_addr} in tx: {txid}")

    # Read app global state 
    app_global_state = creator_app_client.get_application_state()
    print(f"[App id: {app_id}] Global state:\n{app_global_state}\n")

    # opt in from the user_acct and retrieve app local state
    user_app_client = creator_app_client.prepare(signer=user_acct.signer)
    user_app_client.opt_in()
    
    user_local_state = user_app_client.get_account_state(account=user_acct.address)
    print(f"[App id: {app_id}] Account {user_acct.address} local state:\n{user_local_state}\n")


if __name__ == "__main__":
    app = CrowdfundingCampaignApp()
    demo()