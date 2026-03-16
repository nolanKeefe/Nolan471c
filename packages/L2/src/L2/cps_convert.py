from collections.abc import Callable, Sequence
from functools import partial

from L1 import syntax as L1

from L2 import syntax as L2

"""
k is by convention the continuation
the thing that happens next
cps conversion is setting the "then" field that L1 has (the k)

Use identifiers directly

Continuation has not changed meaning as function that you apply variables to
it is just now in our "meta-language" (compiler language) instead of L1 L2

We will be working on trust as k is created and passed around
We "trust" it wont be bad
"""


def cps_convert_term(
    term: L2.Term,
    k: Callable[[L1.Identifier], L1.Statement],  # identifier -> statement the rest of the computation
    fresh: Callable[[str], str],
) -> L1.Statement:  # this whole thing is producing the statement
    _term = partial(cps_convert_term, fresh=fresh)
    _terms = partial(cps_convert_terms, fresh=fresh)

    match term:
        case L2.Let(bindings=bindings, body=body):
            pass

        case L2.Reference(name=name):  # name is an identifier, takes in name returns that name k-ified
            return k(name)

        # abstracts and applys are gonna be calls to k as per notes in class
        case L2.Abstract(parameters=parameters, body=body):
            pass

        case L2.Apply(target=target, arguments=arguments):
            pass

        case L2.Immediate(value=value):  # k needs a this, we need a uniquified name for it
            # looking at immediates in L1 they need a destination, a value, a then (a statement in L2)
            tmp = fresh("t")  # need to store here for consistency
            return L1.Immediate(
                destination=tmp,  # needs a fresh identifier using t to match with the given tests can chang it in tests if wanted
                value=value,
                then=k(tmp),  # what happens next. need to materialize it an actual L1 statement
            )

        case L2.Primitive(operator=operator, left=left, right=right):
            pass

        case L2.Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            pass

        case L2.Allocate(count=count):
            pass

        case L2.Load(base=base, index=index):
            pass

        case L2.Store(base=base, index=index, value=value):
            pass

        case L2.Begin(effects=effects, value=value):  # pragma: no branch
            pass


def cps_convert_terms(
    terms: Sequence[L2.Term],
    k: Callable[[Sequence[L1.Identifier]], L1.Statement],
    fresh: Callable[[str], str],
) -> L1.Statement:
    _term = partial(cps_convert_term, fresh=fresh)
    _terms = partial(cps_convert_terms, fresh=fresh)

    match terms:
        case []:  # empty case
            return k([])

        case [first, *rest]:  # case of 1 thing with other things
            return _term(first, lambda first: _terms(rest, lambda rest: k([first, *rest])))

        case _:  # pragma: no cover
            raise ValueError(terms)


"""
start at the top
how are we to convert it
"""


def cps_convert_program(
    program: L2.Program,
    # source of fresh variable names, need to pass along as its own thing
    fresh: Callable[[str], str],
) -> L1.Program:
    _term = partial(cps_convert_term, fresh=fresh)

    match program:
        case L2.Program(parameters=parameters, body=body):  # pragma: no branch
            return L1.Program(
                parameters=parameters,
                body=_term(
                    body,  # all the program code we need to analyze
                    lambda value: L1.Halt(
                        value=value
                    ),  # when we start k is a simple where it gives a value and then halts
                ),
            )
