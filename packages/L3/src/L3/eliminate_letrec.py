#  Made to convert L3 into L2

# L3.Reference(name = name) becomes
# if name is a recursive variable -> Load(reference name)))
# else return Reference(name = name)
# noqa: F841
from collections.abc import Mapping
from functools import partial

from L2 import syntax as L2

from . import syntax as L3

type Context = Mapping[L3.Identifier, None]


def eliminate_letrec_term(
    term: L3.Term,
    context: Context,
) -> L2.Term:
    recur = partial(eliminate_letrec_term, context=context)

    match term:
        case L3.Let(
            bindings=bindings, body=body
        ):  # we can just convert the let into an L2 let since it is the same in both languages
            return L2.Let(
                bindings=[(name, recur(value)) for name, value in bindings],
                body=recur(body),
            )

        case L3.LetRec(bindings=bindings, body=body):
            pass

        case L3.Reference(name=name):
            # if name is a recursive variable -> (Load (Reference name)))
            # else (Reference name)
            if (
                name not in context
            ):  # if its not in the context then it is a recursive variable so we need to return a load of the reference
                return L2.Load(base=L2.Reference(name=name), index=0)
            else:  # otherwise we can just return the reference in L2
                return L2.Reference(name=name)

        case L3.Abstract(parameters=_parameters, body=body):
            pass

        case L3.Apply(target=_target, arguments=_arguments):
            pass

        case L3.Immediate(value=value):  # pragma: no branch
            return L2.Immediate(value=value)

        case L3.Primitive(operator=_operator, left=left, right=right):  # pragma: no branch
            return L2.Primitive(
                operator=_operator,
                left=recur(left),
                right=recur(right),
            )

        case L3.Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            return L2.Branch(
                operator=operator,
                left=recur(left),
                right=recur(right),
                consequent=recur(consequent),
                otherwise=recur(otherwise),
            )

        case L3.Allocate(count=count):  # pragma: no branch
            return L2.Allocate(count=count)

        case L3.Load(base=base, index=index):  # pragma: no branch
            return L2.Load(
                base=recur(base),
                index=index,
            )

        case L3.Store(base=base, index=index, value=value):  # pragma: no branch
            return L2.Store(
                base=recur(base),
                index=index,
                value=recur(value),
            )

        case L3.Begin(effects=_effects, value=value):  # pragma: no branch
            return L2.Begin(effects=[], value=recur(value))


def eliminate_letrec_program(
    program: L3.Program,
) -> L2.Program:
    match program:
        case L3.Program(parameters=parameters, body=body):  # pragma: no branch
            return L2.Program(parameters=parameters, body=eliminate_letrec_term(body, {}))
