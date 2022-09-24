from pyteal import *

count_key = Bytes("Count")

# Create an expression to store 0 in the `Count` global variable and return 1
handle_creation = Seq(
    App.globalPut(count_key, Int(0)),
    Approve()
)

# Main router class
router = Router(
    # Name of the contract
    "my-first-router",
    # What to do for each on-complete type when no arguments are passed (bare call)
    BareCallActions(
        # On create only, just approve
        no_op=OnCompleteAction.create_only(handle_creation),
        # Always let creator update/delete but only by the creator of this contract
        update_application=OnCompleteAction.always(Reject()),
        delete_application=OnCompleteAction.always(Reject()),
        # No local state, don't bother handling it. 
        close_out=OnCompleteAction.never(),
        opt_in=OnCompleteAction.never(),
        clear_state=OnCompleteAction.never(),
    ),
)

@router.method
def increment():
    # Declare the ScratchVar as a Python variable _outside_ the expression tree
    scratchCount = ScratchVar(TealType.uint64)
    return Seq(
        Assert(Global.group_size() == Int(1)),
        # The initial `store` for the scratch var sets the value to 
        # whatever is in the `Count` global state variable
        scratchCount.store(App.globalGet(count_key)), 
        # Increment the value stored in the scratch var 
        # and update the global state variable 
        App.globalPut(count_key, scratchCount.load() + Int(1)),
    )

@router.method
def decrement():
    # Declare the ScratchVar as a Python variable _outside_ the expression tree
    scratchCount = ScratchVar(TealType.uint64)
    return Seq(
        Assert(Global.group_size() == Int(1)),
        # The initial `store` for the scratch var sets the value to 
        # whatever is in the `Count` global state variable
        scratchCount.store(App.globalGet(count_key)),
        # Check if the value would be negative by decrementing 
        If(scratchCount.load() > Int(0),
            # If the value is > 0, decrement the value stored 
            # in the scratch var and update the global state variable
            App.globalPut(count_key, scratchCount.load() - Int(1)),
        ),
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