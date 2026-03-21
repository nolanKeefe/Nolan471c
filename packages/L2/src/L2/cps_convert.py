# from collections.abc import Callable, Sequence
# from functools import partial

# from L1 import syntax as L1

# from L2 import syntax as L2

# """
# k is by convention the continuation
# the thing that happens next
# cps conversion is setting the "then" field that L1 has (the k)

# Use identifiers directly

# Continuation has not changed meaning as function that you apply variables to
# it is just now in our "meta-language" (compiler language) instead of L1 L2

# We will be working on trust as k is created and passed around
# We "trust" it wont be bad
# """


# def cps_convert_term(
#     term: L2.Term,
#     k: Callable[[L1.Identifier], L1.Statement],  # identifier -> statement the rest of the computation
#     fresh: Callable[[str], str],
# ) -> L1.Statement:  # this whole thing is producing the statement
#     _term = partial(cps_convert_term, fresh=fresh)
#     _terms = partial(cps_convert_terms, fresh=fresh)

#     match term:
#         case L2.Let(bindings=bindings, body=body):
#             pass

#         case L2.Reference(name=name):  # name is an identifier, takes in name returns that name k-ified
#             return k(name)

#         # abstracts and applys are gonna be calls to k as per notes in class
#         case L2.Abstract(parameters=parameters, body=body):
#             pass

#         case L2.Apply(target=target, arguments=arguments):
#             pass
#             # return L1.Apply(target = target, arguments=arguments) need to convert values

#         case L2.Immediate(value=value):  # k needs a this, we need a uniquified name for it
#             # looking at immediates in L1 they need a destination, a value, a then (a statement in L2)
#             tmp = fresh("t")  # need to store here for consistency
#             return L1.Immediate(
#                 destination=tmp,  # needs a fresh identifier using t to match with the given tests can chang it in tests if wanted
#                 value=value,
#                 then=k(tmp),  # what happens next. need to materialize it an actual L1 statement
#             )

#         case L2.Primitive(operator=operator, left=left, right=right):
#             # control flow isnt explicitly stated rn so we need to specify order
#             # need a then
#             # we can do left then right
#             # _term is just courieing it
#             # need to provide some lambda function that gets given the left identifier
#             tmp = fresh("t")  # the result of calling left and right
#             return _term(
#                 left,
#                 k=lambda left: _term(  # We dig into the left side first
#                     right,
#                     k=lambda right: L1.Primitive(  # then we dig into the right but it has to hold the full Primitive
#                         destination=tmp,
#                         operator=operator,
#                         left=left,
#                         right=right,
#                         then=k(tmp),
#                     ),
#                 ),
#             )

#             pass

#         case L2.Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
#             pass

#         case L2.Allocate(count=count):
#             tmp = fresh("t")  # need to store here for consistency
#             return L1.Allocate(
#                 destination=tmp,  # needs a fresh identifier using t to match with the given tests can chang it in tests if wanted
#                 count=count,
#                 then=k(tmp),  # what happens next. need to materialize it an actual L1 statement
#             )

#         case L2.Load(base=base, index=index):
#             tmp = fresh("t")
#             return _term(
#                 base,
#                 k=lambda base: L1.Load(
#                     destination=tmp,
#                     base=base,
#                     index=index,
#                     then=k(tmp),
#                 ),
#             )

#         case L2.Store(base=base, index=index, value=value):
#             # everything in the language evaluates to something
#             tmp = fresh("t")  # the result of calling left and right
#             return _term(
#                 base,
#                 k=lambda base: _term(  # We dig into the base
#                     value,
#                     k=lambda value: L1.Store(  # we then can return a store
#                         base=base,
#                         index=index,
#                         value=value,
#                         then=L1.Immediate(  # due to stores needing to have a value (of 0) but also the true value
#                             # We make an immediate, also because the store lacks the explicit zero in the first place
#                             destination=tmp,
#                             value=0,
#                             then=k(tmp),
#                         ),
#                     ),
#                 ),
#             )
#         case L2.Begin(effects=effects, value=value):  # pragma: no branch
#             # we lack an L1.Begin so now we dont need Begin to represent control flow, we have CPS style
#             # it encodes control flow more unified fashion
#             return _terms(
#                 effects,
#                 lambda effects: _term(  # dig into the effects
#                     value,
#                     lambda value: k(  # dig into the value
#                         value
#                     ),  # we can just call k on value because we already have a name for everything! in value!!
#                 ),
#             )


# def cps_convert_terms(
#     terms: Sequence[L2.Term],
#     k: Callable[[Sequence[L1.Identifier]], L1.Statement],
#     fresh: Callable[[str], str],
# ) -> L1.Statement:
#     _term = partial(cps_convert_term, fresh=fresh)
#     _terms = partial(cps_convert_terms, fresh=fresh)

#     match terms:
#         case []:  # empty case
#             return k([])

#         case [first, *rest]:  # case of 1 thing with other things
#             return _term(first, lambda first: _terms(rest, lambda rest: k([first, *rest])))

#         case _:  # pragma: no cover
#             raise ValueError(terms)


# """
# start at the top
# how are we to convert it
# """


# def cps_convert_program(
#     program: L2.Program,
#     # source of fresh variable names, need to pass along as its own thing
#     fresh: Callable[[str], str],
# ) -> L1.Program:
#     _term = partial(cps_convert_term, fresh=fresh)

#     match program:
#         case L2.Program(parameters=parameters, body=body):  # pragma: no branch
#             return L1.Program(
#                 parameters=parameters,
#                 body=_term(
#                     body,  # all the program code we need to analyze
#                     lambda value: L1.Halt(  # lambda value is the body cps identifier
#                         value=value
#                     ),  # when we start k is a simple where it gives a value and then halts
#                 ),
#             )
