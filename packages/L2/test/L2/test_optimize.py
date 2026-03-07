# from L2.optimize import optimize_program
# from L2.syntax import (
#     Immediate,
#     Primitive,
#     Program,
# )


# def test_optimize_program():
#     #test runs through the program, sees a primitive
#     # should recur into the primitive test
#     # and then do the primitive test case where it adds the immediates
#     program = Program(
#         parameters=[],
#         body=Primitive(
#             operator="+",
#             left=Immediate(value=1),
#             right=Immediate(value=1),
#         ),
#     )

#     expected = Program(
#         parameters=[],
#         body=Immediate(value=2),
#     )

#     actual = optimize_program(program)

#     assert actual == expected
