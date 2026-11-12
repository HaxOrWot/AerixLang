/**
 * Aerix Language Client (Thin LSP Bridge)
 * Delegates all syntax highlighting (Semantic Tokens), diagnostics, completions,
 * hover, signature help, go-to-definition, symbols, inlay hints, codeLens, and
 * formatting directly to the native compiler LSP (`arx lsp`).
 */

const vscode = require('vscode');
const cp = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const TOKEN_TYPES = [
    'comment', 'keyword', 'string', 'number', 'operator',
    'type', 'class', 'enum', 'enumMember', 'function',
    'method', 'property', 'parameter', 'variable', 'namespace', 'macro'
];

const TOKEN_MODIFIERS = [
    'declaration', 'definition', 'readonly', 'static', 'defaultLibrary'
];

const SEMANTIC_LEGEND = new vscode.SemanticTokensLegend(TOKEN_TYPES, TOKEN_MODIFIERS);

function resolveAerixBinary() {
    const cfgPath = (vscode.workspace.getConfiguration('aerix').get('executablePath') || '').trim();
    if (cfgPath && fs.existsSync(cfgPath)) return cfgPath;

    const exe = process.platform === 'win32' ? '.exe' : '';
    const candidates = [
        path.join(os.homedir(), '.aerix', 'bin', `arx${exe}`),
        path.join(os.homedir(), '.aerix', 'bin', `arxc${exe}`)
    ];
    for (const c of candidates) {
        if (fs.existsSync(c)) return c;
    }
    return 'arx';
}

function toLspPos(pos) {
    return { line: pos.line, character: pos.character };
}

function toVsRange(r) {
    if (!r || !r.start || !r.end) return new vscode.Range(0, 0, 0, 0);
    return new vscode.Range(r.start.line || 0, r.start.character || 0, r.end.line || 0, r.end.character || 0);
}

function toDocSymbol(s) {
    const ds = new vscode.DocumentSymbol(
        s.name || '',
        s.detail || '',
        s.kind || vscode.SymbolKind.Variable,
        toVsRange(s.range),
        toVsRange(s.selectionRange || s.range)
    );
    if (Array.isArray(s.children)) {
        ds.children = s.children.map(toDocSymbol);
    }
    return ds;
}

class AerixLspClient {
    constructor(diagnostics, output) {
        this.diagnostics = diagnostics;
        this.output = output;
        this.proc = null;
        this.nextId = 1;
        this.pending = new Map();
        this.rxBuf = Buffer.alloc(0);
        this.ready = null;
    }

    start() {
        if (this.ready) return this.ready;
        this.ready = this._spawnAndInit();
        return this.ready;
    }

    async _spawnAndInit() {
        const bin = resolveAerixBinary();
        this.output.appendLine(`[Aerix LSP] Starting: ${bin} lsp`);
        const proc = cp.spawn(bin, ['lsp'], { stdio: ['pipe', 'pipe', 'pipe'] });
        this.proc = proc;

        proc.stdout.on('data', (chunk) => this._onData(chunk));
        proc.stderr.on('data', (chunk) => this.output.appendLine(`[stderr] ${chunk.toString('utf8').trimEnd()}`));
        proc.on('exit', (code) => {
            this.output.appendLine(`[Aerix LSP] Exited with code ${code}`);
            for (const [, p] of this.pending) p.resolve(null);
            this.pending.clear();
            this.proc = null;
            this.ready = null;
        });
        proc.on('error', (err) => {
            this.output.appendLine(`[Aerix LSP] Failed to start '${bin}': ${err.message}`);
            for (const [, p] of this.pending) p.resolve(null);
            this.pending.clear();
            this.proc = null;
            this.ready = null;
        });

        const folders = vscode.workspace.workspaceFolders;
        await this.request('initialize', {
            processId: process.pid,
            rootUri: folders && folders.length ? folders[0].uri.toString() : null,
            capabilities: {}
        });
        this.notify('initialized', {});
        for (const doc of vscode.workspace.textDocuments) {
            if (doc.languageId === 'aerix') {
                this.notify('textDocument/didOpen', {
                    textDocument: {
                        uri: doc.uri.toString(),
                        languageId: 'aerix',
                        version: doc.version,
                        text: doc.getText()
                    }
                });
            }
        }
    }

    _send(payload) {
        if (!this.proc || !this.proc.stdin.writable) return;
        const json = JSON.stringify(payload);
        const bytes = Buffer.byteLength(json, 'utf8');
        this.proc.stdin.write(`Content-Length: ${bytes}\r\n\r\n${json}`, 'utf8');
    }

    async request(method, params) {
        if (!this.proc && method !== 'initialize') {
            await this.start();
        }
        if (!this.proc) return null;
        const id = this.nextId++;
        return new Promise((resolve) => {
            const timer = setTimeout(() => {
                this.pending.delete(id);
                resolve(null);
            }, 5000);
            this.pending.set(id, {
                resolve: (val) => {
                    clearTimeout(timer);
                    resolve(val);
                }
            });
            this._send({ jsonrpc: '2.0', id, method, params });
        });
    }

