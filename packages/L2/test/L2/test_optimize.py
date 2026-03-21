"""
Tests for all optimisation passes and the fixed-point driver.

Each pass gets its own test class so failures are easy to locate.
Tests are ordered from simplest (single-node) to most complex (interactions
between passes / chains).

Import paths assume the package is named L2, matching the provided
test_optimize.py.

All terms are built directly with the Pydantic model constructors from
syntax.py — no helper wrappers — to avoid any type-coercion surprises.
"""

from L2.branch_elimination import branch_elimination_term
from L2.constant_folding import constant_folding_term
from L2.constant_propagation import constant_propagation_term
from L2.dead_code_elim import dead_code_elimination_term, free_variables, is_pure
from L2.optimize import optimize_program
from L2.syntax import (
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
)

# ===========================================================================
# 1. Constant Folding
# ===========================================================================


class TestConstantFolding:
    # --- addition ---

    def test_add_two_immediates(self):
        # 3 + 4  =>  7
        term = Primitive(
            operator="+",
            left=Immediate(value=3),
            right=Immediate(value=4),
        )
        assert constant_folding_term(term, context={}) == Immediate(value=7)

    def test_add_zero_left(self):
        # 0 + x  =>  x
        term = Primitive(
            operator="+",
            left=Immediate(value=0),
            right=Reference(name="x"),
        )
        assert constant_folding_term(term, context={}) == Reference(name="x")

    def test_add_zero_right(self):
        # x + 0  =>  x
        term = Primitive(
            operator="+",
            left=Reference(name="x"),
            right=Immediate(value=0),
        )
        assert constant_folding_term(term, context={}) == Reference(name="x")

    def test_add_canonicalises_immediate_to_left(self):
        # x + 3  =>  3 + x
        term = Primitive(
            operator="+",
            left=Reference(name="x"),
            right=Immediate(value=3),
        )
        expected = Primitive(
            operator="+",
            left=Immediate(value=3),
            right=Reference(name="x"),
        )
        assert constant_folding_term(term, context={}) == expected

    def test_add_two_vars_unchanged(self):
        # x + y  =>  x + y
        term = Primitive(
            operator="+",
            left=Reference(name="x"),
            right=Reference(name="y"),
        )
        assert constant_folding_term(term, context={}) == term

    def test_add_nested_immediates_with_plus(self):
        # (+ (+ 1 x) (+ 2 y))  =>  (+ 3 (+ x y))
        term = Primitive(
            operator="+",
            left=Primitive(operator="+", left=Immediate(value=1), right=Reference(name="x")),
            right=Primitive(operator="+", left=Immediate(value=2), right=Reference(name="y")),
        )
        expected = Primitive(
            operator="+",
            left=Immediate(value=3),
            right=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")),
        )
        assert constant_folding_term(term, context={}) == expected

    def test_add_nested_immediates_with_sub(self):
        # (+ (- 1 x) (- 2 y))  =>  (- 3 (+ x y))
        term = Primitive(
            operator="+",
            left=Primitive(operator="-", left=Immediate(value=1), right=Reference(name="x")),
            right=Primitive(operator="-", left=Immediate(value=2), right=Reference(name="y")),
        )
        expected = Primitive(
            operator="-",
            left=Immediate(value=3),
            right=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")),
        )
        assert constant_folding_term(term, context={}) == expected

    # --- subtraction ---

    def test_sub_two_immediates(self):
        # 10 - 3  =>  7
        term = Primitive(
            operator="-",
            left=Immediate(value=10),
            right=Immediate(value=3),
        )
        assert constant_folding_term(term, context={}) == Immediate(value=7)

    def test_sub_zero_right(self):
        # x - 0  =>  x
        term = Primitive(
            operator="-",
            left=Reference(name="x"),
            right=Immediate(value=0),
        )
        assert constant_folding_term(term, context={}) == Reference(name="x")

    def test_sub_same_reference(self):
        # x - x  =>  0
        term = Primitive(
            operator="-",
            left=Reference(name="x"),
            right=Reference(name="x"),
        )
        assert constant_folding_term(term, context={}) == Immediate(value=0)

    def test_sub_different_references_unchanged(self):
        # x - y  =>  x - y
        term = Primitive(
            operator="-",
            left=Reference(name="x"),
            right=Reference(name="y"),
        )
        assert constant_folding_term(term, context={}) == term

    def test_sub_canonicalises_immediate_right(self):
        # x - 3  =>  (-3) + x
        term = Primitive(
            operator="-",
            left=Reference(name="x"),
            right=Immediate(value=3),
        )
        expected = Primitive(
            operator="+",
            left=Immediate(value=-3),
            right=Reference(name="x"),
        )
        assert constant_folding_term(term, context={}) == expected

    def test_sub_nested_sub_sub(self):
        # (- (- 5 x) (- 2 y))  =>  (- 3 (- x y))
        term = Primitive(
            operator="-",
            left=Primitive(operator="-", left=Immediate(value=5), right=Reference(name="x")),
            right=Primitive(operator="-", left=Immediate(value=2), right=Reference(name="y")),
        )
        expected = Primitive(
            operator="-",
            left=Immediate(value=3),
            right=Primitive(operator="-", left=Reference(name="x"), right=Reference(name="y")),
        )
        assert constant_folding_term(term, context={}) == expected

    def test_sub_nested_add_add(self):
        # (- (+ 5 x) (+ 2 y))  =>  (+ 3 (- x y))
        term = Primitive(
            operator="-",
            left=Primitive(operator="+", left=Immediate(value=5), right=Reference(name="x")),
            right=Primitive(operator="+", left=Immediate(value=2), right=Reference(name="y")),
        )
        expected = Primitive(
            operator="+",
            left=Immediate(value=3),
            right=Primitive(operator="-", left=Reference(name="x"), right=Reference(name="y")),
        )
        assert constant_folding_term(term, context={}) == expected

    # --- multiplication ---

    def test_mul_two_immediates(self):
        # 3 * 4  =>  12
        term = Primitive(
            operator="*",
            left=Immediate(value=3),
            right=Immediate(value=4),
        )
        assert constant_folding_term(term, context={}) == Immediate(value=12)

    def test_mul_zero_left(self):
        # 0 * x  =>  0
        term = Primitive(
            operator="*",
            left=Immediate(value=0),
            right=Reference(name="x"),
        )
        assert constant_folding_term(term, context={}) == Immediate(value=0)

    def test_mul_zero_right(self):
        # x * 0  =>  0
        term = Primitive(
            operator="*",
            left=Reference(name="x"),
            right=Immediate(value=0),
        )
        assert constant_folding_term(term, context={}) == Immediate(value=0)

    def test_mul_one_left(self):
        # 1 * x  =>  x
        term = Primitive(
            operator="*",
            left=Immediate(value=1),
            right=Reference(name="x"),
        )
        assert constant_folding_term(term, context={}) == Reference(name="x")

    def test_mul_one_right(self):
        # x * 1  =>  x
        term = Primitive(
            operator="*",
            left=Reference(name="x"),
            right=Immediate(value=1),
        )
        assert constant_folding_term(term, context={}) == Reference(name="x")

    def test_mul_canonicalises_immediate_to_left(self):
        # x * 3  =>  3 * x
        term = Primitive(
            operator="*",
            left=Reference(name="x"),
            right=Immediate(value=3),
        )
        expected = Primitive(
            operator="*",
            left=Immediate(value=3),
            right=Reference(name="x"),
        )
        assert constant_folding_term(term, context={}) == expected

    def test_mul_nested_immediates(self):
        # (* (* 2 x) (* 3 y))  =>  (* 6 (* x y))
        term = Primitive(
            operator="*",
            left=Primitive(operator="*", left=Immediate(value=2), right=Reference(name="x")),
            right=Primitive(operator="*", left=Immediate(value=3), right=Reference(name="y")),
        )
        expected = Primitive(
            operator="*",
            left=Immediate(value=6),
            right=Primitive(operator="*", left=Reference(name="x"), right=Reference(name="y")),
        )
        assert constant_folding_term(term, context={}) == expected

    # --- passthrough cases ---

    def test_immediate_unchanged(self):
        term = Immediate(value=42)
        assert constant_folding_term(term, context={}) == Immediate(value=42)

    def test_reference_unchanged(self):
        term = Reference(name="a")
        assert constant_folding_term(term, context={}) == Reference(name="a")

    def test_let_recurses_into_bindings_and_body(self):
        # let x = 2+3 in x  =>  let x = 5 in x
        term = Let(
            bindings=(("x", Primitive(operator="+", left=Immediate(value=2), right=Immediate(value=3))),),
            body=Reference(name="x"),
        )
        expected = Let(
            bindings=(("x", Immediate(value=5)),),
            body=Reference(name="x"),
        )
        assert constant_folding_term(term, context={}) == expected

    def test_abstract_recurses_into_body(self):
        term = Abstract(
            parameters=("x",),
            body=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
        )
        expected = Abstract(parameters=("x",), body=Immediate(value=3))
        assert constant_folding_term(term, context={}) == expected

    def test_apply_recurses_into_arguments(self):
        term = Apply(
            target=Reference(name="f"),
            arguments=(
                Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
                Reference(name="y"),
            ),
        )
        expected = Apply(
            target=Reference(name="f"),
            arguments=(Immediate(value=3), Reference(name="y")),
        )
        assert constant_folding_term(term, context={}) == expected

    def test_branch_known_true_condition(self):
        # if 1 < 2 then 10 else 20  =>  10
        term = Branch(
            operator="<",
            left=Immediate(value=1),
            right=Immediate(value=2),
            consequent=Immediate(value=10),
            otherwise=Immediate(value=20),
        )
        assert constant_folding_term(term, context={}) == Immediate(value=10)

    def test_branch_known_false_condition(self):
        # if 5 < 3 then 10 else 20  =>  20
        term = Branch(
            operator="<",
            left=Immediate(value=5),
            right=Immediate(value=3),
            consequent=Immediate(value=10),
            otherwise=Immediate(value=20),
        )
        assert constant_folding_term(term, context={}) == Immediate(value=20)

    def test_branch_known_equal_true(self):
        # if 4 == 4 then 1 else 0  =>  1
        term = Branch(
            operator="==",
            left=Immediate(value=4),
            right=Immediate(value=4),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=0),
        )
        assert constant_folding_term(term, context={}) == Immediate(value=1)

    def test_branch_unknown_condition_preserved(self):
        # if x < y then 1 else 0  =>  unchanged
        term = Branch(
            operator="<",
            left=Reference(name="x"),
            right=Reference(name="y"),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=0),
        )
        assert constant_folding_term(term, context={}) == term

    def test_allocate_unchanged(self):
        term = Allocate(count=4)
        assert constant_folding_term(term, context={}) == Allocate(count=4)

    def test_load_recurses_base(self):
        term = Load(
            base=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
            index=0,
        )
        expected = Load(base=Immediate(value=3), index=0)
        assert constant_folding_term(term, context={}) == expected

    def test_store_recurses(self):
        term = Store(
            base=Reference(name="arr"),
            index=0,
            value=Primitive(operator="+", left=Immediate(value=2), right=Immediate(value=3)),
        )
        expected = Store(base=Reference(name="arr"), index=0, value=Immediate(value=5))
        assert constant_folding_term(term, context={}) == expected

    def test_begin_recurses(self):
        term = Begin(
            effects=(
                Store(
                    base=Reference(name="arr"),
                    index=0,
                    value=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=1)),
                ),
            ),
            value=Primitive(operator="+", left=Immediate(value=2), right=Immediate(value=3)),
        )
        expected = Begin(
            effects=(Store(base=Reference(name="arr"), index=0, value=Immediate(value=2)),),
            value=Immediate(value=5),
        )
        assert constant_folding_term(term, context={}) == expected

    # --- line 94: addition fallthrough — two non-immediate, non-matching sub-expressions ---

    def test_add_two_primitives_no_immediate_unchanged(self):
        # (x + y) + (a + b) — no immediates anywhere, no pattern matches,
        # hits the fallthrough case left, right on line 94 and rebuilds as-is.
        term = Primitive(
            operator="+",
            left=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")),
            right=Primitive(operator="+", left=Reference(name="a"), right=Reference(name="b")),
        )
        assert constant_folding_term(term, context={}) == term

    def test_add_primitive_left_ref_right_unchanged(self):
        # (x + y) + z — left is a non-immediate Primitive, right is a Reference.
        # Neither the zero-identity, canonicalise, nor nested-constant rules fire.
        term = Primitive(
            operator="+",
            left=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")),
            right=Reference(name="z"),
        )
        assert constant_folding_term(term, context={}) == term

    # --- line 146: subtraction fallthrough — two non-immediate, non-matching sub-expressions ---

    def test_sub_two_primitives_no_immediate_unchanged(self):
        # (x + y) - (a + b) — the nested-constant rules need Immediates on the
        # left of each sub-Primitive; without them the fallthrough on line 146
        # rebuilds unchanged.
        term = Primitive(
            operator="-",
            left=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")),
            right=Primitive(operator="+", left=Reference(name="a"), right=Reference(name="b")),
        )
        assert constant_folding_term(term, context={}) == term

    def test_sub_ref_left_primitive_right_unchanged(self):
        # x - (y + z) — right is a non-immediate Primitive so the canonicalise
        # rule (which requires right to be Immediate) does not fire either.
        term = Primitive(
            operator="-",
            left=Reference(name="x"),
            right=Primitive(operator="+", left=Reference(name="y"), right=Reference(name="z")),
        )
        assert constant_folding_term(term, context={}) == term

    # --- lines 149 / 185: multiplication — two non-immediate, non-matching sub-expressions ---

    def test_mul_two_refs_unchanged(self):
        # x * y — no immediates, no nested Primitives with Immediates,
        # hits the fallthrough on line 185 and rebuilds unchanged.
        term = Primitive(
            operator="*",
            left=Reference(name="x"),
            right=Reference(name="y"),
        )
        assert constant_folding_term(term, context={}) == term

    def test_mul_two_primitives_no_immediate_unchanged(self):
        # (x + y) * (a + b) — nested Primitives but no Immediates on their
        # left sides, so the constant-merging rule does not fire.
        term = Primitive(
            operator="*",
            left=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")),
            right=Primitive(operator="+", left=Reference(name="a"), right=Reference(name="b")),
        )
        assert constant_folding_term(term, context={}) == term

    def test_mul_ref_left_primitive_right_unchanged(self):
        # x * (y + z) — right is a non-immediate Primitive so neither the
        # identity rules nor the canonicalise rule (Immediate on right) fires.
        term = Primitive(
            operator="*",
            left=Reference(name="x"),
            right=Primitive(operator="+", left=Reference(name="y"), right=Reference(name="z")),
        )
        assert constant_folding_term(term, context={}) == term

    # --- line 214: Begin — recurses into multiple effects and the value ---

    def test_begin_folds_multiple_effects(self):
        # begin [store(arr,0,1+1), store(arr,1,2+2)]; 3+3
        # =>  begin [store(arr,0,2), store(arr,1,4)]; 6
        term = Begin(
            effects=(
                Store(
                    base=Reference(name="arr"),
                    index=0,
                    value=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=1)),
                ),
                Store(
                    base=Reference(name="arr"),
                    index=1,
                    value=Primitive(operator="+", left=Immediate(value=2), right=Immediate(value=2)),
                ),
            ),
            value=Primitive(operator="+", left=Immediate(value=3), right=Immediate(value=3)),
        )
        expected = Begin(
            effects=(
                Store(base=Reference(name="arr"), index=0, value=Immediate(value=2)),
                Store(base=Reference(name="arr"), index=1, value=Immediate(value=4)),
            ),
            value=Immediate(value=6),
        )
        assert constant_folding_term(term, context={}) == expected

    def test_begin_no_constants_unchanged(self):
        # begin [store(arr, 0, x)]; y — nothing to fold anywhere,
        # recurse fires but returns everything unchanged.
        term = Begin(
            effects=(Store(base=Reference(name="arr"), index=0, value=Reference(name="x")),),
            value=Reference(name="y"),
        )
        assert constant_folding_term(term, context={}) == term


