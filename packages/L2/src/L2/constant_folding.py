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
        case Let(bindings=bindings, body=body):
            # Fold constants inside each binding's value, and in the body
            folded_bindings = tuple((name, recur(val)) for name, val in bindings)
            return Let(bindings=folded_bindings, body=recur(body))

        case Reference(name=name):
            # Nothing to fold — a reference is already atomic
            return term

        case Abstract(parameters=parameters, body=body):
            # Fold inside the lambda body
            return Abstract(parameters=parameters, body=recur(body))

        case Apply(target=target, arguments=arguments):
            # Fold the function and each argument
            return Apply(target=recur(target), arguments=tuple(recur(a) for a in arguments))

        case Immediate():
            # Already a constant — nothing to do
            return term

        case Primitive(operator=operator, left=left, right=right):
            match operator:
                case "+":
                    match recur(left), recur(right):
                        # Both sides are known constants — evaluate now
                        case Immediate(value=i1), Immediate(value=i2):
                            return Immediate(value=i1 + i2)

                        # 0 + x  =>  x
                        case Immediate(value=0), right:
                            return right

                        # x + 0  =>  x
                        case left, Immediate(value=0):
                            return left

                        # (+ (+ i1 a) (+ i2 b))  =>  (+ (i1+i2) (+ a b))
                        case [
                            Primitive(operator="+", left=Immediate(value=i1), right=left),
                            Primitive(operator="+", left=Immediate(value=i2), right=right),
                        ]:
                            return Primitive(
                                operator="+",
                                left=Immediate(value=i1 + i2),
                                right=Primitive(operator="+", left=left, right=right),
                            )

                        # (+ (- i1 a) (- i2 b))  =>  (- (i1+i2) (+ a b))
                        case [
                            Primitive(operator="-", left=Immediate(value=i1), right=left),
                            Primitive(operator="-", left=Immediate(value=i2), right=right),
                        ]:
                            return Primitive(
                                operator="-",
                                left=Immediate(value=i1 + i2),
                                right=Primitive(operator="+", left=left, right=right),
                            )

                        # Canonicalise: move an immediate to the left so later
                        # passes have a consistent shape to match against.
                        case left, (Immediate() as right):
                            return Primitive(operator="+", left=right, right=left)

                        case left, right:
                            return Primitive(operator="+", left=left, right=right)

                case "-":
                    match recur(left), recur(right):
                        # Both constants
                        case Immediate(value=i1), Immediate(value=i2):
                            return Immediate(value=i1 - i2)

                        # x - 0  =>  x
                        case left, Immediate(value=0):
                            return left

                        # x - x  =>  0  (same reference name)
                        case Reference(name=n1), Reference(name=n2) if n1 == n2:
                            return Immediate(value=0)

                        # (- (- i1 a) (- i2 b))  =>  (- (i1-i2) (- a b))  … wait, sign algebra:
                        # (i1 - a) - (i2 - b) = (i1 - i2) + (b - a)
                        # Keep conservative: just pull constants out on the left.
                        case [
                            Primitive(operator="-", left=Immediate(value=i1), right=left),
                            Primitive(operator="-", left=Immediate(value=i2), right=right),
                        ]:
                            return Primitive(
                                operator="-",
                                left=Immediate(value=i1 - i2),
                                right=Primitive(operator="-", left=left, right=right),
                            )

                        # (- (+ i1 a) (+ i2 b))  =>  (+ (i1-i2) (- a b))
                        case [
                            Primitive(operator="+", left=Immediate(value=i1), right=left),
                            Primitive(operator="+", left=Immediate(value=i2), right=right),
                        ]:
                            return Primitive(
                                operator="+",
                                left=Immediate(value=i1 - i2),
                                right=Primitive(operator="-", left=left, right=right),
                            )

                        # Canonicalise: move a right-side immediate to the left
                        # by negating, turning (- x k) => (+ (-k) x).
                        # This lets subsequent passes treat subtraction of a
                        # constant the same as addition of its negation.
                        case left, Immediate(value=k):
                            return Primitive(
                                operator="+",
                                left=Immediate(value=-k),
                                right=left,
                            )

                        case left, right:
                            return Primitive(operator="-", left=left, right=right)

                case "*":
                    match recur(left), recur(right):
                        # Both constants
                        case Immediate(value=i1), Immediate(value=i2):
                            return Immediate(value=i1 * i2)

                        # 0 * x  =>  0  (and x * 0 below)
                        case Immediate(value=0), _:
                            return Immediate(value=0)

                        case _, Immediate(value=0):
                            return Immediate(value=0)

                        # 1 * x  =>  x
                        case Immediate(value=1), right:
                            return right

                        # x * 1  =>  x
                        case left, Immediate(value=1):
                            return left

                        # (*(* i1 a)(* i2 b))  =>  (* (i1*i2) (* a b))
                        case [
                            Primitive(operator="*", left=Immediate(value=i1), right=left),
                            Primitive(operator="*", left=Immediate(value=i2), right=right),
                        ]:
                            return Primitive(
                                operator="*",
                                left=Immediate(value=i1 * i2),
                                right=Primitive(operator="*", left=left, right=right),
                            )

                        # Canonicalise: immediate to the left
                        case left, (Immediate() as right):
                            return Primitive(operator="*", left=right, right=left)

                        case left, right:
                            return Primitive(operator="*", left=left, right=right)

        case Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            folded_left = recur(left)
            folded_right = recur(right)
            # If both sides of the condition are known, evaluate the branch now
            match folded_left, folded_right:
                case Immediate(value=i1), Immediate(value=i2):
                    condition = (i1 < i2) if operator == "<" else (i1 == i2)
                    return recur(consequent) if condition else recur(otherwise)
                case _:
                    return Branch(
                        operator=operator,
                        left=folded_left,
                        right=folded_right,
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
