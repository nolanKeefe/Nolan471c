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
        case Let(bindings=_bindings, body=_body):
            pass

        case Reference(name=_name):
            pass

        case Abstract(parameters=_parameters, body=_body):
            pass

        case Apply(target=_target, arguments=_arguments):
            pass

        case Immediate():
            pass

        case Primitive(operator=operator, left=left, right=right):
            match operator:
                case "+":
                    match recur(left), recur(right):
                        case Immediate(value=i1), Immediate(value=i2):
                            return Immediate(value=i1 + i2)

                        case Immediate(
                            value=0
                        ), right:  # if the left is 0 we know it's gonna just be right even if it is a var
                            return right

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
                        case Immediate(value=i1), Immediate(value=i2):
                            return Immediate(value=i1 + i2)

                        case Immediate(
                            value=0
                        ), right:  # if the left is 0 we know it's gonna just be right even if it is a var
                            return right

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
