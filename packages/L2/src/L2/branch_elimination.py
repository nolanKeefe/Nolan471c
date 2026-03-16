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


def branch_elimination_term(term: Term) -> Term:
    # Recursively eliminate static branches
    recur = branch_elimination_term

    match term:
        case Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            # recurse to check if they are just immediates on the inside
            left_r = recur(left)
            right_r = recur(right)
            match left_r, right_r:
                case Immediate(value=i1), Immediate(value=i2):
                    # both sides are immediates so we can do the comparison
                    condition = (i1 < i2) if operator == "<" else (i1 == i2)
                    return recur(consequent if condition else otherwise)
                    # get the result and then return the path it would take
                case _:
                    # Condition is not fully known keep the branch whole
                    return Branch(
                        operator=operator,
                        left=left_r,
                        right=right_r,
                        consequent=recur(consequent),
                        otherwise=recur(otherwise),
                    )

        # This is all here for recurrence purposes and to fulfill the term return
        case Let(bindings=bindings, body=body):
            return Let(
                bindings=[(name, recur(val)) for name, val in bindings],
                body=recur(body),
            )

        case Abstract(parameters=parameters, body=body):
            return Abstract(parameters=parameters, body=recur(body))

        case Apply(target=target, arguments=arguments):
            return Apply(target=recur(target), arguments=[recur(a) for a in arguments])

        case Primitive(operator=operator, left=left, right=right):
            return Primitive(operator=operator, left=recur(left), right=recur(right))

        case Load(base=base, index=index):
            return Load(base=recur(base), index=index)

        case Store(base=base, index=index, value=value):
            return Store(base=recur(base), index=index, value=recur(value))

        case Begin(effects=effects, value=value):
            return Begin(effects=[recur(e) for e in effects], value=recur(value))

        case Immediate() | Reference() | Allocate():
            return term

    raise ValueError(f"Unhandled term variant: {term!r}")
