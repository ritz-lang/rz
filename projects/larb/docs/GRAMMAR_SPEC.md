# Ritz Grammar Specification

This document provides the formal grammar specification for the Ritz programming language in Extended Backus-Naur Form (EBNF). It serves as the authoritative reference for parser implementers and language tool developers.

## Notation

| Symbol | Meaning |
|--------|---------|
| `=` | Definition |
| `\|` | Alternative |
| `[ ... ]` | Optional (0 or 1) |
| `{ ... }` | Repetition (0 or more) |
| `( ... )` | Grouping |
| `"..."` | Terminal (literal) |
| `'...'` | Terminal (literal, alternate) |
| `/regex/` | Regular expression pattern |
| `UPPER` | Token (terminal) |
| `lower` | Non-terminal (production rule) |
| `ε` | Empty production |

---

## 1. Lexical Grammar

### 1.1 Character Sets

```
letter     = 'A'..'Z' | 'a'..'z'
digit      = '0'..'9'
hex_digit  = digit | 'A'..'F' | 'a'..'f'
bin_digit  = '0' | '1'
```

### 1.2 Identifiers

```ebnf
IDENT = ( letter | '_' ) { letter | digit | '_' }
```

Identifiers must not be keywords. Keywords take precedence over identifiers during lexical analysis.

### 1.3 Keywords

The following identifiers are reserved keywords:

| | | | | |
|---|---|---|---|---|
| `as` | `assert` | `break` | `const` | `continue` |
| `else` | `enum` | `extern` | `false` | `fn` |
| `for` | `if` | `impl` | `import` | `in` |
| `let` | `match` | `mut` | `null` | `pub` |
| `return` | `struct` | `trait` | `true` | `type` |
| `unsafe` | `var` | `while` | | |

### 1.4 Primitive Type Keywords

| | | | | |
|---|---|---|---|---|
| `i8` | `i16` | `i32` | `i64` | |
| `u8` | `u16` | `u32` | `u64` | |
| `f32` | `f64` | `bool` | | |

### 1.5 Numeric Literals

```ebnf
NUMBER     = digit { digit }
HEX_NUMBER = '0x' hex_digit { hex_digit }
BIN_NUMBER = '0b' bin_digit { bin_digit }
FLOAT      = digit { digit } '.' digit { digit }
```

**Examples:**
```ritz
42          # decimal integer
0xFF        # hexadecimal (255)
0b1010      # binary (10)
3.14159     # floating point
```

### 1.6 String Literals

```ebnf
STRING      = '"' { string_char | escape_seq } '"'
CSTRING     = 'c"' { string_char | escape_seq } '"'
SPAN_STRING = 's"' { string_char | escape_seq } '"'
CHAR        = "'" ( char_char | escape_seq ) "'"

string_char = any character except '"' or '\'
char_char   = any character except "'" or '\'
escape_seq  = '\' ( 'n' | 'r' | 't' | '\' | '"' | "'" | '0' | 'x' hex_digit hex_digit )
```

| Prefix | Type | Description |
|--------|------|-------------|
| (none) | `*u8` | Null-terminated C string |
| `c` | `*u8` | Explicit C string (same as above) |
| `s` | `Span<u8>` | Ritz span (ptr + length) |

### 1.7 Operators and Punctuation

#### Multi-character Operators (ordered by length, longest first)

| Token | Symbol | Description |
|-------|--------|-------------|
| `ARROW` | `->` | Return type, pointer member |
| `FAT_ARROW` | `=>` | Match arm |
| `DOT_DOT` | `..` | Range |
| `COLON_COLON` | `::` | Path separator |
| `AND` | `&&` | Logical AND |
| `OR` | `\|\|` | Logical OR |
| `EQ` | `==` | Equality |
| `NE` | `!=` | Inequality |
| `LE` | `<=` | Less or equal |
| `GE` | `>=` | Greater or equal |
| `SHL` | `<<` | Shift left |
| `SHR` | `>>` | Shift right |
| `PLUS_EQ` | `+=` | Add-assign |
| `MINUS_EQ` | `-=` | Subtract-assign |
| `STAR_EQ` | `*=` | Multiply-assign |
| `SLASH_EQ` | `/=` | Divide-assign |
| `AMP_MUT` | `&mut` | Mutable reference |

#### Single-character Operators