    notify(method, params) {
        if (!this.proc) return;
        this._send({ jsonrpc: '2.0', method, params });
    }

    _onData(chunk) {
        this.rxBuf = Buffer.concat([this.rxBuf, chunk]);
        while (true) {
            const sep = this.rxBuf.indexOf('\r\n\r\n');
            if (sep === -1) break;
            const hdr = this.rxBuf.slice(0, sep).toString('latin1');
            const m = /content-length:\s*(\d+)/i.exec(hdr);
            if (!m) {
                this.rxBuf = this.rxBuf.slice(sep + 4);
                continue;
            }
            const len = parseInt(m[1], 10);
            const total = sep + 4 + len;
            if (this.rxBuf.length < total) break;
            const body = this.rxBuf.slice(sep + 4, total).toString('utf8');
            this.rxBuf = this.rxBuf.slice(total);
            this._handleMessage(body);
        }
    }

    _handleMessage(raw) {
        let msg;
        try { msg = JSON.parse(raw); } catch { return; }
        if (Object.prototype.hasOwnProperty.call(msg, 'id')) {
            const entry = this.pending.get(msg.id);
            if (entry) {
                this.pending.delete(msg.id);
                entry.resolve(msg.error ? null : msg.result);
            }
            return;
        }
        if (msg.method === 'textDocument/publishDiagnostics' && msg.params) {
            const uri = vscode.Uri.parse(msg.params.uri);
            const list = (msg.params.diagnostics || []).map((d) => new vscode.Diagnostic(
                toVsRange(d.range),
                d.message || 'Aerix error',
                d.severity === 2 ? vscode.DiagnosticSeverity.Warning : vscode.DiagnosticSeverity.Error
            ));
            this.diagnostics.set(uri, list);
        }
    }

    async stop() {
        if (!this.proc) return;
        try {
            await this.request('shutdown', null);
            this.notify('exit', null);
        } catch {
            // ignore
        }
        if (this.proc) this.proc.kill();
        this.proc = null;
    }
}

