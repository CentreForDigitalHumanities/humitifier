/**
 * Advanced Search Query Helper
 *
 * Provides comprehensive autocomplete and validation for the ComplexQuery syntax:
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

        init() {
            // These values are populated by the Django template
            // this.value and this.fields will be set externally
            this.updateHighlight();
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
         * Tokenize the query up to the caret position to understand context.
         * Returns an array of tokens with their types.
         */
        _tokenizeUpToCaret() {
            const text = this.value.slice(0, this.getCaret());
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

                // Handle parentheses
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
                if (/[a-zA-Z0-9_.]/.test(char)) {
                    let word = '';
                    while (i < text.length && /[a-zA-Z0-9_.]/.test(text[i])) {
                        word += text[i];
                        i++;
                    }

                    // Check if it's a logical operator
                    if (word === 'AND' || word === 'OR') {
                        tokens.push({ type: 'logical', value: word });
                    } else if (word === 'contains') {
                        tokens.push({ type: 'operator', value: word });
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
         * Determine what type of suggestions to show based on query context.
         */
        _determineContext() {
            const tokens = this._tokenizeUpToCaret();

            if (tokens.length === 0) {
                // Empty query - suggest fields or opening paren
                return { type: 'field_or_paren', partial: '' };
            }

            const lastToken = tokens[tokens.length - 1];

            // Check if we're in the middle of typing something
            const currentPartial = this._getCurrentPartialToken();

            // After opening paren, expect field or another paren
            if (lastToken.type === 'lparen') {
                return { type: 'field_or_paren', partial: currentPartial };
            }

            // After a field name, expect an operator
            if (lastToken.type === 'field') {
                const isValidField = this.getFieldIDs().includes(lastToken.value);

                if (isValidField) {
                    // Valid field - expect an operator
                    return { type: 'operator', partial: currentPartial };
                }

                // Invalid field token - check if it contains a valid field followed by a space
                // This handles cases like "facts.cpu.count a" where the tokenizer creates "facts.cpu.counta"
                // but the user actually meant to type after a valid field
                const fieldIds = this.getFieldIDs();
                for (const fieldId of fieldIds) {
                    // Check if the text contains a complete valid field followed by a space
                    const pattern = new RegExp(fieldId.replace(/\./g, '\\.') + '\\s');
                    if (pattern.test(lastToken.value)) {
                        // We have a complete valid field followed by space
                        // The user is typing an operator or value
                        return { type: 'operator', partial: currentPartial };
                    }
                }

                // Still typing the field name
                return { type: 'field_or_paren', partial: currentPartial };
            }

            // After an operator, expect a value (string/number/boolean)
            if (lastToken.type === 'operator') {
                return { type: 'value', partial: currentPartial };
            }

            // After a complete value (string, number, boolean, rparen), expect logical operator
            if (lastToken.type === 'string' || lastToken.type === 'number' ||
                lastToken.type === 'boolean' || lastToken.type === 'rparen') {

                // Check if value is complete (string ends with quote, etc.)
                const isComplete = this._isValueComplete(lastToken);

                if (isComplete) {
                    return { type: 'logical_or_rparen', partial: currentPartial };
                } else {
                    return { type: 'value', partial: currentPartial };
                }
            }

            // After a logical operator, expect field or opening paren
            if (lastToken.type === 'logical') {
                return { type: 'field_or_paren', partial: currentPartial };
            }

            // Default to field suggestions
            return { type: 'field_or_paren', partial: currentPartial };
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

            // Find the last space, operator, or paren
            let start = before.length - 1;
            while (start >= 0) {
                const char = before[start];
                if (/[\s()=<>]/.test(char)) {
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

            if (context.type === 'field_or_paren') {
                // Add opening parenthesis suggestion
                if ('('.startsWith(partialLower) || partialLower === '') {
                    suggestions.push({
                        id: '(',
                        label: '( — open group',
                        insertValue: '(',
                        type: 'paren'
                    });
                }

                // Add field suggestions
                this.fields.forEach(field => {
                    if (partialLower === '' ||
                        field.id.toLowerCase().includes(partialLower) ||
                        field.label.toLowerCase().includes(partialLower)) {
                        suggestions.push({
                            id: field.id,
                            label: `${field.label} (${field.id})`,
                            insertValue: field.id,
                            type: 'field'
                        });
                    }
                });
            } else if (context.type === 'operator') {
                // Suggest operators
                this.operators.forEach(op => {
                    if (partialLower === '' || op.toLowerCase().startsWith(partialLower)) {
                        suggestions.push({
                            id: op,
                            label: op === 'contains' ? 'contains — substring match' : `${op} — ${this._getOperatorDescription(op)}`,
                            insertValue: op,
                            type: 'operator'
                        });
                    }
                });
            } else if (context.type === 'value') {
                // Suggest value templates
                if (partialLower === '' || '"value"'.startsWith(partialLower)) {
                    suggestions.push({
                        id: 'string',
                        label: '"value" — text value',
                        insertValue: '""',
                        type: 'value',
                        cursorOffset: -1  // Place cursor between quotes
                    });
                }
                if (partialLower === '' || 'true'.startsWith(partialLower)) {
                    suggestions.push({
                        id: 'true',
                        label: 'true — boolean',
                        insertValue: 'true',
                        type: 'value'
                    });
                }
                if (partialLower === '' || 'false'.startsWith(partialLower)) {
                    suggestions.push({
                        id: 'false',
                        label: 'false — boolean',
                        insertValue: 'false',
                        type: 'value'
                    });
                }
                if (partialLower === '' || /^\d/.test(partialLower)) {
                    suggestions.push({
                        id: 'number',
                        label: '42 — numeric value',
                        insertValue: '',  // Don't auto-insert numbers
                        type: 'value'
                    });
                }
            } else if (context.type === 'logical_or_rparen') {
                // Check if we need a closing paren
                const openCount = (this.value.match(/\(/g) || []).length;
                const closeCount = (this.value.match(/\)/g) || []).length;

                if (openCount > closeCount && (')'.startsWith(partialLower) || partialLower === '')) {
                    suggestions.push({
                        id: ')',
                        label: ') — close group',
                        insertValue: ')',
                        type: 'paren'
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

        onInput() {
            const context = this._determineContext();
            this.suggestions = this._generateSuggestions(context);
            this.activeIndex = 0;
            this.open = this.suggestions.length > 0;
            this.updateHighlight();
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
            if (s.type === 'field' || s.type === 'operator' || s.type === 'logical') {
                // Add space after if not already present
                if ((right && !right.startsWith(' ')) || !right) {
                    spacing = ' ';
                }
                // Add space before logical operators if not present
                if (left && !left.endsWith(' ')) {
                    insert = ' ' + insert;
                }
            }

            this.value = left + insert + spacing + right;

            // Position cursor
            let newCaret = (left + spacing + insert).length;
            if (s.cursorOffset !== undefined) {
                newCaret += s.cursorOffset;
            } else if (s.type === 'logical' || s.type === 'operator') {
                newCaret += spacing.length + 1; // After the space
            } else if (s.type === 'paren' && s.insertValue === '(') {
                newCaret; // Stay right after the opening paren
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
                field: 'text-blue-600 dark:text-blue-300',
                operator: 'text-orange-600 dark:text-orange-300',
                logical: 'text-orange-600 dark:text-orange-300',
                string: 'text-green-600 dark:text-green-300',
                number: 'text-blue-600 dark:text-blue-300',
                boolean: 'text-orange-600 dark:text-orange-300',
                paren: 'text-gray-500 dark:text-gray-400'
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

                if (/[a-zA-Z0-9_.]/.test(char)) {
                    let word = '';
                    while (i < text.length && /[a-zA-Z0-9_.]/.test(text[i])) {
                        word += text[i];
                        i++;
                    }

                    if (word === 'AND' || word === 'OR') {
                        pushToken(word, 'logical');
                    } else if (word === 'contains') {
                        pushToken(word, 'operator');
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
        }
    };
}