| Token | Symbol | Token | Symbol | Token | Symbol |
|-------|--------|-------|--------|-------|--------|
| `PLUS` | `+` | `MINUS` | `-` | `STAR` | `*` |
| `SLASH` | `/` | `PERCENT` | `%` | `AMP` | `&` |
| `PIPE` | `\|` | `CARET` | `^` | `TILDE` | `~` |
| `BANG` | `!` | `LT` | `<` | `GT` | `>` |
| `ASSIGN` | `=` | `DOT` | `.` | `QUESTION` | `?` |
| `AT` | `@` | | | | |

#### Delimiters

| Token | Symbol | Token | Symbol |
|-------|--------|-------|--------|
| `LPAREN` | `(` | `RPAREN` | `)` |
| `LBRACKET` | `[` | `RBRACKET` | `]` |
| `LBRACE` | `{` | `RBRACE` | `}` |
| `COMMA` | `,` | `COLON` | `:` |
| `SEMI` | `;` | | |

### 1.8 Whitespace and Comments

```ebnf
WHITESPACE = ' ' | '\t' | '\r'      (* skipped *)
NEWLINE    = '\n'                    (* significant *)
COMMENT    = '#' { any except '\n' } (* to end of line *)
```

Whitespace (spaces, tabs, carriage returns) is skipped. Newlines are significant for statement termination and indentation tracking.

### 1.9 Indentation (Synthesized Tokens)

Ritz uses indentation-sensitive parsing. The lexer synthesizes these tokens:

| Token | Description |
|-------|-------------|
| `INDENT` | Indentation level increased |
| `DEDENT` | Indentation level decreased |
| `EOF` | End of file |

**Rules:**
1. At the start of each line, measure leading whitespace
2. If deeper than current level → emit `INDENT`
3. If shallower → emit one `DEDENT` per level closed
4. Tabs are expanded to 4 spaces (configurable)
5. Empty lines and comment-only lines do not affect indentation

---

## 2. Syntactic Grammar

### 2.1 Module Structure

```ebnf
module = { item }

item = [ attrs ] fn_def
     | struct_def
     | enum_def
     | const_def
     | type_alias
     | trait_def
     | impl_block
     | import_stmt
     | global_var
```

### 2.2 Attributes

```ebnf
attrs = attr { attr }

attr = '@' IDENT [ NEWLINE ]
```

**Examples:**
```ritz
@test
fn test_something()
    assert 1 == 1

@inline
fn fast_add(a: i32, b: i32) -> i32
    return a + b
```

### 2.3 Functions

```ebnf
fn_def = 'fn' IDENT [ generic_params ] '(' [ params ] ')' [ return_type ] block
       | 'extern' 'fn' IDENT '(' [ params ] ')' [ return_type ] NEWLINE
       | 'pub' 'fn' IDENT [ generic_params ] '(' [ params ] ')' [ return_type ] block

generic_params = '<' generic_param_list '>'
generic_param_list = IDENT { ',' IDENT }

params = param { ',' param }
param = IDENT ':' type

return_type = '->' type
```

**Examples:**
```ritz
fn add(a: i32, b: i32) -> i32
    return a + b

fn identity<T>(x: T) -> T
    return x

extern fn printf(fmt: *u8) -> i32

pub fn api_function() -> bool
    return true
```

### 2.4 Structures

```ebnf
struct_def = 'struct' IDENT [ generic_params ] NEWLINE INDENT struct_fields DEDENT

struct_fields = { struct_field }
struct_field = IDENT ':' type NEWLINE
```

**Example:**
```ritz
struct Point<T>
    x: T
    y: T
```

### 2.5 Enumerations

```ebnf
enum_def = 'enum' IDENT [ generic_params ] NEWLINE INDENT enum_variants DEDENT

enum_variants = { enum_variant }
enum_variant = IDENT [ '(' type ')' ] NEWLINE
```

**Example:**
```ritz
enum Option<T>
    Some(T)
    None

enum Color
    Red
    Green
    Blue
```

### 2.6 Type Aliases

```ebnf
type_alias = 'type' IDENT [ generic_params ] '=' type NEWLINE
```

**Example:**
```ritz
type Byte = u8
type Result<T> = Option<T>
```

### 2.7 Traits

```ebnf
trait_def = 'trait' IDENT NEWLINE INDENT trait_methods DEDENT

trait_methods = { trait_method }
trait_method = 'fn' IDENT '(' [ params ] ')' [ return_type ] NEWLINE
```

