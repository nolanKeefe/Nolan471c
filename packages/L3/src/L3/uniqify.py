from collections.abc import Callable, Mapping
from functools import partial

from util.sequential_name_generator import SequentialNameGenerator

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

type Context = Mapping[Identifier, Identifier]  # makes name unique


def uniqify_term(
    term: Term,
    context: Context,
    fresh: Callable[[str], str],
) -> Term:
    _term = partial(uniqify_term, context=context, fresh=fresh)

    match term:
        case Let(bindings=bindings, body=body):
            local = dict(context)
            new_bindings: list[tuple[Identifier, Term]] = []

            for name, val in bindings:
                # Process RHS first, using context BEFORE this name is added.
                # So Reference("x") still looks up the OUTER "x" -> "y"
                new_val = uniqify_term(val, context, fresh)
                # Only AFTER processing RHS do we freshen this name
                # and add it to context for subsequent bindings and body
                fresh_name = fresh(name)
                local[name] = fresh_name

                new_bindings.append((fresh_name, new_val))

            return Let(
                bindings=new_bindings,
                body=uniqify_term(body, local, fresh),
            )

        case LetRec(bindings=bindings, body=body):
            # need to freshen all names first and then process things
            local = dict(context)
            for name, _ in bindings:
                local[name] = fresh(name)
            new_bindings = [(local[name], uniqify_term(val, local, fresh)) for name, val in bindings]
            return LetRec(bindings=new_bindings, body=uniqify_term(body, local, fresh))

        case Reference(name=name):
            # need to look at name in context to get replacement
            return Reference(name=context[name])

        case Abstract(parameters=parameters, body=body):
            local = dict(context)
            fresh_params: list[Identifier] = []
            for param in parameters:
                fresh_param = fresh(param)
                local[param] = fresh_param
                fresh_params.append(fresh_param)
            return Abstract(
                parameters=fresh_params,
                body=uniqify_term(body, local, fresh),
            )

        case Apply(target=target, arguments=arguments):
            # need to recurse into parts
            return Apply(target=_term(target), arguments=[_term(arg) for arg in arguments])

        case Immediate():
            # no name return
            return term

        case Primitive(operator=operator, left=left, right=right):
            # need to recurse into each part
            return Primitive(operator=operator, left=_term(left), right=_term(right))

        case Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            # need to recurse into the branch parts
            return Branch(
                operator=operator,
                left=_term(left),
                right=_term(right),
                consequent=_term(consequent),
                otherwise=_term(otherwise),
            )

        case Allocate():
            # no name return
            return term

        case Load(base=base, index=index):
            # need to recur into base but index is just a flat num so its good
            return Load(base=_term(base), index=index)

        case Store(base=base, index=index, value=value):
            # same as above just with value now which is able to be a variable
            return Store(base=_term(base), index=index, value=_term(value))

        case Begin(effects=effects, value=value):  # pragma: no branch
            # recursively uniqify each effect is the only special part
            return Begin(effects=[_term(effect) for effect in effects], value=_term(value))


# A sequential name generator made for name uniqueness
def uniqify_program(
    program: Program,
) -> tuple[Callable[[str], str], Program]:
    fresh = SequentialNameGenerator()

    _term = partial(uniqify_term, fresh=fresh)  # curried function(?) he says

    match program:  # for each of the parameters make a new context where it is a fresh of that thing
        case Program(parameters=parameters, body=body):  # pragma: no branch
            local = {parameter: fresh(parameter) for parameter in parameters}
            return (
                fresh,
                Program(
                    parameters=[
                        local[parameter] for parameter in parameters
                    ],  # renamed to renames Look up new name of param and use it instead
                    body=_term(body, local),
                ),
            )