# ===========================================================================
# 2. Constant Propagation
# ===========================================================================


class TestConstantPropagation:
    def test_reference_in_env_replaced(self):
        term = Reference(name="x")
        assert constant_propagation_term(term, env={"x": 5}) == Immediate(value=5)

    def test_reference_not_in_env_unchanged(self):
        term = Reference(name="y")
        assert constant_propagation_term(term, env={"x": 5}) == Reference(name="y")

    def test_immediate_unchanged(self):
        term = Immediate(value=7)
        assert constant_propagation_term(term, env={}) == Immediate(value=7)

    def test_propagates_into_primitive(self):
        # x + y with x=3 in env  =>  3 + y
        term = Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y"))
        expected = Primitive(operator="+", left=Immediate(value=3), right=Reference(name="y"))
        assert constant_propagation_term(term, env={"x": 3}) == expected

    def test_let_extends_env_for_body(self):
        # let x = 5 in x + 1  =>  let x = 5 in 5 + 1
        term = Let(
            bindings=(("x", Immediate(value=5)),),
            body=Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=1)),
        )
        expected = Let(
            bindings=(("x", Immediate(value=5)),),
            body=Primitive(operator="+", left=Immediate(value=5), right=Immediate(value=1)),
        )
        assert constant_propagation_term(term, env={}) == expected

    def test_let_binding_cascades_to_later_binding(self):
        # let x = 3
        #     y = x + 1   <- x is now known as 3, propagated in
        # in  y            <- y's value is not Immediate so y not added to env
        term = Let(
            bindings=(
                ("x", Immediate(value=3)),
                ("y", Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=1))),
            ),
            body=Reference(name="y"),
        )
        expected = Let(
            bindings=(
                ("x", Immediate(value=3)),
                ("y", Primitive(operator="+", left=Immediate(value=3), right=Immediate(value=1))),
            ),
            body=Reference(name="y"),
        )
        assert constant_propagation_term(term, env={}) == expected

    def test_let_constant_binding_propagated_into_body(self):
        # let x = 10 in x * 2  =>  let x = 10 in 10 * 2
        term = Let(
            bindings=(("x", Immediate(value=10)),),
            body=Primitive(operator="*", left=Reference(name="x"), right=Immediate(value=2)),
        )
        expected = Let(
            bindings=(("x", Immediate(value=10)),),
            body=Primitive(operator="*", left=Immediate(value=10), right=Immediate(value=2)),
        )
        assert constant_propagation_term(term, env={}) == expected

    def test_abstract_shadows_parameter(self):
        # lambda(x): x + y  with x=99, y=7 in outer env
        # x is a parameter so must NOT be replaced; y is free so it is
        term = Abstract(
            parameters=("x",),
            body=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")),
        )
        expected = Abstract(
            parameters=("x",),
            body=Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=7)),
        )
        assert constant_propagation_term(term, env={"x": 99, "y": 7}) == expected

    def test_apply_propagates_into_arguments(self):
        term = Apply(
            target=Reference(name="f"),
            arguments=(Reference(name="x"), Reference(name="y")),
        )
        expected = Apply(
            target=Reference(name="f"),
            arguments=(Immediate(value=1), Reference(name="y")),
        )
        assert constant_propagation_term(term, env={"x": 1}) == expected

    def test_branch_propagates_into_all_sub_terms(self):
        term = Branch(
            operator="<",
            left=Reference(name="x"),
            right=Reference(name="y"),
            consequent=Reference(name="x"),
            otherwise=Reference(name="y"),
        )
        expected = Branch(
            operator="<",
            left=Immediate(value=3),
            right=Reference(name="y"),
            consequent=Immediate(value=3),
            otherwise=Reference(name="y"),
        )
        assert constant_propagation_term(term, env={"x": 3}) == expected

    def test_empty_env_leaves_everything_unchanged(self):
        term = Primitive(operator="+", left=Reference(name="a"), right=Reference(name="b"))
        assert constant_propagation_term(term, env={}) == term

    def test_allocate(self):
        term = Allocate(count=1)
        assert constant_propagation_term(term, env={}) == term

    def test_load(self):
        term = Load(base=Immediate(value=1), index=1)
        assert constant_propagation_term(term, env={}) == term

    def test_store(self):
        term = Store(base=Immediate(value=1), index=1, value=Immediate(value=1))
        assert constant_propagation_term(term, env={}) == term