**Example:**
```ritz
trait Printable
    fn print(self: *Self)
    fn to_string(self: *Self) -> *u8
```

### 2.8 Implementations

```ebnf
impl_block = 'impl' [ generic_params ] type_name [ 'for' type_name ] NEWLINE INDENT impl_methods DEDENT

impl_methods = { fn_def }
```

**Examples:**
```ritz
impl Point
    fn new(x: i32, y: i32) -> Point
        return Point{x: x, y: y}

impl Printable for Point
    fn print(self: *Self)
        printf("(%d, %d)", self.x, self.y)
```

### 2.9 Imports

```ebnf
import_stmt = 'import' module_path NEWLINE

module_path = IDENT { '.' IDENT }
```

**Example:**
```ritz
import std.io
import collections.hashmap
```

### 2.10 Constants and Global Variables

```ebnf
const_def = 'const' IDENT ':' type '=' expr NEWLINE

global_var = 'var' IDENT ':' type [ '=' expr ] NEWLINE
```

**Examples:**
```ritz
const PI: f64 = 3.14159265359
const MAX_SIZE: u64 = 1024

var counter: i32 = 0
var buffer: [1024]u8
```

---

## 3. Types

```ebnf
type = primitive_type
     | type_name
     | '*' type                    (* pointer *)
     | '*' 'mut' type              (* mutable pointer *)
     | '&' type                    (* reference *)
     | '&mut' type                 (* mutable reference *)
     | '[' NUMBER ']' type         (* fixed array *)
     | '[' ']' type                (* slice *)
     | type '|' type               (* union type *)
     | '(' type ')'                (* grouping *)

type_name = IDENT [ generic_args ]
generic_args = '<' type_list '>'
type_list = type { ',' type }

primitive_type = 'i8' | 'i16' | 'i32' | 'i64'
               | 'u8' | 'u16' | 'u32' | 'u64'
               | 'f32' | 'f64' | 'bool'
```

**Type Examples:**
```ritz
i32                     # 32-bit signed integer
*u8                     # pointer to byte
*mut Node               # mutable pointer to Node
&Point                  # reference to Point
&mut i32                # mutable reference to i32
[16]u8                  # array of 16 bytes
[]i32                   # slice of i32
Option<T>               # generic type
HashMap<String, i32>    # generic with multiple params
i32 | null              # nullable integer
```

---

## 4. Statements

```ebnf
block = NEWLINE INDENT stmts DEDENT
      | stmt                        (* single-line block *)

stmts = { stmt }

stmt = let_stmt
     | var_stmt
     | return_stmt
     | if_stmt
     | while_stmt
     | for_stmt
     | match_stmt
     | break_stmt
     | continue_stmt
     | assert_stmt
     | assign_stmt
     | expr_stmt
```

### 4.1 Variable Declarations

```ebnf
let_stmt = 'let' IDENT [ ':' type ] '=' expr NEWLINE
var_stmt = 'var' IDENT ':' type [ '=' expr ] NEWLINE
```

- `let` declares an immutable binding (type can be inferred)
- `var` declares a mutable variable (type required)

**Examples:**
```ritz
let x = 42              # type inferred as i32
let y: i64 = 100        # explicit type
var counter: i32 = 0    # mutable
var buffer: [256]u8     # uninitialized
```

### 4.2 Control Flow

```ebnf
return_stmt = 'return' [ expr ] NEWLINE

if_stmt = 'if' expr block [ else_clause ]
else_clause = 'else' block
            | 'else' if_stmt

while_stmt = 'while' expr block

for_stmt = 'for' IDENT 'in' expr block

break_stmt = 'break' NEWLINE
continue_stmt = 'continue' NEWLINE
```

**Examples:**
```ritz
if x > 0
    return x
else if x < 0
    return -x
else
    return 0

while i < 10
    process(i)
    i += 1

for item in collection
    print(item)
```

### 4.3 Pattern Matching

```ebnf
match_stmt = 'match' expr NEWLINE INDENT match_arms DEDENT

match_arms = { match_arm }
match_arm = pattern '=>' expr NEWLINE
          | pattern '=>' block

pattern = IDENT '(' pattern ')'    (* variant pattern *)
        | IDENT                     (* binding or unit variant *)
        | NUMBER                    (* literal *)
        | 'true' | 'false'          (* boolean literals *)
```

**Example:**
```ritz
match opt
    Some(value) => print(value)
    None => print("nothing")
```

