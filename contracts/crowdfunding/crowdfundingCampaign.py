from pyteal import *

# Global states
global_amount = Bytes("total_amount")  # int
global_start_date = Bytes("start_date")  # int
global_end_date = Bytes("end_date")  # int
global_creator = Bytes("cretor")  # byteslice
global_receiver = Bytes("receiver")  # byteslice

# local states
local_amount = Bytes("amount")  # int

# initialize the global states
handle_creation = Seq(
    # TODO: check number of arguments, transactions, ecc.
    App.globalPut(global_amount, Int(0)),
    # TODO: manage dates
    App.globalPut(global_start_date, Int(0)),
    App.globalPut(global_end_date, Int(0)),
    # TODO: add accounts to the creation or manage the initialization with another transaction
    App.globalPut(global_creator, Txn.accounts[0]),
    App.globalPut(global_receiver, Bytes("test")),
    Approve()
)

# initialize local states
handle_optin = Seq(
    App.localPut(Txn.accounts[0], local_amount, Int(0)),
    Approve()
)

# main router class
router = Router(
    # name of the contract
    "crowdfunding-campaign",
    # what to do for each on-complete type when no arguments are passed (bare call)
    BareCallActions(
        # on create only
        no_op=OnCompleteAction.create_only(handle_creation),
        # always let creator update/delete but only by the creator of this contract
        # TODO: manage update and delete application
        update_application=OnCompleteAction.always(Reject()),
        delete_application=OnCompleteAction.always(Reject()),
        # TODO: implement close out 
        close_out=OnCompleteAction.never(),
        # TODO: allow opt_in
        opt_in=OnCompleteAction.never(),
        clear_state=OnCompleteAction.never(),
    ),
)

#@router.method
#def configure(start_date: Expr, end_date: Expr):
#    return Approve()

def check_rekey_zero(
    num_transactions: int,
):
    return Assert(
        And(
            *[
                Gtxn[i].rekey_to() == Global.zero_address()
                for i in range(num_transactions)
            ]
        )
    )


def check_self(
    group_size: Expr = Int(1),
    group_index: Expr = Int(0),
):
    return Assert(
        And(
            Global.group_size() == group_size,
            Txn.group_index() == group_index,
        )
    )

def compile():
    approval_program, clear_program, contract = router.compile_program(version=6)
    return approval_program, clear_program, contract

if __name__ == '__main__':
    import sys

    approval_filename = sys.argv[1]
    clear_filename = sys.argv[2]
    interface_filename = sys.argv[3]

    # Compile the program
    approval_program, clear_program, contract = compile()

    # print out the results
    #print(approval_program)
    #print(clear_program)

    # save TEAL in build folder
    with open(approval_filename, "w") as f:
        f.write(approval_program)

    with open(clear_filename, "w") as f:
        f.write(clear_program)

    import json
    with open(interface_filename, "w") as f:
        f.write(json.dumps(contract.dictify()))

    
    print('\nBuild completed!\n')