# ===========================================================================
# 3. Dead Code Elimination — free_variables helper
# ===========================================================================


class TestFreeVariables:
    def test_reference(self):
        assert free_variables(Reference(name="x")) == frozenset({"x"})

    def test_immediate(self):
        assert free_variables(Immediate(value=5)) == frozenset()

    def test_primitive(self):
        term = Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y"))
        assert free_variables(term) == frozenset({"x", "y"})

    def test_let_binds_name(self):
        # let x = 1 in x  — x is bound, not free
        term = Let(bindings=(("x", Immediate(value=1)),), body=Reference(name="x"))
        assert free_variables(term) == frozenset()

    def test_let_free_in_value(self):
        # let x = y in x  — y is free
        term = Let(bindings=(("x", Reference(name="y")),), body=Reference(name="x"))
        assert free_variables(term) == frozenset({"y"})

    def test_let_free_in_body(self):
        # let x = 1 in x + z  — z is free
        term = Let(
            bindings=(("x", Immediate(value=1)),),
            body=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="z")),
        )
        assert free_variables(term) == frozenset({"z"})

    def test_abstract_binds_parameter(self):
        # lambda(x): x + y  — x bound by lambda, y is free
        term = Abstract(
            parameters=("x",),
            body=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")),
        )
        assert free_variables(term) == frozenset({"y"})

    def test_apply(self):
        term = Apply(
            target=Reference(name="f"),
            arguments=(Reference(name="x"), Reference(name="y")),
        )
        assert free_variables(term) == frozenset({"f", "x", "y"})

    def test_branch(self):
        term = Branch(
            operator="<",
            left=Reference(name="a"),
            right=Reference(name="b"),
            consequent=Reference(name="c"),
            otherwise=Reference(name="d"),
        )
        assert free_variables(term) == frozenset({"a", "b", "c", "d"})