### 4.4 Assignment

```ebnf
assign_stmt = lvalue '=' expr NEWLINE
            | lvalue '+=' expr NEWLINE
            | lvalue '-=' expr NEWLINE
            | lvalue '*=' expr NEWLINE
            | lvalue '/=' expr NEWLINE

lvalue = IDENT
       | '*' expr                   (* dereference *)
       | lvalue '[' expr ']'        (* index *)
       | lvalue '.' IDENT           (* field access *)
```

### 4.5 Assertions

```ebnf
assert_stmt = 'assert' expr [ ',' STRING ] NEWLINE
```

**Examples:**
```ritz
assert x > 0
assert valid, "invariant violated"
```

### 4.6 Expression Statement

```ebnf
expr_stmt = expr NEWLINE
```

---

## 5. Expressions

### 5.1 Precedence Table

From lowest to highest precedence:

| Level | Operators | Associativity | Description |
|-------|-----------|---------------|-------------|
| 1 | `\|\|` | Right | Logical OR |
| 2 | `&&` | Right | Logical AND |
| 3 | `==` `!=` `<` `<=` `>` `>=` | None | Comparison |
| 4 | `\|` | Right | Bitwise OR |
| 5 | `..` | None | Range |
| 6 | `^` | Right | Bitwise XOR |
| 7 | `&` | Right | Bitwise AND |
| 8 | `<<` `>>` | Right | Shift |
| 9 | `+` `-` | Right | Additive |
| 10 | `*` `/` `%` | Right | Multiplicative |
| 11 | `as` | Left | Type cast |
| 12 | `-` `!` `~` `*` `&` `&mut` | Prefix | Unary |
| 13 | `?` | Postfix | Try/propagate |
| 14 | `()` `[]` `.` | Left | Postfix (call, index, field) |

### 5.2 Expression Grammar

```ebnf
expr = or_expr

or_expr = and_expr { '||' and_expr }
and_expr = cmp_expr { '&&' cmp_expr }

cmp_expr = bit_or_expr [ cmp_op bit_or_expr ]
cmp_op = '==' | '!=' | '<' | '<=' | '>' | '>='

bit_or_expr = range_expr { '|' range_expr }
range_expr = bit_xor_expr [ '..' bit_xor_expr ]
bit_xor_expr = bit_and_expr { '^' bit_and_expr }
bit_and_expr = shift_expr { '&' shift_expr }

shift_expr = add_expr { ( '<<' | '>>' ) add_expr }
add_expr = mul_expr { ( '+' | '-' ) mul_expr }
mul_expr = cast_expr { ( '*' | '/' | '%' ) cast_expr }

cast_expr = unary_expr [ 'as' type ]

unary_expr = '-' unary_expr
           | '!' unary_expr
           | '~' unary_expr
           | '*' unary_expr
           | '&' unary_expr
           | '&mut' unary_expr
           | try_expr

try_expr = postfix_expr [ '?' ]

postfix_expr = primary_expr { postfix_op }
postfix_op = '(' [ args ] ')'              (* call *)
           | '[' expr ']'                   (* index *)
           | '.' IDENT [ generic_args ]     (* field/method *)
           | '.' NUMBER                     (* tuple field *)

args = expr { ',' expr }
```

### 5.3 Primary Expressions

```ebnf
primary_expr = NUMBER
             | HEX_NUMBER
             | BIN_NUMBER
             | FLOAT
             | STRING
             | CSTRING
             | SPAN_STRING
             | CHAR
             | 'true' | 'false'
             | 'null'
             | IDENT [ struct_lit ]
             | IDENT generic_args '(' [ args ] ')'   (* generic call *)
             | '(' expr ')'
             | '[' [ array_items ] ']'
             | '[' expr ';' NUMBER ']'               (* array repeat *)
             | if_expr
             | block_expr

struct_lit = '{' field_inits '}'
field_inits = [ field_init { ',' field_init } ]
field_init = IDENT ':' expr

array_items = expr { ',' expr }

if_expr = 'if' expr block else_clause

block_expr = '{' stmts [ expr ] '}'
```

