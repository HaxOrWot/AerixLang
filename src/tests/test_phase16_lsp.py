"""
Tests for Phase 16: Native Language Server Protocol (LSP) Daemon (arx lsp)
Validates JSON-RPC framing, diagnostics, completions, hover info, definition lookups, and formatting.
"""

import unittest
import io
import json
from src.tools.lsp import AerixLanguageServer


class MockLSPClient:
    """Helper client to simulate an IDE sending JSON-RPC messages to AerixLanguageServer."""
    def __init__(self):
        self.in_stream = io.BytesIO()
        self.out_stream = io.BytesIO()
        self.server = AerixLanguageServer(self.in_stream, self.out_stream)

    def send_message(self, msg: dict):
        body = json.dumps(msg).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("latin1")
        # Save current position in in_stream to append
        pos = self.in_stream.tell()
        self.in_stream.seek(0, io.SEEK_END)
        self.in_stream.write(header + body)
        self.in_stream.seek(pos)

    def read_responses(self) -> list:
        responses = []
        raw = self.out_stream.getvalue()
        stream = io.BytesIO(raw)
        while True:
            content_length = None
            while True:
                line_bytes = stream.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("latin1").strip()
                if not line:
                    break
                if line.lower().startswith("content-length:"):
                    content_length = int(line.split(":", 1)[1].strip())
            if content_length is None:
                break
            body = stream.read(content_length)
            responses.append(json.loads(body.decode("utf-8")))
        return responses


class TestPhase16LSP(unittest.TestCase):
    def test_initialize_and_capabilities(self):
        client = MockLSPClient()
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"processId": 1234, "rootUri": "file:///workspace"}
        }
        client.server._handle_message(init_req)
        responses = client.read_responses()
        self.assertEqual(len(responses), 1)
        resp = responses[0]
        self.assertEqual(resp["id"], 1)
        caps = resp["result"]["capabilities"]
        self.assertTrue(caps["hoverProvider"])
        self.assertTrue(caps["definitionProvider"])
        self.assertTrue(caps["documentFormattingProvider"])
        self.assertEqual(resp["result"]["serverInfo"]["name"], "aerix-lsp")

    def test_diagnostics_clean_and_syntax_error(self):
        client = MockLSPClient()
        uri = "file:///test.arx"

        # 1. Open valid file -> zero diagnostics
        clean_code = "fn main() {\n    let x = 10\n    println(\"x is {x}\")\n}\n"
        client.server._handle_did_open({
            "textDocument": {"uri": uri, "text": clean_code, "version": 1}
        })
        responses = client.read_responses()
        self.assertEqual(len(responses), 1)
        diag_msg = responses[0]
        self.assertEqual(diag_msg["method"], "textDocument/publishDiagnostics")
        self.assertEqual(len(diag_msg["params"]["diagnostics"]), 0)

        # 2. Syntax error -> diagnostics emitted
        bad_code = "fn main() {\n    let x =\n}\n"
        client.server._handle_did_change({
            "textDocument": {"uri": uri, "version": 2},
            "contentChanges": [{"text": bad_code}]
        })
        responses2 = client.read_responses()
        latest = responses2[-1]
        self.assertEqual(latest["method"], "textDocument/publishDiagnostics")
        diags = latest["params"]["diagnostics"]
        self.assertTrue(len(diags) > 0)
        self.assertEqual(diags[0]["severity"], 1)

    def test_hover_information(self):
        client = MockLSPClient()
        uri = "file:///hover_test.arx"
        code = "fn calculate_power(core: i64) -> i64 {\n    guard core > 0 else { return 0 }\n    return core * 2\n}\n"
        client.server.documents[uri] = code

        # Hover over 'guard'
        client.server._handle_hover(2, {
            "textDocument": {"uri": uri},
            "position": {"line": 1, "character": 6}
        })
        # Hover over user function 'calculate_power'
        client.server._handle_hover(3, {
            "textDocument": {"uri": uri},
            "position": {"line": 0, "character": 4}
        })

        responses = client.read_responses()
        self.assertEqual(len(responses), 2)
        # Guard hover
        self.assertIn("Keyword `guard`", responses[0]["result"]["contents"]["value"])
        # Function signature hover
        self.assertIn("fn calculate_power(core: i64) -> i64", responses[1]["result"]["contents"]["value"])

    def test_definition_and_completion(self):
        client = MockLSPClient()
        uri = "file:///def_test.arx"
        code = "fn target_fn() {\n    println(\"Target\")\n}\n\nfn main() {\n    target_fn()\n}\n"
        client.server.documents[uri] = code

        # Go to definition of 'target_fn' at line 5, char 6
        client.server._handle_definition(10, {
            "textDocument": {"uri": uri},
            "position": {"line": 5, "character": 6}
        })
        # Completions at line 5
        client.server._handle_completion(11, {
            "textDocument": {"uri": uri},
            "position": {"line": 5, "character": 0}
        })

        responses = client.read_responses()
        self.assertEqual(len(responses), 2)

        # Definition check
        def_res = responses[0]["result"]
        self.assertIsNotNone(def_res)
        self.assertEqual(def_res["uri"], uri)
        self.assertEqual(def_res["range"]["start"]["line"], 0) # Defined at line 1 (0-indexed line 0)

        # Completion check
        comp_res = responses[1]["result"]
        labels = [item["label"] for item in comp_res["items"]]
        self.assertIn("fn", labels)
        self.assertIn("target_fn", labels)
        self.assertIn("println", labels)
        self.assertIn("i64", labels)

    def test_formatting_provider(self):
        client = MockLSPClient()
        uri = "file:///fmt_test.arx"
        unformatted = "fn main(){\nlet x=10\nprintln(\"x\")\n}\n"
        client.server.documents[uri] = unformatted

        client.server._handle_formatting(20, {
            "textDocument": {"uri": uri},
            "options": {"tabSize": 4, "insertSpaces": True}
        })

        responses = client.read_responses()
        self.assertEqual(len(responses), 1)
        edits = responses[0]["result"]
        self.assertEqual(len(edits), 1)
        new_text = edits[0]["newText"]
        self.assertIn("    let x=10", new_text)



if __name__ == "__main__":
    unittest.main()