# ===========================================================================
# 4. Dead Code Elimination — is_pure helper
# ===========================================================================


class TestIsPure:
    def test_immediate_is_pure(self):
        assert is_pure(Immediate(value=1))

    def test_reference_is_pure(self):
        assert is_pure(Reference(name="x"))

    def test_primitive_both_pure(self):
        assert is_pure(Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=2)))

    def test_abstract_is_pure(self):
        assert is_pure(Abstract(parameters=("x",), body=Reference(name="x")))

    def test_apply_is_impure(self):
        assert not is_pure(Apply(target=Reference(name="f"), arguments=()))

    def test_allocate_is_impure(self):
        assert not is_pure(Allocate(count=1))

    def test_load_is_impure(self):
        assert not is_pure(Load(base=Reference(name="arr"), index=0))

    def test_store_is_impure(self):
        assert not is_pure(Store(base=Reference(name="arr"), index=0, value=Immediate(value=1)))

    def test_begin_is_impure(self):
        assert not is_pure(
            Begin(
                effects=(Store(base=Reference(name="arr"), index=0, value=Immediate(value=0)),),
                value=Immediate(value=1),
            )
        )

    def test_let_all_pure(self):
        assert is_pure(Let(bindings=(("x", Immediate(value=1)),), body=Reference(name="x")))

    def test_let_impure_binding(self):
        assert not is_pure(Let(bindings=(("x", Allocate(count=1)),), body=Reference(name="x")))


# ===========================================================================
# 5. Dead Code Elimination — main pass
# ===========================================================================


