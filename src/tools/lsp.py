"""
Aerix Language Server Protocol (LSP) Daemon (arx lsp)
Implements standard JSON-RPC 2.0 language server protocol v3.17 over stdio.
Provides live diagnostics, completions, hover info, definition lookups,
and automatic formatting for Antigravity IDE, VS Code, Neovim, and Zed.
"""

import sys
import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple, BinaryIO

from src.frontend.tokens import TokenType, KEYWORDS
from src.frontend.lexer import Lexer, LexerError
from src.frontend.parser import Parser, ParserError
from src.frontend.ast_nodes import (
    ProgramNode, FunctionDefNode, ClassDefNode, VarDeclNode,
    EnumDefNode, TraitDefNode, ASTNode
)
from src.middle.semantic import SemanticAnalyzer, SemanticError
from src.tools.formatter import AerixFormatter
from src.tools.linter import AerixLinter

LSP_VERSION = "1.0.84-alpha"

# LSP CompletionItemKind constants
KIND_TEXT = 1
KIND_METHOD = 2
KIND_FUNCTION = 3
KIND_CONSTRUCTOR = 4
KIND_FIELD = 5
KIND_VARIABLE = 6
KIND_CLASS = 7
KIND_INTERFACE = 8
KIND_MODULE = 9
KIND_PROPERTY = 10
KIND_UNIT = 11
KIND_VALUE = 12
KIND_ENUM = 13
KIND_KEYWORD = 14
KIND_SNIPPET = 15

# Standard Aerix Keyword & Built-in Hover Documentation Cards
HOVER_DOCS = {
    "fn": "**Keyword `fn`** — Defines a function or method.\n\n```aerix\nfn calculate_damage(atk: i64, def: i64) -> i64 {\n    return atk - def\n}\n```\nSupports arrow expression bodies (`=> expr`).",
    "class": "**Keyword `class`** — Declares an object-oriented class.\n\n```aerix\nclass Warrior {\n    pub name: str\n    init(name: str) { self.name = name }\n}\n```\nStack-allocated by default with automatic cache-conscious struct packing.",
    "guard": "**Keyword `guard`** — Precondition assertion flow control.\n\n```aerix\nguard condition else {\n    return false\n}\n```\nMandates exiting scope if condition evaluates to false, flattening nested pyramids.",
    "match": "**Keyword `match`** — Exhaustive pattern matching.\n\n```aerix\nmatch packet {\n    Ping => println(\"Pong\"),\n    Data(bytes, size) => process(bytes)\n}\n```\nStatically verifies all enum variant branches at compile time.",
    "enum": "**Keyword `enum`** — Tagged algebraic data type.\n\n```aerix\nenum Packet {\n    Ping\n    Data(payload: str, size: usize)\n}\n```\nLowered to a memory-efficient 1-byte tagged C union.",
    "extend": "**Keyword `extend`** — Zero-cost static type extension.\n\n```aerix\nextend str {\n    pub fn is_empty() -> bool => self.len() == 0\n}\n```\nAdds methods to existing types without subclassing or wrapping overhead.",
    "defer": "**Keyword `defer`** — Deterministic resource cleanup.\n\n```aerix\nlet file = open_file(\"log.txt\")\ndefer file.close()\n```\nExecutes in guaranteed LIFO order when current stack scope exits.",
    "let": "**Keyword `let`** — Declares an immutable local variable.\n\n```aerix\nlet max_retries = 5\n```\nReassignment is prohibited at compile time.",
    "mut": "**Keyword `mut`** — Declares a mutable variable.\n\n```aerix\nlet mut counter = 0\ncounter += 1\n```",
    "prop": "**Keyword `prop`** — Declares a reactive property.\n\n```aerix\npub prop hp: i64 {\n    get => self.raw_hp\n    set(val) { self.raw_hp = val }\n}\n```",
    "pub": "**Keyword `pub`** — Public visibility modifier.",
    "priv": "**Keyword `priv`** — Private visibility modifier.",
    "LinearArena": "**Built-in `LinearArena`** — High-speed linear bump allocator.\n\n```aerix\nmut arena = LinearArena(1024 * 1024)\ndefer arena.reset()\n```\nO(1) instant memory recycling without OS heap fragmentation.",
    "println": "**Built-in `println`** — Prints formatted text to stdout followed by a newline.",
    "print": "**Built-in `print`** — Prints text to stdout without trailing newline.",
    "eprintln": "**Built-in `eprintln`** — Prints formatted error text to standard error.",
    "input": "**Built-in `input`** — Reads user terminal input with type-directed dispatch.",
    "typeof": "**Built-in `typeof`** — Evaluates symbol type identifier at compile time.",
    "|>": "**Pipeline Operator `|>`** — Pipes previous value into next function call.\n\n```aerix\nvalue |> process() |> println()\n```",
    "~>": "**Fluent Cascade Operator `~>`** — Chains mutations while threading receiver instance forward.\n\n```aerix\nship ~> recharge(50) ~> cloak()\n```",
    "spawn": "**Keyword `spawn`** — Asynchronously evaluates a function call on a native operating system thread.\n\n```aerix\nlet t = spawn worker(ch, 42)\narx_thread_join(t)\n```",
    "Channel": "**Class `Channel<T>`** — Thread-safe bounded communication channel ring buffer.\n\n```aerix\nmut ch = Channel<i64>(8)\nch.send(42)\nlet val = ch.recv()\n```",
    "arx_channel_new": "**Built-in `arx_channel_new(cap: i64) -> i64`** — Allocates a thread-safe bounded channel with backpressure condition variables.",
    "arx_channel_send": "**Built-in `arx_channel_send(ch: i64, val: i64)`** — Enqueues an item into a bounded channel, blocking when full.",
    "arx_channel_recv": "**Built-in `arx_channel_recv(ch: i64) -> i64`** — Dequeues an item from a bounded channel, blocking when empty.",
    "arx_channel_close": "**Built-in `arx_channel_close(ch: i64)`** — Closes a channel and wakes all waiting worker threads.",
    "arx_channel_free": "**Built-in `arx_channel_free(ch: i64)`** — Closes channel, destroys mutexes, and frees memory.",
    "arx_thread_join": "**Built-in `arx_thread_join(handle: i64)`** — Synchronously waits for a spawned worker thread to terminate.",
    "arx_sleep_ms": "**Built-in `arx_sleep_ms(ms: i64)`** — Puts calling thread to sleep for specified milliseconds.",
}

