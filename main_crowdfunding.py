import datetime
import time

from beaker.client import ApplicationClient
from beaker import sandbox, consts

from algosdk.future import transaction
from algosdk.atomic_transaction_composer import TransactionWithSigner

from contracts.crowdfunding.crowdfundingCampaign import CrowdfundingCampaignApp

def demo():
    client = sandbox.get_algod_client()

    accts = sandbox.get_accounts()
    creator_acct = accts[0]
    user_acct = accts[1]

    # Create the Application client containing both an algod client and CrowdfundingCampaignApp
    creator_app_client = ApplicationClient(client, CrowdfundingCampaignApp(), signer=creator_acct.signer)

    current_time = datetime.datetime.now(datetime.timezone.utc)
    unix_timestamp = current_time.timestamp()
    unix_timestamp_end = unix_timestamp + (1 * 30) # current + 30 seconds

    print("---------Deploy the contract from creator account")
    # Create the applicatiion on chain, set the app id for the app client. AppArgs:
    # campaign_goal: abi.Uint64,
    # funds_receiver: abi.Byte,
    # fund_start_date: abi.Uint64,
    # fund_end_date: abi.Uint64,
    # reward_metadata: abi.Byte,
    # total_milestones: abi.Uint8,
    # funds_0_milestone: abi.Uint64,
    # funds_1_milestone: abi.Uint64,
    app_id, app_addr, txid = creator_app_client.create(
        campaign_goal = 10 * consts.algo,
        funds_receiver = creator_acct.address,
        fund_start_date = round(unix_timestamp),
        fund_end_date = round(unix_timestamp_end),
        reward_metadata = "ipfs:/metadata/CID",
        total_milestones = 2,
        funds_0_milestone = 7 * consts.algo,
        funds_1_milestone = 3 * consts.algo
    )
    print(f"Created App with id: {app_id} and address addr: {app_addr} in tx: {txid}")

    # Read app global state 
    app_global_state = creator_app_client.get_application_state()
    print(f"[App id: {app_id}] Global state:\n{app_global_state}\n")

    # opt in from the creator_acct
    creator_app_client.opt_in()

    # opt in from the user_acct and retrieve app local state
    print("---------Opt in the contract from user account")
    user_app_client = creator_app_client.prepare(signer=user_acct.signer)
    user_app_client.opt_in()
    
    user_local_state = user_app_client.get_account_state(account=user_acct.address)
    print(f"[App id: {app_id}] Account {user_acct.address} local state:\n{user_local_state}\n")

    # fund the campaign from the user_acct
    print("---------Fund the campaign from user account")
    sp = user_app_client.client.suggested_params()

    result = user_app_client.call(CrowdfundingCampaignApp.fund, 
        funding = TransactionWithSigner(
            txn = transaction.PaymentTxn(
                sender = user_acct.address, 
                sp = sp,
                receiver = app_addr, 
                amt = 15 * consts.algo
            ),
            signer=user_acct.signer,
        )
    )

    app_global_state = creator_app_client.get_application_state()
    print(f"[App id: {app_id}] Global state:\n{app_global_state}\n")

    user_local_state = user_app_client.get_account_state(account=user_acct.address)
    print(f"[App id: {app_id}] Account {user_acct.address} local state:\n{user_local_state}\n")

    # Wait for the funding time window to close
    time.sleep(30)

    # claim funds
    print("---------Claim funds 0 milestone from creator account")
    result = creator_app_client.call(CrowdfundingCampaignApp.claim_funds)

    app_global_state = creator_app_client.get_application_state()
    print(f"[App id: {app_id}] Global state:\n{app_global_state}\n")

    # claim R-NFT
    #TODO: implement CrowdfundingCampaignApp.claim_reward() and test

    # submit milestone 
    #TODO: implement CrowdfundingCampaignApp.submit_milestone() and test

    # claim funds
    print("---------Claim funds 1 milestone from creator account")





if __name__ == "__main__":
    app = CrowdfundingCampaignApp()
    demo()