class TestDeadCodeElimination:
    def test_unused_pure_binding_dropped(self):
        # let x = 1 in 42  =>  42
        term = Let(bindings=(("x", Immediate(value=1)),), body=Immediate(value=42))
        assert dead_code_elimination_term(term) == Immediate(value=42)

    def test_used_binding_kept(self):
        # let x = 1 in x  =>  unchanged
        term = Let(bindings=(("x", Immediate(value=1)),), body=Reference(name="x"))
        assert dead_code_elimination_term(term) == term

    def test_impure_unused_binding_kept(self):
        # let _ = store(arr, 0, 1) in 42  — side-effect must not be dropped
        term = Let(
            bindings=(("_", Store(base=Reference(name="arr"), index=0, value=Immediate(value=1))),),
            body=Immediate(value=42),
        )
        assert dead_code_elimination_term(term) == term

    def test_cascade_elimination(self):
        # let a = 1        <- only feeds b
        #     b = a + 1    <- not used in body
        # in  99
        # => both are dead and pure => 99
        term = Let(
            bindings=(
                ("a", Immediate(value=1)),
                ("b", Primitive(operator="+", left=Reference(name="a"), right=Immediate(value=1))),
            ),
            body=Immediate(value=99),
        )
        assert dead_code_elimination_term(term) == Immediate(value=99)

    def test_partial_elimination(self):
        # let a = 1    <- used in body
        #     b = 2    <- NOT used
        # in  a
        # => b dropped, a kept
        term = Let(
            bindings=(("a", Immediate(value=1)), ("b", Immediate(value=2))),
            body=Reference(name="a"),
        )
        expected = Let(bindings=(("a", Immediate(value=1)),), body=Reference(name="a"))
        assert dead_code_elimination_term(term) == expected

    def test_empty_let_collapses_to_body(self):
        # All bindings dead => Let disappears entirely
        term = Let(
            bindings=(("x", Immediate(value=0)), ("y", Immediate(value=0))),
            body=Immediate(value=7),
        )
        assert dead_code_elimination_term(term) == Immediate(value=7)

    def test_nested_dead_binding_inside_abstract(self):
        # lambda(p): let unused = 1 in p  =>  lambda(p): p
        term = Abstract(
            parameters=("p",),
            body=Let(bindings=(("unused", Immediate(value=1)),), body=Reference(name="p")),
        )
        expected = Abstract(parameters=("p",), body=Reference(name="p"))
        assert dead_code_elimination_term(term) == expected

    def test_dead_binding_inside_branch_arm(self):
        # if x < y then (let z=1 in 10) else 20  =>  if x < y then 10 else 20
        term = Branch(
            operator="<",
            left=Reference(name="x"),
            right=Reference(name="y"),
            consequent=Let(bindings=(("z", Immediate(value=1)),), body=Immediate(value=10)),
            otherwise=Immediate(value=20),
        )
        expected = Branch(
            operator="<",
            left=Reference(name="x"),
            right=Reference(name="y"),
            consequent=Immediate(value=10),
            otherwise=Immediate(value=20),
        )
        assert dead_code_elimination_term(term) == expected

    def test_immediate_passthrough(self):
        assert dead_code_elimination_term(Immediate(value=5)) == Immediate(value=5)

    def test_reference_passthrough(self):
        assert dead_code_elimination_term(Reference(name="x")) == Reference(name="x")

    def test_begin_effects_always_kept(self):
        # Effects in Begin are side-effectful by definition — never dropped
        term = Begin(
            effects=(Store(base=Reference(name="arr"), index=0, value=Immediate(value=1)),),
            value=Immediate(value=0),
        )
        assert dead_code_elimination_term(term) == term

    # --- line 196: Apply — recurses into target and all arguments ---

    def test_apply_recurses_dead_binding_in_argument(self):
        # f(let unused=1 in x)  =>  f(x)
        # Dead Let inside an argument is eliminated; Apply itself is kept.
        term = Apply(
            target=Reference(name="f"),
            arguments=(Let(bindings=(("unused", Immediate(value=1)),), body=Reference(name="x")),),
        )
        expected = Apply(
            target=Reference(name="f"),
            arguments=(Reference(name="x"),),
        )
        assert dead_code_elimination_term(term) == expected

    def test_apply_recurses_dead_binding_in_target(self):
        # (let unused=1 in f)(x)  =>  f(x)
        term = Apply(
            target=Let(bindings=(("unused", Immediate(value=1)),), body=Reference(name="f")),
            arguments=(Reference(name="x"),),
        )
        expected = Apply(
            target=Reference(name="f"),
            arguments=(Reference(name="x"),),
        )
        assert dead_code_elimination_term(term) == expected

    def test_apply_no_dead_bindings_unchanged(self):
        # f(x, y) — nothing nested to eliminate, returned structurally equal.
        term = Apply(
            target=Reference(name="f"),
            arguments=(Reference(name="x"), Reference(name="y")),
        )
        assert dead_code_elimination_term(term) == term

    # --- line 220: Load — recurses into base ---

    def test_load_recurses_dead_binding_in_base(self):
        # load(let unused=1 in arr, 0)  =>  load(arr, 0)
        term = Load(
            base=Let(bindings=(("unused", Immediate(value=1)),), body=Reference(name="arr")),
            index=0,
        )
        expected = Load(base=Reference(name="arr"), index=0)
        assert dead_code_elimination_term(term) == expected

    def test_load_no_dead_bindings_unchanged(self):
        # load(arr, 2) — nothing to eliminate.
        term = Load(base=Reference(name="arr"), index=2)
        assert dead_code_elimination_term(term) == term

    def test_load_impure_kept_when_result_unused(self):
        # let x = load(arr, 0) in 42
        # Load reads memory — impure — binding must NOT be dropped.
        term = Let(
            bindings=(("x", Load(base=Reference(name="arr"), index=0)),),
            body=Immediate(value=42),
        )
        assert dead_code_elimination_term(term) == term

    # --- lines 238+: Immediate | Reference | Allocate passthrough ---
    # Each sub-pattern is listed explicitly so the coverage tool sees all three
    # branches of the combined case hit independently.

    def test_immediate_direct_passthrough(self):
        # Immediate(5) passed directly — hits the Immediate branch of line 238.
        term = Immediate(value=5)
        assert dead_code_elimination_term(term) is term

    def test_reference_direct_passthrough(self):
        # Reference("x") passed directly — hits the Reference branch of line 238.
        term = Reference(name="x")
        assert dead_code_elimination_term(term) is term

    def test_allocate_passthrough(self):
        # Allocate is atomic — hits the Allocate branch of line 238.
        term = Allocate(count=4)
        assert dead_code_elimination_term(term) is term

    def test_allocate_impure_kept_when_result_unused(self):
        # let x = allocate(4) in 99
        # Allocate is impure — binding must NOT be dropped even though x unused.
        term = Let(
            bindings=(("x", Allocate(count=4)),),
            body=Immediate(value=99),
        )
        assert dead_code_elimination_term(term) == term


# ===========================================================================
# New tests for free_variables: lines 104, 108, 115-123
# ===========================================================================


