from collections import Counter
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
    LetRec,
    Load,
    Primitive,
    Program,
    Reference,
    Store,
    Term,
)

type Context = Mapping[Identifier, None]


def check_program(
    program: Program,
) -> None:
    # recur = partial(check_term, context=context)

    match program:
        case Program(parameters=parameters, body=body):  # no branch
            counts = Counter(parameters)
            duplicates = {name for name, count in counts.items() if count > 1}
            if duplicates:
                raise ValueError(f"duplicate parameters: {duplicates}")

            local = dict.fromkeys(parameters, None)
            check_term(body, context=local)


def check_term(
    term: Term,
    context: Context,
) -> None:
    recur = partial(check_term, context=context)  # noqa: F841

    match term:
        case Let(bindings=bindings, body=body):
            counts = Counter(name for name, _ in bindings)
            duplicates = {name: count for name, count in counts.items() if count > 1}
            if duplicates:
                raise ValueError(f"duplicate bindings: {duplicates}")
            for _, value in bindings:
                recur(value)
            local = dict.fromkeys([name for name, _ in bindings])
            recur(body, context={**context, **local})  # recur on body because it is a reference

        case LetRec(bindings=bindings, body=body):
            counts = Counter(name for name, _ in bindings)
            duplicates = {name: count for name, count in counts.items() if count > 1}
            if duplicates:  # if there are duplicate values it fails
                raise ValueError(f"duplicate bindings: {duplicates}")

            local = dict.fromkeys([name for name, _ in bindings])

            for name, value in bindings:
                recur(value, context={**context, **local})
            check_term(body, {**context, **local})

        # check if reference has a real name if it doesn't then it doesn't exist throw error
        case Reference(name=name):
            if name not in context:
                raise ValueError(f"unknwnown variable: {name}")

        case Abstract():
            pass

        case Apply():
            pass

        case Immediate():  # immediate always passes
            pass

        # We need to check the left and right elements of the primitive for validity
        case Primitive(operator=_operator, left=left, right=right):
            recur(left)
            recur(right)

        case Branch(operator=_operator, left=left, right=right, consequent=_consequent, otherwise=_otherwise):
            recur(left)
            recur(right)

        case Allocate():
            pass

        case Load(base=base, index=_index):
            recur(base)

        case Store():
            pass

        case Begin():  # pragma: no branch
            pass
