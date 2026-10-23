"""Tests for the advanced search lexer, generic parser, and AST validation."""

from django.test import SimpleTestCase

from hosts.search.constants import (
    Cardinality,
    FieldKind,
    LogicalOperator,
    Section,
    TokenType,
    ValueType,
)
from hosts.search.functions.aggregations import Concat, Count, Max, Min, Sum
from hosts.search.functions.filtering import Filter
from hosts.search.lexer import tokenize
from hosts.search.nodes import (
    Comparison,
    FieldRef,
    FunctionCall,
    Literal,
    Logical,
)
from hosts.search.operators import (
    Contains,
    Equals,
    GreaterOrEqual,
    GreaterThan,
    LessOrEqual,
    LessThan,
)
from hosts.search.parser import parse_query
from hosts.search.types import SearchableField


class SearchLexerTestCase(SimpleTestCase):
    """Test tokenization of queries."""

    def test_tokenize_empty(self):
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize("   \n\t  "), [])

    def test_tokenize_primitives_and_operators(self):
        tokens = tokenize('meta.fqdn = "host01" and count >= 5')
        self.assertEqual(len(tokens), 7)
        self.assertEqual(tokens[0].type, TokenType.IDENT)
        self.assertEqual(tokens[0].value, "meta.fqdn")
        self.assertEqual(tokens[0].position, 0)

        self.assertEqual(tokens[1].type, TokenType.OPERATOR)
        self.assertEqual(tokens[1].value, "=")

        self.assertEqual(tokens[2].type, TokenType.STRING)
        self.assertEqual(tokens[2].value, "host01")

        self.assertEqual(tokens[3].type, TokenType.LOGICAL)
        self.assertEqual(tokens[3].value, LogicalOperator.AND)

        self.assertEqual(tokens[4].type, TokenType.IDENT)
        self.assertEqual(tokens[4].value, "count")

        self.assertEqual(tokens[5].type, TokenType.OPERATOR)
        self.assertEqual(tokens[5].value, ">=")

        self.assertEqual(tokens[6].type, TokenType.NUMBER)
        self.assertEqual(tokens[6].value, 5)

    def test_quoted_literals_always_strings(self):
        # A quoted boolean or number must remain a string token
        tokens = tokenize('"true" "42" \'false\'')
        self.assertEqual(len(tokens), 3)
        for tok in tokens:
            self.assertEqual(tok.type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "true")
        self.assertEqual(tokens[1].value, "42")
        self.assertEqual(tokens[2].value, "false")

    def test_unquoted_booleans(self):
        tokens = tokenize("true FALSE True False")
        self.assertEqual(len(tokens), 4)
        for tok in tokens:
            self.assertEqual(tok.type, TokenType.BOOLEAN)
        self.assertTrue(tokens[0].value)
        self.assertFalse(tokens[1].value)
        self.assertTrue(tokens[2].value)
        self.assertFalse(tokens[3].value)

    def test_escaped_strings(self):
        tokens = tokenize('"hello \\"world\\"" \'it\\\'s\'')
        self.assertEqual(tokens[0].value, 'hello "world"')
        self.assertEqual(tokens[1].value, "it's")

    def test_unterminated_string_error(self):
        with self.assertRaises(ValueError) as ctx:
            tokenize('meta.fqdn = "unclosed')
        self.assertIn("Unterminated string literal", str(ctx.exception))
        self.assertIn("position 12", str(ctx.exception))

    def test_unexpected_character_error(self):
        with self.assertRaises(ValueError) as ctx:
            tokenize("field @ value")
        self.assertIn("Unexpected character '@'", str(ctx.exception))
        self.assertIn("position 6", str(ctx.exception))