class TestFreeVariablesExtended:
    # --- line 104: Allocate has no variable references ---

    def test_allocate_has_no_free_variables(self):
        assert free_variables(Allocate(count=8)) == frozenset()

    # --- line 108: Load — free variables come from base expression ---

    def test_load_free_variables_from_base_reference(self):
        # load(arr, 0) — arr is free
        term = Load(base=Reference(name="arr"), index=0)
        assert free_variables(term) == frozenset({"arr"})

    def test_load_free_variables_from_base_primitive(self):
        # load(x + y, 0) — both x and y are free
        term = Load(
            base=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")),
            index=0,
        )
        assert free_variables(term) == frozenset({"x", "y"})

    def test_load_base_immediate_no_free_variables(self):
        # load(5, 0) — no variables in base
        term = Load(base=Immediate(value=5), index=0)
        assert free_variables(term) == frozenset()

    # --- lines 115-123: Begin — unions value and all effects ---

    def test_begin_free_variables_from_value_only(self):
        # begin [store(arr,0,1)]; x
        # arr is in the effect, x is in the value — both free
        term = Begin(
            effects=(Store(base=Reference(name="arr"), index=0, value=Immediate(value=1)),),
            value=Reference(name="x"),
        )
        assert free_variables(term) == frozenset({"arr", "x"})

    def test_begin_free_variables_from_multiple_effects(self):
        # begin [store(a,0,1), store(b,0,2)]; c
        # a, b from effects; c from value — all free
        term = Begin(
            effects=(
                Store(base=Reference(name="a"), index=0, value=Immediate(value=1)),
                Store(base=Reference(name="b"), index=0, value=Immediate(value=2)),
            ),
            value=Reference(name="c"),
        )
        assert free_variables(term) == frozenset({"a", "b", "c"})

    def test_begin_free_variables_effect_and_value_overlap(self):
        # begin [store(arr,0,x)]; x
        # x appears in both the effect value and the Begin value — still just {arr, x}
        term = Begin(
            effects=(Store(base=Reference(name="arr"), index=0, value=Reference(name="x")),),
            value=Reference(name="x"),
        )
        assert free_variables(term) == frozenset({"arr", "x"})

    def test_begin_no_free_variables(self):
        # begin [store(arr,0,1)]; 42 — arr is still free (it's a reference)
        # Use all immediates to get truly empty set
        term = Begin(
            effects=(Store(base=Immediate(value=0), index=0, value=Immediate(value=1)),),
            value=Immediate(value=42),
        )
        assert free_variables(term) == frozenset()

    def test_unhandled_variant_raises(self):
        # Line 123 — the raise ValueError at the bottom of free_variables fires
        # when passed something that matches none of the known Term cases.
        # A plain Python object satisfies this because structural pattern
        # matching only matches the cases whose class attributes are present.
        import pytest

        class _Unknown:
            pass

        with pytest.raises((ValueError, Exception)):
            free_variables(_Unknown())


# ===========================================================================
# New tests for is_pure: lines 151-154 (Branch impure + wildcard fallthrough)
# ===========================================================================


class TestIsPureExtended:
    def test_branch_is_impure(self):
        # Branch is treated as impure — its arms may have side-effects.
        term = Branch(
            operator="<",
            left=Immediate(value=1),
            right=Immediate(value=2),
            consequent=Immediate(value=10),
            otherwise=Immediate(value=20),
        )
        assert not is_pure(term)

    def test_branch_impure_binding_kept_even_if_unused(self):
        # let _ = (if 1 < 2 then 10 else 20) in 99
        # Branch is impure so the binding must be kept even though _ is unused.
        term = Let(
            bindings=(
                (
                    "_",
                    Branch(
                        operator="<",
                        left=Immediate(value=1),
                        right=Immediate(value=2),
                        consequent=Immediate(value=10),
                        otherwise=Immediate(value=20),
                    ),
                ),
            ),
            body=Immediate(value=99),
        )
        assert dead_code_elimination_term(term) == term

    def test_let_with_pure_bindings_and_pure_body_is_pure(self):
        # let x = 1
        #     y = x + 2
        # in  y
        # All values are pure Primitives/Immediates/References, body is a Reference.
        term = Let(
            bindings=(
                ("x", Immediate(value=1)),
                ("y", Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=2))),
            ),
            body=Reference(name="y"),
        )
        assert is_pure(term)

    def test_let_with_impure_body_is_impure(self):
        # let x = 1 in load(arr, 0)
        # Body performs a load — impure.
        term = Let(
            bindings=(("x", Immediate(value=1)),),
            body=Load(base=Reference(name="arr"), index=0),
        )
        assert not is_pure(term)

    def test_unknown_object_is_impure(self):
        # Lines 151-154 — the wildcard case _ fires when passed something
        # that matches none of the known Term variants.  The function must
        # return False (conservative: treat unknown as impure).
        class _Unknown:
            pass

        assert is_pure(_Unknown()) is False


# ===========================================================================
# 6. Branch Elimination
# ===========================================================================


