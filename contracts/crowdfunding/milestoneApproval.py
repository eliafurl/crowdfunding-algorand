from typing import Final

from pyteal import (
    abi,
    TealType,
    Global,
    Int,
    Seq,
    Txn,
    Assert,
    Reject,
    If,
    And,
)

from beaker.application import Application
from beaker.state import (
    ApplicationStateValue,
    AccountStateValue
)

from beaker.decorators import (
    external,
    create,
    opt_in,
)


class MilestoneApprovalApp(Application):

    # global states
    creator: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="Creator of the crowdfunding campaign.",
    )
    
    crowdfunding_address: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="Crowdfunding campaign application address.",
    )

    milestone_to_approve: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Milestone number to be approved.",
    )
    
    milestone_metadata: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="IPFS metadata link providing evidence about the reached milestone.",
    )
    
    vote_end_date: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="UNIX timestamp for when the milestone approval voting ends.",
    )
    
    approve_votes: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Total votes approving the submitted milestone.",
    )
    
    reject_votes: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Total votes rejecting the submitted milestone.",
    )
    
    approval_state: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Current state of the voting: \
            [pending_approval:0, approved:1, rejected:2].",
    )

    # local states
    account_votes: Final[AccountStateValue] = AccountStateValue(
        stack_type=TealType.uint64,
        descr="Total amount of Lymph used to weight the user vote.",
    )

    @create
    def create(self,
        creator: abi.Address,
        crowdfunding_address: abi.Address,
        milestone_to_approve: abi.Uint64,
        vote_end_date: abi.Uint64,
        milestone_metadata: abi.String,
    ):
        return Seq(
            self.initialize_application_state(),
            self.creator.set(creator.get()),
            self.crowdfunding_address.set(crowdfunding_address.get()),
            self.milestone_to_approve.set(milestone_to_approve.get()),
            self.vote_end_date.set(vote_end_date.get()),
            self.milestone_metadata.set(milestone_metadata.get()),
            self.approval_state.set(Int(0))
        )

    @opt_in
    def opt_in(self, vote: abi.Uint8): # vote {0: reject, 1: approve}
        return Seq(
            self.initialize_account_state(),
            If(Txn.sender() != self.creator.get())
            .Then(
                Seq(
                    #TODO: check amount of Lymph and set account votes accordingly
                    # If zero Reject()
                    self.account_votes.set(Int(1)),
                    # cast the vote
                    If(vote.get() == Int(0)) # reject the milestone
                    .Then(
                        self.reject_votes.increment(self.account_votes.get())
                    )
                    .ElseIf(vote.get() == Int(1)) # approve the milestone
                    .Then(
                        self.approve_votes.increment(self.account_votes.get())
                    )
                    .Else(Reject())
                )
            )
        )

    @external
    def vote_settling(self):
        return Seq(
            Assert(Txn.sender() == self.creator.get(), comment="must be called by creator"),
            Assert(
                And(
                    self.vote_end_date.get() < Global.latest_timestamp(),
                    self.approval_state.get() == Int(0) # pending_approval
                ),
                comment="vote window must be ended and voting not already settled"
            ),
            # Evaluate if the milestone has been approved or rejected
            If(self.approve_votes.get() > self.reject_votes.get()) # milestone approved
            .Then(
                Seq(
                    # TODO: Mint M-NFT and transfer it to parent CrowdfundingCampaingApp
                    self.approval_state.set(Int(1))
                )
            ).Else(self.approval_state.set(Int(2))) # milestone rejected
        )



if __name__ == "__main__":

    app = MilestoneApprovalApp()

    try:
        app.dump("./build/milestoneApproval")
        print('\n------------TEAL generation completed!------------\n')
    except Exception as err:
        print('Error: {}'.format(err))