**Expression Examples:**
```ritz
# Arithmetic
1 + 2 * 3           # 7 (precedence)
(1 + 2) * 3         # 9

# Comparisons
x == y && y > 0

# Bitwise
flags | MASK
value & 0xFF
bits << 4

# Cast
ptr as *u8
count as i64

# Unary
-x
!valid
*ptr
&value
&mut array[0]

# Try operator
file.read()?

# Struct literal
Point{x: 10, y: 20}

# Array literal
[1, 2, 3, 4, 5]
[0; 100]            # 100 zeros

# If expression
let max = if a > b
    a
else
    b

# Block expression
let result = {
    let temp = compute()
    temp * 2
}
```

---

## 6. Grammar Summary

### Production Count

| Category | Productions |
|----------|-------------|
| Module level | 10 |
| Functions | 6 |
| Types | 12 |
| Statements | 15 |
| Expressions | 20 |
| **Total** | **~63** |

### Token Count

| Category | Count |
|----------|-------|
| Keywords | 27 |
| Type keywords | 11 |
| Multi-char operators | 17 |
| Single-char operators | 17 |
| Delimiters | 9 |
| Synthesized | 4 |
| **Total** | **~85** |

---

## 7. Design Notes

### 7.1 Indentation-Sensitive Parsing

Ritz uses significant indentation similar to Python, but with stricter rules:

1. **Consistency**: Within a block, all statements must have the same indentation
2. **Spaces preferred**: 4 spaces per level recommended
3. **Tab handling**: Tabs expanded to 4 spaces (implementation-defined)
4. **Single-line blocks**: Allowed after `:` for simple statements

### 7.2 No Semicolons

Statements are terminated by newlines. This requires:
- No multi-line expressions without explicit continuation
- Operators that indicate continuation must end the line (not start next line)

```ritz
# Good
let x = a +
    b + c

# Bad (parse error)
let x = a
    + b + c
```

### 7.3 Union Types

The `|` in type position creates discriminated unions:

```ritz
type Nullable<T> = T | null
type Result<T, E> = T | E
```

### 7.4 Reference vs Pointer

| Syntax | Meaning | Can be null? | Arithmetic? |
|--------|---------|--------------|-------------|
| `&T` | Reference | No | No |
| `&mut T` | Mutable reference | No | No |
| `*T` | Pointer | Yes | Yes |
| `*mut T` | Mutable pointer | Yes | Yes |

---

## Appendix A: Complete EBNF

