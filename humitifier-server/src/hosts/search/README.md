# Advanced Search Architecture

The advanced search engine evaluates search queries against Host metadata and JSONB scan cache data (`last_scan_cache`). It is built around an **expression tree (AST)** and a **compiler** that generates Django `Q` objects and parameterised PostgreSQL JSONB queries.

---

## Architectural Principles

1. **Self-Registering Components**:
   - `SearchFunction` subclasses auto-register in `function_registry`.
   - `ComparisonOperator` subclasses auto-register in `operator_registry`.
   - Functions defined anywhere in `hosts/search/functions/` are auto-discovered using `pkgutil.iter_modules`.

2. **No Hardcoded Strings Convention**:
   - All section identifiers (`facts`, `metrics`, `meta`), kinds (`scalar`, `array`), value types (`string`, `integer`, `boolean`), logical keywords, token types, form parameter names, and export formats are defined as `StrEnum`s or constants in `hosts/search/constants.py`.
   - Function names exist exclusively as `SearchFunction.name`.
   - Operator symbols exist exclusively as `ComparisonOperator.symbol`.
   - Never introduce raw string literals when referring to these concepts anywhere in the codebase.

3. **Composable Parameterised SQL (`SqlFragment`)**:
   - Every SQL fragment carries its parameters (`SqlFragment(sql, params)`).
   - SQL fragments can be combined with `+` or `SqlFragment.join()` without tracking parameter indexes manually.
   - All values are parameterised (`%s`) to prevent SQL injection.

4. **Element Scopes (`ElementSet`) & Single-Query Execution**:
   - Array fields compile to `ElementSet` instances representing a `LATERAL jsonb_array_elements` expansion.
   - Array filtering adds conditions to the element scope.
   - Array aggregations wrap the scope in a scalar subquery `(SELECT AGG(...) ...)`.
   - Array comparisons wrap the scope in `EXISTS (SELECT 1 FROM ...)`.
   - Boolean queries compile into Django `Q` objects combining ORM lookups and `RawSQL(..., output_field=BooleanField())`.
   - Conjunctions (`AND`) and disjunctions (`OR`) compile to `&` and `|`, executing in a single SQL query without materializing ID lists.

---

## How to Add a Search Function

To add a new search function:

1. Create a class inheriting from `SearchFunction` in `hosts/search/functions/` (e.g. in a new or existing module):

```python
from hosts.search.constants import Cardinality, ValueType
from hosts.search.functions.base import Param, ParamKind, SearchFunction
from hosts.search.nodes import ExprType
from hosts.search.sql import CompileContext, ScalarSql, SqlFragment

class ExampleFunc(SearchFunction):
    name = "example_func"
    description = "Example function description shown in help"
    examples = ("example_func(facts.generic.Users[].name) > 0",)
    params = (
        Param("field", ParamKind.FIELD, frozenset({ValueType.STRING}), Cardinality.ELEMENTS),
    )

    @classmethod
    def return_type(cls, args):
        return ExprType(ValueType.INTEGER, Cardinality.SINGLE)

    @classmethod
    def compile(cls, args, ctx: CompileContext):
        elem_set = ctx.to_element_set(args[0])
        # Build SQL fragment using elem_set.source and elem_set.conditions
        ...
```

2. That's it!
   - `functions/__init__.py` will discover your submodule automatically.
   - `function_registry` registers the class.
   - `get_language_spec()` will expose it to the frontend autocomplete and help panel.
   - The query parser will recognize its signature and validate argument types at parse time.

### Variadic & Correlated Functions
Functions can accept repeated argument groups via `variadic`. For example, correlated predicates matching multiple fields on the same array element:

```python
class CorrelatedMatch(SearchFunction):
    name = "correlated_match"
    description = "Match multiple fields on the same array element"
    params = ()
    variadic = (
        Param("field", ParamKind.FIELD, frozenset({ValueType.STRING}), Cardinality.ELEMENTS),
        Param("pattern", ParamKind.LITERAL, frozenset({ValueType.STRING}), Cardinality.SINGLE),
    )

    @classmethod
    def return_type(cls, args):
        return ExprType(ValueType.BOOLEAN, Cardinality.SINGLE)

    @classmethod
    def compile(cls, args, ctx: CompileContext):
        source = ctx.get_element_source(args[0].field)
        # All fields share the same source (same LATERAL element alias)
        ...
```

---

## How to Add a Comparison Operator

To add a new comparison operator:

1. Subclass `ComparisonOperator` in `hosts/search/operators.py`:

```python
class CustomOp(ComparisonOperator):
    symbol = "!="
    keyword = False
    description = "not equal"

    @classmethod
    def to_lookup(cls, value_type: ValueType) -> str:
        # Django ORM lookup
        return "exact"  # used with invert or custom lookup

    @classmethod
    def to_sql(cls, lhs: SqlFragment, rhs: Any, value_type: ValueType) -> SqlFragment:
        return SqlFragment(f"{lhs.sql} != %s", lhs.params + (rhs,))
```

2. Concrete subclasses without `abstract = True` are registered in `operator_registry` automatically.
