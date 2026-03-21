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
Remove bindings who never get used

not used:
if its name does not appear free in the body of the Let.
or if evaluating it can have no observable side-effects.  

Can't change load stores and begins due to not knowing how their
allocations change stuff

needs to be bottom up as discussed in class
"""


# Helpers


def free_variables(term: Term) -> frozenset[Identifier]:
    """Return the set of variable names that are *used but not defined* in term.

    A variable is "free" in a term if it is referenced inside that term but
    not introduced (bound) by that same term.  This tells us which names a
    term depends on from its surrounding context.
    """
    match term:
        case Reference(name=name):
            # A bare variable reference — the name itself is free.
            return frozenset({name})

        case Let(bindings=bindings, body=body):
            # A Let introduces new names, so we must be careful:
            #   - Each binding's *value* can use names from outer scope or
            #     from bindings that appear earlier in the same Let.
            #   - The names introduced by the bindings are NOT free in the
            #     Let as a whole — they are "consumed" internally.
            #
            # We walk the bindings left-to-right, tracking which names have
            # been introduced so far in `bound`.
            #
            # Example:  let a = x        # free in value: {x}
            #               b = a + y    # free in value: {a, y}, but a is bound -> {y}
            #           in  b + z        # free in body:  {b, z}, but b is bound -> {z}
            #
            # Overall free variables: {x, y, z}
            bound: set[Identifier] = set()
            fvs: set[Identifier] = set()
            for name, val in bindings:
                # Collect free variables of this value, minus names already bound
                fvs |= free_variables(val) - bound
                # Mark this name as bound for subsequent bindings and the body
                bound.add(name)
            # The body can use anything from outer scope except what Let binds
            fvs |= free_variables(body) - bound
            return frozenset(fvs)

        case Abstract(parameters=parameters, body=body):
            # A lambda binds its parameters inside the body.
            # Free variables of the lambda = free variables of the body
            # minus the parameter names (they are provided by the caller).
            #
            # Example:  lambda (x, y): x + z
            #   free in body: {x, y, z}  minus parameters {x, y}  ->  {z}
            return free_variables(body) - frozenset(parameters)

        case Apply(target=target, arguments=arguments):
            # A function call: collect free variables from the function
            # expression and from every argument.
            result: set[Identifier] = set(free_variables(target))
            for a in arguments:
                result |= free_variables(a)
            return frozenset(result)

        case Immediate():
            # A literal integer constant — no variables at all.
            return frozenset()

        case Primitive(left=left, right=right):
            # An arithmetic expression — union of both operands' free variables.
            return free_variables(left) | free_variables(right)

        case Branch(left=left, right=right, consequent=consequent, otherwise=otherwise):
            # A conditional — variables can appear in the condition operands
            # and in either branch arm, so union all four.
            return free_variables(left) | free_variables(right) | free_variables(consequent) | free_variables(otherwise)

        case Allocate():
            # Allocation takes a fixed count — no variable references.
            return frozenset()

        case Load(base=base):
            # The address to load from may contain variable references.
            return free_variables(base)

        case Store(base=base, value=value):
            # Both the address and the value being stored may reference variables.
            # (index is a compile-time Nat literal, not a variable)
            return free_variables(base) | free_variables(value)

        case Begin(effects=effects, value=value):
            # A sequence of effects followed by a final value.
            # Variables can appear in any effect or in the final value.
            result = set(free_variables(value))
            for e in effects:
                result |= free_variables(e)
            return frozenset(result)

    raise ValueError(f"Unhandled term variant: {term!r}")


def is_pure(term: Term) -> bool:
    match term:
        case Immediate() | Reference():
            # Literals and variable reads have no side-effects.
            return True

        case Primitive(left=left, right=right):
            # Arithmetic is pure only if both operands are pure.
            # (No division — so no division-by-zero side-effect to worry about.)
            return is_pure(left) and is_pure(right)

        case Abstract():
            # Building a closure captures variables but does not execute the
            # body — so the act of forming the closure is itself pure.
            return True

        case Let(bindings=bindings, body=body):
            # A Let is pure only if every bound value is pure AND the body is
            # pure.  If any binding is impure we must keep the whole thing.
            return all(is_pure(v) for _, v in bindings) and is_pure(body)

        case Apply() | Allocate() | Load() | Store() | Begin() | Branch():
            # All of these can have side-effects — treat as impure.
            return False

        case _:
            # Unknown variant — be conservative and say "not pure" so we
            # never accidentally drop something important.
            return False


# main


def dead_code_elimination_term(term: Term) -> Term:
    """Recursively eliminate dead Let-bindings from *term*.

    The only term kind where elimination actually happens is Let — all other
    term kinds just recurse into their sub-terms to clean up anything nested
    inside them.
    """
    match term:
        case Let(bindings=bindings, body=body):
            # Step 1: recurse bottom-up
            reduced_body = dead_code_elimination_term(body)
            reduced_bindings = tuple((name, dead_code_elimination_term(val)) for name, val in bindings)

            # Step 2: decide which bindings are live

            live_bindings: list[tuple[Identifier, Term]] = []

            # Seed `live` with names that are actually needed by the body.
            live: frozenset[Identifier] = free_variables(reduced_body)

            for name, val in reversed(reduced_bindings):
                if name in live or not is_pure(val):
                    live_bindings.insert(0, (name, val))
                    live = live | free_variables(val)

            # Step 3: reassemble
            if not live_bindings:
                return reduced_body
            return Let(bindings=tuple(live_bindings), body=reduced_body)

        case Abstract(parameters=parameters, body=body):
            # Recurse into the lambda body — dead bindings can hide inside lambdas.
            return Abstract(parameters=parameters, body=dead_code_elimination_term(body))

        case Apply(target=target, arguments=arguments):
            # Recurse into the function and each argument.
            return Apply(
                target=dead_code_elimination_term(target),
                arguments=tuple(dead_code_elimination_term(a) for a in arguments),
            )

        case Primitive(operator=operator, left=left, right=right):
            # Recurse into both operands.
            return Primitive(
                operator=operator,
                left=dead_code_elimination_term(left),
                right=dead_code_elimination_term(right),
            )

        case Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            # Recurse into the condition operands and both arms.
            return Branch(
                operator=operator,
                left=dead_code_elimination_term(left),
                right=dead_code_elimination_term(right),
                consequent=dead_code_elimination_term(consequent),
                otherwise=dead_code_elimination_term(otherwise),
            )

        case Load(base=base, index=index):
            return Load(base=dead_code_elimination_term(base), index=index)

        case Store(base=base, index=index, value=value):
            return Store(
                base=dead_code_elimination_term(base),
                index=index,
                value=dead_code_elimination_term(value),
            )

        case Begin(effects=effects, value=value):
            # Every effect in a Begin is intentionally side-effectful, so we
            # never drop them — but we still recurse inside each one in case
            # there are dead Let-bindings nested within an effect expression.
            return Begin(
                effects=tuple(dead_code_elimination_term(e) for e in effects),
                value=dead_code_elimination_term(value),
            )

        case Immediate() | Reference() | Allocate():  # pragma: no branch
            # Atomic terms — nothing to eliminate, return as-is.
            return term
