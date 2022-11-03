import datetime
import time

from beaker.client import ApplicationClient
from beaker import sandbox

from contracts.crowdfunding.milestoneApproval import MilestoneApprovalApp

def demo():
    client = sandbox.get_algod_client()

    accts = sandbox.get_accounts()
    creator_acct = accts[0]
    user_acct = accts[1]

    # Create the Application client containing both an algod client and MilestoneApprovalApp
    creator_app_client = ApplicationClient(client, MilestoneApprovalApp(), signer=creator_acct.signer)

    current_time = datetime.datetime.now(datetime.timezone.utc)
    unix_timestamp = current_time.timestamp()
    unix_timestamp_end = unix_timestamp + (1 * 30) # current + 30 seconds

    print("---------Deploy the contract from creator account")
    # Create the applicatiion on chain, set the app id for the app client. AppArgs:
    # creator: abi.Address,
    # crowdfunding_address: abi.Address,
    # milestone_to_approve: abi.Uint64,
    # vote_end_date: abi.Uint64,
    # milestone_metadata: abi.String,
    app_id, app_addr, txid = creator_app_client.create(
        creator = creator_acct.address,
        crowdfunding_address = creator_acct.address,
        milestone_to_approve = 3,
        vote_end_date = round(unix_timestamp_end),
        milestone_metadata = "ipfs:/milestone_metadata/CID",
    )
    print(f"Created App with id: {app_id} and address addr: {app_addr} in tx: {txid}")

    # Read app global state 
    print_state(creator_app_client)

    # opt in from the creator_acct
    creator_app_client.opt_in(vote=1)

    # opt in from the user_acct and retrieve app local state
    print("---------Opt in the contract from user account and vote")
    user_app_client = creator_app_client.prepare(signer=user_acct.signer)
    user_app_client.opt_in(vote=1)
    
    print_state(creator_app_client, account=user_acct)

    # Read app global state 
    print_state(creator_app_client, states=["approval_state","approve_votes", "reject_votes"])

    # # Wait for the funding time window to close
    time.sleep(35)

    # settle the voting
    print(f"---------Settle the voting from creator account")
    result = creator_app_client.call(MilestoneApprovalApp.vote_settling)

    # Read app global state 
    print_state(creator_app_client, states=["approval_state","approve_votes", "reject_votes"])

def print_state(app_client, states=[], account=""):
    """
    Utility used to retrieve and print the global or local state of an Application/Account.
    
    Args:
    app_client: ApplicationClient used to retrieve the global or local state for the specific Applicaiton
    states: list containing all the states to be printed. Empty for printing all states.
    account: SanboxAccount for retrieving the local state of the account of interest. Required only for local state.
    """

    state = {}
    if not account: # global state
        print(f"[AppID: {app_client.app_id}] Global State")
        state = app_client.get_application_state()
    else:
        print(f"[AppID: {app_client.app_id}] Local State for {account.address}")
        state = app_client.get_account_state(account=account.address)

    if not states:
        states = state.keys()
    for key in states:
        print(f"{key}: {state[key]}")
    print("\n")

if __name__ == "__main__":
    app = MilestoneApprovalApp()
    demo()