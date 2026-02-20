# made for later use in L3 to convert into L2
# from L2 import syntax as L2
# from . import syntax as L3
# based on how it looks from him is its like the check.py but with l3.the case name
# and then some basic conversion stuff of l2. instead of a check for duplicates and stuff like that
# returns on things like branch is return L2.Branch (all the thing in branch = recur(thing in branch))
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
        case L3.Let(bindings=bindings, body=body):
            pass

        case L3.LetRec(bindings=bindings, body=body):
            pass

        case L3.Reference(name=name):
            # if name is a recursive variable -> (Load (Reference name)))
            # else (Reference name)
            pass

        case L3.Abstract(parameters=parameters, body=body):
            pass

        case L3.Apply(target=target, arguments=arguments):
            pass

        case L3.Immediate(value=value):
            return L2.Immediate(value=value)

        case L3.Primitive(operator=_operator, left=left, right=right):
            pass

        case L3.Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            return L2.Branch(
                operator=operator,
                left=recur(left),
                right=recur(right),
                consequent=recur(consequent),
                otherwise=recur(otherwise),
            )

        case L3.Allocate(count=count):
            return L2.Allocate(count=count)

        case L3.Load(base=base, index=index):
            return L2.Load(
                base=recur(base),
                index=index,
            )

        case L3.Store(base=base, index=_index, value=value):
            pass

        case L3.Begin(effects=effects, value=value):  # pragma: no branch
            pass


def eliminate_letrec_program(
    program: L3.Program,
) -> L2.Program:
    match program:
        case L3.Program(parameters=parameters, body=body):  # pragma: no branch
            return L2.Program(
                parameters=parameters,
                body=eliminate_letrec_term(body, {}),
            )
