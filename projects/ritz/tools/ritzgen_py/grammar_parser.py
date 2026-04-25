"""
grammar_parser.py - Parse .grammar files

Reads the grammar DSL and produces structured token definitions and grammar rules.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum, auto


class SymbolKind(Enum):
    TERMINAL = auto()       # Token (uppercase, e.g., IDENT, NUMBER)
    NONTERMINAL = auto()    # Rule reference (lowercase, e.g., expr, stmt)
    OPTIONAL = auto()       # foo?
    STAR = auto()           # foo*
    PLUS = auto()           # foo+


@dataclass
class TokenDef:
    """A token definition from %tokens section."""
    name: str           # Token name (e.g., IDENT, PLUS)
    pattern: str        # Pattern string or regex
    is_literal: bool    # True if exact string match, False if regex
    is_skip: bool       # True if this token should be skipped (whitespace)
    token_id: int = 0   # Assigned token ID


@dataclass
class GrammarSymbol:
    """A symbol in a grammar alternative."""
    kind: SymbolKind
    name: str           # Symbol name (token or rule name)
    quantifier: str = ''  # '', '?', '*', '+'


@dataclass
class GrammarAlt:
    """An alternative in a grammar rule."""
    symbols: List[GrammarSymbol]
    action: Optional[str] = None  # Semantic action in { }


@dataclass
class GrammarRule:
    """A grammar rule."""
    name: str                       # Rule name
    return_type: Optional[str]      # Return type (e.g., "*Expr", "i32")
    alternatives: List[GrammarAlt]


@dataclass
class Grammar:
    """Complete parsed grammar."""
    tokens: List[TokenDef] = field(default_factory=list)
    rules: List[GrammarRule] = field(default_factory=list)
    token_map: Dict[str, TokenDef] = field(default_factory=dict)
    # Per-rule recovery directives.  Maps rule name -> list of token names.
    # When all alternatives of the rule fail and we're not at EOF, the
    # generated code skips forward to the next token whose kind is in this
    # list, clears the error, and reports progress (return 1).  Used to
    # convert "silent drop on unknown top-level item" into "skip & continue".
    recovery: Dict[str, List[str]] = field(default_factory=dict)


class GrammarParser:
    """Parse a .grammar file into structured data."""

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1

    def parse(self) -> Grammar:
        """Parse the entire grammar file."""
        grammar = Grammar()

        # Add built-in tokens
        builtins = [
            ('EOF', '', True, False),
            ('ERROR', '', True, False),
            ('SKIP', '', True, True),
            ('NEWLINE', '\n', True, False),
            ('INDENT', '', True, False),
            ('DEDENT', '', True, False),
        ]
        for i, (name, pattern, is_literal, is_skip) in enumerate(builtins):
            tok = TokenDef(name, pattern, is_literal, is_skip, i)
            grammar.tokens.append(tok)
            grammar.token_map[name] = tok

        next_token_id = len(builtins)
        in_skip_section = False

        while self.pos < len(self.text):
            self._skip_whitespace_and_comments()
            if self.pos >= len(self.text):
                break

            # Check for section markers
            if self._match('%tokens'):
                in_skip_section = False
                continue
            elif self._match('%skip'):
                in_skip_section = True
                continue
            elif self._match('%recovery'):
                in_skip_section = False
                self._parse_recovery_section(grammar)
                continue
            elif self._match('%grammar'):
                # Parse grammar rules
                self._parse_grammar_rules(grammar)
                break

            # Parse token definition
            tok = self._parse_token_def(is_skip=in_skip_section)
            if tok:
                # Skip if already defined (e.g., NEWLINE appears in both %tokens and %skip)
                if tok.name in grammar.token_map:
                    continue
                tok.token_id = next_token_id
                next_token_id += 1
                grammar.tokens.append(tok)
                grammar.token_map[tok.name] = tok

        return grammar

    def _skip_whitespace_and_comments(self):
        """Skip whitespace and # comments."""
        while self.pos < len(self.text):
            c = self.text[self.pos]
            if c == '#':
                # Skip to end of line
                while self.pos < len(self.text) and self.text[self.pos] != '\n':
                    self.pos += 1
            elif c in ' \t\r\n':
                if c == '\n':
                    self.line += 1
                    self.col = 1
                else:
                    self.col += 1
                self.pos += 1
            else:
                break

    def _match(self, s: str) -> bool:
        """Try to match a string at current position."""
        if self.text[self.pos:self.pos+len(s)] == s:
            self.pos += len(s)
            self.col += len(s)
            return True
        return False

    def _parse_token_def(self, is_skip: bool) -> Optional[TokenDef]:
        """Parse a token definition like: NAME = "literal" or NAME = /regex/"""
        self._skip_whitespace_and_comments()
        if self.pos >= len(self.text):
            return None

        # Parse name (uppercase identifier)
        name_match = re.match(r'([A-Z_][A-Z0-9_]*)', self.text[self.pos:])
        if not name_match:
            return None

        name = name_match.group(1)
        self.pos += len(name)
        self.col += len(name)

        self._skip_whitespace_and_comments()
        if not self._match('='):
            return None

        self._skip_whitespace_and_comments()

        # Parse pattern - "literal" or /regex/
        if self.pos < len(self.text) and self.text[self.pos] == '"':
            # Literal string
            self.pos += 1
            start = self.pos
            while self.pos < len(self.text) and self.text[self.pos] != '"':
                if self.text[self.pos] == '\\' and self.pos + 1 < len(self.text):
                    self.pos += 2
                else:
                    self.pos += 1
            pattern = self.text[start:self.pos]
            self.pos += 1  # skip closing "
            return TokenDef(name, pattern, is_literal=True, is_skip=is_skip)

        elif self.pos < len(self.text) and self.text[self.pos] == '/':
            # Regex pattern
            self.pos += 1
            start = self.pos
            while self.pos < len(self.text) and self.text[self.pos] != '/':
                if self.text[self.pos] == '\\' and self.pos + 1 < len(self.text):
                    self.pos += 2
                else:
                    self.pos += 1
            pattern = self.text[start:self.pos]
            self.pos += 1  # skip closing /
            return TokenDef(name, pattern, is_literal=False, is_skip=is_skip)

        return None

    def _parse_recovery_section(self, grammar: Grammar):
        """Parse %recovery declarations.

        Format:
            %recovery
            <rule_name> = <TOKEN1> <TOKEN2> ... ;

        Each line declares the recovery token-set for one rule: when
        all alternatives of <rule_name> fail to match, the generator
        will emit a skip-forward loop that advances p.pos past the
        unmatched token until p_peek returns one of the listed tokens
        (or EOF).  After the skip, p.error is cleared and the rule
        returns 1 to signal progress so the enclosing star/plus loop
        keeps going instead of silently dropping subsequent items.
        """
        while self.pos < len(self.text):
            self._skip_whitespace_and_comments()
            if self.pos >= len(self.text):
                return
            # Stop at next section marker.
            if self.text[self.pos] == '%':
                return
            # Rule name (lowercase ident).
            name_match = re.match(r'([a-z_][a-z0-9_]*)', self.text[self.pos:])
            if not name_match:
                return
            name = name_match.group(1)
            self.pos += len(name)
            self._skip_whitespace_and_comments()
            if not self._match('='):
                return
            self._skip_whitespace_and_comments()
            # Collect tokens until ';' or newline-followed-by-non-token.
            tokens: List[str] = []
            while self.pos < len(self.text):
                self._skip_whitespace_and_comments()
                if self.pos >= len(self.text):
                    break
                if self._match(';'):
                    break
                tok_match = re.match(r'([A-Z_][A-Z0-9_]*)', self.text[self.pos:])
                if not tok_match:
                    break
                tokens.append(tok_match.group(1))
                self.pos += len(tok_match.group(1))
            grammar.recovery[name] = tokens

    def _parse_grammar_rules(self, grammar: Grammar):
        """Parse grammar rules after %grammar."""
        while self.pos < len(self.text):
            self._skip_whitespace_and_comments()
            if self.pos >= len(self.text):
                break

            rule = self._parse_rule()
            if rule:
                grammar.rules.append(rule)

    def _parse_rule(self) -> Optional[GrammarRule]:
        """Parse a grammar rule."""
        self._skip_whitespace_and_comments()
        if self.pos >= len(self.text):
            return None

        # Parse rule name (lowercase identifier)
        name_match = re.match(r'([a-z_][a-z0-9_]*)', self.text[self.pos:])
        if not name_match:
            return None

        name = name_match.group(1)
        self.pos += len(name)

        self._skip_whitespace_and_comments()

        # Optional return type: -> *Type
        return_type = None
        if self._match('->'):
            self._skip_whitespace_and_comments()
            # Parse type (may include *)
            type_match = re.match(r'(\*?[A-Za-z_][A-Za-z0-9_]*)', self.text[self.pos:])
            if type_match:
                return_type = type_match.group(1)
                self.pos += len(return_type)

        self._skip_whitespace_and_comments()

        # Expect :
        if not self._match(':'):
            return None

        # Parse alternatives
        alternatives = []
        while True:
            self._skip_whitespace_and_comments()
            alt = self._parse_alternative()
            if alt:
                alternatives.append(alt)

            self._skip_whitespace_and_comments()
            if self._match('|'):
                continue
            elif self._match(';'):
                break
            else:
                break

        return GrammarRule(name, return_type, alternatives)

    def _parse_alternative(self) -> Optional[GrammarAlt]:
        """Parse one alternative in a rule."""
        symbols = []
        action = None

        while True:
            self._skip_whitespace_and_comments()
            if self.pos >= len(self.text):
                break

            c = self.text[self.pos]
            if c in '|;':
                break

            # Check for semantic action { ... }
            if c == '{':
                action = self._parse_action()
                break

            # Parse symbol
            sym = self._parse_symbol()
            if sym:
                symbols.append(sym)
            else:
                break

        return GrammarAlt(symbols, action) if symbols or action else None

    def _parse_symbol(self) -> Optional[GrammarSymbol]:
        """Parse a single grammar symbol."""
        self._skip_whitespace_and_comments()
        if self.pos >= len(self.text):
            return None

        # Parse identifier (terminal or non-terminal)
        id_match = re.match(r'([A-Za-z_][A-Za-z0-9_]*)', self.text[self.pos:])
        if not id_match:
            return None

        name = id_match.group(1)
        self.pos += len(name)

        # Check for quantifier
        quantifier = ''
        if self.pos < len(self.text) and self.text[self.pos] in '?*+':
            quantifier = self.text[self.pos]
            self.pos += 1

        # Determine kind
        if name.isupper():
            kind = SymbolKind.TERMINAL
        else:
            kind = SymbolKind.NONTERMINAL

        # Adjust kind for quantifiers
        if quantifier == '?':
            kind = SymbolKind.OPTIONAL
        elif quantifier == '*':
            kind = SymbolKind.STAR
        elif quantifier == '+':
            kind = SymbolKind.PLUS

        return GrammarSymbol(kind, name, quantifier)

    def _parse_action(self) -> Optional[str]:
        """Parse a semantic action { ... }."""
        if not self._match('{'):
            return None

        depth = 1
        start = self.pos
        while self.pos < len(self.text) and depth > 0:
            c = self.text[self.pos]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            self.pos += 1

        return self.text[start:self.pos-1].strip()


def parse_grammar_file(path: str) -> Grammar:
    """Parse a grammar file and return Grammar object."""
    with open(path, 'r') as f:
        text = f.read()
    parser = GrammarParser(text)
    return parser.parse()


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: grammar_parser.py <grammar_file>")
        sys.exit(1)

    grammar = parse_grammar_file(sys.argv[1])
    print(f"Tokens: {len(grammar.tokens)}")
    for tok in grammar.tokens:
        print(f"  {tok.token_id}: {tok.name} = {repr(tok.pattern)}")

    print(f"\nRules: {len(grammar.rules)}")
    for rule in grammar.rules:
        print(f"  {rule.name} -> {rule.return_type or 'void'}")
        for alt in rule.alternatives:
            syms = ' '.join(f"{s.name}{s.quantifier}" for s in alt.symbols)
            print(f"    : {syms}")
            if alt.action:
                print(f"      {{ {alt.action} }}")
