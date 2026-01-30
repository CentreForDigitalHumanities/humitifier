/**
 * Advanced Search Query Helper
 *
 * Provides autocomplete and validation for the ComplexQuery syntax:
 * - Operators: =, >, >=, <, <=, contains
 * - Logical operators: AND, OR
 * - Parentheses for grouping: (expr)
 * - Quoted strings: "value" or 'value'
 * - Unquoted values for numbers and booleans: 42, true, false
 *
 * Examples:
 *   - facts.cpu.count = 4
 *   - facts.os.name = "Ubuntu" AND facts.cpu.count >= 4
 *   - (facts.os.name = "Ubuntu" OR facts.os.name = "Debian") AND facts.cpu.count > 2
 *   - facts.hostname contains "web"
 */

function advancedSearchQuery() {
    return {
        fields: [], // [{id, label}]
        value: '',
        open: false,
        suggestions: [],
        activeIndex: 0,
        // Columns multiselect state
        selectedColumns: [], // [{id,label}]
        columnsFilter: '',
        colOpen: false,
        colSuggestions: [],
        colActiveIndex: 0,

        // Supported operators in the new syntax
        operators: ['=', '>', '>=', '<', '<=', 'contains'],
        logicalOperators: ['AND', 'OR'],

        init() {
            // These values are populated by the Django template
            // this.value and this.fields will be set externally
        },

        getCaret() {
            const el = this.$refs.input;
            return el ? el.selectionStart : 0;
        },

        setCaret(pos) {
            const el = this.$refs.input;
            if (!el) return;
            requestAnimationFrame(() => {
                el.setSelectionRange(pos, pos);
                el.focus();
            });
        },

        /**
         * Find the current token context at the caret position.
         * Returns information about what's being typed (field, operator, or value).
         */
        getCurrentContext() {
            const caret = this.getCaret();
            const before = this.value.slice(0, caret);

            // Find the start of the current expression (after last AND/OR or opening paren)
            let exprStart = 0;
            const andMatch = before.lastIndexOf(' AND ');
            const orMatch = before.lastIndexOf(' OR ');
            const parenMatch = before.lastIndexOf('(');

            exprStart = Math.max(andMatch + 5, orMatch + 4, parenMatch + 1, 0);

            const currentExpr = before.slice(exprStart, caret).trim();

            // Determine what we're typing based on the expression
            // Check if we have an operator
            const hasOperator = this.operators.some(op => currentExpr.includes(` ${op} `) || currentExpr.includes(op));

            if (!hasOperator) {
                // We're typing a field name
                return {
                    type: 'field',
                    text: currentExpr,
                    start: exprStart,
                    end: caret
                };
            }

            // We have an operator, check if we're past it (typing value)
            for (const op of this.operators) {
                const opIndex = currentExpr.lastIndexOf(` ${op} `);
                if (opIndex !== -1) {
                    const afterOp = currentExpr.slice(opIndex + op.length + 2);
                    return {
                        type: 'value',
                        text: afterOp.trim(),
                        start: exprStart + opIndex + op.length + 2,
                        end: caret
                    };
                }
            }

            return {
                type: 'unknown',
                text: currentExpr,
                start: exprStart,
                end: caret
            };
        },

        onInput() {
            const context = this.getCurrentContext();

            if (context.type === 'field') {
                // Show field suggestions
                const needle = context.text.toLowerCase();
                if (needle.length === 0) {
                    this.suggestions = this.fields.slice(0, 50);
                } else {
                    this.suggestions = this.fields
                        .filter(f => f.id.toLowerCase().includes(needle) || f.label.toLowerCase().includes(needle))
                        .slice(0, 50);
                }
                this.activeIndex = 0;
                this.open = this.suggestions.length > 0;
            } else {
                // Don't show suggestions for values or when operator is being typed
                this.closeSuggestions();
            }
        },

        move(delta) {
            if (!this.open || !this.suggestions.length) return;
            const len = this.suggestions.length;
            this.activeIndex = (this.activeIndex + delta + len) % len;
        },

        choose(idx) {
            if (!this.suggestions.length) return;
            const s = this.suggestions[idx ?? this.activeIndex];
            const context = this.getCurrentContext();

            if (context.type === 'field') {
                // Replace the current field text with the selected field and add operator
                const left = this.value.slice(0, context.start);
                const right = this.value.slice(context.end);
                const insert = `${s.id} = ""`;

                this.value = left + insert + right;
                const caretPos = (left + `${s.id} = "`).length;
                this.setCaret(caretPos);
            }

            this.closeSuggestions();
        },

        onTab() {
            if (this.open && this.suggestions.length) {
                this.choose(this.activeIndex);
                return;
            }

            // Check if we can add a logical operator
            const context = this.getCurrentContext();
            const trimmed = this.value.trim();

            // Simple heuristic: if the query looks complete (has field, operator, and value)
            // and doesn't already end with AND/OR, add AND
            if (trimmed && !trimmed.endsWith(' AND') && !trimmed.endsWith(' OR') &&
                !trimmed.endsWith('(') && this._looksComplete(trimmed)) {
                this.value = this.value.trim() + ' AND ';
                this.setCaret(this.value.length);
            }
        },

        /**
         * Check if the query looks syntactically complete enough to add another term.
         */
        _looksComplete(text) {
            // Remove any trailing whitespace
            text = text.trim();

            // Check if it ends with a quoted string or a value
            if (text.endsWith('"') || text.endsWith("'")) {
                return true;
            }

            // Check if it ends with a number or boolean
            const tokens = text.split(/\s+/);
            const lastToken = tokens[tokens.length - 1];
            if (lastToken && (lastToken.match(/^\d+$/) || lastToken === 'true' || lastToken === 'false')) {
                return true;
            }

            // Check if it ends with a closing paren
            if (text.endsWith(')')) {
                return true;
            }

            return false;
        },

        closeSuggestions() {
            this.open = false;
            this.suggestions = [];
            this.activeIndex = 0;
        },

        /**
         * Validate the query syntax before submission.
         * This provides client-side feedback but the server will do the real validation.
         */
        validateQuery() {
            if (!this.value.trim()) {
                return { valid: true, message: '' };
            }

            // Basic syntax checks
            const openParens = (this.value.match(/\(/g) || []).length;
            const closeParens = (this.value.match(/\)/g) || []).length;

            if (openParens !== closeParens) {
                return {
                    valid: false,
                    message: 'Mismatched parentheses'
                };
            }

            // Check for unterminated strings
            const quotePattern = /(?:[^\\]|^)["'](?:[^\\]|\\[\\])*$/;
            if (quotePattern.test(this.value)) {
                return {
                    valid: false,
                    message: 'Unterminated string - missing closing quote'
                };
            }

            return { valid: true, message: '' };
        },

        normalizeForSubmit() {
            // The new parser handles the query as-is, so we don't need to transform it
            // Just trim whitespace
            this.value = this.value.trim();
        },

        // ==== Columns multiselect methods ====
        onColumnsInput() {
            const needle = (this.columnsFilter || '').toLowerCase();
            const selectedIds = new Set(this.selectedColumns.map(c => c.id));
            let pool = this.fields.filter(f => !selectedIds.has(f.id));
            if (needle.length) {
                pool = pool.filter(f => f.label.toLowerCase().includes(needle) || f.id.toLowerCase().includes(needle));
            }
            this.colSuggestions = pool.slice(0, 100);
            this.colActiveIndex = 0;
            this.colOpen = this.colSuggestions.length > 0;
        },

        moveColumn(delta) {
            if (!this.colOpen || !this.colSuggestions.length) return;
            const len = this.colSuggestions.length;
            this.colActiveIndex = (this.colActiveIndex + delta + len) % len;
        },

        chooseColumn(idx) {
            if (!this.colSuggestions.length) return;
            const s = this.colSuggestions[idx ?? this.colActiveIndex];
            if (!s) return;
            // Prevent duplicates
            if (this.selectedColumns.some(c => c.id === s.id)) return this.closeColumnSuggestions();
            this.selectedColumns.push({ id: s.id, label: s.label });
            this.columnsFilter = '';
            this.$refs.columnsInput && this.$refs.columnsInput.focus();
            this.onColumnsInput();
        },

        removeColumn(idx) {
            this.selectedColumns.splice(idx, 1);
            this.onColumnsInput();
        },

        maybeBackspaceRemove() {
            if ((this.columnsFilter || '').length === 0 && this.selectedColumns.length) {
                this.selectedColumns.pop();
                this.onColumnsInput();
            }
        },

        closeColumnSuggestions() {
            this.colOpen = false;
            this.colSuggestions = [];
            this.colActiveIndex = 0;
        }
    };
}