class TestBranchElimination:
    def test_lt_true_replaced_with_consequent(self):
        # if 1 < 2 then 10 else 20  =>  10
        term = Branch(
            operator="<",
            left=Immediate(value=1),
            right=Immediate(value=2),
            consequent=Immediate(value=10),
            otherwise=Immediate(value=20),
        )
        assert branch_elimination_term(term) == Immediate(value=10)

    def test_lt_false_replaced_with_otherwise(self):
        # if 5 < 3 then 10 else 20  =>  20
        term = Branch(
            operator="<",
            left=Immediate(value=5),
            right=Immediate(value=3),
            consequent=Immediate(value=10),
            otherwise=Immediate(value=20),
        )
        assert branch_elimination_term(term) == Immediate(value=20)

    def test_lt_equal_values_is_false(self):
        # if 4 < 4 then 1 else 0  =>  0  (strict less-than, not <=)
        term = Branch(
            operator="<",
            left=Immediate(value=4),
            right=Immediate(value=4),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=0),
        )
        assert branch_elimination_term(term) == Immediate(value=0)

    def test_eq_true_replaced_with_consequent(self):
        # if 7 == 7 then 1 else 0  =>  1
        term = Branch(
            operator="==",
            left=Immediate(value=7),
            right=Immediate(value=7),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=0),
        )
        assert branch_elimination_term(term) == Immediate(value=1)

    def test_eq_false_replaced_with_otherwise(self):
        # if 3 == 5 then 1 else 0  =>  0
        term = Branch(
            operator="==",
            left=Immediate(value=3),
            right=Immediate(value=5),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=0),
        )
        assert branch_elimination_term(term) == Immediate(value=0)

    def test_unknown_condition_preserved(self):
        # if x < y then 1 else 0  =>  unchanged
        term = Branch(
            operator="<",
            left=Reference(name="x"),
            right=Reference(name="y"),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=0),
        )
        assert branch_elimination_term(term) == term

    def test_recurses_into_arms(self):
        # Outer condition unknown; inner branch in consequent is statically known.
        # if x < y then (if 1 < 2 then 10 else 20) else 30  =>  if x < y then 10 else 30
        term = Branch(
            operator="<",
            left=Reference(name="x"),
            right=Reference(name="y"),
            consequent=Branch(
                operator="<",
                left=Immediate(value=1),
                right=Immediate(value=2),
                consequent=Immediate(value=10),
                otherwise=Immediate(value=20),
            ),
            otherwise=Immediate(value=30),
        )
        expected = Branch(
            operator="<",
            left=Reference(name="x"),
            right=Reference(name="y"),
            consequent=Immediate(value=10),
            otherwise=Immediate(value=30),
        )
        assert branch_elimination_term(term) == expected

    def test_recurses_into_let_bindings(self):
        # let x = (if 1 < 2 then 5 else 6) in x  =>  let x = 5 in x
        term = Let(
            bindings=(
                (
                    "x",
                    Branch(
                        operator="<",
                        left=Immediate(value=1),
                        right=Immediate(value=2),
                        consequent=Immediate(value=5),
                        otherwise=Immediate(value=6),
                    ),
                ),
            ),
            body=Reference(name="x"),
        )
        expected = Let(bindings=(("x", Immediate(value=5)),), body=Reference(name="x"))
        assert branch_elimination_term(term) == expected

    def test_recurses_into_abstract_body(self):
        term = Abstract(
            parameters=("p",),
            body=Branch(
                operator="==",
                left=Immediate(value=1),
                right=Immediate(value=1),
                consequent=Immediate(value=99),
                otherwise=Immediate(value=0),
            ),
        )
        expected = Abstract(parameters=("p",), body=Immediate(value=99))
        assert branch_elimination_term(term) == expected

    def test_passthrough_immediate(self):
        assert branch_elimination_term(Immediate(value=3)) == Immediate(value=3)

    def test_passthrough_reference(self):
        assert branch_elimination_term(Reference(name="z")) == Reference(name="z")

    def test_passthrough_allocate(self):
        assert branch_elimination_term(Allocate(count=2)) == Allocate(count=2)

    def test_passthrough_Load(self):
        assert branch_elimination_term(Load(base=Immediate(value=1), index=3)) == Load(base=Immediate(value=1), index=3)

    def test_recurses_into_otherwise_arm(self):
        # Outer condition unknown; inner known branch is in the otherwise arm.
        # if x < y then 30 else (if 1 < 2 then 10 else 20)  =>  if x < y then 30 else 10
        term = Branch(
            operator="<",
            left=Reference(name="x"),
            right=Reference(name="y"),
            consequent=Immediate(value=30),
            otherwise=Branch(
                operator="<",
                left=Immediate(value=1),
                right=Immediate(value=2),
                consequent=Immediate(value=10),
                otherwise=Immediate(value=20),
            ),
        )
        expected = Branch(
            operator="<",
            left=Reference(name="x"),
            right=Reference(name="y"),
            consequent=Immediate(value=30),
            otherwise=Immediate(value=10),
        )
        assert branch_elimination_term(term) == expected

    def test_recurses_into_apply_arguments(self):
        # f(if 1 < 2 then 10 else 20)  =>  f(10)
        term = Apply(
            target=Reference(name="f"),
            arguments=(
                Branch(
                    operator="<",
                    left=Immediate(value=1),
                    right=Immediate(value=2),
                    consequent=Immediate(value=10),
                    otherwise=Immediate(value=20),
                ),
            ),
        )
        expected = Apply(
            target=Reference(name="f"),
            arguments=(Immediate(value=10),),
        )
        assert branch_elimination_term(term) == expected

    def test_recurses_into_apply_target(self):
        # (if 1==1 then f else g)(x)  =>  f(x)
        term = Apply(
            target=Branch(
                operator="==",
                left=Immediate(value=1),
                right=Immediate(value=1),
                consequent=Reference(name="f"),
                otherwise=Reference(name="g"),
            ),
            arguments=(Reference(name="x"),),
        )
        expected = Apply(
            target=Reference(name="f"),
            arguments=(Reference(name="x"),),
        )
        assert branch_elimination_term(term) == expected

    def test_recurses_into_primitive_operands(self):
        # (if 1 < 2 then 3 else 4) + (if 5 == 5 then 6 else 7)  =>  3 + 6
        term = Primitive(
            operator="+",
            left=Branch(
                operator="<",
                left=Immediate(value=1),
                right=Immediate(value=2),
                consequent=Immediate(value=3),
                otherwise=Immediate(value=4),
            ),
            right=Branch(
                operator="==",
                left=Immediate(value=5),
                right=Immediate(value=5),
                consequent=Immediate(value=6),
                otherwise=Immediate(value=7),
            ),
        )
        expected = Primitive(
            operator="+",
            left=Immediate(value=3),
            right=Immediate(value=6),
        )
        assert branch_elimination_term(term) == expected

    def test_recurses_into_store_value(self):
        # store(arr, 0, if 2==2 then 99 else 0)  =>  store(arr, 0, 99)
        term = Store(
            base=Reference(name="arr"),
            index=0,
            value=Branch(
                operator="==",
                left=Immediate(value=2),
                right=Immediate(value=2),
                consequent=Immediate(value=99),
                otherwise=Immediate(value=0),
            ),
        )
        expected = Store(
            base=Reference(name="arr"),
            index=0,
            value=Immediate(value=99),
        )
        assert branch_elimination_term(term) == expected

    def test_recurses_into_store_base(self):
        # store(if 1<2 then arr else arr2, 0, x)  =>  store(arr, 0, x)
        term = Store(
            base=Branch(
                operator="<",
                left=Immediate(value=1),
                right=Immediate(value=2),
                consequent=Reference(name="arr"),
                otherwise=Reference(name="arr2"),
            ),
            index=0,
            value=Reference(name="x"),
        )
        expected = Store(
            base=Reference(name="arr"),
            index=0,
            value=Reference(name="x"),
        )
        assert branch_elimination_term(term) == expected

    def test_recurses_into_begin_effect(self):
        # begin [store(arr, 0, if 1<2 then 10 else 20)]; 0  =>  begin [store(arr, 0, 10)]; 0
        term = Begin(
            effects=(
                Store(
                    base=Reference(name="arr"),
                    index=0,
                    value=Branch(
                        operator="<",
                        left=Immediate(value=1),
                        right=Immediate(value=2),
                        consequent=Immediate(value=10),
                        otherwise=Immediate(value=20),
                    ),
                ),
            ),
            value=Immediate(value=0),
        )
        expected = Begin(
            effects=(Store(base=Reference(name="arr"), index=0, value=Immediate(value=10)),),
            value=Immediate(value=0),
        )
        assert branch_elimination_term(term) == expected

    def test_recurses_into_begin_value(self):
        # begin [store(arr,0,1)]; if 3==3 then x else y  =>  begin [store(arr,0,1)]; x
        term = Begin(
            effects=(Store(base=Reference(name="arr"), index=0, value=Immediate(value=1)),),
            value=Branch(
                operator="==",
                left=Immediate(value=3),
                right=Immediate(value=3),
                consequent=Reference(name="x"),
                otherwise=Reference(name="y"),
            ),
        )
        expected = Begin(
            effects=(Store(base=Reference(name="arr"), index=0, value=Immediate(value=1)),),
            value=Reference(name="x"),
        )
        assert branch_elimination_term(term) == expected