```ebnf
(* === Module === *)
module = { item } ;
item = [ attrs ] fn_def | struct_def | enum_def | const_def
     | type_alias | trait_def | impl_block | import_stmt | global_var ;

(* === Attributes === *)
attrs = attr { attr } ;
attr = '@' IDENT [ NEWLINE ] ;

(* === Functions === *)
fn_def = 'fn' IDENT [ generic_params ] '(' [ params ] ')' [ return_type ] block
       | 'extern' 'fn' IDENT '(' [ params ] ')' [ return_type ] NEWLINE
       | 'pub' 'fn' IDENT [ generic_params ] '(' [ params ] ')' [ return_type ] block ;
generic_params = '<' IDENT { ',' IDENT } '>' ;
params = param { ',' param } ;
param = IDENT ':' type ;
return_type = '->' type ;

(* === Structures === *)
struct_def = 'struct' IDENT [ generic_params ] NEWLINE INDENT { struct_field } DEDENT ;
struct_field = IDENT ':' type NEWLINE ;

(* === Enumerations === *)
enum_def = 'enum' IDENT [ generic_params ] NEWLINE INDENT { enum_variant } DEDENT ;
enum_variant = IDENT [ '(' type ')' ] NEWLINE ;

(* === Type Aliases === *)
type_alias = 'type' IDENT [ generic_params ] '=' type NEWLINE ;

(* === Traits === *)
trait_def = 'trait' IDENT NEWLINE INDENT { trait_method } DEDENT ;
trait_method = 'fn' IDENT '(' [ params ] ')' [ return_type ] NEWLINE ;

(* === Impl Blocks === *)
impl_block = 'impl' [ generic_params ] type_name [ 'for' type_name ] NEWLINE INDENT { fn_def } DEDENT ;

(* === Imports === *)
import_stmt = 'import' IDENT { '.' IDENT } NEWLINE ;

(* === Constants/Variables === *)
const_def = 'const' IDENT ':' type '=' expr NEWLINE ;
global_var = 'var' IDENT ':' type [ '=' expr ] NEWLINE ;

(* === Types === *)
type = primitive_type | type_name
     | '*' type | '*' 'mut' type | '&' type | '&mut' type
     | '[' NUMBER ']' type | '[' ']' type
     | type '|' type | '(' type ')' ;
type_name = IDENT [ '<' type { ',' type } '>' ] ;
primitive_type = 'i8' | 'i16' | 'i32' | 'i64' | 'u8' | 'u16' | 'u32' | 'u64' | 'f32' | 'f64' | 'bool' ;

(* === Blocks === *)
block = NEWLINE INDENT { stmt } DEDENT | stmt ;

(* === Statements === *)
stmt = let_stmt | var_stmt | return_stmt | if_stmt | while_stmt
     | for_stmt | match_stmt | break_stmt | continue_stmt
     | assert_stmt | assign_stmt | expr_stmt ;

let_stmt = 'let' IDENT [ ':' type ] '=' expr NEWLINE ;
var_stmt = 'var' IDENT ':' type [ '=' expr ] NEWLINE ;
return_stmt = 'return' [ expr ] NEWLINE ;
if_stmt = 'if' expr block [ 'else' ( block | if_stmt ) ] ;
while_stmt = 'while' expr block ;
for_stmt = 'for' IDENT 'in' expr block ;
match_stmt = 'match' expr NEWLINE INDENT { match_arm } DEDENT ;
match_arm = pattern '=>' ( expr NEWLINE | block ) ;
pattern = IDENT [ '(' pattern ')' ] | NUMBER | 'true' | 'false' ;
break_stmt = 'break' NEWLINE ;
continue_stmt = 'continue' NEWLINE ;
assert_stmt = 'assert' expr [ ',' STRING ] NEWLINE ;
assign_stmt = lvalue ( '=' | '+=' | '-=' | '*=' | '/=' ) expr NEWLINE ;
lvalue = IDENT | '*' expr | lvalue '[' expr ']' | lvalue '.' IDENT ;
expr_stmt = expr NEWLINE ;

(* === Expressions === *)
expr = or_expr ;
or_expr = and_expr { '||' and_expr } ;
and_expr = cmp_expr { '&&' cmp_expr } ;
cmp_expr = bit_or_expr [ ( '==' | '!=' | '<' | '<=' | '>' | '>=' ) bit_or_expr ] ;
bit_or_expr = range_expr { '|' range_expr } ;
range_expr = bit_xor_expr [ '..' bit_xor_expr ] ;
bit_xor_expr = bit_and_expr { '^' bit_and_expr } ;
bit_and_expr = shift_expr { '&' shift_expr } ;
shift_expr = add_expr { ( '<<' | '>>' ) add_expr } ;
add_expr = mul_expr { ( '+' | '-' ) mul_expr } ;
mul_expr = cast_expr { ( '*' | '/' | '%' ) cast_expr } ;
cast_expr = unary_expr [ 'as' type ] ;
unary_expr = ( '-' | '!' | '~' | '*' | '&' | '&mut' ) unary_expr | try_expr ;
try_expr = postfix_expr [ '?' ] ;
postfix_expr = primary_expr { '(' [ expr { ',' expr } ] ')' | '[' expr ']' | '.' IDENT [ generic_args ] | '.' NUMBER } ;
primary_expr = NUMBER | HEX_NUMBER | BIN_NUMBER | FLOAT | STRING | CSTRING | SPAN_STRING | CHAR
             | 'true' | 'false' | 'null'
             | IDENT [ '{' [ IDENT ':' expr { ',' IDENT ':' expr } ] '}' ]
             | IDENT generic_args '(' [ expr { ',' expr } ] ')'
             | '(' expr ')' | '[' [ expr { ',' expr } ] ']' | '[' expr ';' NUMBER ']'
             | 'if' expr block 'else' ( block | if_stmt )
             | '{' { stmt } [ expr ] '}' ;
generic_args = '<' type { ',' type } '>' ;
```

---

## Appendix B: Reserved for Future Use

The following are not currently used but may be reserved:

- `async`, `await` - Asynchronous programming
- `yield` - Generators
- `where` - Generic constraints
- `self`, `Self` - Method receivers and associated types
- `super` - Parent module access
- `crate` - Current crate root
- `dyn` - Dynamic dispatch
- `move` - Closure capture mode
- `ref` - Pattern reference binding
- `loop` - Infinite loop
- `try`, `catch`, `throw` - Exception handling (alternative to `?`)

---

*Document version: 1.0*
*Generated from: `ritz.grammar`*
*Last updated: 2026-02-13*
