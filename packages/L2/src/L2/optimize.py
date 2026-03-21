from .branch_elimination import branch_elimination_term
from .constant_folding import constant_folding_term
from .constant_propagation import constant_propagation_term
from .dead_code_elim import dead_code_elimination_term
from .syntax import (
    Program,
    Term,
)

"""
controls the optimization overall, the number of repetitions, to a fixed point (until it stops changing)
Order of operation
  1. Constant propagation
  2. Constant folding
  3. Dead code elimination
  4. Branch elimination
"""

# Single-pass optimisation of a Term


def optimize_term(term: Term) -> Term:
    """Apply all passes once, in order."""
    # 1. Propagate known constants downward
    term = constant_propagation_term(term, env={})
    # 2. Fold constant expressions
    term = constant_folding_term(term, context={})
    # 3. Eliminate dead (unreferenced, pure) bindings
    term = dead_code_elimination_term(term)
    # 4. Eliminate branches whose condition is now statically known
    term = branch_elimination_term(term)
    return term


# main running of it
# currently set to do an arbitrary max of 100 iterations but you could make it more
# use 100 to prevent any weird infinite loop stuff
def optimize_program(program: Program, max_iterations: int = 100) -> Program:
    # Should run until we no longer see meaningful change
    for _ in range(max_iterations):  # pragma: no branch
        optimized_body = optimize_term(program.body)
        new_program = Program(parameters=program.parameters, body=optimized_body)

        # check if it's changed at all after the pass
        if new_program.model_dump() == program.model_dump():
            break  # they didnt change so break out of the loop

        program = new_program

    return program
