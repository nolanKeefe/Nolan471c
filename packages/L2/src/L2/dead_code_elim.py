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


def free_variables(term: Term) -> frozenset[Identifier]:
    # Return the set of identifiers that occur free in a term

    match term:
        case Reference(name=name):
            return frozenset({name})  # the name itself free

        case Let(bindings=bindings, body=body):
            # Things are free if they are only in the lets bounds and not from an outer let
            bound: set[Identifier] = set()
            fvs: set[Identifier] = set()  # free variables

            for name, val in bindings:
                fvs |= free_variables(val) - bound
                bound.add(name)  # we are getting new names that aren't already bound

            fvs |= free_variables(body) - bound
            return frozenset(fvs)

        case Abstract(parameters=parameters, body=body):
            # free variables in the body are the only thing we can get from the abstract
            # the parameters are removed from the free variable set basically
            return free_variables(body) - frozenset(parameters)

        case Apply(target=target, arguments=arguments):
            # function calls collect free vars from function and from the args
            result: set[Identifier] = set(free_variables(target))
            for a in arguments:
                result |= free_variables(a)
            return frozenset(result)

        case Immediate():
            # Immediates don't have vars bro...
            return frozenset()

        case Primitive(left=left, right=right):
            # arithmetic expression union of both left and right vars
            # cuz like we got 2 ends to work from here
            return free_variables(left) | free_variables(right)

        case Branch(left=left, right=right, consequent=consequent, otherwise=otherwise):
            # need to look at union of all the paths n stuff
            return free_variables(left) | free_variables(right) | free_variables(consequent) | free_variables(otherwise)

        case Allocate():
            # fixed nothing to add
            return frozenset()

        case Load(base=base):
            # loading address can have variable
            return free_variables(base)

        case Store(base=base, value=value):
            # address and the value can be vars
            return free_variables(base) | free_variables(value)

        case Begin(effects=effects, value=value):
            # need to look at all the effects is the main thing here
            result = set(free_variables(value))
            for e in effects:
                result |= free_variables(e)
            return frozenset(result)

    # shouldnt hit but like the in case
    raise ValueError(f"Unhandled term variant: {term!r}")


def is_pure(term: Term) -> bool:
    """Return True iff evaluating the term produces no observable side-effects.

    we're saying a term is pure only if it provably cannot perform
    allocation, memory reads/writes, or other effectful operations.
    tryna not mess things up
    """
    match term:
        case Immediate() | Reference():
            return True
        case Primitive(left=left, right=right):
            return is_pure(left) and is_pure(right)
        case Abstract():
            # Forming a closure is pure
            # calling it might not be, but we aren't evaluating the body here.
            return True
        case Let(bindings=bindings, body=body):
            # need to check em all for "pureness"
            return all(is_pure(v) for _, v in bindings) and is_pure(body)

        case Apply() | Allocate() | Load() | Store() | Begin() | Branch():
            # BLATANTLY doing memory shit so false
            return False
        case _:
            # other cases we don't know so false
            return False


# Main pass


def dead_code_elimination_term(term: Term) -> Term:
    # Recursively eliminate dead Let-bindings from terms
    match term:
        case Let(bindings=bindings, body=body):
            # Recurse into every sub-term first (bottom-up)
            reduced_body = dead_code_elimination_term(body)
            reduced_bindings = [(name, dead_code_elimination_term(val)) for name, val in bindings]

            # Filtering keeps a binding if it is used OR has side-effects.
            # We recompute free variables after each removal so that removing
            # one binding can expose another as dead
            live_bindings: list[tuple[Identifier, Term]] = []
            # Work right-to-left so we can incrementally track what is live
            # Start with the free variables of the body
            live: frozenset[Identifier] = free_variables(reduced_body)

            for name, val in reversed(reduced_bindings):
                if name in live or not is_pure(val):
                    live_bindings.insert(0, (name, val))
                    # This binding's value's free variables are now needed too
                    live = live | free_variables(val)
                # else: name is dead and value is pure — drop it entirely

            if not live_bindings:
                return reduced_body
            return Let(bindings=live_bindings, body=reduced_body)

        case Abstract(parameters=parameters, body=body):
            return Abstract(parameters=parameters, body=dead_code_elimination_term(body))

        case Apply(target=target, arguments=arguments):
            return Apply(
                target=dead_code_elimination_term(target),
                arguments=[dead_code_elimination_term(a) for a in arguments],
            )

        case Primitive(operator=operator, left=left, right=right):
            return Primitive(
                operator=operator,
                left=dead_code_elimination_term(left),
                right=dead_code_elimination_term(right),
            )

        case Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
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
            # Keep all effects
            # recurse to clean up inside them.
            return Begin(
                effects=[dead_code_elimination_term(e) for e in effects],
                value=dead_code_elimination_term(value),
            )

        case Immediate() | Reference() | Allocate():
            return term

    raise ValueError(f"Unhandled term variant: {term!r}")  # shouldn't reach but coverage
