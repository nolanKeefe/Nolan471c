# should control the optimization overall, the number of repetitions, to a fixed point (until it stops changing)
from .syntax import Program


def optimize_program(
    program: Program,
) -> Program:
    return program


# Primitive
# When processing an addition expression, we can always produce one of the following for both left and right:
# an integer constant
# (+ 1 1) immediate
# an addition expression with an integer constant on the left but not right
# (+ 1 x) immediate/not immediate = no change
# an addition expression in which neither sub-expression is a constant
# (+ x y) not immediate/not immediate = no change
