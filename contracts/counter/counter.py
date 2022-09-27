from typing import Final

from pyteal import abi, TealType, Global, Int, Seq
from beaker.application import Application
from beaker.state import ApplicationStateValue
from beaker.decorators import external, create, Authorize


class CounterApp(Application):

    counter: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="A counter for showing how to use application state",
    )

    @create
    def create(self):
        return self.initialize_application_state()

    @external(authorize=Authorize.only(Global.creator_address()))
    def increment(self, *, output: abi.Uint64):
        """increment the counter"""
        return Seq(
            self.counter.set(self.counter + Int(1)),
            output.set(self.counter),
        )

    @external(authorize=Authorize.only(Global.creator_address()))
    def decrement(self, *, output: abi.Uint64):
        """decrement the counter"""
        return Seq(
            self.counter.set(self.counter - Int(1)),
            output.set(self.counter),
        )

if __name__ == "__main__":

    approval_filename = "./build/approval.teal"
    clear_filename = "./build/clear.teal"
    interface_filename = "./build/contract.json"
    
    app = CounterApp()

    # export TEAL and ABI in build folder
    with open(approval_filename, "w") as f:
        f.write(app.approval_program)

    with open(clear_filename, "w") as f:
        f.write(app.clear_program)

    import json
    with open(interface_filename, "w") as f:
        f.write(json.dumps(app.contract.dictify()))
    
    print('\n------------TEAL generation completed!------------\n')