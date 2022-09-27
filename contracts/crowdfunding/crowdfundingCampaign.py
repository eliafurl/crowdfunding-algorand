from typing import Final

from pyteal import abi, TealType, Global, Int, Seq
from beaker.application import Application
from beaker.state import ApplicationStateValue, AccountStateValue
from beaker.decorators import external, create, opt_in, Authorize


class CrowdfundingCampaignApp(Application):

    # global states
    total_amount: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Actual amount collected by the crowdfunding campaign",
    )

    start_date: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Crowdfunding campaign's start date",
    )

    end_date: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Crowdfunding campaign's end date",
    )

    creator: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="Crowdfunding campaign's creator",
    )

    receiver: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="Crowdfunding campaign's funds receiver",
    )

    # local states
    account_amount: Final[AccountStateValue] = AccountStateValue(
        stack_type=TealType.uint64,
        descr="Actual amount funded by the current account",
    )

    @create
    def create(self):
        return self.initialize_application_state()

    @opt_in
    def opt_in(self):
        return self.initialize_account_state()

if __name__ == "__main__":

    approval_filename = "./build/approval.teal"
    clear_filename = "./build/clear.teal"
    interface_filename = "./build/contract.json"
    
    app = CrowdfundingCampaignApp()

    # save TEAL and ABI in build folder
    with open(approval_filename, "w") as f:
        f.write(app.approval_program)

    with open(clear_filename, "w") as f:
        f.write(app.clear_program)

    import json
    with open(interface_filename, "w") as f:
        f.write(json.dumps(app.contract.dictify()))
    
    print('\n------------TEAL generation completed!------------\n')