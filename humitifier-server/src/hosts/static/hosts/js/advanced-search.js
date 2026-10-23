/**
 * Advanced Search Query Helper
 *
 * Provides autocomplete, validation, and syntax highlighting driven dynamically
 * by the server-side language specification (spec.py).
 */

function advancedSearchQuery() {
    return {
        spec: null,
        fields: [], // [{id, label, valueType, kind, section}]
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

        // Defaults populated from spec
        operators: ['=', '!=', '>', '>=', '<', '<=', 'CONTAINS'],
        operatorObjects: [],
        logicalOperators: ['AND', 'OR', 'NOT'],
        binaryLogicalOperators: ['AND', 'OR'],
        functions: [],
        grouping: { open: '{', close: '}' },

        setLanguageSpec(spec) {
            if (!spec) return;
            this.spec = spec;
            this.operatorObjects = spec.operators || [];
            this.operators = this.operatorObjects.map(o => o.symbol);
            this.logicalOperators = spec.logical_operators || ['AND', 'OR', 'NOT'];
            this.binaryLogicalOperators = (this.logicalOperators || []).filter(op => op.toUpperCase() !== 'NOT');
            this.functions = spec.functions || [];
            this.grouping = spec.grouping || { open: '{', close: '}' };
            this.fields = (spec.fields || []).map(f => ({
                id: f.id,
                label: f.label,
                valueType: f.value_type,
                kind: f.kind,
                section: f.section
            }));
        },

        init() {
            this.updateHighlight();
            this.$nextTick(() => this.autoResize());
        },

        autoResize() {
            const textarea = this.$refs.input;
            if (!textarea) return;
            textarea.style.height = 'auto';
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
         * Tokenize arbitrary text using spec keywords.
         */
        _tokenizeText(text) {
            const tokens = [];
            let i = 0;

            const isFunc = (word) => {
                const lower = word.toLowerCase();
                return this.functions.find(f => f.name.toLowerCase() === lower);
            };

            const isOpKeyword = (word) => {
                const upper = word.toUpperCase();
                return this.operatorObjects.find(o => o.keyword && o.symbol.toUpperCase() === upper);
            };

            while (i < text.length) {
                const char = text[i];

                if (/\s/.test(char) || char === '\n' || char === '\r') {
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
                    tokens.push({ type: 'string', value: str });
                    continue;
                }

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
                if (char === ',') {
                    tokens.push({ type: 'comma', value: ',' });
                    i++;
                    continue;
                }

                if (char === '>' || char === '<' || char === '=' || char === '!') {
                    let op = char;
                    if (i + 1 < text.length && text[i + 1] === '=') {
                        op += '=';
                        i++;
                    }
                    tokens.push({ type: 'operator', value: op });
                    i++;
                    continue;
                }

                if (/[a-zA-Z0-9_.\[]/.test(char)) {
                    let word = '';
                    while (i < text.length && /[a-zA-Z0-9_.\[\]-]/.test(text[i])) {
                        word += text[i];
                        i++;
                    }

                    const wordUpper = word.toUpperCase();
                    if (this.logicalOperators.map(o => o.toUpperCase()).includes(wordUpper)) {
                        tokens.push({ type: 'logical', value: word });
                    } else if (isOpKeyword(word)) {
                        tokens.push({ type: 'operator', value: word });
                    } else if (isFunc(word)) {
                        tokens.push({ type: 'function', value: word, func: isFunc(word) });
                    } else if (word === 'true' || word === 'false') {
                        tokens.push({ type: 'boolean', value: word });
                    } else if (/^-?\d+(\.\d+)?$/.test(word)) {
                        tokens.push({ type: 'number', value: word });
                    } else {
                        tokens.push({ type: 'field', value: word });
                    }
                    continue;
                }

                i++;
            }

            return tokens;
        },

        _tokenizeUpToCaret() {
            const text = this.value.slice(0, this.getCaret());
            return this._tokenizeText(text);
        },

        /**
         * Find enclosing function call and argument index for cursor context.
         */
        _findEnclosingFunctionCall(tokens) {
            let parenDepth = 0;
            let argIndex = 0;
            for (let i = tokens.length - 1; i >= 0; i--) {
                const tok = tokens[i];
                if (tok.type === 'rparen') {
                    parenDepth++;
                } else if (tok.type === 'lparen') {
                    if (parenDepth > 0) {
                        parenDepth--;
                    } else {
                        if (i > 0 && tokens[i - 1].type === 'function') {
                            const funcDef = tokens[i - 1].func || this.functions.find(f => f.name.toLowerCase() === tokens[i - 1].value.toLowerCase());
                            return {
                                funcDef: funcDef,
                                funcToken: tokens[i - 1],
                                argIndex: argIndex
                            };
                        }
                    }
                } else if (tok.type === 'comma' && parenDepth === 0) {
                    argIndex++;
                }
            }
            return null;
        },

        _getParamSpec(funcDef, argIndex) {
            if (!funcDef) return null;
            const fixedParams = funcDef.params || [];
            if (argIndex < fixedParams.length) {
                return fixedParams[argIndex];
            }
            const variadic = funcDef.variadic;
            if (variadic && variadic.length > 0) {
                const varIdx = (argIndex - fixedParams.length) % variadic.length;
                return variadic[varIdx];
            }
            return null;
        },

        /**
         * Resolve the return type of a function call, handling static and dynamic return types.
         */
        _resolveFunctionReturnType(funcDef, tokens, funcTokenIndex) {
            if (!funcDef || !funcDef.return_type) {
                return null;
            }
            const returnType = funcDef.return_type;
            if (returnType.value_type !== 'dynamic') {
                return returnType;
            }

            // Dynamic return type: inspect argument(s)
            const targetArgIdx = returnType.dynamic_from_arg != null ? returnType.dynamic_from_arg : 0;
            if (tokens && funcTokenIndex != null && funcTokenIndex >= 0) {
                let currentArg = 0;
                let depth = 0;
                let argFieldToken = null;
                let argFuncToken = null;
                let argFuncIndex = -1;

                for (let i = funcTokenIndex + 1; i < tokens.length; i++) {
                    const tok = tokens[i];
                    if (tok.type === 'lparen') {
                        depth++;
                    } else if (tok.type === 'rparen') {
                        depth--;
                        if (depth <= 0) break;
                    } else if (tok.type === 'comma' && depth === 1) {
                        currentArg++;
                    } else if (depth === 1 && currentArg === targetArgIdx) {
                        if (tok.type === 'field' && !argFieldToken) {
                            argFieldToken = tok;
                        } else if (tok.type === 'function' && !argFuncToken) {
                            argFuncToken = tok;
                            argFuncIndex = i;
                        }
                    }
                }

                if (argFieldToken) {
                    const field = this.fields.find(f => f.id === argFieldToken.value);
                    if (field) {
                        return {
                            value_type: field.valueType,
                            cardinality: returnType.cardinality || 'elements'
                        };
                    }
                } else if (argFuncToken) {
                    const argFuncDef = argFuncToken.func || this.functions.find(f => f.name.toLowerCase() === argFuncToken.value.toLowerCase());
                    const nestedReturnType = this._resolveFunctionReturnType(argFuncDef, tokens, argFuncIndex);
                    if (nestedReturnType) {
                        return {
                            value_type: nestedReturnType.value_type,
                            cardinality: returnType.cardinality || nestedReturnType.cardinality
                        };
                    }
                }
            }

            return {
                value_type: 'string',
                cardinality: returnType.cardinality || 'elements'
            };
        },

        /**
         * Determine query context before the caret.
         */
        _determineContext() {
            const currentPartial = this._getCurrentPartialToken();
            const beforePartial = this.value.slice(0, this.getCaret() - currentPartial.length);
            const tokens = this._tokenizeText(beforePartial);

            if (tokens.length === 0) {
                return { type: 'start', partial: currentPartial };
            }

            const lastToken = tokens[tokens.length - 1];
            const enclosing = this._findEnclosingFunctionCall(tokens);

            switch (lastToken.type) {
                case 'lbracket':
                case 'logical':
                    return { type: 'start', partial: currentPartial };

                case 'function':
                    return { type: 'expect_lparen', partial: currentPartial, func: lastToken.func };

                case 'lparen':
                    if (enclosing) {
                        const paramSpec = this._getParamSpec(enclosing.funcDef, enclosing.argIndex);
                        return { type: 'expect_arg', partial: currentPartial, enclosing, paramSpec };
                    }
                    return { type: 'start', partial: currentPartial };

                case 'comma':
                    if (enclosing) {
                        const paramSpec = this._getParamSpec(enclosing.funcDef, enclosing.argIndex);
                        return { type: 'expect_arg', partial: currentPartial, enclosing, paramSpec };
                    }
                    return { type: 'start', partial: currentPartial };

                case 'field':
                    if (enclosing) {
                        return { type: 'after_arg', partial: currentPartial, enclosing };
                    }
                    const field = this.fields.find(f => f.id === lastToken.value);
                    return {
                        type: 'expect_operator',
                        partial: currentPartial,
                        fieldType: field ? field.valueType : null,
                        isArrayField: lastToken.value.includes('[]')
                    };

                case 'rparen':
                    // Check if this rparen closed an outer function call or an inner one
                    if (enclosing) {
                        return { type: 'after_arg', partial: currentPartial, enclosing };
                    }
                    // Standalone or closed function expression at top level: can be followed by operator or logical
                    let closedFuncDef = null;
                    let closedFuncTokenIndex = -1;
                    let parenDepth = 1;
                    for (let i = tokens.length - 2; i >= 0; i--) {
                        if (tokens[i].type === 'rparen') parenDepth++;
                        else if (tokens[i].type === 'lparen') {
                            parenDepth--;
                            if (parenDepth === 0 && i > 0 && tokens[i - 1].type === 'function') {
                                closedFuncDef = tokens[i - 1].func || this.functions.find(f => f.name.toLowerCase() === tokens[i - 1].value.toLowerCase());
                                closedFuncTokenIndex = i - 1;
                                break;
                            }
                        }
                    }

                    const returnType = closedFuncDef
                        ? this._resolveFunctionReturnType(closedFuncDef, tokens, closedFuncTokenIndex)
                        : null;

                    return {
                        type: 'expect_operator_or_logical',
                        partial: currentPartial,
                        funcDef: closedFuncDef,
                        returnType: returnType,
                        fieldType: returnType ? returnType.value_type : null
                    };

                case 'operator':
                    let valueType = null;
                    // Check if preceding expression is a closed function call (ended with rparen)
                    if (tokens.length >= 2 && tokens[tokens.length - 2].type === 'rparen') {
                        let parenDepth = 1;
                        for (let i = tokens.length - 3; i >= 0; i--) {
                            if (tokens[i].type === 'rparen') parenDepth++;
                            else if (tokens[i].type === 'lparen') {
                                parenDepth--;
                                if (parenDepth === 0 && i > 0 && tokens[i - 1].type === 'function') {
                                    const funcDef = tokens[i - 1].func || this.functions.find(f => f.name.toLowerCase() === tokens[i - 1].value.toLowerCase());
                                    const retType = this._resolveFunctionReturnType(funcDef, tokens, i - 1);
                                    if (retType) {
                                        valueType = retType.value_type;
                                    }
                                    break;
                                }
                            }
                        }
                    }
                    if (!valueType) {
                        // Find preceding field
                        for (let i = tokens.length - 2; i >= 0; i--) {
                            if (tokens[i].type === 'field') {
                                const f = this.fields.find(fld => fld.id === tokens[i].value);
                                if (f) { valueType = f.valueType; break; }
                            }
                        }
                    }
                    return { type: 'expect_value', partial: currentPartial, fieldType: valueType };

                case 'string':
                case 'number':
                case 'boolean':
                    if (enclosing) {
                        return { type: 'after_arg', partial: currentPartial, enclosing };
                    }
                    if (this._isValueComplete(lastToken)) {
                        return { type: 'expect_logical', partial: currentPartial };
                    }
                    return { type: 'expect_value', partial: currentPartial };

                case 'rbracket':
                    return { type: 'expect_logical', partial: currentPartial };

                default:
                    return { type: 'start', partial: currentPartial };
            }
        },

        _isValueComplete(token) {
            if (token.type === 'string') {
                return token.value.endsWith('"') || token.value.endsWith("'");
            }
            return true;
        },

        _getCurrentPartialToken() {
            const caret = this.getCaret();
            const before = this.value.slice(0, caret);

            let start = before.length - 1;
            while (start >= 0) {
                const char = before[start];
                if (/[\s{}=<>()]/.test(char) || char === '\n' || char === '\r') {
                    start++;
                    break;
                }
                start--;
            }
            if (start < 0) start = 0;
            return before.slice(start).trim();
        },

        /**
         * Generate autocomplete suggestions based on context and language spec.
         */
        _generateSuggestions(context) {
            const suggestions = [];
            const partialLower = context.partial.toLowerCase();

            // Start of query or after { or AND/OR
            if (context.type === 'start') {
                if (this.grouping.open.startsWith(partialLower) || partialLower === '') {
                    suggestions.push({
                        id: this.grouping.open,
                        label: `${this.grouping.open} — open group`,
                        insertValue: this.grouping.open,
                        type: 'bracket'
                    });
                }

                if ('not'.startsWith(partialLower) || partialLower === '') {
                    suggestions.push({
                        id: 'NOT',
                        label: 'NOT — negate condition',
                        insertValue: 'NOT',
                        type: 'logical'
                    });
                }

                // All registered functions
                this.functions.forEach(func => {
                    if (partialLower === '' || func.name.toLowerCase().startsWith(partialLower)) {
                        suggestions.push({
                            id: func.name,
                            label: `${func.name}() — ${func.description}`,
                            insertValue: func.name,
                            type: 'function'
                        });
                    }
                });

                // Searchable fields
                this.fields.forEach(field => {
                    if (partialLower === '' ||
                        field.id.toLowerCase().includes(partialLower) ||
                        field.label.toLowerCase().includes(partialLower)) {
                        suggestions.push({
                            id: field.id,
                            label: field.label,
                            insertValue: field.id,
                            type: 'field'
                        });
                    }
                });
            }

            else if (context.type === 'expect_lparen') {
                if ('('.startsWith(partialLower) || partialLower === '') {
                    suggestions.push({
                        id: '(',
                        label: '( — open arguments',
                        insertValue: '(',
                        type: 'paren'
                    });
                }
            }

            else if (context.type === 'expect_arg') {
                const paramSpec = context.paramSpec;
                if (!paramSpec) return [];

                // Field expected
                if (paramSpec.accepts === 'field' || paramSpec.accepts === 'expr') {
                    const reqCardinality = paramSpec.cardinality;
                    const reqTypes = paramSpec.value_types;

                    this.fields.forEach(field => {
                        if (reqCardinality === 'elements' && !field.id.includes('[]')) {
                            return;
                        }
                        if (reqTypes && !reqTypes.includes(field.valueType)) {
                            return;
                        }

                        if (partialLower === '' ||
                            field.id.toLowerCase().includes(partialLower) ||
                            field.label.toLowerCase().includes(partialLower)) {
                            suggestions.push({
                                id: field.id,
                                label: field.label,
                                insertValue: field.id,
                                type: 'field'
                            });
                        }
                    });

                    // Nested functions if expr
                    if (paramSpec.accepts === 'expr') {
                        this.functions.forEach(func => {
                            if (func.return_type) {
                                const funcCard = func.return_type.cardinality;
                                if (reqCardinality && funcCard && funcCard !== reqCardinality) {
                                    return;
                                }
                                const funcValType = func.return_type.value_type;
                                if (reqTypes && funcValType && funcValType !== 'dynamic' && !reqTypes.includes(funcValType)) {
                                    return;
                                }
                            }
                            if (partialLower === '' || func.name.toLowerCase().startsWith(partialLower)) {
                                suggestions.push({
                                    id: func.name,
                                    label: `${func.name}() — ${func.description}`,
                                    insertValue: func.name,
                                    type: 'function'
                                });
                            }
                        });
                    }
                }

                // Literal expected
                if (paramSpec.accepts === 'literal' || (paramSpec.accepts === 'expr' && paramSpec.cardinality !== 'elements')) {
                    const reqTypes = paramSpec.value_types || ['string', 'integer', 'boolean'];
                    if (reqTypes.includes('string') && (partialLower === '' || '"pattern"'.startsWith(partialLower))) {
                        suggestions.push({
                            id: 'string',
                            label: '"pattern" — string literal',
                            insertValue: '""',
                            type: 'value',
                            cursorOffset: -1
                        });
                    }
                    if (reqTypes.includes('integer') && (partialLower === '' || /^\d/.test(partialLower))) {
                        suggestions.push({
                            id: 'number',
                            label: '42 — integer literal',
                            insertValue: '',
                            type: 'value'
                        });
                    }
                    if (reqTypes.includes('boolean')) {
                        if (partialLower === '' || 'true'.startsWith(partialLower)) {
                            suggestions.push({ id: 'true', label: 'true — boolean', insertValue: 'true', type: 'value' });
                        }
                        if (partialLower === '' || 'false'.startsWith(partialLower)) {
                            suggestions.push({ id: 'false', label: 'false — boolean', insertValue: 'false', type: 'value' });
                        }
                    }
                }
            }

            else if (context.type === 'after_arg') {
                if (','.startsWith(partialLower) || partialLower === '') {
                    suggestions.push({
                        id: ',',
                        label: ', — next argument',
                        insertValue: ',',
                        type: 'comma'
                    });
                }
                if (')'.startsWith(partialLower) || partialLower === '') {
                    suggestions.push({
                        id: ')',
                        label: ') — close arguments',
                        insertValue: ')',
                        type: 'paren'
                    });
                }
            }

            else if (context.type === 'expect_operator_or_logical') {
                const retType = context.returnType;
                const isBooleanPredicate = retType
                    ? (retType.value_type === 'boolean' && retType.cardinality === 'single')
                    : true;

                if (isBooleanPredicate) {
                    const openCount = (this.value.match(/\{/g) || []).length;
                    const closeCount = (this.value.match(/\}/g) || []).length;

                    if (openCount > closeCount && (this.grouping.close.startsWith(partialLower) || partialLower === '')) {
                        suggestions.push({
                            id: this.grouping.close,
                            label: `${this.grouping.close} — close group`,
                            insertValue: this.grouping.close,
                            type: 'bracket'
                        });
                    }

                    this.binaryLogicalOperators.forEach(op => {
                        if (partialLower === '' || op.toLowerCase().startsWith(partialLower)) {
                            suggestions.push({
                                id: op,
                                label: `${op} — logical ${op}`,
                                insertValue: op,
                                type: 'logical'
                            });
                        }
                    });
                }

                // Comparison operators
                const valueType = retType ? retType.value_type : context.fieldType;
                this.operators.forEach(op => {
                    if (valueType && !this._isOperatorApplicableToFieldType(op, valueType)) {
                        return;
                    }
                    if (partialLower === '' || op.toLowerCase().startsWith(partialLower)) {
                        const opObj = this.operatorObjects.find(o => o.symbol === op);
                        suggestions.push({
                            id: op,
                            label: `${op} — ${opObj ? opObj.description : op}`,
                            insertValue: op,
                            type: 'operator'
                        });
                    }
                });
            }

            else if (context.type === 'expect_operator') {
                const fieldType = context.fieldType;
                this.operators.forEach(op => {
                    const isApplicable = this._isOperatorApplicableToFieldType(op, fieldType);
                    if (isApplicable && (partialLower === '' || op.toLowerCase().startsWith(partialLower))) {
                        const opObj = this.operatorObjects.find(o => o.symbol === op);
                        suggestions.push({
                            id: op,
                            label: `${op} — ${opObj ? opObj.description : op}`,
                            insertValue: op,
                            type: 'operator'
                        });
                    }
                });
            }

            else if (context.type === 'expect_value') {
                const fieldType = context.fieldType;

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
                    suggestions.push({ id: 'true', label: 'true — boolean', insertValue: 'true', type: 'value' });
                }
                if ((fieldType === 'boolean' || !fieldType) && (partialLower === '' || 'false'.startsWith(partialLower))) {
                    suggestions.push({ id: 'false', label: 'false — boolean', insertValue: 'false', type: 'value' });
                }
                if ((fieldType === 'integer' || !fieldType) && (partialLower === '' || /^\d/.test(partialLower))) {
                    suggestions.push({ id: 'number', label: '42 — numeric value', insertValue: '', type: 'value' });
                }
            }

            else if (context.type === 'expect_logical') {
                const openCount = (this.value.match(/\{/g) || []).length;
                const closeCount = (this.value.match(/\}/g) || []).length;

                if (openCount > closeCount && (this.grouping.close.startsWith(partialLower) || partialLower === '')) {
                    suggestions.push({
                        id: this.grouping.close,
                        label: `${this.grouping.close} — close group`,
                        insertValue: this.grouping.close,
                        type: 'bracket'
                    });
                }

                this.binaryLogicalOperators.forEach(op => {
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

        _isOperatorApplicableToFieldType(operator, fieldType) {
            if (!fieldType) return true;
            if (fieldType === 'boolean') return operator === '=' || operator === '!=';
            const opUpper = (operator || '').toUpperCase();
            if (fieldType === 'string') return operator === '=' || operator === '!=' || opUpper === 'CONTAINS';
            if (fieldType === 'integer') return opUpper !== 'CONTAINS';
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

            const caret = this.getCaret();
            const partial = this._getCurrentPartialToken();

            let replaceStart = caret - partial.length;
            let replaceEnd = caret;

            const left = this.value.slice(0, replaceStart);
            const right = this.value.slice(replaceEnd);

            let insert = s.insertValue;
            let spacing = '';

            if (s.type === 'function') {
                insert = insert + '( ';
                if (left && !left.endsWith(' ')) {
                    insert = ' ' + insert;
                }
            } else if (s.type === 'comma') {
                spacing = ' ';
            } else if (s.type === 'field' || s.type === 'operator' || s.type === 'logical') {
                if ((right && !right.startsWith(' ')) || !right) {
                    spacing = ' ';
                }
                if (s.type === 'logical' && left && !left.endsWith(' ')) {
                    insert = ' ' + insert;
                }
            } else if (s.type === 'paren' && s.insertValue === ')') {
                spacing = ' ';
            }

            this.value = left + insert + spacing + right;

            let newCaret = (left + insert + spacing).length;
            if (s.cursorOffset !== undefined) {
                newCaret += s.cursorOffset;
            }

            this.setCaret(newCaret);
            this.closeSuggestions();
            this.updateHighlight();

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

        validateQuery() {
            if (!this.value.trim()) {
                return { valid: true, message: '' };
            }
            const openBrackets = (this.value.match(/\{/g) || []).length;
            const closeBrackets = (this.value.match(/\}/g) || []).length;
            if (openBrackets !== closeBrackets) {
                return { valid: false, message: 'Mismatched brackets' };
            }
            const quotePattern = /(?:[^\\]|^)["'](?:[^\\]|\\[\\])*$/;
            if (quotePattern.test(this.value)) {
                return { valid: false, message: 'Unterminated string - missing closing quote' };
            }
            return { valid: true, message: '' };
        },

        normalizeForSubmit() {
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
            if (!text) return '';

            const tokenClasses = {
                field: 'text-neutral-900 dark:text-neutral-50',
                operator: 'text-orange-600 dark:text-orange-500',
                logical: 'text-orange-600 dark:text-orange-500',
                string: 'text-green-600 dark:text-green-300',
                number: 'text-blue-600 dark:text-blue-300',
                boolean: 'text-red-600 dark:text-red-300',
                bracket: 'text-orange-500 dark:text-orange-400',
                function: 'text-yellow-800 dark:text-yellow-300',
                paren: 'text-yellow-800 dark:text-yellow-300',
                comma: 'text-neutral-600 dark:text-neutral-400'
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

            const isFunc = (word) => {
                const lower = word.toLowerCase();
                return this.functions.some(f => f.name.toLowerCase() === lower);
            };

            const isOpKeyword = (word) => {
                const upper = word.toUpperCase();
                return this.operatorObjects.some(o => o.keyword && o.symbol.toUpperCase() === upper);
            };

            while (i < text.length) {
                const char = text[i];

                if (/\s/.test(char) || char === '\n' || char === '\r') {
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

                if (char === ',') {
                    pushToken(char, 'comma');
                    i++;
                    continue;
                }

                if (char === '>' || char === '<' || char === '=' || char === '!') {
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
                    while (i < text.length && /[a-zA-Z0-9_.\[\]-]/.test(text[i])) {
                        word += text[i];
                        i++;
                    }

                    const wordUpper = word.toUpperCase();
                    if (this.logicalOperators.map(o => o.toUpperCase()).includes(wordUpper)) {
                        pushToken(word, 'logical');
                    } else if (isOpKeyword(word)) {
                        pushToken(word, 'operator');
                    } else if (isFunc(word)) {
                        pushToken(word, 'function');
                    } else if (word === 'true' || word === 'false') {
                        pushToken(word, 'boolean');
                    } else if (/^-?\d+(\.\d+)?$/.test(word)) {
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
            const searchQuery = this.value || '';
            const columns = this.selectedColumns.map(c => c.id).join(',');
            const params = new URLSearchParams();
            params.set('query', searchQuery);
            params.set('columns', columns);
            window.location.href = '/hosts/saved_searches/create/?' + params.toString();
        }
    };
}
