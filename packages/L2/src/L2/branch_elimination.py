from .syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Immediate,
    Let,
    Load,
    Primitive,
    Reference,
    Store,
    Term,
)

"""
Removes Branch nodes whose condition is statically decidable — i.e. both
operands of the condition are known integer constants at compile time.

"""


def branch_elimination_term(term: Term) -> Term:
    # Recursively eliminate statically-decidable Branch nodes from term
    recur = branch_elimination_term

    match term:
        case Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            # Recurse into the condition operands first — a nested pass may
            # have turned them into Immediates that we can now evaluate.
            left_r = recur(left)
            right_r = recur(right)
            match left_r, right_r:
                case Immediate(value=i1), Immediate(value=i2):
                    # Both sides of the condition are now known constants.
                    # Evaluate the condition at compile time and return only
                    # the branch arm that would have been taken — the other
                    # arm is unreachable and is dropped entirely.
                    condition = (i1 < i2) if operator == "<" else (i1 == i2)
                    return recur(consequent if condition else otherwise)
                case _:
                    # Condition is not fully known — keep the Branch but still
                    # recurse into both arms to clean up anything inside them.
                    return Branch(
                        operator=operator,
                        left=left_r,
                        right=right_r,
                        consequent=recur(consequent),
                        otherwise=recur(otherwise),
                    )

        case Let(bindings=bindings, body=body):
            return Let(
                bindings=tuple((name, recur(val)) for name, val in bindings),
                body=recur(body),
            )

        case Abstract(parameters=parameters, body=body):
            return Abstract(parameters=parameters, body=recur(body))

        case Apply(target=target, arguments=arguments):
            return Apply(target=recur(target), arguments=tuple(recur(a) for a in arguments))

        case Primitive(operator=operator, left=left, right=right):
            return Primitive(operator=operator, left=recur(left), right=recur(right))

        case Load(base=base, index=index):
            return Load(base=recur(base), index=index)

        case Store(base=base, index=index, value=value):
            return Store(base=recur(base), index=index, value=recur(value))

        case Begin(effects=effects, value=value):
            return Begin(effects=tuple(recur(e) for e in effects), value=recur(value))

        case Immediate() | Reference() | Allocate():
            return term
