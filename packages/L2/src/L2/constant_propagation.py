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

"""
How it works: Made an environment (wow its directly below :P)
Then if something is a refrence it checks if its in the environment and then 
substitutes in the immediate. 

Lets extend the environment whenever a binding folds to a constant
bastracts "shadow" parameters so they arent replaced wrong in the lambda body
"""

# Maps variable names to their known constant integer values.
type Env = Mapping[Identifier, int]


def constant_propagation_term(term: Term, env: Env) -> Term:
    """Return a new term with every known-constant reference substituted."""
    recur = partial(constant_propagation_term, env=env)

    match term:
        case Reference(name=name):
            # Replace with the known constant if we have one
            if name in env:
                return Immediate(value=env[name])
            return term

        case Let(bindings=bindings, body=body):
            # Process bindings left-to-right, extending the env as constants
            # are discovered so later bindings can benefit immediately.
            new_env = dict(env)
            new_bindings: list[tuple[Identifier, Term]] = []
            for name, val in bindings:
                propagated = constant_propagation_term(val, new_env)
                new_bindings.append((name, propagated))
                if isinstance(propagated, Immediate):
                    new_env[name] = propagated.value
            return Let(
                bindings=tuple(new_bindings),
                body=constant_propagation_term(body, new_env),
            )

        case Abstract(parameters=parameters, body=body):
            # Parameters shadow any enclosing constants — remove them from env
            inner_env = {k: v for k, v in env.items() if k not in parameters}
            return Abstract(
                parameters=parameters,
                body=constant_propagation_term(body, inner_env),
            )

        case Apply(target=target, arguments=arguments):
            return Apply(
                target=recur(target),
                arguments=tuple(recur(a) for a in arguments),
            )

        case Immediate():
            return term

        case Primitive(operator=operator, left=left, right=right):
            return Primitive(operator=operator, left=recur(left), right=recur(right))

        case Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            return Branch(
                operator=operator,
                left=recur(left),
                right=recur(right),
                consequent=recur(consequent),
                otherwise=recur(otherwise),
            )

        case Allocate():
            return term

        case Load(base=base, index=index):
            return Load(base=recur(base), index=index)

        case Store(base=base, index=index, value=value):
            return Store(base=recur(base), index=index, value=recur(value))

        case Begin(effects=effects, value=value):
            return Begin(effects=tuple(recur(e) for e in effects), value=recur(value))

    # Should be unreachable if all Term variants are handled above
    raise ValueError(f"Unhandled term variant: {term!r}")