class SearchParserTestCase(SimpleTestCase):
    """Test AST construction and semantic validation."""

    def setUp(self):
        self.mock_fields = [
            SearchableField(
                id="meta.fqdn",
                label="meta.fqdn (string)",
                value_type=ValueType.STRING,
                section=Section.META,
                kind=FieldKind.SCALAR,
                artefact_key="",
                field_path=("fqdn",),
            ),
            SearchableField(
                id="meta.archived",
                label="meta.archived (boolean)",
                value_type=ValueType.BOOLEAN,
                section=Section.META,
                kind=FieldKind.SCALAR,
                artefact_key="",
                field_path=("archived",),
            ),
            SearchableField(
                id="facts.hardware.cpus",
                label="facts.hardware.cpus (integer)",
                value_type=ValueType.INTEGER,
                section=Section.FACTS,
                kind=FieldKind.SCALAR,
                artefact_key="hardware",
                field_path=("cpus",),
            ),
            SearchableField(
                id="facts.hardware.memory[].size",
                label="facts.hardware.memory[].size (integer)",
                value_type=ValueType.INTEGER,
                section=Section.FACTS,
                kind=FieldKind.ARRAY,
                artefact_key="hardware",
                field_path=(),
                array_path=("memory", "[]"),
                element_field_path=("size",),
            ),
            SearchableField(
                id="facts.users[].name",
                label="facts.users[].name (string)",
                value_type=ValueType.STRING,
                section=Section.FACTS,
                kind=FieldKind.ARRAY,
                artefact_key="users",
                field_path=(),
                array_path=("[]",),
                element_field_path=("name",),
            ),
        ]

    def _parse(self, query: str):
        return parse_query(query, fields=self.mock_fields)

    def test_parse_empty(self):
        self.assertIsNone(self._parse(""))
        self.assertIsNone(self._parse("   "))
        self.assertIsNone(self._parse(None))

    def test_parse_simple_comparison(self):
        ast = self._parse('meta.fqdn = "web01"')
        self.assertIsInstance(ast, Comparison)
        self.assertIsInstance(ast.lhs, FieldRef)
        self.assertEqual(ast.lhs.field.id, "meta.fqdn")
        self.assertEqual(ast.operator, Equals)
        self.assertIsInstance(ast.rhs, Literal)
        self.assertEqual(ast.rhs.value, "web01")
        self.assertEqual(ast.rhs.value_type, ValueType.STRING)

    def test_parse_all_comparison_operators(self):
        cases = [
            ("facts.hardware.cpus > 4", GreaterThan),
            ("facts.hardware.cpus >= 4", GreaterOrEqual),
            ("facts.hardware.cpus < 4", LessThan),
            ("facts.hardware.cpus <= 4", LessOrEqual),
            ('meta.fqdn contains "web"', Contains),
            ('meta.fqdn CONTAINS "web"', Contains),
        ]
        for query, expected_op in cases:
            ast = self._parse(query)
            self.assertIsInstance(ast, Comparison)
            self.assertEqual(ast.operator, expected_op)

    def test_parse_logical_precedence(self):
        # AND should bind tighter than OR: a OR b AND c -> OR(a, AND(b, c))
        ast = self._parse(
            'meta.fqdn = "a" OR facts.hardware.cpus > 2 AND meta.archived = false'
        )
        self.assertIsInstance(ast, Logical)
        self.assertEqual(ast.operator, LogicalOperator.OR)
        self.assertEqual(len(ast.children), 2)
        self.assertIsInstance(ast.children[0], Comparison)
        self.assertIsInstance(ast.children[1], Logical)
        self.assertEqual(ast.children[1].operator, LogicalOperator.AND)

    def test_parse_grouping_with_braces(self):
        # {a OR b} AND c
        ast = self._parse(
            '{meta.fqdn = "a" OR facts.hardware.cpus > 2} AND meta.archived = false'
        )
        self.assertIsInstance(ast, Logical)
        self.assertEqual(ast.operator, LogicalOperator.AND)
        self.assertEqual(len(ast.children), 2)
        self.assertIsInstance(ast.children[0], Logical)
        self.assertEqual(ast.children[0].operator, LogicalOperator.OR)
        self.assertIsInstance(ast.children[1], Comparison)

    def test_parse_aggregations(self):
        ast = self._parse("count(facts.users[].name) >= 2")
        self.assertIsInstance(ast, Comparison)
        self.assertIsInstance(ast.lhs, FunctionCall)
        self.assertEqual(ast.lhs.function, Count)
        self.assertEqual(len(ast.lhs.args), 1)
        self.assertEqual(ast.operator, GreaterOrEqual)
        self.assertEqual(ast.rhs.value, 2)

        ast_sum = self._parse("sum(facts.hardware.memory[].size) > 1000")
        self.assertIsInstance(ast_sum.lhs, FunctionCall)
        self.assertEqual(ast_sum.lhs.function, Sum)

        ast_min = self._parse("min(facts.hardware.memory[].size) >= 100")
        self.assertEqual(ast_min.lhs.function, Min)

        ast_max = self._parse("max(facts.hardware.memory[].size) <= 500")
        self.assertEqual(ast_max.lhs.function, Max)

        ast_concat = self._parse('concat(facts.users[].name) contains "root"')
        self.assertEqual(ast_concat.lhs.function, Concat)

    def test_nested_filter_and_count(self):
        ast = self._parse('count(filter(facts.users[].name, "^admin")) > 0')
        self.assertIsInstance(ast, Comparison)
        count_call = ast.lhs
        self.assertIsInstance(count_call, FunctionCall)
        self.assertEqual(count_call.function, Count)

        filter_call = count_call.args[0]
        self.assertIsInstance(filter_call, FunctionCall)
        self.assertEqual(filter_call.function, Filter)
        self.assertEqual(filter_call.args[0].field.id, "facts.users[].name")
        self.assertEqual(filter_call.args[1].value, "^admin")

    def test_error_type_mismatch_in_comparison(self):
        with self.assertRaises(ValueError) as ctx:
            self._parse('facts.hardware.cpus = "eight"')
        self.assertIn("Type mismatch: cannot compare integer with string", str(ctx.exception))

    def test_error_contains_on_non_string(self):
        with self.assertRaises(ValueError) as ctx:
            self._parse("facts.hardware.cpus contains 4")
        self.assertIn("CONTAINS operator requires string type", str(ctx.exception))

    def test_error_aggregation_on_scalar(self):
        with self.assertRaises(ValueError) as ctx:
            self._parse("count(meta.fqdn) > 1")
        self.assertIn("'count' requires an array field", str(ctx.exception))

    def test_error_sum_on_string_array(self):
        with self.assertRaises(ValueError) as ctx:
            self._parse("sum(facts.users[].name) > 0")
        self.assertIn("'sum' requires an integer array field, got string", str(ctx.exception))

    def test_error_unknown_function(self):
        with self.assertRaises(ValueError) as ctx:
            self._parse("foo(facts.users[].name) > 0")
        self.assertIn("Unknown function 'foo'", str(ctx.exception))

    def test_error_unknown_field(self):
        with self.assertRaises(ValueError) as ctx:
            self._parse('nonexistent.field = "value"')
        self.assertIn("Unknown field 'nonexistent.field'", str(ctx.exception))

    def test_error_unclosed_brace(self):
        with self.assertRaises(ValueError) as ctx:
            self._parse('{meta.fqdn = "a"')
        self.assertIn("Unclosed '{'", str(ctx.exception))
