from typing import Final
from webbrowser import get

from pyteal import (
    abi,
    TealType,
    Global,
    Int,
    Seq,
    App,
    Txn,
    Assert,
    Approve,
    Reject,
    If,
    And,
    Subroutine,
    InnerTxnBuilder,
    TxnField,
    TxnType,
    InnerTxn,
    Bytes,
    Itob,
    MethodSignature
)

from beaker.application import (
    Application,
)
from beaker.state import (
    ApplicationStateValue,
    #DynamicApplicationStateValue,
    AccountStateValue
)
from beaker.decorators import (
    external,
    create,
    opt_in,
    Authorize
)

from beaker import consts, sandbox
from beaker.precompile import AppPrecompile

try:
    from milestoneApproval import MilestoneApprovalApp
except ImportError:
    print('Relative import failed')

try:
    from contracts.crowdfunding.milestoneApproval import MilestoneApprovalApp
except ModuleNotFoundError:
    print('Absolute import failed')

class CrowdfundingCampaignApp(Application):

    milestone_app: AppPrecompile = AppPrecompile(MilestoneApprovalApp())

    # global states
    creator: Final[ApplicationStateValue] = ApplicationStateValue( # TODO: Is it really necessary?
        stack_type=TealType.bytes,
        descr="Creator of the crowdfunding campaign.",
    )

    campaign_goal: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Minimum ALGO amount to be collect by the crowdfunding campaign.",
    )

    collected_funds: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Minimum ALGO amount to be collect by the crowdfunding campaign.",
    )

    funds_receiver: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="Address of the funds receiver (address specified by the Creator).",
    )

    total_backers: Final[ApplicationStateValue] = ApplicationStateValue( # TODO: Is it really necessary?
        stack_type=TealType.uint64,
        descr="Total number of backers for the campaign.",
    )

    fund_start_date: Final[ApplicationStateValue] = ApplicationStateValue( # UNIX timestamp
        stack_type=TealType.uint64,
        descr="UNIX timestamp of when the crowdfunding campaign starts.",
    )

    fund_end_date: Final[ApplicationStateValue] = ApplicationStateValue( # UNIX timestamp
        stack_type=TealType.uint64,
        descr="UNIX timestamp of when the crowdfunding campaign endss.",
    )

    total_milestones: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Crowdfunding campaign's total milestones (max 10 milestones).",
    )

    reached_milestone: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        default=Int(0xFFFFFFFFFFFFFFFF),
        descr="Current number of milestones reached.",
    )

    # TODO: use funds_per_milestone for storing the values
    # funds_per_milestone: Final[DynamicApplicationStateValue] = DynamicApplicationStateValue(
    #     stack_type=TealType.uint64,
    #     max_keys=10,
    #     descr="List of funds divided for each milestone (max 10 milestones)",
    # )

    funds_0_milestone: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Funds for 0 milestone",
    )
    
    funds_1_milestone: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Funds for 1st milestone",
    )

    campaign_state: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Current state of the crowdfunding campaign: \
        [funding:0, waiting_for_next_milestone:1, milestone_validation:2, ended:3].",
    )

    milestone_approval_app_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Application ID for the current milestone approval app.",
    )

    RNFT_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="ID for the R-NFT (Reward-NFT).",
    )

    reward_metadata: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="IPFS metadata link about the reward (R-NFT) to be claimed by the user.",
    )

    # local states
    amount_backed: Final[AccountStateValue] = AccountStateValue(
        stack_type=TealType.uint64,
        descr="Total amount of ALGO backed to the campaign by single backer.",
    )

    @create
    def create(self,
        campaign_goal: abi.Uint64,
        funds_receiver: abi.Address,
        fund_start_date: abi.Uint64,
        fund_end_date: abi.Uint64,
        reward_metadata: abi.String,
        total_milestones: abi.Uint64,
        funds_0_milestone: abi.Uint64,
        funds_1_milestone: abi.Uint64,
    ):
        return Seq(
            self.initialize_application_state(),
            self.creator.set(Txn.sender()),
            self.campaign_goal.set(campaign_goal.get()),
            self.funds_receiver.set(funds_receiver.get()),
            self.fund_start_date.set(fund_start_date.get()),
            self.fund_end_date.set(fund_end_date.get()),
            self.reward_metadata.set(reward_metadata.get()),
            self.total_milestones.set(total_milestones.get()),

            # TODO: use funds_per_milestone for storing the values
            # self.set_funds_per_milestone_val(k=Int(0), v=funds_0_milestone.get()),
            # self.set_funds_per_milestone_val(k=Int(1), v=funds_0_milestone.get()), 
            self.funds_0_milestone.set(funds_0_milestone.get()),    
            self.funds_1_milestone.set(funds_1_milestone.get()),
        )

    @opt_in
    def opt_in(self):
        return Seq(
            self.initialize_account_state(),
        )

    @external(authorize=Authorize.opted_in(Global.current_application_id()))
    def fund(self, funding: abi.PaymentTransaction):
        return Seq(
            Assert(
               self.campaign_state.get() == Int(0), comment="campaign must be in funding phase"
            ),
            Assert(
                    funding.get().amount() >= consts.Algos(10), comment="must be greater then 10 algos"
            ),
            Assert(funding.get().receiver() == self.address, comment="must be to me"),
            Assert(self.amount_backed[Txn.sender()].get() == Int(0), comment="must have not yet funded"),

            self.amount_backed[Txn.sender()].set(funding.get().amount()),
            self.collected_funds.increment(self.amount_backed[Txn.sender()].get()),
            self.total_backers.increment(Int(1)),
            Approve(),
        )

    @external(authorize=Authorize.only(Global.creator_address()))
    def claim_funds(self):
        return Seq(
            If(
                And(
                    self.campaign_state.get() == Int(0), # in funding phase
                    self.fund_end_date.get() < Global.latest_timestamp(), # funding window ended
                    self.collected_funds.get() < self.campaign_goal.get() # campaign unsuccessful
                )
            )
            .Then(self.campaign_state.set(Int(3))) # campaign ended unsuccessfully
            .ElseIf(
                And(
                    self.campaign_state.get() == Int(0), # in funding phase
                    self.fund_end_date.get() < Global.latest_timestamp(), # funding window ended
                    self.collected_funds.get() >= self.campaign_goal.get(), # campaign successful
                )
            )
            .Then(
                Seq( # campaign funded successfully, mint R-NFT and transfer first funds
                    self.RNFT_id.set(self.mint_RNFT()), 
                    self.reached_milestone.set(Int(0)),
                    #Transfer funds_per_milestone[reached_milestone] to funds_receiver
                    #TODO: implement
                )
            )
            .ElseIf(
                self.campaign_state.get() == Int(2) # Campaign already funded. Milestone submitted
            )
            .Then(
                # Reject if the voting is in progress
                #TODO: implement -> Assert (MilestoneApprovalApp.approval_state == pending_approval)
                # If(MilestoneApprovalApp.approval_state == approved) # Milestone approved.
                # .Then(self.reached_milestone.increment(Int(1)))
                # Transfer funds_per_milestone[reached_milestone] to funds_receiver

                self.milestone_approval_app_id.set(Int(0)),
                #TODO: MilestoneApprovalApp.delete()
            )
            .Else(Reject()),

            # Check that all the milestones have been completed
            If(self.reached_milestone.get() == (self.total_milestones.get() - Int(1)))
            .Then(self.campaign_state.set(Int(3))) # campaign: ended
            .Else(self.campaign_state.set(Int(1))), # campaign: waiting for next milestone
            Approve()
        )

    @external(authorize=Authorize.only(Global.creator_address()))
    def submit_milestone(self,
        milestone_to_approve: abi.Uint64,
        milestone_metadata: abi.String,
        vote_end_date: abi.Uint64,
        *,
        output: abi.Uint64 # milestone_approval_app_id
    ):
        return Seq(
            Assert(self.campaign_state.get() == Int(1), comment="must be in waiting_for_next_milestone state"),
            # Create the MilestoneApprovalApp
            # creator: abi.Address,
            # crowdfunding_address: abi.Address,
            # milestone_to_approve: abi.Uint64,
            # vote_end_date: abi.Uint64,
            # milestone_metadata: abi.String,
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.ApplicationCall,
                    TxnField.approval_program: self.milestone_app.approval.binary,
                    TxnField.clear_state_program: self.milestone_app.clear.binary,
                    TxnField.global_num_uints: Int(5),
                    TxnField.global_num_byte_slices: Int(3),
                    TxnField.local_num_uints: Int(1),
                    TxnField.local_num_byte_slices: Int(0),
                    TxnField.fee: Int(0),
                    TxnField.application_args: [
                            MethodSignature("create(address,address,uint64,uint64,string)void"),
                            Global.creator_address(),
                            Global.current_application_address(),
                            milestone_to_approve.encode(),
                            vote_end_date.encode(),
                            milestone_metadata.encode()
                        ],
                }
            ),
            InnerTxnBuilder.Submit(),

            # Set milestone_approval_app_id
            self.milestone_approval_app_id.set(InnerTxn.created_application_id()),
            
            self.campaign_state.set(Int(2)), # in milestone_validation phase
            output.set(self.milestone_approval_app_id.get())
        )

    @Subroutine(TealType.uint64) 
    def mint_RNFT(): # output: RNFT ID
        return Int(1) #TODO: implementation

    # def set_funds_per_milestone_val(self, k: abi.Uint8, v: abi.Uint64):
    #     return self.funds_per_milestone[k].set(v.get())

    # @internal(read_only=True)
    # def get_funds_per_milestone_val(self, k: abi.Uint8, *, output: abi.Uint64):
    #     return output.set(self.funds_per_milestone[k])

if __name__ == "__main__":

    app = CrowdfundingCampaignApp()
    try:
        app.dump("./build/crowdfundingCampaign", client=sandbox.get_algod_client())
        print('\n------------TEAL generation completed!------------\n')
    except Exception as err:
        print('Error: {}'.format(err))