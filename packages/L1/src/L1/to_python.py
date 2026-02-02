import ast
from functools import partial

from util.encode import encode

from .syntax import (
    Abstract,
    Allocate,
    Apply,
    Branch,
    Copy,
    Halt,
    Immediate,
    Load,
    Primitive,
    Program,
    Statement,
    Store,
)


def load(name: str) -> ast.Name:
    return ast.Name(id=encode(name), ctx=ast.Load())


def store(name: str) -> ast.Name:
    return ast.Name(id=encode(name), ctx=ast.Store())


def to_ast_statement(
    statement: Statement,
) -> list[ast.stmt]:
    _statement = partial(to_ast_statement)

    match statement:
        case Copy(destination=destination, source=source, then=then):
            return [
                ast.Assign(targets=[store(destination)], value=load(source)),
                *_statement(then),
            ]

        case Abstract(destination=destination, parameters=parameters, body=body, then=then):
            return [
                ast.FunctionDef(
                    name=encode(destination),
                    args=ast.arguments(args=[ast.arg(arg=parameter) for parameter in parameters]),
                    body=_statement(body),
                ),
                *_statement(then),
            ]

        case Apply(target=target, arguments=arguments):
            return [
                ast.Return(
                    ast.Call(
                        func=load(target),
                        args=[load(argument) for argument in arguments],
                    )
                )
            ]

        case Immediate(destination=destination, value=value, then=then):
            return [
                ast.Assign(targets=[store(destination)], value=ast.Constant(value=value)),
                *_statement(then),
            ]

        case Primitive(destination=destination, operator=operator, left=left, right=right, then=then):
            match operator:
                case "+":
                    op = ast.Add()

                case "-":
                    op = ast.Sub()

                case "*":  # pragma: no branch
                    op = ast.Mult()

            return [
                ast.Assign(
                    targets=[store(destination)],
                    value=ast.BinOp(left=load(left), op=op, right=load(right)),
                ),
                *_statement(then),
            ]

        case Branch(operator=operator, left=left, right=right, then=then, otherwise=otherwise):
            match operator:
                case "<":
                    op = ast.Lt()

                case "==":  # pragma: no branch
                    op = ast.Eq()

            return [
                ast.If(
                    ast.Compare(left=load(left), ops=[op], comparators=[load(right)]),
                    body=_statement(then),
                    orelse=_statement(otherwise),
                ),
            ]

        case Allocate(destination=destination, count=count, then=then):
            return [
                ast.Assign(
                    targets=[store(destination)],
                    value=ast.List(
                        elts=[ast.Constant(None) for _ in range(count)],
                        ctx=ast.Load(),
                    ),
                ),
                *_statement(then),
            ]

        case Load(destination=destination, base=base, index=index, then=then):
            return [
                ast.Assign(
                    targets=[store(destination)],
                    value=ast.Subscript(
                        value=load(base),
                        slice=ast.Constant(index),
                        ctx=ast.Load(),
                    ),
                ),
                *_statement(then),
            ]

        case Store(base=base, index=index, value=value, then=then):
            return [
                ast.Assign(
                    targets=[
                        ast.Subscript(
                            value=load(base),
                            slice=ast.Constant(index),
                            ctx=ast.Store(),
                        )
                    ],
                    value=load(value),
                ),
                *_statement(then),
            ]

        case Halt(value=value):  # pragma: no branch
            return [
                ast.Return(value=load(value)),
            ]


def to_ast_program(
    program: Program,
) -> str:
    match program:
        case Program(parameters=parameters, body=body):  # pragma: no branch
            module = ast.Module(
                body=[
                    ast.FunctionDef(
                        name="l1",
                        args=ast.arguments(args=[ast.arg(arg=parameter) for parameter in parameters]),
                        body=to_ast_statement(body),
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
                                            func=ast.Name(id="l1", ctx=ast.Load()),
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