function activate(context) {
    const diagnostics = vscode.languages.createDiagnosticCollection('aerix');
    const output = vscode.window.createOutputChannel('Aerix Language Server');
    const client = new AerixLspClient(diagnostics, output);
    client.start();

    context.subscriptions.push(diagnostics, output, { dispose: () => client.stop() });

    context.subscriptions.push(
        vscode.workspace.onDidOpenTextDocument((doc) => {
            if (doc.languageId === 'aerix') {
                client.start().then(() => client.notify('textDocument/didOpen', {
                    textDocument: { uri: doc.uri.toString(), languageId: 'aerix', version: doc.version, text: doc.getText() }
                }));
            }
        }),
        vscode.workspace.onDidChangeTextDocument((ev) => {
            if (ev.document.languageId === 'aerix') {
                client.start().then(() => client.notify('textDocument/didChange', {
                    textDocument: { uri: ev.document.uri.toString(), version: ev.document.version },
                    contentChanges: [{ text: ev.document.getText() }]
                }));
            }
        }),
        vscode.workspace.onDidSaveTextDocument((doc) => {
            if (doc.languageId === 'aerix') {
                client.start().then(() => client.notify('textDocument/didSave', {
                    textDocument: { uri: doc.uri.toString() },
                    text: doc.getText()
                }));
            }
        }),
        vscode.workspace.onDidCloseTextDocument((doc) => {
            if (doc.languageId === 'aerix') {
                client.notify('textDocument/didClose', { textDocument: { uri: doc.uri.toString() } });
                diagnostics.delete(doc.uri);
            }
        })
    );

    const sel = { language: 'aerix', scheme: 'file' };

    context.subscriptions.push(
        vscode.languages.registerDocumentSemanticTokensProvider(sel, {
            async provideDocumentSemanticTokens(doc) {
                const res = await client.request('textDocument/semanticTokens/full', {
                    textDocument: { uri: doc.uri.toString() }
                });
                if (!res || !Array.isArray(res.data)) return new vscode.SemanticTokens(new Uint32Array(0));
                return new vscode.SemanticTokens(new Uint32Array(res.data));
            }
        }, SEMANTIC_LEGEND),

        vscode.languages.registerCompletionItemProvider(sel, {
            async provideCompletionItems(doc, pos) {
                const res = await client.request('textDocument/completion', {
                    textDocument: { uri: doc.uri.toString() },
                    position: toLspPos(pos)
                });
                const items = res && Array.isArray(res.items) ? res.items : (Array.isArray(res) ? res : []);
                return items.map((it) => {
                    const ci = new vscode.CompletionItem(it.label, it.kind || vscode.CompletionItemKind.Text);
                    if (it.detail) ci.detail = it.detail;
                    if (it.documentation && it.documentation.value) {
                        ci.documentation = new vscode.MarkdownString(it.documentation.value);
                    }
                    if (it.insertText) ci.insertText = new vscode.SnippetString(it.insertText);
                    return ci;
                });
            }
        }, '.', '>', ':'),

        vscode.languages.registerHoverProvider(sel, {
            async provideHover(doc, pos) {
                const res = await client.request('textDocument/hover', {
                    textDocument: { uri: doc.uri.toString() },
                    position: toLspPos(pos)
                });
                if (!res || !res.contents) return null;
                const val = typeof res.contents === 'string' ? res.contents : (res.contents.value || '');
                return val ? new vscode.Hover(new vscode.MarkdownString(val)) : null;
            }
        }),

        vscode.languages.registerSignatureHelpProvider(sel, {
            async provideSignatureHelp(doc, pos) {
                const res = await client.request('textDocument/signatureHelp', {
                    textDocument: { uri: doc.uri.toString() },
                    position: toLspPos(pos)
                });
                if (!res || !Array.isArray(res.signatures)) return null;
                const sh = new vscode.SignatureHelp();
                sh.activeSignature = res.activeSignature || 0;
                sh.activeParameter = res.activeParameter || 0;
                sh.signatures = res.signatures.map((s) => {
                    const si = new vscode.SignatureInformation(s.label);
                    si.parameters = (s.parameters || []).map((p) => new vscode.ParameterInformation(p.label));
                    return si;
                });
                return sh;
            }
        }, '(', ','),

        vscode.languages.registerDefinitionProvider(sel, {
            async provideDefinition(doc, pos) {
                const res = await client.request('textDocument/definition', {
                    textDocument: { uri: doc.uri.toString() },
                    position: toLspPos(pos)
                });
                if (!res || !res.uri) return null;
                return new vscode.Location(vscode.Uri.parse(res.uri), toVsRange(res.range));
            }
        }),

        vscode.languages.registerDocumentSymbolProvider(sel, {
            async provideDocumentSymbols(doc) {
                const res = await client.request('textDocument/documentSymbol', {
                    textDocument: { uri: doc.uri.toString() }
                });
                return Array.isArray(res) ? res.map(toDocSymbol) : [];
            }
        }),

        vscode.languages.registerInlayHintsProvider(sel, {
            async provideInlayHints(doc) {
                const res = await client.request('textDocument/inlayHint', {
                    textDocument: { uri: doc.uri.toString() }
                });
                if (!Array.isArray(res)) return [];
                return res.map((h) => {
                    const hint = new vscode.InlayHint(
                        new vscode.Position(h.position.line || 0, h.position.character || 0),
                        h.label || '',
                        h.kind === 2 ? vscode.InlayHintKind.Parameter : vscode.InlayHintKind.Type
                    );
                    hint.paddingLeft = !!h.paddingLeft;
                    hint.paddingRight = !!h.paddingRight;
                    return hint;
                });
            }
        }),

        vscode.languages.registerCodeLensProvider(sel, {
            async provideCodeLenses(doc) {
                const res = await client.request('textDocument/codeLens', {
                    textDocument: { uri: doc.uri.toString() }
                });
                if (!Array.isArray(res)) return [];
                return res.map((l) => new vscode.CodeLens(toVsRange(l.range), {
                    title: (l.command && l.command.title) || '▶ Run Program',
                    command: (l.command && l.command.command) || 'aerix.runFile',
                    arguments: [doc.uri]
                }));
            }
        }),

        vscode.languages.registerDocumentFormattingEditProvider(sel, {
            async provideDocumentFormattingEdits(doc) {
                const res = await client.request('textDocument/formatting', {
                    textDocument: { uri: doc.uri.toString() }
                });
                if (!Array.isArray(res)) return [];
                return res.map((e) => vscode.TextEdit.replace(toVsRange(e.range), e.newText || ''));
            }
        })
    );

    // Commands
    const runInTerm = (cmdLine) => {
        let term = vscode.window.terminals.find((t) => t.name === 'Aerix Terminal');
        if (!term) term = vscode.window.createTerminal('Aerix Terminal');
        term.show();
        term.sendText(cmdLine);
    };

    const resolveDocPath = (uri) => {
        const ed = vscode.window.activeTextEditor;
        return uri ? uri.fsPath : (ed ? ed.document.fileName : null);
    };

    context.subscriptions.push(
        vscode.commands.registerCommand('aerix.runFile', (uri) => {
            const p = resolveDocPath(uri);
            if (p) runInTerm(`arx run "${p}"`);
        }),
        vscode.commands.registerCommand('aerix.checkFile', (uri) => {
            const p = resolveDocPath(uri);
            if (p) runInTerm(`arx check "${p}"`);
        }),
        vscode.commands.registerCommand('aerix.buildWasm', (uri) => {
            const p = resolveDocPath(uri);
            if (p) runInTerm(`arx wasm "${p}" --wat --html`);
        }),
        vscode.commands.registerCommand('aerix.serveWasm', (uri) => {
            const p = resolveDocPath(uri);
            if (p) runInTerm(`arx wasm "${p}" --serve`);
        })
    );
}

function deactivate() {}

module.exports = { activate, deactivate };
