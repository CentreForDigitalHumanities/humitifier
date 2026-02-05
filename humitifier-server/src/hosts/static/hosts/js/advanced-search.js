/**
 * Advanced Search Query Helper
 *
 * Provides comprehensive autocomplete and validation for the ComplexQuery syntax:
 * - Operators: =, >, >=, <, <=, contains
 * - Logical operators: AND, OR
 * - Brackets for grouping: {expr}
 * - Quoted strings: "value" or 'value'
 * - Unquoted values for numbers and booleans: 42, true, false
 *
 * Examples:
 *   - facts.cpu.count = 4
 *   - facts.os.name = "Ubuntu" AND facts.cpu.count >= 4
 *   - {facts.os.name = "Ubuntu" OR facts.os.name = "Debian"} AND facts.cpu.count > 2
 *   - facts.hostname contains "web"
 */

function advancedSearchQuery() {
    return {
        fields: [], // [{id, label, valueType}]
        value: '',
        highlightHtml: '',
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
        aggregationFunctions: ['min', 'max', 'sum', 'concat', 'count'],

        init() {
            // These values are populated by the Django template
            // this.value and this.fields will be set externally
            this.updateHighlight();
            this.autoResize();
        },

        autoResize() {
            const textarea = this.$refs.input;
            if (!textarea) return;

            // Reset height to auto to get the correct scrollHeight
            textarea.style.height = 'auto';
            // Set height based on scrollHeight
            textarea.style.height = textarea.scrollHeight + 'px';
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

        getFieldIDs() {
            return this.fields.map(field => field.id);
        },

        /**
         * Tokenize arbitrary text.
         * Returns an array of tokens with their types.
         */
        _tokenizeText(text) {
            const tokens = [];
            let i = 0;

            while (i < text.length) {
                const char = text[i];

                // Skip whitespace
                if (/\s/.test(char)) {
                    i++;
                    continue;
                }

                // Handle quoted strings
                if (char === '"' || char === "'") {
                    const quote = char;
                    let str = quote;
                    i++;
                    while (i < text.length) {
                        if (text[i] === '\\' && i + 1 < text.length) {
                            str += text[i] + text[i + 1];
                            i += 2;
                        } else if (text[i] === quote) {
                            str += text[i];
                            i++;
                            break;
                        } else {
                            str += text[i];
                            i++;
                        }
                    }
                    tokens.push({ type: 'string', value: str });
                    continue;
                }

                // Handle brackets and parentheses
                if (char === '{') {
                    tokens.push({ type: 'lbracket', value: '{' });
                    i++;
                    continue;
                }
                if (char === '}') {
                    tokens.push({ type: 'rbracket', value: '}' });
                    i++;
                    continue;
                }
                if (char === '(') {
                    tokens.push({ type: 'lparen', value: '(' });
                    i++;
                    continue;
                }
                if (char === ')') {
                    tokens.push({ type: 'rparen', value: ')' });
                    i++;
                    continue;
                }

                // Handle operators
                if (char === '>' || char === '<' || char === '=') {
                    let op = char;
                    if (i + 1 < text.length && text[i + 1] === '=') {
                        op += '=';
                        i++;
                    }
                    tokens.push({ type: 'operator', value: op });
                    i++;
                    continue;
                }

                // Handle identifiers/keywords
                if (/[a-zA-Z0-9_.\[]/.test(char)) {
                    let word = '';
                    while (i < text.length && /[a-zA-Z0-9_.\[\]]/.test(text[i])) {
                        word += text[i];
                        i++;
                    }

                    // Check if it's a logical operator
                    if (word === 'AND' || word === 'OR') {
                        tokens.push({ type: 'logical', value: word });
                    } else if (word === 'contains') {
                        tokens.push({ type: 'operator', value: word });
                    } else if (word === 'min' || word === 'max' || word === 'sum' || word === 'concat' || word === 'count') {
                        tokens.push({ type: 'aggregation', value: word });
                    } else if (word === 'true' || word === 'false') {
                        tokens.push({ type: 'boolean', value: word });
                    } else if (/^\d+(\.\d+)?$/.test(word)) {
                        tokens.push({ type: 'number', value: word });
                    } else {
                        // It's a field identifier
                        tokens.push({ type: 'field', value: word });
                    }
                    continue;
                }

                // Unknown character, skip it
                i++;
            }

            return tokens;
        },

        /**
         * Tokenize the query up to the caret position to understand context.
         * Returns an array of tokens with their types.
         */
        _tokenizeUpToCaret() {
            const text = this.value.slice(0, this.getCaret());
            return this._tokenizeText(text);
        },

        /**
         * Determine what type of suggestions to show based on query context.
         *
         * This function analyzes the tokens before the cursor to determine what should be suggested next.
         */
        _determineContext() {
            const currentPartial = this._getCurrentPartialToken();
            const beforePartial = this.value.slice(0, this.getCaret() - currentPartial.length);
            const tokens = this._tokenizeText(beforePartial);

            // Empty query - start fresh
            if (tokens.length === 0) {
                return { type: 'start', partial: currentPartial };
            }

            const lastToken = tokens[tokens.length - 1];

            // Helper: Find the unclosed aggregation if we're inside one
            const findUnclosedAggregation = () => {
                let parenDepth = 0;
                for (let i = tokens.length - 1; i >= 0; i--) {
                    if (tokens[i].type === 'rparen') parenDepth++;
                    else if (tokens[i].type === 'lparen') {
                        if (parenDepth > 0) {
                            parenDepth--;
                        } else if (i > 0 && tokens[i - 1].type === 'aggregation') {
                            return tokens[i - 1].value;
                        }
                    }
                }
                return null;
            };

            // Helper: Find the field or aggregation before an operator
            const findFieldOrAggregationBeforeOperator = () => {
                for (let i = tokens.length - 2; i >= 0; i--) {
                    if (tokens[i].type === 'aggregation') {
                        return { type: 'aggregation', value: tokens[i].value };
                    }
                    if (tokens[i].type === 'field') {
                        const field = this.fields.find(f => f.id === tokens[i].value);
                        return field ? { type: 'field', field: field } : null;
                    }
                }
                return null;
            };

            // Determine context based on last token type
            switch (lastToken.type) {
                case 'lbracket':
                case 'logical':
                    return { type: 'start', partial: currentPartial };

                case 'aggregation':
                    return { type: 'expect_lparen', partial: currentPartial };

                case 'lparen':
                    const aggFunc = findUnclosedAggregation();
                    if (aggFunc) {
                        return { type: 'expect_array_field', partial: currentPartial, aggregationFunction: aggFunc };
                    }
                    return { type: 'start', partial: currentPartial };

                case 'field':
                    const field = this.fields.find(f => f.id === lastToken.value);
                    if (!field) {
                        return { type: 'start', partial: currentPartial };
                    }

                    const unclosedAgg = findUnclosedAggregation();
                    if (unclosedAgg) {
                        return { type: 'expect_rparen', partial: currentPartial };
                    }

                    return {
                        type: 'expect_operator',
                        partial: currentPartial,
                        fieldType: field.valueType,
                        isArrayField: field.id.includes('[]')
                    };

                case 'rparen':
                    // Look for the aggregation this closes and the field inside it
                    let aggFuncForRparen = null;
                    let fieldInsideAgg = null;
                    let depth = 1;
                    for (let i = tokens.length - 2; i >= 0; i--) {
                        if (tokens[i].type === 'rparen') {
                            depth++;
                        } else if (tokens[i].type === 'lparen') {
                            depth--;
                            if (depth === 0 && i > 0 && tokens[i - 1].type === 'aggregation') {
                                aggFuncForRparen = tokens[i - 1].value;
                                // Find the field after this lparen
                                for (let j = i + 1; j < tokens.length; j++) {
                                    if (tokens[j].type === 'field') {
                                        fieldInsideAgg = this.fields.find(f => f.id === tokens[j].value);
                                        break;
                                    }
                                }
                                break;
                            }
                        }
                    }

                    if (aggFuncForRparen) {
                        return {
                            type: 'expect_operator',
                            partial: currentPartial,
                            fieldType: this._getAggregationResultType(aggFuncForRparen, fieldInsideAgg)
                        };
                    }
                    return { type: 'expect_logical', partial: currentPartial };

                case 'operator':
                    const source = findFieldOrAggregationBeforeOperator();
                    let valueType = null;

                    if (source) {
                        if (source.type === 'aggregation') {
                            // For aggregations, we need to find the field inside the aggregation
                            let aggField = null;
                            for (let i = tokens.length - 2; i >= 0; i--) {
                                if (tokens[i].type === 'aggregation' && tokens[i].value === source.value) {
                                    // Found the aggregation, look for field after its lparen
                                    for (let j = i + 1; j < tokens.length; j++) {
                                        if (tokens[j].type === 'field') {
                                            aggField = this.fields.find(f => f.id === tokens[j].value);
                                            break;
                                        }
                                    }
                                    break;
                                }
                            }
                            valueType = this._getAggregationResultType(source.value, aggField);
                        } else if (source.type === 'field') {
                            valueType = source.field.valueType;
                        }
                    }

                    return { type: 'expect_value', partial: currentPartial, fieldType: valueType };

                case 'string':
                case 'number':
                case 'boolean':
                    const isComplete = this._isValueComplete(lastToken);
                    if (isComplete) {
                        return { type: 'expect_logical', partial: currentPartial };
                    }
                    return { type: 'expect_value', partial: currentPartial };

                case 'rbracket':
                    return { type: 'expect_logical', partial: currentPartial };

                default:
                    return { type: 'start', partial: currentPartial };
            }
        },

        /**
         * Check if a value token is complete.
         */
        _isValueComplete(token) {
            if (token.type === 'string') {
                return token.value.endsWith('"') || token.value.endsWith("'");
            }
            if (token.type === 'number' || token.type === 'boolean') {
                return true;
            }
            return false;
        },

        /**
         * Get the partial token being typed at the cursor.
         */
        _getCurrentPartialToken() {
            const caret = this.getCaret();
            const before = this.value.slice(0, caret);

            // Find the last space, operator, bracket, or parenthesis
            let start = before.length - 1;
            while (start >= 0) {
                const char = before[start];
                if (/[\s{}=<>()]/.test(char)) {
                    start++;
                    break;
                }
                start--;
            }
            if (start < 0) start = 0;

            return before.slice(start).trim();
        },

        /**
         * Generate suggestions based on context.
         */
        _generateSuggestions(context) {
            const suggestions = [];
            const partialLower = context.partial.toLowerCase();

            // Start context: suggest fields, aggregations, and brackets
            if (context.type === 'start') {
                // Bracket
                if ('{'.startsWith(partialLower) || partialLower === '') {
                    suggestions.push({
                        id: '{',
                        label: '{ — open group',
                        insertValue: '{',
                        type: 'bracket'
                    });
                }

                // Aggregation functions
                this.aggregationFunctions.forEach(agg => {
                    if (partialLower === '' || agg.toLowerCase().startsWith(partialLower)) {
                        suggestions.push({
                            id: agg,
                            label: `${agg}() — ${this._getAggregationDescription(agg)}`,
                            insertValue: agg,
                            type: 'aggregation'
                        });
                    }
                });

                // Fields
                this.fields.forEach(field => {
                    if (partialLower === '' ||
                        field.id.toLowerCase().includes(partialLower) ||
                        field.label.toLowerCase().includes(partialLower)) {
                        suggestions.push({
                            id: field.id,
                            label: `${field.label}`,
                            insertValue: field.id,
                            type: 'field'
                        });
                    }
                });
            }

            // Expect opening parenthesis after aggregation
            else if (context.type === 'expect_lparen') {
                if ('('.startsWith(partialLower) || partialLower === '') {
                    suggestions.push({
                        id: '(',
                        label: '( — open aggregation',
                        insertValue: '(',
                        type: 'paren'
                    });
                }
            }

            // Expect array field inside aggregation
            else if (context.type === 'expect_array_field') {
                const aggregationFunction = context.aggregationFunction;

                this.fields.forEach(field => {
                    if (!field.id.includes('[]')) return;

                    if (aggregationFunction && !this._isFieldCompatibleWithAggregation(field.valueType, aggregationFunction)) {
                        return;
                    }

                    if (partialLower === '' ||
                        field.id.toLowerCase().includes(partialLower) ||
                        field.label.toLowerCase().includes(partialLower)) {
                        suggestions.push({
                            id: field.id,
                            label: `${field.label}`,
                            insertValue: field.id,
                            type: 'field'
                        });
                    }
                });
            }

            // Expect closing parenthesis
            else if (context.type === 'expect_rparen') {
                if (')'.startsWith(partialLower) || partialLower === '') {
                    suggestions.push({
                        id: ')',
                        label: ') — close aggregation',
                        insertValue: ')',
                        type: 'paren'
                    });
                }
            }

            // Expect operator
            else if (context.type === 'expect_operator') {
                // Suggest operators based on field type
                const fieldType = context.fieldType;
                const isArrayField = context.isArrayField;

                this.operators.forEach(op => {
                    const isApplicable = this._isOperatorApplicableToFieldType(op, fieldType, isArrayField);

                    if (isApplicable && (partialLower === '' || op.toLowerCase().startsWith(partialLower))) {
                        suggestions.push({
                            id: op,
                            label: op === 'contains' ? 'contains — substring match' : `${op} — ${this._getOperatorDescription(op)}`,
                            insertValue: op,
                            type: 'operator'
                        });
                    }
                });
            }

            // Expect value
            else if (context.type === 'expect_value') {
                // Suggest value templates based on field type
                const fieldType = context.fieldType;

                // String values
                if ((fieldType === 'string' || !fieldType) && (partialLower === '' || '"value"'.startsWith(partialLower))) {
                    suggestions.push({
                        id: 'string',
                        label: '"value" — text value',
                        insertValue: '""',
                        type: 'value',
                        cursorOffset: -1
                    });
                }

                if ((fieldType === 'boolean' || !fieldType) && (partialLower === '' || 'true'.startsWith(partialLower))) {
                    suggestions.push({
                        id: 'true',
                        label: 'true — boolean',
                        insertValue: 'true',
                        type: 'value'
                    });
                }

                if ((fieldType === 'boolean' || !fieldType) && (partialLower === '' || 'false'.startsWith(partialLower))) {
                    suggestions.push({
                        id: 'false',
                        label: 'false — boolean',
                        insertValue: 'false',
                        type: 'value'
                    });
                }

                if ((fieldType === 'integer' || !fieldType) && (partialLower === '' || /^\d/.test(partialLower))) {
                    suggestions.push({
                        id: 'number',
                        label: '42 — numeric value',
                        insertValue: '',
                        type: 'value'
                    });
                }
            }

            // Expect logical operator or closing bracket
            else if (context.type === 'expect_logical') {
                // Check if we need a closing bracket
                const openCount = (this.value.match(/\{/g) || []).length;
                const closeCount = (this.value.match(/\}/g) || []).length;

                if (openCount > closeCount && ('}'.startsWith(partialLower) || partialLower === '')) {
                    suggestions.push({
                        id: '}',
                        label: '} — close group',
                        insertValue: '}',
                        type: 'bracket'
                    });
                }

                // Suggest logical operators
                this.logicalOperators.forEach(op => {
                    if (partialLower === '' || op.toLowerCase().startsWith(partialLower)) {
                        suggestions.push({
                            id: op,
                            label: `${op} — ${op === 'AND' ? 'both conditions' : 'either condition'}`,
                            insertValue: op,
                            type: 'logical'
                        });
                    }
                });
            }

            return suggestions;
        },

        _getOperatorDescription(op) {
            const descriptions = {
                '=': 'equals',
                '>': 'greater than',
                '>=': 'greater or equal',
                '<': 'less than',
                '<=': 'less or equal'
            };
            return descriptions[op] || op;
        },

        _getAggregationDescription(agg) {
            const descriptions = {
                'min': 'minimum value',
                'max': 'maximum value',
                'sum': 'sum of values',
                'concat': 'concatenate strings',
                'count': 'count elements'
            };
            return descriptions[agg] || agg;
        },

        _getAggregationResultType(aggregationFunction, field) {
            // Determine the result type of an aggregation function
            // Some aggregations always return a specific type regardless of input
            if (aggregationFunction === 'count') {
                return 'integer';  // count always returns integer
            }
            if (aggregationFunction === 'sum') {
                return 'integer';  // sum only works on integers, returns integer
            }
            if (aggregationFunction === 'concat') {
                return 'string';   // concat only works on strings, returns string
            }

            // min/max return the same type as the field they operate on
            if (aggregationFunction === 'min' || aggregationFunction === 'max') {
                if (field && field.valueType) {
                    return field.valueType;  // Returns the field's type (integer or string)
                }
                return 'integer';  // Default to integer if field unknown
            }

            return null;
        },

        _isFieldCompatibleWithAggregation(fieldType, aggregationFunction) {
            // Check if a field type is compatible with an aggregation function
            const compatibility = {
                'min': ['integer', 'string'],  // min works on integers and strings
                'max': ['integer', 'string'],  // max works on integers and strings
                'sum': ['integer'],            // sum only works on integers
                'concat': ['string'],          // concat only works on strings
                'count': ['integer', 'string', 'boolean']  // count works on any array
            };
            const compatibleTypes = compatibility[aggregationFunction];
            return compatibleTypes ? compatibleTypes.includes(fieldType) : true;
        },

        /**
         * Determine if an operator is applicable to a given field type.
         */
        _isOperatorApplicableToFieldType(operator, fieldType, isArrayField) {
            // If no field type is known, show all operators
            if (!fieldType) {
                return true;
            }

            // Array fields without aggregation support all their type-specific operators
            // because the backend will check if ANY element matches

            // Boolean fields only support equality
            if (fieldType === 'boolean') {
                return operator === '=';
            }

            // String fields support equality and contains
            if (fieldType === 'string') {
                return operator === '=' || operator === 'contains';
            }

            // Integer fields support all comparison operators except contains
            if (fieldType === 'integer') {
                return operator !== 'contains';
            }

            return true;
        },

        onInput() {
            const context = this._determineContext();
            this.suggestions = this._generateSuggestions(context);
            this.activeIndex = 0;
            this.open = this.suggestions.length > 0;
            this.updateHighlight();
            this.autoResize();
        },

        move(delta) {
            if (!this.open || !this.suggestions.length) return;
            const len = this.suggestions.length;
            this.activeIndex = (this.activeIndex + delta + len) % len;
        },

        choose(idx) {
            if (!this.suggestions.length) return;
            const s = this.suggestions[idx ?? this.activeIndex];

            // Find what we're replacing
            const caret = this.getCaret();
            const partial = this._getCurrentPartialToken();

            // Calculate replacement range
            let replaceStart = caret - partial.length;
            let replaceEnd = caret;

            // Build the new value
            const left = this.value.slice(0, replaceStart);
            const right = this.value.slice(replaceEnd);

            let insert = s.insertValue;
            let spacing = '';

            // Add appropriate spacing based on token type
            if (s.type === 'aggregation') {
                // Aggregation functions need opening paren
                insert = insert + '( ';
                // Add space before if needed
                if (left && !left.endsWith(' ')) {
                    insert = ' ' + insert;
                }
            } else if (s.type === 'field' || s.type === 'operator' || s.type === 'logical') {
                // Add space after if not already present
                if ((right && !right.startsWith(' ')) || !right) {
                    spacing = ' ';
                }
                // Add space before logical operators if not present
                if (s.type === 'logical' && left && !left.endsWith(' ')) {
                    insert = ' ' + insert;
                }
            } else if (s.type === 'paren' && s.insertValue === ')') {
                // Closing paren should have space after for operator
                spacing = ' ';
            }

            this.value = left + insert + spacing + right;

            // Position cursor
            let newCaret = (left + insert + spacing).length;
            if (s.cursorOffset !== undefined) {
                newCaret += s.cursorOffset;
            } else if (s.type === 'logical' || s.type === 'operator') {
                // After the space
                newCaret;
            } else if (s.type === 'bracket' && s.insertValue === '{') {
                // Stay right after the opening bracket
                newCaret;
            } else if (s.type === 'aggregation') {
                // Position cursor inside the parentheses
                newCaret;
            }

            this.setCaret(newCaret);
            this.closeSuggestions();
            this.updateHighlight();

            // Trigger onInput to show next suggestions
            setTimeout(() => this.onInput(), 10);
        },

        onTab() {
            if (this.open && this.suggestions.length) {
                this.choose(this.activeIndex);
                this.autoResize();
                return;
            }
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
            const openBrackets = (this.value.match(/\{/g) || []).length;
            const closeBrackets = (this.value.match(/\}/g) || []).length;

            if (openBrackets !== closeBrackets) {
                return {
                    valid: false,
                    message: 'Mismatched brackets'
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
            this.updateHighlight();
        },

        updateHighlight() {
            this.highlightHtml = this._renderHighlight(this.value);
            this.syncHighlightScroll();
        },

        syncHighlightScroll() {
            const input = this.$refs.input;
            const highlight = this.$refs.highlight;
            if (!input || !highlight) return;
            highlight.scrollLeft = input.scrollLeft;
        },

        _escapeHtml(value) {
            return value
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        },

        _renderHighlight(text) {
            if (!text) {
                return '';
            }

            const tokenClasses = {
                field: 'text-neutral-900 dark:text-neutral-50',
                operator: 'text-orange-600 dark:text-orange-500',
                logical: 'text-orange-600 dark:text-orange-500',
                string: 'text-green-600 dark:text-green-300',
                number: 'text-blue-600 dark:text-blue-300',
                boolean: 'text-red-600 dark:text-red-300',
                bracket: 'text-orange-500 dark:text-orange-400',
                aggregation: 'text-yellow-800 dark:text-yellow-300',
                paren: 'text-yellow-800 dark:text-yellow-300'
            };
            let i = 0;
            let output = '';

            const pushToken = (token, type) => {
                const escaped = this._escapeHtml(token);
                const classes = type ? tokenClasses[type] : '';
                if (!classes) {
                    output += escaped;
                    return;
                }
                output += `<span class="${classes}">${escaped}</span>`;
            };

            while (i < text.length) {
                const char = text[i];

                if (/\s/.test(char)) {
                    pushToken(char, null);
                    i++;
                    continue;
                }

                if (char === '"' || char === "'") {
                    const quote = char;
                    let str = quote;
                    i++;
                    while (i < text.length) {
                        if (text[i] === '\\' && i + 1 < text.length) {
                            str += text[i] + text[i + 1];
                            i += 2;
                        } else if (text[i] === quote) {
                            str += text[i];
                            i++;
                            break;
                        } else {
                            str += text[i];
                            i++;
                        }
                    }
                    pushToken(str, 'string');
                    continue;
                }

                if (char === '{' || char === '}') {
                    pushToken(char, 'bracket');
                    i++;
                    continue;
                }

                if (char === '(' || char === ')') {
                    pushToken(char, 'paren');
                    i++;
                    continue;
                }

                if (char === '>' || char === '<' || char === '=') {
                    let op = char;
                    if (i + 1 < text.length && text[i + 1] === '=') {
                        op += '=';
                        i++;
                    }
                    pushToken(op, 'operator');
                    i++;
                    continue;
                }

                if (/[a-zA-Z0-9_.\[]/.test(char)) {
                    let word = '';
                    while (i < text.length && /[a-zA-Z0-9_.\[]/.test(text[i])) {
                        word += text[i];
                        i++;
                    }
                    // Check for closing bracket in array fields
                    if (i < text.length && text[i] === ']') {
                        word += text[i];
                        i++;
                    }

                    if (word === 'AND' || word === 'OR') {
                        pushToken(word, 'logical');
                    } else if (word === 'contains') {
                        pushToken(word, 'operator');
                    } else if (word === 'min' || word === 'max' || word === 'sum' || word === 'concat' || word === 'count') {
                        pushToken(word, 'aggregation');
                    } else if (word === 'true' || word === 'false') {
                        pushToken(word, 'boolean');
                    } else if (/^\d+(\.\d+)?$/.test(word)) {
                        pushToken(word, 'number');
                    } else {
                        pushToken(word, 'field');
                    }
                    continue;
                }

                pushToken(char, null);
                i++;
            }

            return output;
        },

        // ==== Columns multiselect methods ====
        onColumnsInput() {
            const needle = (this.columnsFilter || '').toLowerCase();
            const selectedIds = new Set(this.selectedColumns.map(c => c.id));
            let pool = this.fields.filter(f => !selectedIds.has(f.id));
            if (needle.length) {
                pool = pool.filter(f => f.label.toLowerCase().includes(needle) || f.id.toLowerCase().includes(needle));
            }
            this.colSuggestions = pool;
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
        },

        saveCurrentSearch() {
            // Get current values
            const searchQuery = this.value || '';
            const columns = this.selectedColumns.map(c => c.id).join(',');

            // Build URL with query parameters
            const params = new URLSearchParams();
            params.set('query', searchQuery);
            params.set('columns', columns);

            // Redirect to save form
            window.location.href = '/hosts/saved_searches/create/?' + params.toString();
        }
    };
}
