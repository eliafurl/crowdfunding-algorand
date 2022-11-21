import datetime
import time

from beaker.client import ApplicationClient
from beaker import sandbox, consts

from algosdk.future import transaction
from algosdk.atomic_transaction_composer import TransactionWithSigner

from contracts.crowdfunding.crowdfundingCampaign import CrowdfundingCampaignApp
from contracts.crowdfunding.milestoneApproval import MilestoneApprovalApp

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
    print_state(creator_app_client)

    # opt in from the creator_acct
    creator_app_client.opt_in()

    # opt in from the user_acct and retrieve app local state
    print("---------Opt in the campaign from user account")
    user_app_client = creator_app_client.prepare(signer=user_acct.signer)
    user_app_client.opt_in()
    
    print_state(user_app_client, account=user_acct)

    # fund the campaign from the user_acct
    print("---------Fund the campaign from user account")
    sp = user_app_client.client.suggested_params()

    result = user_app_client.call(
        CrowdfundingCampaignApp.fund, 
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

    print_state(creator_app_client, ["campaign_state", "collected_funds", "total_backers"])

    print_state(user_app_client, account=user_acct)

    # Wait for the funding time window to close
    time.sleep(35)

    # claim funds
    print("---------Claim funds 0 milestone from creator account")
    result = creator_app_client.call(CrowdfundingCampaignApp.claim_funds)

    print_state(creator_app_client, ["campaign_state", "collected_funds", "total_backers", "milestone_approval_app_id"])

    # claim R-NFT
    #TODO: implement CrowdfundingCampaignApp.claim_reward() and test

    # submit milestone 
    print("---------Submit 1 milestone from creator account")
    # raise the fees for paying the inner transactions
    sp = creator_app_client.client.suggested_params()
    sp.fee = sp.min_fee * 2
    sp.flat_fee = True
    # set voting time window
    current_time = datetime.datetime.now(datetime.timezone.utc)
    end_time = current_time.timestamp() + 10

    # milestone_to_approve: abi.Uint8,
    # milestone_metadata: abi.String,
    # vote_end_date: abi.Uint64,
    milestone_app_id = creator_app_client.call(
        CrowdfundingCampaignApp.submit_milestone,
        milestone_to_approve=1,
        milestone_metadata="ipfs:/milestone_1_metadata/CID",
        vote_end_date=round(end_time),
        suggested_params=sp
    )

    print_state(creator_app_client, ["campaign_state", "collected_funds", "total_backers", "milestone_approval_app_id"])

    # Create the Application client containing both an algod client and MilestoneApprovalApp
    creator_milapp_client = ApplicationClient(client, MilestoneApprovalApp(), app_id=milestone_app_id.return_value, signer=creator_acct.signer)
    print_state(creator_milapp_client)

    print("--[MILESTONE VOTING]---------Opt in the contract from user account")
    user_milapp_client = creator_milapp_client.prepare(signer=user_acct.signer)
    user_milapp_client.opt_in(vote=1) # mandatory vote in opt-in (0: reject, 1: approve)
    print_state(user_milapp_client, account=user_acct)

    # try to call claim_funds while le voting is in progress, it should fail
    try:
        state = creator_app_client.get_application_state()
        result = creator_app_client.call(CrowdfundingCampaignApp.claim_funds, foreign_apps=[state["milestone_approval_app_id"]])
        print_state(creator_app_client, ["campaign_state", "collected_funds", "total_backers", "milestone_approval_app_id"])
    except Exception as err:
        print('Error: {}'.format(err))
        print("OK")

    # Wait for the voting time window to close
    time.sleep(20)

    # settle voting
    print("--[MILESTONE VOTING]---------Vote settling for current milestone")
    result = creator_milapp_client.call(
        MilestoneApprovalApp.vote_settling,
        suggested_params=sp
    )

    print_state(creator_milapp_client, ["approval_state", "approve_votes", "reject_votes"])

    # claim funds
    print("---------Claim funds 1 milestone from creator account")
    state = creator_app_client.get_application_state()
    result = creator_app_client.call(CrowdfundingCampaignApp.claim_funds, foreign_apps=[state["milestone_approval_app_id"]])
    print_state(creator_app_client, ["campaign_state", "collected_funds", "total_backers", "milestone_approval_app_id"])

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
    app = CrowdfundingCampaignApp()
    demo()