# ===========================================================================
# 7. Full optimize_program — integration tests
# ===========================================================================


class TestOptimizeProgram:
    def test_add_two_immediates(self):
        # The example from the provided test file
        program = Program(
            parameters=(),
            body=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=1)),
        )
        expected = Program(parameters=(), body=Immediate(value=2))
        assert optimize_program(program) == expected

    def test_already_optimal_unchanged(self):
        program = Program(parameters=(), body=Immediate(value=42))
        assert optimize_program(program) == program

    def test_deep_constant_expression(self):
        # (1 + 2) * (3 + 4)  =>  21
        program = Program(
            parameters=(),
            body=Primitive(
                operator="*",
                left=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
                right=Primitive(operator="+", left=Immediate(value=3), right=Immediate(value=4)),
            ),
        )
        expected = Program(parameters=(), body=Immediate(value=21))
        assert optimize_program(program) == expected

    def test_propagation_then_folding(self):
        # let x = 3 in x + 2  =>  5
        program = Program(
            parameters=(),
            body=Let(
                bindings=(("x", Immediate(value=3)),),
                body=Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=2)),
            ),
        )
        expected = Program(parameters=(), body=Immediate(value=5))
        assert optimize_program(program) == expected

    def test_dead_binding_then_propagation(self):
        # let unused = 99
        #     x      = 4
        # in  x * 2
        # => 8
        program = Program(
            parameters=(),
            body=Let(
                bindings=(("unused", Immediate(value=99)), ("x", Immediate(value=4))),
                body=Primitive(operator="*", left=Reference(name="x"), right=Immediate(value=2)),
            ),
        )
        expected = Program(parameters=(), body=Immediate(value=8))
        assert optimize_program(program) == expected

    def test_branch_elimination_after_propagation(self):
        # let threshold = 10 in if threshold < 20 then 1 else 0  =>  1
        program = Program(
            parameters=(),
            body=Let(
                bindings=(("threshold", Immediate(value=10)),),
                body=Branch(
                    operator="<",
                    left=Reference(name="threshold"),
                    right=Immediate(value=20),
                    consequent=Immediate(value=1),
                    otherwise=Immediate(value=0),
                ),
            ),
        )
        expected = Program(parameters=(), body=Immediate(value=1))
        assert optimize_program(program) == expected

    def test_cascade_across_all_passes(self):
        # let a = 2 + 3       folded to 5
        #     b = a * 2       propagated + folded to 10
        #     unused = 99     dead
        # in  b + 0           +0 identity + propagation => 10
        program = Program(
            parameters=(),
            body=Let(
                bindings=(
                    ("a", Primitive(operator="+", left=Immediate(value=2), right=Immediate(value=3))),
                    ("b", Primitive(operator="*", left=Reference(name="a"), right=Immediate(value=2))),
                    ("unused", Immediate(value=99)),
                ),
                body=Primitive(operator="+", left=Reference(name="b"), right=Immediate(value=0)),
            ),
        )
        expected = Program(parameters=(), body=Immediate(value=10))
        assert optimize_program(program) == expected

    def test_program_with_parameters_optimises_body(self):
        # Parameters are unknown at compile time but the body can still be folded
        program = Program(
            parameters=("n",),
            body=Primitive(operator="+", left=Immediate(value=2), right=Immediate(value=3)),
        )
        expected = Program(parameters=("n",), body=Immediate(value=5))
        assert optimize_program(program) == expected

    def test_unknown_variable_expression_unchanged(self):
        # n + 1 — n is a runtime parameter, cannot be reduced
        # Canonicalisation moves the immediate to the left: 1 + n
        program = Program(
            parameters=("n",),
            body=Primitive(operator="+", left=Reference(name="n"), right=Immediate(value=1)),
        )
        expected = Program(
            parameters=("n",),
            body=Primitive(operator="+", left=Immediate(value=1), right=Reference(name="n")),
        )
        assert optimize_program(program) == expected

    def test_idempotent(self):
        # Running the optimizer twice should give the same result as once
        program = Program(
            parameters=(),
            body=Let(
                bindings=(("x", Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2))),),
                body=Primitive(operator="*", left=Reference(name="x"), right=Immediate(value=4)),
            ),
        )
        once = optimize_program(program)
        twice = optimize_program(once)
        assert once == twice