PRIMITIVE_TYPES = [
    "i8", "i16", "i32", "i64", "int",
    "u8", "u16", "u32", "u64", "uint", "usize",
    "f32", "f64", "float", "f32x4",
    "bool", "char", "str", "void", "null"
]


class AerixLanguageServer:
    def __init__(self, in_stream: Optional[BinaryIO] = None, out_stream: Optional[BinaryIO] = None):
        self.in_stream = in_stream or (sys.stdin.buffer if hasattr(sys.stdin, "buffer") else sys.stdin)
        self.out_stream = out_stream or (sys.stdout.buffer if hasattr(sys.stdout, "buffer") else sys.stdout)
        self.documents: Dict[str, str] = {}
        self.is_running = True
        self.formatter = AerixFormatter()
        self.linter = AerixLinter()

    def run(self):
        """Main JSON-RPC request processing loop."""
        while self.is_running:
            try:
                payload = self._read_message()
                if not payload:
                    break
                self._handle_message(payload)
            except EOFError:
                break
            except Exception as e:
                # Keep server alive on unexpected handler errors
                pass

    def _read_message(self) -> Optional[Dict[str, Any]]:
        """Reads a JSON-RPC 2.0 message with Content-Length header."""
        content_length = None
        while True:
            line_bytes = self.in_stream.readline()
            if not line_bytes:
                return None
            line = line_bytes.decode("latin1").strip()
            if not line:
                # Empty line marks end of headers
                break
            if line.lower().startswith("content-length:"):
                parts = line.split(":", 1)
                content_length = int(parts[1].strip())

        if content_length is None:
            return None

        body_bytes = self.in_stream.read(content_length)
        if not body_bytes or len(body_bytes) < content_length:
            return None

        return json.loads(body_bytes.decode("utf-8"))

    def send_response(self, req_id: Any, result: Any = None, error: Optional[Dict[str, Any]] = None):
        """Sends a JSON-RPC response."""
        response = {
            "jsonrpc": "2.0",
            "id": req_id
        }
        if error:
            response["error"] = error
        else:
            response["result"] = result
        self._write_message(response)

    def send_notification(self, method: str, params: Any):
        """Sends a JSON-RPC notification."""
        msg = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self._write_message(msg)

    def _write_message(self, data: Dict[str, Any]):
        """Encodes and writes message with Content-Length header."""
        body = json.dumps(data, ensure_ascii=False)
        body_bytes = body.encode("utf-8")
        header = f"Content-Length: {len(body_bytes)}\r\n\r\n".encode("latin1")
        self.out_stream.write(header)
        self.out_stream.write(body_bytes)
        self.out_stream.flush()

    def _handle_message(self, msg: Dict[str, Any]):
        """Routes message to corresponding handler."""
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize":
            self._handle_initialize(req_id, params)
        elif method == "initialized":
            pass # Client acknowledgment
        elif method == "shutdown":
            self.send_response(req_id, None)
        elif method == "exit":
            self.is_running = False
        elif method == "textDocument/didOpen":
            self._handle_did_open(params)
        elif method == "textDocument/didChange":
            self._handle_did_change(params)
        elif method == "textDocument/didClose":
            self._handle_did_close(params)
        elif method == "textDocument/hover":
            self._handle_hover(req_id, params)
        elif method == "textDocument/definition":
            self._handle_definition(req_id, params)
        elif method == "textDocument/completion":
            self._handle_completion(req_id, params)
        elif method == "textDocument/formatting":
            self._handle_formatting(req_id, params)
        elif req_id is not None:
            # Method not found
            self.send_response(req_id, error={"code": -32601, "message": f"Method {method} not found"})

    def _handle_initialize(self, req_id: Any, params: Dict[str, Any]):
        capabilities = {
            "capabilities": {
                "textDocumentSync": 1,  # Full sync
                "hoverProvider": True,
                "definitionProvider": True,
                "completionProvider": {
                    "resolveProvider": False,
                    "triggerCharacters": [".", ":", ">", " "]
                },
                "documentFormattingProvider": True
            },
            "serverInfo": {
                "name": "aerix-lsp",
                "version": LSP_VERSION
            }
        }
        self.send_response(req_id, capabilities)

    def _handle_did_open(self, params: Dict[str, Any]):
        doc = params.get("textDocument", {})
        uri = doc.get("uri", "")
        text = doc.get("text", "")
        self.documents[uri] = text
        self.publish_diagnostics(uri, text)

    def _handle_did_change(self, params: Dict[str, Any]):
        doc = params.get("textDocument", {})
        uri = doc.get("uri", "")
        changes = params.get("contentChanges", [])
        if changes:
            text = changes[0].get("text", "")
            self.documents[uri] = text
            self.publish_diagnostics(uri, text)

    def _handle_did_close(self, params: Dict[str, Any]):
        doc = params.get("textDocument", {})
        uri = doc.get("uri", "")
        if uri in self.documents:
            del self.documents[uri]

    def publish_diagnostics(self, uri: str, text: str):
        """Runs lexer, parser, semantic analyzer and linter to emit LSP diagnostics."""
        diagnostics = []

        try:
            # 1. Lexer Stage
            lexer = Lexer(text, uri)
            tokens = lexer.tokenize()

            # 2. Parser Stage
            parser = Parser(tokens, text.splitlines())
            ast = parser.parse()

            from src.middle.monomorphizer import GenericMonomorphizer
            ast = GenericMonomorphizer().monomorphize(ast)

            # 3. Semantic Stage
            analyzer = SemanticAnalyzer()
            analyzer.analyze(ast)

            # 4. Lint Stage (Warnings)
            warnings = self.linter.lint_source(text, uri)
            for w in warnings:
                diagnostics.append({
                    "range": {
                        "start": {"line": max(0, w.line - 1), "character": max(0, w.col - 1)},
                        "end": {"line": max(0, w.line - 1), "character": max(0, w.col + 5)}
                    },
                    "severity": 2, # Warning
                    "code": w.code,
                    "source": "aerix-lint",
                    "message": w.message
                })

        except LexerError as le:
            diagnostics.append({
                "range": {
                    "start": {"line": max(0, le.line - 1), "character": max(0, le.col - 1)},
                    "end": {"line": max(0, le.line - 1), "character": max(0, le.col + 1)}
                },
                "severity": 1, # Error
                "source": "aerix-lexer",
                "message": le.message
            })
        except ParserError as pe:
            if hasattr(pe, "errors") and pe.errors:
                for err in pe.errors:
                    err_tok = getattr(err, "token", None)
                    err_val = getattr(err_tok, "value", "") if err_tok else ""
                    err_len = max(1, len(str(err_val))) if err_val else 1
                    err_line = getattr(err, "line", 1)
                    err_col = getattr(err, "col", 1)
                    diagnostics.append({
                        "range": {
                            "start": {"line": max(0, err_line - 1), "character": max(0, err_col - 1)},
                            "end": {"line": max(0, err_line - 1), "character": max(0, err_col + err_len)}
                        },
                        "severity": 1,
                        "source": "aerix-parser",
                        "message": getattr(err, "message", str(err))
                    })
            else:
                diagnostics.append({
                    "range": {
                        "start": {"line": max(0, pe.line - 1), "character": max(0, pe.col - 1)},
                        "end": {"line": max(0, pe.line - 1), "character": max(0, pe.col + max(1, len(str(getattr(pe.token, "value", "") or ""))))}
                    },
                    "severity": 1,
                    "source": "aerix-parser",
                    "message": pe.message
                })
        except SemanticError as se:
            diagnostics.append({
                "range": {
                    "start": {"line": max(0, se.line - 1), "character": max(0, se.col - 1)},
                    "end": {"line": max(0, se.line - 1), "character": max(0, se.col + 1)}
                },
                "severity": 1,
                "source": "aerix-semantic",
                "message": se.message
            })
        except Exception as e:
            pass

        self.send_notification("textDocument/publishDiagnostics", {
            "uri": uri,
            "diagnostics": diagnostics
        })

    def _get_word_at_position(self, text: str, line: int, char: int) -> str:
        """Extracts identifier or operator under cursor coordinate."""
        lines = text.splitlines()
        if line < 0 or line >= len(lines):
            return ""
        l = lines[line]
        if char < 0 or char > len(l):
            return ""

        # Check multi-char operators first
        for op in ["~>", "|>", "==", "!=", "<=", ">=", "->", "=>"]:
            start_idx = l.find(op)
            if start_idx != -1 and start_idx <= char <= start_idx + len(op):
                return op

        # Regex match word characters
        start = char
        while start > 0 and (l[start - 1].isalnum() or l[start - 1] == "_"):
            start -= 1
        end = char
        while end < len(l) and (l[end].isalnum() or l[end] == "_"):
            end += 1

        return l[start:end]

    def _handle_hover(self, req_id: Any, params: Dict[str, Any]):
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line = pos.get("line", 0)
        char = pos.get("character", 0)

        text = self.documents.get(uri, "")
        word = self._get_word_at_position(text, line, char)

        if not word:
            self.send_response(req_id, None)
            return

        # 1. Check static built-in / keyword hover documentation
        if word in HOVER_DOCS:
            self.send_response(req_id, {
                "contents": {
                    "kind": "markdown",
                    "value": HOVER_DOCS[word]
                }
            })
            return

        # 2. Check primitive types
        if word in PRIMITIVE_TYPES:
            self.send_response(req_id, {
                "contents": {
                    "kind": "markdown",
                    "value": f"**Aerix Primitive Type `{word}`**\n\nDirect hardware-mapped zero-overhead primitive."
                }
            })
            return

        # 3. Dynamic AST symbol lookup
        try:
            lexer = Lexer(text, uri)
            tokens = lexer.tokenize()
            parser = Parser(tokens, text.splitlines())
            ast = parser.parse()

            for stmt in ast.declarations:
                if isinstance(stmt, FunctionDefNode) and stmt.name == word:
                    params_str = ", ".join(f"{p.name}: {p.type_name}" for p in stmt.params)
                    self.send_response(req_id, {
                        "contents": {
                            "kind": "markdown",
                            "value": f"**Function** `fn {stmt.name}({params_str}) -> {stmt.return_type}`\n\n*User-defined Aerix function.*"
                        }
                    })
                    return
                elif isinstance(stmt, ClassDefNode) and stmt.name == word:
                    fields_info = [f"  pub {f.name}: {f.type_name}" for f in stmt.fields]
                    field_str = "\n".join(fields_info) if fields_info else "  (none)"
                    self.send_response(req_id, {
                        "contents": {
                            "kind": "markdown",
                            "value": f"**Class** `class {stmt.name}`\n\n**Fields:**\n```aerix\n{field_str}\n```\n*Cache-packed value struct.*"
                        }
                    })
                    return
                elif isinstance(stmt, EnumDefNode) and stmt.name == word:
                    variants_str = ", ".join(v.name for v in stmt.variants)
                    self.send_response(req_id, {
                        "contents": {
                            "kind": "markdown",
                            "value": f"**Enum** `enum {stmt.name}`\n\nVariants: `{variants_str}`"
                        }
                    })
                    return
        except Exception:
            pass

        self.send_response(req_id, None)

    def _handle_definition(self, req_id: Any, params: Dict[str, Any]):
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line = pos.get("line", 0)
        char = pos.get("character", 0)

        text = self.documents.get(uri, "")
        word = self._get_word_at_position(text, line, char)

        if not word:
            self.send_response(req_id, None)
            return

        try:
            lexer = Lexer(text, uri)
            tokens = lexer.tokenize()
            parser = Parser(tokens, text.splitlines())
            ast = parser.parse()

            for stmt in ast.declarations:
                if (isinstance(stmt, (FunctionDefNode, ClassDefNode, EnumDefNode)) and stmt.name == word) or \
                   (isinstance(stmt, VarDeclNode) and stmt.name == word):
                    self.send_response(req_id, {
                        "uri": uri,
                        "range": {
                            "start": {"line": max(0, stmt.line - 1), "character": max(0, stmt.col - 1)},
                            "end": {"line": max(0, stmt.line - 1), "character": max(0, stmt.col - 1 + len(word))}
                        }
                    })
                    return
        except Exception:
            pass

        self.send_response(req_id, None)

    def _handle_completion(self, req_id: Any, params: Dict[str, Any]):
        uri = params.get("textDocument", {}).get("uri", "")
        text = self.documents.get(uri, "")
        items = []

        # 1. Keywords
        for kw in KEYWORDS.keys():
            items.append({
                "label": kw,
                "kind": KIND_KEYWORD,
                "detail": f"Aerix keyword: {kw}"
            })

        # 2. Primitives
        for prim in PRIMITIVE_TYPES:
            items.append({
                "label": prim,
                "kind": KIND_CLASS,
                "detail": f"Primitive Type: {prim}"
            })

        # 3. Built-in functions
        builtins = ["println", "print", "eprintln", "input", "typeof", "LinearArena"]
        for b in builtins:
            items.append({
                "label": b,
                "kind": KIND_FUNCTION,
                "detail": f"Aerix standard builtin: {b}"
            })

        # 4. In-document symbols
        try:
            lexer = Lexer(text, uri)
            tokens = lexer.tokenize()
            parser = Parser(tokens, text.splitlines())
            ast = parser.parse()
            for stmt in ast.declarations:
                if isinstance(stmt, FunctionDefNode):
                    items.append({
                        "label": stmt.name,
                        "kind": KIND_FUNCTION,
                        "detail": f"fn {stmt.name}() -> {stmt.return_type}"
                    })
                elif isinstance(stmt, ClassDefNode):
                    items.append({
                        "label": stmt.name,
                        "kind": KIND_CLASS,
                        "detail": f"class {stmt.name}"
                    })
                elif isinstance(stmt, EnumDefNode):
                    items.append({
                        "label": stmt.name,
                        "kind": KIND_ENUM,
                        "detail": f"enum {stmt.name}"
                    })
                elif isinstance(stmt, VarDeclNode):
                    items.append({
                        "label": stmt.name,
                        "kind": KIND_VARIABLE,
                        "detail": f"var {stmt.name}"
                    })
        except Exception:
            pass


        self.send_response(req_id, {"isIncomplete": False, "items": items})

    def _handle_formatting(self, req_id: Any, params: Dict[str, Any]):
        uri = params.get("textDocument", {}).get("uri", "")
        text = self.documents.get(uri, "")
        if not text:
            self.send_response(req_id, [])
            return

        formatted = self.formatter.format_source(text)
        lines = text.splitlines()
        last_line = len(lines)
        last_char = len(lines[-1]) if lines else 0

        edits = [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": last_line, "character": last_char}
                },
                "newText": formatted
            }
        ]
        self.send_response(req_id, edits)


def main():
    """Runs the Aerix LSP server in stdio mode."""
    server = AerixLanguageServer()
    server.run()


if __name__ == "__main__":
    main()
