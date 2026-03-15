from collections.abc import Mapping
from functools import partial

from .syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Identifier,
    Immediate,
    Let,
    Load,
    Primitive,
    Reference,
    Store,
    Term,
)

type Context = Mapping[Identifier, None]


def constant_folding_term(
    term: Term,
    context: Context,
) -> Term:  # returns an L2 term
    recur = partial(constant_folding_term, context=context)

    match term:
        case Let(bindings=bindings, body=body):
            # Fold constants inside each binding's value, and in the body
            folded_bindings = [(name, recur(val)) for name, val in bindings]
            return Let(bindings=folded_bindings, body=recur(body))

        case Reference(name=_name):
            # no changes needed
            return term

        case Abstract(parameters=parameters, body=body):
            # Folding inside the lambda body
            return Abstract(parameters=parameters, body=recur(body))

        case Apply(target=target, arguments=arguments):
            # Fold the function and each argument
            return Apply(target=recur(target), arguments=[recur(a) for a in arguments])

        case Immediate():
            pass

        case Primitive(operator=operator, left=left, right=right):
            match operator:  # checks the operator
                case "+":
                    match recur(left), recur(right):
                        # 2 immediates case
                        case Immediate(value=i1), Immediate(value=i2):
                            return Immediate(value=i1 + i2)

                        # left is 0 so it is just the right
                        case Immediate(
                            value=0
                        ), right:  # if the left is 0 we know it's gonna just be right even if it is a var
                            return right

                        # Both sides are addition with an immediate left
                        # (+(+ 1 a) (+ 1 b)) => (+ 2 (+ a b))
                        case [
                            Primitive(operator="+", left=Immediate(value=i1), right=left),
                            Primitive(operator="+", left=Immediate(value=i2), right=right),
                        ]:
                            Primitive(
                                operator="+",
                                left=Immediate(value=i1 + i2),
                                right=Primitive(
                                    operator="+",
                                    left=left,
                                    right=right,
                                ),
                            )
                        # Similar to above but its mixing addition and subtraction
                        # results in a subtraction case to keep consistent
                        # (+(- 1 a) (- 1 b)) => (- 2 (+ a b))
                        case [
                            Primitive(operator="-", left=Immediate(value=i1), right=left),
                            Primitive(operator="-", left=Immediate(value=i2), right=right),
                        ]:
                            Primitive(
                                operator="-",
                                left=Immediate(value=i1 + i2),
                                right=Primitive(
                                    operator="+",
                                    left=left,
                                    right=right,
                                ),
                            )

                        # Swap case for effeciency
                        case (
                            left,
                            Immediate() as right,
                        ):  # Swap the immediate to the correct side for other test functionality
                            return Primitive(
                                operator="+",
                                left=right,
                                right=left,
                            )
                # subtraction case
                case "-":
                    match recur(left), recur(right):
                        case Immediate(value=i1), Immediate(value=i2):  # both are immediates just do the math
                            return Immediate(value=i1 - i2)

                        # No 0 on the left case as that would result in a negative
                        # Immediates can't be negative as we have it

                        case [  # both sides are Primitives with 1 immediate so we can take out the immediates
                            Primitive(operator="-", left=Immediate(value=i1), right=left),
                            Primitive(operator="-", left=Immediate(value=i2), right=right),
                        ]:
                            Primitive(
                                operator="-",  # subtract our "positives" and subtractors
                                left=Immediate(value=i1 + i2),  # add our "positive" immediates
                                right=Primitive(
                                    operator="+",  # add our negatives
                                    left=left,
                                    right=right,
                                ),
                            )

                        case [  # both sides are Primitives with 1 immediate so we can take out the immediates
                            Primitive(operator="+", left=Immediate(value=i1), right=left),
                            Primitive(operator="+", left=Immediate(value=i2), right=right),
                        ]:
                            Primitive(
                                operator="-",
                                left=Immediate(value=i1 + i2),
                                right=Primitive(
                                    operator="+",
                                    left=left,
                                    right=right,
                                ),
                            )

                        case (
                            left,
                            Immediate() as right,
                        ):  # Swap the immediate to the correct side for other test functionality
                            return Primitive(
                                operator="-",
                                left=right,
                                right=left,
                            )
                case "*":
                    match recur(left), recur(right):
                        case Immediate(value=i1), Immediate(value=i2):  # both are immediates just do the math
                            return Immediate(value=i1 * i2)

                        case [  # both sides are Primitives with 1 immediate so we can take out the immediates and multiply them
                            Primitive(operator="*", left=Immediate(value=i1), right=left),
                            Primitive(operator="*", left=Immediate(value=i2), right=right),
                        ]:
                            Primitive(
                                operator="*",
                                left=Immediate(value=i1 * i2),
                                right=Primitive(
                                    operator="*",
                                    left=left,
                                    right=right,
                                ),
                            )

                        case (
                            left,
                            Immediate() as right,
                        ):  # Swap the immediate to the correct side for other test functionality
                            return Primitive(
                                operator="-",
                                left=right,
                                right=left,
                            )

        case Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            pass

        case Allocate():
            pass

        case Load(base=base, index=index):
            pass

        case Store(base=base, index=index, value=value):
            pass
        case Begin(effects=effects, value=value):
            pass
