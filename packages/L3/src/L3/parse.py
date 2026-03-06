from collections.abc import Sequence
from pathlib import Path

from lark import Lark, Token, Transformer
from lark.visitors import v_args  # pyright: ignore[reportUnknownVariableType]

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


class AstTransformer(Transformer[Token, Program | Term]):
    @v_args(inline=True)
    def program(
        self,
        _program: Token,
        parameters: Sequence[Identifier],
        body: Term,
    ) -> Program:
        return Program(
            parameters=parameters,
            body=body,
        )

    def parameters(
        self,
        parameters: Sequence[Identifier],
    ) -> Sequence[Identifier]:
        return parameters

    @v_args(inline=True)
    def term(
        self,
        term: Term,
    ) -> Term:
        return term

    @v_args(inline=True)
    def let(
        self,
        _let: Token,
        bindings: Sequence[tuple[Identifier, Term]],
        body: Term,
    ) -> Term:
        return Let(
            bindings=bindings,
            body=body,
        )

    @v_args(inline=True)
    def letrec(
        self,
        _letrec: Token,
        bindings: Sequence[tuple[Identifier, Term]],
        body: Term,
    ) -> Term:
        return LetRec(
            bindings=bindings,
            body=body,
        )

    def bindings(
        self,
        bindings: Sequence[tuple[Identifier, Term]],
    ) -> Sequence[tuple[Identifier, Term]]:
        return bindings

    @v_args(inline=True)
    def binding(
        self,
        name: Identifier,
        value: Term,
    ) -> tuple[Identifier, Term]:
        return name, value

    @v_args(inline=True)
    def reference(
        self,
        name: Token,  # token from IDENTIFIER
    ) -> Term:
        return Reference(name=str(name))

    @v_args(inline=True)
    def immediate(
        self,
        value: Token,  # token from IDENTIFIER
    ) -> Term:
        return Immediate(value=int(value))

    @v_args(inline=True)
    def abstract(
        self,
        _lambda: Token,  # lambda token we discarded
        parameters: Sequence[Identifier],  # token from IDENTIFIER
        body: Term,
    ) -> Term:
        return Abstract(
            parameters=list(parameters),  # need to convert the parameters to a list so it isn't deemd a single thing
            body=body,
        )

    @v_args(inline=True)
    def apply(
        self,
        arguments: Sequence[Term],  # due to how its a term into a term it kinda clumps
    ) -> Term:
        # target is the first arg, the args are the rest
        return Apply(target=arguments[0], arguments=list(arguments[1:]))

    @v_args(inline=True)
    def primitive(
        self,
        operator: Token,  # One of "+", "-", "*" as a Token
        left: Term,
        right: Term,
    ) -> Term:
        # str(operator) extracts the operator symbol from the Token.
        # The pyright ignore is needed because str is wider than Literal["+","-","*"],
        return Primitive(
            operator=str(operator),  # pyright: ignore[reportArgumentType]
            left=left,
            right=right,
        )

    @v_args(inline=True)
    def branch(
        self,
        operator: Token,
        left: Term,
        right: Term,
        consequent: Term,
        otherwise: Term,
    ) -> Term:
        return Branch(
            # same thing as prev where we ignore the string things
            operator=str(operator),  # pyright: ignore[reportArgumentType]
            left=left,
            right=right,
            consequent=consequent,
            otherwise=otherwise,
        )

    @v_args(inline=True)
    def allocate(self, count: Token) -> Term:
        return Allocate(
            count=int(count),
        )

    @v_args(inline=True)
    def load(self, base: Term, index: Token) -> Term:
        return Load(base=base, index=int(index))

    @v_args(inline=True)
    def store(self, base: Term, index: Token, value: Term) -> Term:
        return Store(base=base, index=int(index), value=value)

    # length varies can't inline it
    def begin(
        self,
        effects: Sequence[Term],
    ) -> Term:
        return Begin(effects=list(effects[:-1]), value=effects[-1])


def parse_term(source: str) -> Term:
    grammar = Path(__file__).with_name("L3.lark").read_text()
    parser = Lark(grammar, start="term")
    tree = parser.parse(source)  # pyright: ignore[reportUnknownMemberType]
    return AstTransformer().transform(tree)  # pyright: ignore[reportReturnType]


def parse_program(source: str) -> Program:
    grammar = Path(__file__).with_name("L3.lark").read_text()
    parser = Lark(grammar, start="program")
    tree = parser.parse(source)  # pyright: ignore[reportUnknownMemberType]
    return AstTransformer().transform(tree)  # pyright: ignore[reportReturnType]
