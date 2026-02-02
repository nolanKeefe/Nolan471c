import ast
from functools import partial

from util.encode import encode

from .syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Immediate,
    Let,
    Load,
    Primitive,
    Program,
    Reference,
    Store,
    Term,
)


def to_ast_term(
    term: Term,
) -> ast.expr:
    _term = partial(to_ast_term)

    match term:
        case Let(bindings=bindings, body=body):
            return ast.Subscript(
                value=ast.Tuple(
                    elts=[
                        *[
                            ast.NamedExpr(target=ast.Name(id=encode(name), ctx=ast.Store()), value=_term(value))
                            for name, value in bindings
                        ],
                        _term(body),
                    ],
                    ctx=ast.Load(),
                ),
                slice=ast.Constant(-1),
                ctx=ast.Load(),
            )

        case Reference(name=name):
            return ast.Name(id=encode(name), ctx=ast.Load())

        case Abstract(parameters=parameters, body=body):
            return ast.Lambda(
                args=ast.arguments(args=[ast.arg(arg=parameter) for parameter in parameters]),
                body=_term(body),
            )

        case Apply(target=target, arguments=arguments):
            return ast.Call(
                func=_term(target),
                args=[_term(argument) for argument in arguments],
            )

        case Immediate(value=value):
            return ast.Constant(value=value)

        case Primitive(operator=operator, left=left, right=right):
            match operator:
                case "+":
                    op = ast.Add()

                case "-":
                    op = ast.Sub()

                case "*":  # pragma: no branch
                    op = ast.Mult()

            return ast.BinOp(left=_term(left), op=op, right=_term(right))

        case Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            match operator:
                case "<":
                    op = ast.Lt()

                case "==":  # pragma: no branch
                    op = ast.Eq()

            return ast.IfExp(
                test=ast.Compare(left=_term(left), ops=[op], comparators=[_term(right)]),
                body=_term(consequent),
                orelse=_term(otherwise),
            )

        case Allocate(count=count):
            return ast.List(
                elts=[ast.Constant(None) for _ in range(count)],
                ctx=ast.Load(),
            )

        case Load(base=base, index=index):
            return ast.Call(
                func=ast.Attribute(value=_term(base), attr="__getitem__", ctx=ast.Load()),
                args=[ast.Constant(value=index)],
            )

        case Store(base=base, index=index, value=value):
            return ast.Subscript(
                value=ast.Tuple(
                    elts=[
                        ast.Call(
                            func=ast.Attribute(value=_term(base), attr="__setitem__", ctx=ast.Load()),
                            args=[ast.Constant(value=index), _term(value)],
                        ),
                        ast.Constant(value=0),
                    ],
                    ctx=ast.Load(),
                ),
                slice=ast.Constant(-1),
                ctx=ast.Load(),
            )

        case Begin(effects=effects, value=value):  # pragma: no branch
            return ast.Subscript(
                value=ast.Tuple(
                    elts=[
                        *[_term(effect) for effect in effects],
                        _term(value),
                    ],
                    ctx=ast.Load(),
                ),
                slice=ast.Constant(-1),
                ctx=ast.Load(),
            )


def to_ast_program(
    program: Program,
) -> str:
    match program:
        case Program(parameters=parameters, body=body):  # pragma: no branch
            module = ast.Module(
                body=[
                    ast.FunctionDef(
                        name="l2",
                        args=ast.arguments(args=[ast.arg(arg=parameter) for parameter in parameters]),
                        body=[
                            ast.Return(value=to_ast_term(body)),
                        ],
                    ),
                    ast.If(
                        test=ast.Compare(
                            left=ast.Name(id="__name__", ctx=ast.Load()),
                            ops=[ast.Eq()],
                            comparators=[ast.Constant(value="__main__")],
                        ),
                        body=[
                            ast.Import(names=[ast.alias(name="sys", asname=None)]),
                            ast.Expr(
                                value=ast.Call(
                                    func=ast.Name(id="print", ctx=ast.Load()),
                                    args=[
                                        ast.Call(
                                            func=ast.Name(id="l2", ctx=ast.Load()),
                                            args=[
                                                ast.Call(
                                                    func=ast.Name(id="int", ctx=ast.Load()),
                                                    args=[
                                                        ast.Subscript(
                                                            value=ast.Attribute(
                                                                value=ast.Name(id="sys", ctx=ast.Load()),
                                                                attr="argv",
                                                                ctx=ast.Load(),
                                                            ),
                                                            slice=ast.Constant(value=i + 1),
                                                        )
                                                    ],
                                                )
                                                for i, _ in enumerate(parameters)
                                            ],
                                        )
                                    ],
                                )
                            ),
                        ],
                    ),
                ]
            )

            ast.fix_missing_locations(module)

            return ast.unparse(module)
