/**
 * Aerix Language Client (Thin LSP Bridge)
 * Delegates all syntax highlighting (Semantic Tokens), diagnostics, completions,
 * hover, signature help, go-to-definition, symbols, inlay hints, codeLens, and
 * formatting directly to the native compiler LSP (`arx lsp`).
 */

const vscode = require('vscode');
const cp = require('child_process');
const fs = require('fs');
const https = require('https');
const os = require('os');
const path = require('path');

const TOKEN_TYPES = [
    'comment', 'keyword', 'string', 'number', 'operator',
    'type', 'class', 'enum', 'enumMember', 'function',
    'method', 'property', 'parameter', 'variable', 'namespace', 'macro', 'typeParameter'
];

const TOKEN_MODIFIERS = [
    'declaration', 'definition', 'readonly', 'static', 'defaultLibrary', 'documentation', 'abstract', 'controlFlow'
];

const AERIX_FALLBACK_COMPLETIONS = [
    // Keywords & Declarations
    { label: 'fn', kind: vscode.CompletionItemKind.Keyword, detail: 'fn name(params) -> type', insertText: 'fn ${1:name}(${2:params}) -> ${3:void} {\n\t${0}\n}' },
    { label: 'struct', kind: vscode.CompletionItemKind.Struct, detail: 'struct Name { pub field: type }', insertText: 'struct ${1:Name} {\n\tpub ${2:field}: ${3:i64}\n\n\tinit(${2:field}: ${3:i64}) {\n\t\tself.${2:field} = ${2:field}\n\t}\n}' },
    { label: 'class', kind: vscode.CompletionItemKind.Class, detail: 'class Name { pub field: type }', insertText: 'class ${1:Name} {\n\tpub ${2:field}: ${3:str}\n\n\tinit(${2:field}: ${3:str}) {\n\t\tself.${2:field} = ${2:field}\n\t}\n}' },
    { label: 'enum', kind: vscode.CompletionItemKind.Enum, detail: 'enum Name { Variant1, Variant2 }', insertText: 'enum ${1:Name} {\n\t${2:Variant1},\n\t${3:Variant2}\n}' },
    { label: 'trait', kind: vscode.CompletionItemKind.Interface, detail: 'trait Name { fn method() }', insertText: 'trait ${1:Name} {\n\tfn ${2:method}() -> ${3:void}\n}' },
    { label: 'extend', kind: vscode.CompletionItemKind.Keyword, detail: 'extend Type { pub fn ... }', insertText: 'extend ${1:Type} {\n\tpub fn ${2:method}() -> ${3:void} {\n\t\t${0}\n\t}\n}' },
    { label: 'let', kind: vscode.CompletionItemKind.Keyword, detail: 'let var = value', insertText: 'let ${1:name} = ${0}' },
    { label: 'mut', kind: vscode.CompletionItemKind.Keyword, detail: 'mut var = value', insertText: 'mut ${1:name} = ${0}' },
    { label: 'const', kind: vscode.CompletionItemKind.Keyword, detail: 'const NAME: type = val', insertText: 'const ${1:NAME}: ${2:i64} = ${0}' },
    { label: 'if', kind: vscode.CompletionItemKind.Keyword, detail: 'if condition { ... }', insertText: 'if ${1:condition} {\n\t${0}\n}' },
    { label: 'ifelse', kind: vscode.CompletionItemKind.Snippet, detail: 'if cond { ... } else { ... }', insertText: 'if ${1:condition} {\n\t${2}\n} else {\n\t${0}\n}' },
    { label: 'for', kind: vscode.CompletionItemKind.Keyword, detail: 'for i in 0..10', insertText: 'for ${1:i} in ${2:0}..${3:10} {\n\t${0}\n}' },
    { label: 'for_in', kind: vscode.CompletionItemKind.Snippet, detail: 'for item in collection', insertText: 'for ${1:item} in ${2:items} {\n\t${0}\n}' },
    { label: 'while', kind: vscode.CompletionItemKind.Keyword, detail: 'while condition { ... }', insertText: 'while ${1:condition} {\n\t${0}\n}' },
    { label: 'guard', kind: vscode.CompletionItemKind.Keyword, detail: 'guard cond else { return }', insertText: 'guard ${1:condition} else {\n\t${0:return}\n}' },
    { label: 'defer', kind: vscode.CompletionItemKind.Keyword, detail: 'defer cleanup()', insertText: 'defer ${0:cleanup()}' },
    { label: 'match', kind: vscode.CompletionItemKind.Keyword, detail: 'match expr { case ... => ... }', insertText: 'match ${1:expr} {\n\tcase ${2:pattern} => {\n\t\t${0}\n\t}\n}' },
    { label: 'try', kind: vscode.CompletionItemKind.Keyword, detail: 'try { ... } catch err { ... }', insertText: 'try {\n\t${1}\n} catch ${2:err} {\n\t${0}\n}' },
    { label: 'return', kind: vscode.CompletionItemKind.Keyword, detail: 'return value', insertText: 'return ${0}' },
    { label: 'spawn', kind: vscode.CompletionItemKind.Keyword, detail: 'spawn { ... }', insertText: 'let ${1:th} = spawn {\n\t${0}\n}' },
    { label: 'import', kind: vscode.CompletionItemKind.Keyword, detail: 'import Module', insertText: 'import ${0:Math}' },
    { label: 'from', kind: vscode.CompletionItemKind.Keyword, detail: 'from Module import ...', insertText: 'from ${1:Window.Gui.Canvas} import ${0:colorRed}' },
    // Standard Built-in Functions & Methods
    { label: 'println', kind: vscode.CompletionItemKind.Function, detail: 'println(text: str) -> void', insertText: 'println(${1:"${0}"})' },
    { label: 'print', kind: vscode.CompletionItemKind.Function, detail: 'print(text: str) -> void', insertText: 'print(${1:val})' },
    { label: 'eprintln', kind: vscode.CompletionItemKind.Function, detail: 'eprintln(text: str) -> void', insertText: 'eprintln(${1:val})' },
    { label: 'len', kind: vscode.CompletionItemKind.Function, detail: 'len(collection) -> i64', insertText: 'len(${1:coll})' },
    { label: 'assert', kind: vscode.CompletionItemKind.Function, detail: 'assert(cond: bool)', insertText: 'assert(${1:condition})' },
    { label: 'assert_eq', kind: vscode.CompletionItemKind.Function, detail: 'assert_eq(actual, expected)', insertText: 'assert_eq(${1:actual}, ${2:expected})' },
    { label: 'rgb', kind: vscode.CompletionItemKind.Function, detail: 'rgb(r: i64, g: i64, b: i64) -> i64', insertText: 'rgb(${1:255}, ${2:0}, ${3:0})' },
    { label: 'RGB', kind: vscode.CompletionItemKind.Function, detail: 'RGB(r: i64, g: i64, b: i64) -> i64', insertText: 'RGB(${1:255}, ${2:0}, ${3:0})' },
    { label: 'colorRed', kind: vscode.CompletionItemKind.Function, detail: 'colorRed() -> i64 (0x0000FF)', insertText: 'colorRed()' },
    { label: 'colorBlack', kind: vscode.CompletionItemKind.Function, detail: 'colorBlack() -> i64 (0x000000)', insertText: 'colorBlack()' },
    { label: 'colorWhite', kind: vscode.CompletionItemKind.Function, detail: 'colorWhite() -> i64 (0xFFFFFF)', insertText: 'colorWhite()' },
    { label: 'colorGreen', kind: vscode.CompletionItemKind.Function, detail: 'colorGreen() -> i64 (0x00FF00)', insertText: 'colorGreen()' },
    { label: 'colorBlue', kind: vscode.CompletionItemKind.Function, detail: 'colorBlue() -> i64 (0xFF0000)', insertText: 'colorBlue()' },
    { label: 'colorYellow', kind: vscode.CompletionItemKind.Function, detail: 'colorYellow() -> i64 (0x00FFFF)', insertText: 'colorYellow()' },
    { label: 'colorCyan', kind: vscode.CompletionItemKind.Function, detail: 'colorCyan() -> i64 (0xFFFF00)', insertText: 'colorCyan()' },
    { label: 'colorGray', kind: vscode.CompletionItemKind.Function, detail: 'colorGray() -> i64 (0x808080)', insertText: 'colorGray()' },
    // Standard Primitive Types
    { label: 'i64', kind: vscode.CompletionItemKind.TypeParameter, detail: '64-bit signed integer' },
    { label: 'i32', kind: vscode.CompletionItemKind.TypeParameter, detail: '32-bit signed integer' },
    { label: 'u8', kind: vscode.CompletionItemKind.TypeParameter, detail: '8-bit unsigned byte' },
    { label: 'f64', kind: vscode.CompletionItemKind.TypeParameter, detail: '64-bit IEEE 754 float' },
    { label: 'bool', kind: vscode.CompletionItemKind.TypeParameter, detail: 'Boolean (true / false)' },
    { label: 'char', kind: vscode.CompletionItemKind.TypeParameter, detail: 'Unicode codepoint character' },
    { label: 'str', kind: vscode.CompletionItemKind.TypeParameter, detail: 'Immutable UTF-8 string' },
    { label: 'void', kind: vscode.CompletionItemKind.TypeParameter, detail: 'Unit / void return type' },
    // Standard Collections & Modules
    { label: 'List', kind: vscode.CompletionItemKind.Class, detail: 'Dynamic growable array List<T>', insertText: 'List<${1:i64}>()' },
    { label: 'Map', kind: vscode.CompletionItemKind.Class, detail: 'Key-value hash map Map<K, V>', insertText: 'Map<${1:str}, ${2:i64}>()' },
    { label: 'Set', kind: vscode.CompletionItemKind.Class, detail: 'Unique element hash set Set<T>', insertText: 'Set<${1:str}>()' },
    { label: 'Channel', kind: vscode.CompletionItemKind.Class, detail: 'Thread-safe bounded channel Channel<T>', insertText: 'Channel<${1:str}>(${2:32})' },
    { label: 'Math', kind: vscode.CompletionItemKind.Module, detail: 'Standard mathematics module' },
    { label: 'Random', kind: vscode.CompletionItemKind.Module, detail: 'PRNG pseudo-random generator module' },
    { label: 'Time', kind: vscode.CompletionItemKind.Module, detail: 'High-resolution timing & clock module' },
    { label: 'Socket', kind: vscode.CompletionItemKind.Module, detail: 'TCP/UDP networking module' },
    { label: 'Canvas', kind: vscode.CompletionItemKind.Class, detail: 'Double-buffered GDI graphics canvas', insertText: 'Canvas(${1:hwnd})' },
    { label: 'Application', kind: vscode.CompletionItemKind.Class, detail: 'Native Win32 GUI application window', insertText: 'Application("${1:Title}", ${2:800}, ${3:600})' }
];

function buildFallbackCompletions() {
    return AERIX_FALLBACK_COMPLETIONS.map((fb) => {
        const ci = new vscode.CompletionItem(fb.label, fb.kind);
        ci.detail = fb.detail;
        if (fb.insertText) {
            ci.insertText = new vscode.SnippetString(fb.insertText);
        }
        return ci;
    });
}

const SEMANTIC_LEGEND = new vscode.SemanticTokensLegend(TOKEN_TYPES, TOKEN_MODIFIERS);

function resolveAerixBinary() {
    const cfgPath = (vscode.workspace.getConfiguration('aerix').get('executablePath') || '').trim().replace(/^["']|["']$/g, '');
    if (cfgPath && fs.existsSync(cfgPath)) return cfgPath;

    const exe = process.platform === 'win32' ? '.exe' : '';
    const candidates = [];
    if (process.env.AERIX_HOME) {
        candidates.push(
            path.join(process.env.AERIX_HOME, 'bin', `arx${exe}`),
            path.join(process.env.AERIX_HOME, 'bin', `arxc${exe}`)
        );
    }
    if (process.platform === 'win32' && process.env.LOCALAPPDATA) {
        candidates.push(
            path.join(process.env.LOCALAPPDATA, 'Programs', 'Aerix', 'bin', 'arx.exe'),
            path.join(process.env.LOCALAPPDATA, 'Programs', 'Aerix', 'bin', 'arxc.exe')
        );
    }
    candidates.push(
        path.join(os.homedir(), '.aerix', 'bin', `arx${exe}`),
        path.join(os.homedir(), '.aerix', 'bin', `arxc${exe}`)
    );
    if (process.platform === 'win32') {
        const sysDrive = process.env.SystemDrive || 'C:';
        candidates.push(
            path.join(sysDrive + '\\', 'Aerix', 'bin', 'arx.exe'),
            path.join(sysDrive + '\\', 'Aerix', 'bin', 'arxc.exe')
        );
    }
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
    constructor(diagnostics, output, onTokensRefresh) {
        this.diagnostics = diagnostics;
        this.output = output;
        this.onTokensRefresh = onTokensRefresh;
        this.proc = null;
        this.nextId = 1;
        this.pending = new Map();
        this.rxBuf = Buffer.alloc(0);
        this.ready = null;
        this.initialized = false;
        this.openedUris = new Set();
        this.dirtyTimers = new Map();
        this.diagTimers = new Map();
    }

    start() {
        if (this.ready) return this.ready;
        this.ready = this._spawnAndInit().catch((err) => {
            this.output.appendLine(`[Aerix LSP] Init error: ${err && err.message ? err.message : err}`);
            this.ready = null;
            this.initialized = false;
        });
        return this.ready;
    }

    async stop() {
        for (const [, pending] of this.dirtyTimers) clearTimeout(pending.timer);
        this.dirtyTimers.clear();
        for (const [, t] of this.diagTimers) clearTimeout(t);
        this.diagTimers.clear();
        for (const [, p] of this.pending) p.resolve(null);
        this.pending.clear();
        this.ready = null;
        this.initialized = false;
        this.openedUris.clear();
        const proc = this.proc;
        this.proc = null;
        if (!proc) return;
        try {
            await this._requestRaw('shutdown', null, 2000);
            this._send({ jsonrpc: '2.0', method: 'exit', params: null });
        } catch {
            // ignore
        }
        try { proc.kill(); } catch (_) {}
    }

    async restart() {
        await this.stop();
        return this.start();
    }

    async _spawnAndInit() {
        const bin = resolveAerixBinary();
        this.output.appendLine(`[Aerix LSP] Starting: ${bin} lsp`);
        this.initialized = false;
        this.openedUris.clear();
        const proc = cp.spawn(bin, ['lsp'], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true });
        this.proc = proc;

        proc.stdout.on('data', (chunk) => this._onData(chunk));
        proc.stderr.on('data', (chunk) => this.output.appendLine(`[stderr] ${chunk.toString('utf8').trimEnd()}`));
        proc.on('exit', (code) => {
            this.output.appendLine(`[Aerix LSP] Exited with code ${code}`);
            for (const [, p] of this.pending) p.resolve(null);
            this.pending.clear();
            this.proc = null;
            this.ready = null;
            this.initialized = false;
            this.openedUris.clear();
        });
        proc.on('error', (err) => {
            this.output.appendLine(`[Aerix LSP] Failed to start '${bin}': ${err.message}`);
            for (const [, p] of this.pending) p.resolve(null);
            this.pending.clear();
            this.proc = null;
            this.ready = null;
            this.initialized = false;
            this.openedUris.clear();
        });

        const folders = vscode.workspace.workspaceFolders;
        await this._requestRaw('initialize', {
            processId: process.pid,
            rootUri: folders && folders.length ? folders[0].uri.toString() : null,
            capabilities: {}
        }, 15000);
        this._send({ jsonrpc: '2.0', method: 'initialized', params: {} });
        this.initialized = true;

        for (const doc of vscode.workspace.textDocuments) {
            if (doc.languageId === 'aerix') {
                this._openDoc(doc);
            }
        }
        if (this.onTokensRefresh) this.onTokensRefresh();
        const activeEd = vscode.window.activeTextEditor;
        if (activeEd && activeEd.document && activeEd.document.languageId === 'aerix') {
            this.scheduleDiagnostics(activeEd.document, 120);
        }
    }

    _openDoc(doc) {
        const uri = doc.uri.toString();
        this.openedUris.add(uri);
        this._send({
            jsonrpc: '2.0',
            method: 'textDocument/didOpen',
            params: {
                textDocument: {
                    uri,
                    languageId: 'aerix',
                    version: doc.version,
                    text: doc.getText()
                }
            }
        });
    }

    _changeDoc(doc) {
        const uri = doc.uri.toString();
        if (!this.openedUris.has(uri)) {
            this._openDoc(doc);
            return;
        }
        this._send({
            jsonrpc: '2.0',
            method: 'textDocument/didChange',
            params: {
                textDocument: { uri, version: doc.version },
                contentChanges: [{ text: doc.getText() }]
            }
        });
    }

    async ensureDocSynced(doc) {
        await this.start();
        if (!this.proc || !this.initialized) return false;
        const uri = doc.uri.toString();
        const pending = this.dirtyTimers.get(uri);
        if (pending) {
            clearTimeout(pending.timer);
            this.dirtyTimers.delete(uri);
            this._changeDoc(pending.doc);
        } else if (!this.openedUris.has(uri)) {
            this._openDoc(doc);
        }
        return true;
    }

    scheduleDocChange(doc) {
        const uri = doc.uri.toString();
        const prev = this.dirtyTimers.get(uri);
        if (prev) clearTimeout(prev.timer);
        const timer = setTimeout(async () => {
            this.dirtyTimers.delete(uri);
            await this.start();
            if (this.proc && this.initialized) {
                this._changeDoc(doc);
                if (this.onTokensRefresh) this.onTokensRefresh();
            }
        }, 40);
        this.dirtyTimers.set(uri, { timer, doc });
        this.scheduleDiagnostics(doc, 650);
    }

    scheduleDiagnostics(doc, delayMs = 650) {
        const uri = doc.uri.toString();
        const prev = this.diagTimers.get(uri);
        if (prev) clearTimeout(prev);
        const timer = setTimeout(async () => {
            this.diagTimers.delete(uri);
            await this.start();
            if (!this.proc || !this.initialized) return;
            await this.ensureDocSynced(doc);
            this._send({
                jsonrpc: '2.0',
                method: 'aerix/diagnostics',
                params: { textDocument: { uri } }
            });
        }, delayMs);
        this.diagTimers.set(uri, timer);
    }

    _send(payload) {
        if (!this.proc || !this.proc.stdin.writable) return;
        const json = JSON.stringify(payload);
        const bytes = Buffer.byteLength(json, 'utf8');
        this.proc.stdin.write(`Content-Length: ${bytes}\r\n\r\n${json}`, 'utf8');
    }

    _requestRaw(method, params, timeoutMs = 30000) {
        if (!this.proc) return Promise.resolve(null);
        const id = this.nextId++;
        return new Promise((resolve) => {
            const timer = setTimeout(() => {
                this.pending.delete(id);
                this.output.appendLine(`[Aerix LSP] Request timeout (${timeoutMs}ms): ${method}`);
                resolve(null);
            }, timeoutMs);
            this.pending.set(id, {
                resolve: (val) => {
                    clearTimeout(timer);
                    resolve(val);
                }
            });
            this._send({ jsonrpc: '2.0', id, method, params });
        });
    }

    async request(method, params, doc) {
        await this.start();
        if (!this.proc || !this.initialized) return null;
        if (doc) await this.ensureDocSynced(doc);
        return this._requestRaw(method, params, 30000);
    }

    async notify(method, params) {
        await this.start();
        if (!this.proc || !this.initialized) return;
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
            const list = (msg.params.diagnostics || []).map((d) => {
                const diag = new vscode.Diagnostic(
                    toVsRange(d.range),
                    d.message || 'Aerix error',
                    d.severity === 2 ? vscode.DiagnosticSeverity.Warning : vscode.DiagnosticSeverity.Error
                );
                if (d.code !== undefined && d.code !== null && d.code !== '') diag.code = d.code;
                diag.source = d.source || 'aerix';
                return diag;
            });
            this.diagnostics.set(uri, list);
        }
    }
}

function activate(context) {
    const diagnostics = vscode.languages.createDiagnosticCollection('aerix');
    const output = vscode.window.createOutputChannel('Aerix Language Server');
    const semTokensEmitter = new vscode.EventEmitter();
    const client = new AerixLspClient(diagnostics, output, () => semTokensEmitter.fire());
    client.start();

    context.subscriptions.push(diagnostics, output, semTokensEmitter, { dispose: () => client.stop() });

    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBar.command = 'aerix.checkFile';
    statusBar.text = '$(zap) Aerix';
    const updateStatusBar = (editor) => {
        if (editor && editor.document && editor.document.languageId === 'aerix') {
            statusBar.tooltip = `Aerix Native LSP (${resolveAerixBinary()}) — Click to Check File`;
            statusBar.show();
        } else {
            statusBar.hide();
        }
    };
    updateStatusBar(vscode.window.activeTextEditor);
    context.subscriptions.push(
        statusBar,
        vscode.window.onDidChangeActiveTextEditor(updateStatusBar)
    );

    context.subscriptions.push(
        vscode.workspace.onDidOpenTextDocument((doc) => {
            if (doc.languageId === 'aerix') {
                client.ensureDocSynced(doc).then(() => {
                    semTokensEmitter.fire();
                    client.scheduleDiagnostics(doc, 120);
                });
            }
        }),
        vscode.workspace.onDidChangeTextDocument((ev) => {
            if (ev.document.languageId === 'aerix') {
                client.scheduleDocChange(ev.document);
            }
        }),
        vscode.workspace.onDidSaveTextDocument((doc) => {
            if (doc.languageId === 'aerix') {
                const uri = doc.uri.toString();
                const prevDiag = client.diagTimers.get(uri);
                if (prevDiag) {
                    clearTimeout(prevDiag);
                    client.diagTimers.delete(uri);
                }
                client.ensureDocSynced(doc).then(() => {
                    client.notify('textDocument/didSave', {
                        textDocument: { uri },
                        text: doc.getText()
                    });
                    semTokensEmitter.fire();
                });
            }
        }),
        vscode.workspace.onDidCloseTextDocument((doc) => {
            if (doc.languageId === 'aerix') {
                const uri = doc.uri.toString();
                const pending = client.dirtyTimers.get(uri);
                if (pending) {
                    clearTimeout(pending.timer);
                    client.dirtyTimers.delete(uri);
                }
                const diagT = client.diagTimers.get(uri);
                if (diagT) {
                    clearTimeout(diagT);
                    client.diagTimers.delete(uri);
                }
                client.openedUris.delete(uri);
                client.notify('textDocument/didClose', { textDocument: { uri } });
                diagnostics.delete(doc.uri);
            }
        })
    );

    const sel = { language: 'aerix' };

    context.subscriptions.push(
        vscode.languages.registerDocumentSemanticTokensProvider(sel, {
            onDidChangeSemanticTokens: semTokensEmitter.event,
            async provideDocumentSemanticTokens(doc) {
                const res = await client.request('textDocument/semanticTokens/full', {
                    textDocument: { uri: doc.uri.toString() }
                }, doc);
                if (!res || !Array.isArray(res.data)) return new vscode.SemanticTokens(new Uint32Array(0));
                return new vscode.SemanticTokens(new Uint32Array(res.data));
            }
        }, SEMANTIC_LEGEND),

        vscode.languages.registerCompletionItemProvider(sel, {
            async provideCompletionItems(doc, pos) {
                const res = await client.request('textDocument/completion', {
                    textDocument: { uri: doc.uri.toString() },
                    position: toLspPos(pos)
                }, doc);
                const items = res && Array.isArray(res.items) ? res.items : (Array.isArray(res) ? res : []);
                if (!items.length) {
                    return buildFallbackCompletions();
                }
                return items.map((it) => {
                    const labelObj = it.labelDetails
                        ? {
                            label: it.label,
                            detail: it.labelDetails.detail || '',
                            description: it.labelDetails.description || ''
                        }
                        : it.label;
                    const ci = new vscode.CompletionItem(labelObj, it.kind || vscode.CompletionItemKind.Text);
                    if (it.detail) ci.detail = it.detail;
                    if (it.sortText) ci.sortText = it.sortText;
                    if (it.filterText) ci.filterText = it.filterText;
                    if (it.preselect) ci.preselect = true;
                    if (it.documentation && (it.documentation.value || typeof it.documentation === 'string')) {
                        const docStr = typeof it.documentation === 'string' ? it.documentation : it.documentation.value;
                        const md = new vscode.MarkdownString(docStr);
                        md.isTrusted = true;
                        ci.documentation = md;
                    }
                    const rawInsert = it.textEdit ? (it.textEdit.newText || '') : (it.insertText || '');
                    if (it.textEdit && it.textEdit.range) {
                        ci.range = toVsRange(it.textEdit.range);
                        ci.insertText = it.insertTextFormat === 2 ? new vscode.SnippetString(rawInsert) : rawInsert;
                    } else if (it.insertText) {
                        ci.insertText = new vscode.SnippetString(it.insertText);
                    }
                    if (rawInsert.includes('${') && rawInsert.includes('(')) {
                        ci.command = { command: 'editor.action.triggerParameterHints', title: 'Trigger Parameter Hints' };
                    }
                    return ci;
                });
            }
        }, '.', '>', ':', '<', '"', '/', '$', '~', '@', '#', '{', ' '),

        vscode.languages.registerHoverProvider(sel, {
            async provideHover(doc, pos) {
                const res = await client.request('textDocument/hover', {
                    textDocument: { uri: doc.uri.toString() },
                    position: toLspPos(pos)
                }, doc);
                if (!res || !res.contents) return null;
                const val = typeof res.contents === 'string' ? res.contents : (res.contents.value || '');
                if (!val) return null;
                const md = new vscode.MarkdownString(val);
                md.isTrusted = true;
                return new vscode.Hover(md);
            }
        }),

        vscode.languages.registerSignatureHelpProvider(sel, {
            async provideSignatureHelp(doc, pos) {
                const res = await client.request('textDocument/signatureHelp', {
                    textDocument: { uri: doc.uri.toString() },
                    position: toLspPos(pos)
                }, doc);
                if (!res || !Array.isArray(res.signatures)) return null;
                const sh = new vscode.SignatureHelp();
                sh.activeSignature = res.activeSignature || 0;
                sh.activeParameter = res.activeParameter || 0;
                sh.signatures = res.signatures.map((s) => {
                    const sDoc = s.documentation
                        ? new vscode.MarkdownString(typeof s.documentation === 'string' ? s.documentation : (s.documentation.value || ''))
                        : undefined;
                    if (sDoc) sDoc.isTrusted = true;
                    const si = new vscode.SignatureInformation(s.label, sDoc);
                    si.parameters = (s.parameters || []).map((p) => {
                        const pDoc = p.documentation
                            ? new vscode.MarkdownString(typeof p.documentation === 'string' ? p.documentation : (p.documentation.value || ''))
                            : undefined;
                        return new vscode.ParameterInformation(p.label, pDoc);
                    });
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
                }, doc);
                if (!res) return null;
                if (Array.isArray(res)) {
                    const locs = res.filter((r) => r && r.uri).map((r) => new vscode.Location(vscode.Uri.parse(r.uri), toVsRange(r.range)));
                    return locs.length ? locs : null;
                }
                if (!res.uri) return null;
                return new vscode.Location(vscode.Uri.parse(res.uri), toVsRange(res.range));
            }
        }),

        vscode.languages.registerTypeDefinitionProvider(sel, {
            async provideTypeDefinition(doc, pos) {
                const res = await client.request('textDocument/typeDefinition', {
                    textDocument: { uri: doc.uri.toString() },
                    position: toLspPos(pos)
                }, doc);
                if (!res) return null;
                if (Array.isArray(res)) {
                    const locs = res.filter((r) => r && r.uri).map((r) => new vscode.Location(vscode.Uri.parse(r.uri), toVsRange(r.range)));
                    return locs.length ? locs : null;
                }
                if (!res.uri) return null;
                return new vscode.Location(vscode.Uri.parse(res.uri), toVsRange(res.range));
            }
        }),

        vscode.languages.registerDocumentSymbolProvider(sel, {
            async provideDocumentSymbols(doc) {
                const res = await client.request('textDocument/documentSymbol', {
                    textDocument: { uri: doc.uri.toString() }
                }, doc);
                return Array.isArray(res) ? res.map(toDocSymbol) : [];
            }
        }),

        vscode.languages.registerInlayHintsProvider(sel, {
            async provideInlayHints(doc) {
                const res = await client.request('textDocument/inlayHint', {
                    textDocument: { uri: doc.uri.toString() }
                }, doc);
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
                }, doc);
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
                }, doc);
                if (!Array.isArray(res)) return [];
                return res.map((e) => vscode.TextEdit.replace(toVsRange(e.range), e.newText || ''));
            }
        }),

        vscode.languages.registerDocumentHighlightProvider(sel, {
            async provideDocumentHighlights(doc, pos) {
                const res = await client.request('textDocument/documentHighlight', {
                    textDocument: { uri: doc.uri.toString() },
                    position: toLspPos(pos)
                }, doc);
                if (!Array.isArray(res)) return [];
                return res.map((h) => new vscode.DocumentHighlight(
                    toVsRange(h.range),
                    h.kind === 3 ? vscode.DocumentHighlightKind.Write : vscode.DocumentHighlightKind.Read
                ));
            }
        }),

        vscode.languages.registerReferenceProvider(sel, {
            async provideReferences(doc, pos, ctx) {
                const res = await client.request('textDocument/references', {
                    textDocument: { uri: doc.uri.toString() },
                    position: toLspPos(pos),
                    context: { includeDeclaration: !ctx || ctx.includeDeclaration !== false }
                }, doc);
                if (!Array.isArray(res)) return [];
                return res.map((loc) => new vscode.Location(vscode.Uri.parse(loc.uri), toVsRange(loc.range)));
            }
        }),

        vscode.languages.registerRenameProvider(sel, {
            async prepareRename(doc, pos) {
                const res = await client.request('textDocument/prepareRename', {
                    textDocument: { uri: doc.uri.toString() },
                    position: toLspPos(pos)
                }, doc);
                if (!res || !res.range) return undefined;
                return { range: toVsRange(res.range), placeholder: res.placeholder || '' };
            },
            async provideRenameEdits(doc, pos, newName) {
                const res = await client.request('textDocument/rename', {
                    textDocument: { uri: doc.uri.toString() },
                    position: toLspPos(pos),
                    newName
                }, doc);
                if (!res || !res.changes) return undefined;
                const edit = new vscode.WorkspaceEdit();
                for (const [uriStr, edits] of Object.entries(res.changes)) {
                    if (!Array.isArray(edits)) continue;
                    const targetUri = vscode.Uri.parse(uriStr);
                    for (const e of edits) {
                        edit.replace(targetUri, toVsRange(e.range), e.newText != null ? e.newText : newName);
                    }
                }
                return edit;
            }
        }),

        vscode.languages.registerFoldingRangeProvider(sel, {
            async provideFoldingRanges(doc) {
                const res = await client.request('textDocument/foldingRange', {
                    textDocument: { uri: doc.uri.toString() }
                }, doc);
                if (!Array.isArray(res)) return [];
                return res.map((f) => {
                    let kind;
                    if (f.kind === 'comment') kind = vscode.FoldingRangeKind.Comment;
                    else if (f.kind === 'imports') kind = vscode.FoldingRangeKind.Imports;
                    else if (f.kind === 'region') kind = vscode.FoldingRangeKind.Region;
                    return new vscode.FoldingRange(f.startLine || 0, f.endLine || 0, kind);
                });
            }
        }),

        vscode.languages.registerCodeActionsProvider(sel, {
            async provideCodeActions(doc, range, context) {
                const res = await client.request('textDocument/codeAction', {
                    textDocument: { uri: doc.uri.toString() },
                    range: {
                        start: toLspPos(range.start),
                        end: toLspPos(range.end)
                    },
                    context: { diagnostics: [] }
                }, doc);
                if (!Array.isArray(res)) return [];
                return res.map((ca) => {
                    const action = new vscode.CodeAction(ca.title || 'Apply fix', vscode.CodeActionKind.QuickFix);
                    action.isPreferred = Boolean(ca.isPreferred);
                    if (ca.edit && ca.edit.changes) {
                        const edit = new vscode.WorkspaceEdit();
                        for (const [uriStr, edits] of Object.entries(ca.edit.changes)) {
                            if (!Array.isArray(edits)) continue;
                            const targetUri = vscode.Uri.parse(uriStr);
                            for (const e of edits) {
                                edit.replace(targetUri, toVsRange(e.range), e.newText != null ? e.newText : '');
                            }
                        }
                        action.edit = edit;
                    }
                    return action;
                });
            }
        }, { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }),

        vscode.languages.registerColorProvider(sel, {
            provideDocumentColors(doc) {
                const text = doc.getText();
                const colors = [];
                const rgbRegex = /\b(?:RGB|rgb)\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/g;
                let match;
                while ((match = rgbRegex.exec(text)) !== null) {
                    const startPos = doc.positionAt(match.index);
                    const endPos = doc.positionAt(match.index + match[0].length);
                    const r = Math.min(255, Math.max(0, parseInt(match[1], 10))) / 255;
                    const g = Math.min(255, Math.max(0, parseInt(match[2], 10))) / 255;
                    const b = Math.min(255, Math.max(0, parseInt(match[3], 10))) / 255;
                    colors.push(new vscode.ColorInformation(new vscode.Range(startPos, endPos), new vscode.Color(r, g, b, 1)));
                }
                const hexRegex = /(?:#|0x)([0-9a-fA-F]{6})\b/g;
                while ((match = hexRegex.exec(text)) !== null) {
                    const startPos = doc.positionAt(match.index);
                    const endPos = doc.positionAt(match.index + match[0].length);
                    const hex = match[1];
                    const r = parseInt(hex.slice(0, 2), 16) / 255;
                    const g = parseInt(hex.slice(2, 4), 16) / 255;
                    const b = parseInt(hex.slice(4, 6), 16) / 255;
                    colors.push(new vscode.ColorInformation(new vscode.Range(startPos, endPos), new vscode.Color(r, g, b, 1)));
                }
                return colors;
            },
            provideColorPresentations(color) {
                const r = Math.round(color.red * 255);
                const g = Math.round(color.green * 255);
                const b = Math.round(color.blue * 255);
                const hex = ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase();
                return [
                    new vscode.ColorPresentation(`RGB(${r}, ${g}, ${b})`),
                    new vscode.ColorPresentation(`rgb(${r}, ${g}, ${b})`),
                    new vscode.ColorPresentation(`"#${hex.toLowerCase()}"`),
                    new vscode.ColorPresentation(`0x${hex}`)
                ];
            }
        }),

        vscode.languages.registerDocumentLinkProvider(sel, {
            provideDocumentLinks(doc) {
                const text = doc.getText();
                const links = [];
                const impRegex = /(?:import|from)\s+["']([^"']+\.arx)["']/g;
                let match;
                const dir = path.dirname(doc.fileName);
                while ((match = impRegex.exec(text)) !== null) {
                    const targetPath = path.resolve(dir, match[1]);
                    const startPos = doc.positionAt(match.index + match[0].indexOf(match[1]));
                    const endPos = doc.positionAt(match.index + match[0].indexOf(match[1]) + match[1].length);
                    links.push(new vscode.DocumentLink(new vscode.Range(startPos, endPos), vscode.Uri.file(targetPath)));
                }
                return links;
            }
        })
    );

    // Commands
    const getOrCreateTerminal = () => {
        let term = vscode.window.terminals.find((t) => t.name === 'Aerix Terminal');
        if (!term) term = vscode.window.createTerminal('Aerix Terminal');
        return term;
    };

    const formatCliInvocation = (term, subcmdAndArgs) => {
        const bin = resolveAerixBinary();
        if (bin === 'arx') {
            return `arx ${subcmdAndArgs}`;
        }
        const shellPath = (term.creationOptions && term.creationOptions.shellPath) || vscode.env.shell || '';
        const isPowerShell = process.platform === 'win32' && (!shellPath || /powershell|pwsh/i.test(shellPath));
        return isPowerShell ? `& "${bin}" ${subcmdAndArgs}` : `"${bin}" ${subcmdAndArgs}`;
    };

    const runInTerm = (subcmdAndArgs) => {
        const term = getOrCreateTerminal();
        term.show();
        term.sendText(formatCliInvocation(term, subcmdAndArgs));
    };

    const prepareDocPath = async (uri) => {
        const ed = vscode.window.activeTextEditor;
        let doc = null;
        if (uri) {
            doc = vscode.workspace.textDocuments.find((d) => d.uri.fsPath === uri.fsPath) || null;
        } else if (ed) {
            doc = ed.document;
        }
        if (doc && doc.isUntitled) {
            const saved = await doc.save();
            if (!saved) return null;
        } else if (doc && doc.isDirty) {
            await doc.save();
        }
        return uri ? uri.fsPath : (doc ? doc.fileName : null);
    };

    const vmStatusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 95);
    vmStatusBar.command = 'aerix.switchVersion';
    vmStatusBar.tooltip = 'Aerix Toolchain Version Manager — Click to switch or install versions';
    vmStatusBar.text = '$(versions) Aerix';
    vmStatusBar.show();
    refreshAerixStatusBar(vmStatusBar);

    context.subscriptions.push(
        vmStatusBar,
        vscode.commands.registerCommand('aerix.runFile', async (uri) => {
            const p = await prepareDocPath(uri);
            if (p) runInTerm(`run "${p}"`);
        }),
        vscode.commands.registerCommand('aerix.checkFile', async (uri) => {
            const p = await prepareDocPath(uri);
            if (p) runInTerm(`check "${p}"`);
        }),
        vscode.commands.registerCommand('aerix.buildWasm', async (uri) => {
            const p = await prepareDocPath(uri);
            if (p) runInTerm(`wasm "${p}" --wat --html`);
        }),
        vscode.commands.registerCommand('aerix.serveWasm', async (uri) => {
            const p = await prepareDocPath(uri);
            if (p) runInTerm(`wasm "${p}" --serve`);
        }),
        vscode.commands.registerCommand('aerix.checkUpdates', () => {
            checkAndApplyUpdates(context, client, output, true, vmStatusBar);
        }),
        vscode.commands.registerCommand('aerix.switchVersion', () => {
            switchAerixVersion(context, client, output, vmStatusBar);
        })
    );

    scheduleAutoUpdateCheck(context, client, output);
}

const GITHUB_RELEASES_API = 'https://api.github.com/repos/HaxOrWot/AerixLang/releases?per_page=15';
const AUTO_UPDATE_INTERVAL_MS = 6 * 60 * 60 * 1000;
let aerixUpdateInFlight = false;

function parseSemverParts(raw) {
    const s = String(raw || '').trim().replace(/^v/i, '');
    const dash = s.indexOf('-');
    const core = dash >= 0 ? s.slice(0, dash) : s;
    let tag = dash >= 0 ? s.slice(dash + 1).trim().toLowerCase() : '';
    const parts = core.split('.');
    const maj = parseInt(parts[0], 10) || 0;
    const min = parseInt(parts[1], 10) || 0;
    let pat = 0;
    if (parts[2]) {
        const pm = parts[2].match(/^(\d+)(.*)$/);
        if (pm) {
            pat = parseInt(pm[1], 10) || 0;
            if (!tag && pm[2]) tag = pm[2].trim().toLowerCase();
        }
    }
    let rank = 0;
    if (!tag || tag === 'stable') rank = 4;
    else if (tag.startsWith('rc')) rank = 3;
    else if (tag === 'p' || tag.startsWith('pre')) rank = 2;
    else if (tag === 'b' || tag.startsWith('beta')) rank = 1;
    return [maj, min, pat, rank];
}

function compareSemver(a, b) {
    const pa = parseSemverParts(a);
    const pb = parseSemverParts(b);
    for (let i = 0; i < 4; i++) {
        if (pa[i] !== pb[i]) return pa[i] - pb[i];
    }
    return 0;
}

function httpsGetText(url, redirectsLeft = 5) {
    return new Promise((resolve, reject) => {
        const req = https.get(url, {
            headers: {
                'User-Agent': 'Aerix-VSCode-Updater',
                'Accept': 'application/vnd.github+json'
            },
            timeout: 12000
        }, (res) => {
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location && redirectsLeft > 0) {
                res.resume();
                httpsGetText(res.headers.location, redirectsLeft - 1).then(resolve, reject);
                return;
            }
            if (res.statusCode !== 200) {
                res.resume();
                reject(new Error(`HTTP ${res.statusCode}`));
                return;
            }
            const chunks = [];
            res.on('data', (c) => chunks.push(c));
            res.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
        });
        req.on('timeout', () => { req.destroy(new Error('Request timed out')); });
        req.on('error', reject);
    });
}

function downloadFileWithRedirects(url, destPath, redirectsLeft = 5) {
    return new Promise((resolve, reject) => {
        const req = https.get(url, {
            headers: { 'User-Agent': 'Aerix-VSCode-Updater' },
            timeout: 60000
        }, (res) => {
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location && redirectsLeft > 0) {
                res.resume();
                downloadFileWithRedirects(res.headers.location, destPath, redirectsLeft - 1).then(resolve, reject);
                return;
            }
            if (res.statusCode !== 200) {
                res.resume();
                reject(new Error(`Download failed (HTTP ${res.statusCode})`));
                return;
            }
            const out = fs.createWriteStream(destPath);
            res.pipe(out);
            out.on('finish', () => out.close(() => resolve(destPath)));
            out.on('error', reject);
        });
        req.on('timeout', () => { req.destroy(new Error('Download timed out')); });
        req.on('error', reject);
    });
}

function getInstalledAerixVersion(bin) {
    return new Promise((resolve) => {
        cp.execFile(bin, ['version'], { timeout: 5000 }, (err, stdout) => {
            if (err || !stdout) {
                resolve('');
                return;
            }
            const m = String(stdout).match(/v([0-9]+\.[0-9]+\.[0-9]+[^\s]*)/);
            resolve(m ? m[1] : '');
        });
    });
}

function resolveUninstallExe(bin) {
    const cands = [];
    if (bin && bin !== 'arx') {
        cands.push(path.join(path.dirname(path.dirname(bin)), 'Uninstall.exe'));
    }
    if (process.env.AERIX_HOME) {
        cands.push(path.join(process.env.AERIX_HOME, 'Uninstall.exe'));
    }
    if (process.env.LOCALAPPDATA) {
        cands.push(path.join(process.env.LOCALAPPDATA, 'Programs', 'Aerix', 'Uninstall.exe'));
    }
    if (process.platform === 'win32') {
        const sysDrive = process.env.SystemDrive || 'C:';
        cands.push(path.join(sysDrive + '\\', 'Aerix', 'Uninstall.exe'));
    } else {
        cands.push('C:\\Aerix\\Uninstall.exe');
    }
    for (const c of cands) {
        if (fs.existsSync(c)) return c;
    }
    return '';
}

async function fetchLatestStableRelease() {
    const raw = await httpsGetText(GITHUB_RELEASES_API);
    const list = JSON.parse(raw);
    if (!Array.isArray(list)) return null;
    let best = null;
    for (const rel of list) {
        if (!rel || rel.draft || rel.prerelease) continue;
        const tag = String(rel.tag_name || '').trim();
        const low = tag.toLowerCase();
        if (!tag || low.endsWith('-pre') || low.endsWith('-alpha') || low.endsWith('-beta') || low.includes('-rc')) {
            continue;
        }
        const assets = Array.isArray(rel.assets) ? rel.assets : [];
        let setupAsset = assets.find((a) => a && /^AerixSetup-.*-stable\.exe$/i.test(String(a.name || '')));
        if (!setupAsset) {
            setupAsset = assets.find((a) => a && /^AerixSetup-.*\.exe$/i.test(String(a.name || '')));
        }
        if (!setupAsset || !setupAsset.browser_download_url) continue;
        const ver = tag.replace(/^v/i, '');
        if (!best || compareSemver(ver, best.version) > 0) {
            best = {
                tagName: tag,
                version: ver,
                assetName: setupAsset.name,
                downloadUrl: setupAsset.browser_download_url
            };
        }
    }
    return best;
}

function execAsync(exe, args) {
    return new Promise((resolve, reject) => {
        cp.execFile(exe, args, { timeout: 180000, windowsHide: true }, (err, stdout, stderr) => {
            if (err) {
                reject(new Error((stderr || stdout || err.message || 'Update failed').trim()));
                return;
            }
            resolve((stdout || '').trim());
        });
    });
}

function scheduleAutoUpdateCheck(context, client, output) {
    if (process.platform !== 'win32') return;
    const mode = vscode.workspace.getConfiguration('aerix').get('autoUpdate', 'auto');
    if (mode === 'off') return;
    const lastCheck = context.globalState.get('aerix.lastUpdateCheckMs', 0);
    if (Date.now() - lastCheck < AUTO_UPDATE_INTERVAL_MS) return;
    const timer = setTimeout(() => {
        checkAndApplyUpdates(context, client, output, false).catch(() => {});
    }, 4500);
    context.subscriptions.push({ dispose: () => clearTimeout(timer) });
}

async function checkAndApplyUpdates(context, client, output, isManual, statusBar) {
    if (process.platform !== 'win32') {
        if (isManual) vscode.window.showInformationMessage('Aerix auto-updater is currently Windows-only.');
        return;
    }
    if (aerixUpdateInFlight) {
        if (isManual) vscode.window.showInformationMessage('An Aerix update check is already running.');
        return;
    }
    aerixUpdateInFlight = true;
    try {
        await context.globalState.update('aerix.lastUpdateCheckMs', Date.now());
        const bin = resolveAerixBinary();
        const currentVer = await getInstalledAerixVersion(bin);
        const latest = await fetchLatestStableRelease();
        if (!latest) {
            if (isManual) vscode.window.showInformationMessage('No stable Aerix release found on GitHub.');
            return;
        }
        if (currentVer && compareSemver(latest.version, currentVer) <= 0) {
            if (isManual) vscode.window.showInformationMessage(`Aerix is already up to date (v${currentVer}).`);
            return;
        }

        const mode = vscode.workspace.getConfiguration('aerix').get('autoUpdate', 'auto');
        if (!isManual && mode === 'prompt') {
            const pick = await vscode.window.showInformationMessage(
                `Aerix v${latest.version} is available (installed: ${currentVer ? 'v' + currentVer : 'unknown'}). Update now?`,
                'Update Now',
                'Later'
            );
            if (pick !== 'Update Now') return;
        }

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: `Updating Aerix to v${latest.version}...`,
            cancellable: false
        }, async (progress) => {
            output.appendLine(`[Aerix Updater] Updating ${currentVer || '?'} -> ${latest.version}...`);
            client.stop();
            const uninst = resolveUninstallExe(bin);
            if (uninst) {
                progress.report({ message: 'Downloading & installing latest stable release...' });
                await execAsync(uninst, ['--update', '--silent', '--quiet']);
            } else {
                progress.report({ message: `Downloading ${latest.assetName}...` });
                const tmpExe = path.join(os.tmpdir(), latest.assetName);
                await downloadFileWithRedirects(latest.downloadUrl, tmpExe);
                progress.report({ message: 'Running silent installer...' });
                try {
                    await execAsync(tmpExe, ['--silent']);
                } finally {
                    try { fs.unlinkSync(tmpExe); } catch (_) {}
                }
            }
            progress.report({ message: 'Restarting Aerix LSP...' });
            await client.restart();
            if (statusBar) await refreshAerixStatusBar(statusBar);
        });

        const reloadChoice = await vscode.window.showInformationMessage(
            `Aerix auto-updated to v${latest.version}! Reload window if extension features were updated.`,
            'Reload Window',
            'OK'
        );
        if (reloadChoice === 'Reload Window') {
            await vscode.commands.executeCommand('workbench.action.reloadWindow');
        }
    } catch (err) {
        output.appendLine(`[Aerix Updater] Error: ${err && err.message ? err.message : err}`);
        if (isManual) {
            vscode.window.showErrorMessage(`Aerix update check failed: ${err && err.message ? err.message : err}`);
        }
    } finally {
        aerixUpdateInFlight = false;
    }
}

async function refreshAerixStatusBar(statusBar) {
    if (!statusBar) return;
    try {
        const ver = await getInstalledAerixVersion(resolveAerixBinary());
        statusBar.text = ver ? `$(versions) Aerix v${ver}` : '$(versions) Aerix';
    } catch (_) {
        statusBar.text = '$(versions) Aerix';
    }
}

async function switchAerixVersion(context, client, output, statusBar) {
    if (process.platform !== 'win32') {
        vscode.window.showInformationMessage('Aerix Version Manager is currently Windows-only.');
        return;
    }
    if (aerixUpdateInFlight) {
        vscode.window.showInformationMessage('Another Aerix install/update operation is already running.');
        return;
    }
    const bin = resolveAerixBinary();
    const uninst = resolveUninstallExe(bin);
    if (!uninst) {
        vscode.window.showErrorMessage('Aerix Uninstall.exe / Version Manager host was not found. Please install Aerix first.');
        return;
    }

    let localData = { activeVersion: '', toolchains: [] };
    let remoteList = [];
    let remoteError = '';

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Loading Aerix versions...',
        cancellable: false
    }, async () => {
        try {
            const rawLocal = await execAsync(uninst, ['--vm-list-json']);
            if (rawLocal && rawLocal.trim()) localData = JSON.parse(rawLocal.trim());
        } catch (err) {
            output.appendLine(`[Aerix VM] Local list error: ${err && err.message ? err.message : err}`);
        }
        try {
            const rawRemote = await execAsync(uninst, ['--vm-remote-json']);
            if (rawRemote && rawRemote.trim()) remoteList = JSON.parse(rawRemote.trim());
        } catch (err) {
            remoteError = err && err.message ? err.message : String(err);
            output.appendLine(`[Aerix VM] Remote list unavailable (offline?): ${remoteError}`);
        }
    });

    const cachedMap = new Map();
    for (const tc of (localData.toolchains || [])) {
        if (tc && tc.version) cachedMap.set(tc.version.toLowerCase(), tc);
    }

    const merged = new Map();
    for (const tc of (localData.toolchains || [])) {
        if (!tc || !tc.version) continue;
        merged.set(tc.version.toLowerCase(), {
            version: tc.version,
            active: Boolean(tc.active),
            cached: true,
            channel: tc.version.toLowerCase().endsWith('b') ? 'beta' : (tc.version.toLowerCase().endsWith('p') ? 'pre' : 'stable'),
            size: 0
        });
    }
    for (const r of (Array.isArray(remoteList) ? remoteList : [])) {
        if (!r || !r.version) continue;
        const key = r.version.toLowerCase();
        const existing = merged.get(key);
        merged.set(key, {
            version: r.version,
            active: Boolean(r.active) || (existing ? existing.active : false),
            cached: Boolean(r.cached) || cachedMap.has(key),
            channel: r.channel || (existing ? existing.channel : 'stable'),
            size: r.size || 0
        });
    }

    const entries = Array.from(merged.values()).sort((a, b) => compareSemver(b.version, a.version));
    if (entries.length === 0) {
        const msg = remoteError
            ? `No cached Aerix toolchains found and GitHub Releases could not be reached (${remoteError}).`
            : 'No Aerix versions >= 1.1.3b were found locally or on GitHub Releases.';
        vscode.window.showInformationMessage(msg);
        return;
    }

    const items = entries.map((e) => {
        const tags = [];
        if (e.active) tags.push('$(check) active');
        tags.push(e.cached ? 'cached (offline ready)' : 'download');
        tags.push(e.channel);
        if (!e.cached && e.size > 0) {
            tags.push(`${(e.size / (1024 * 1024)).toFixed(1)} MB`);
        }
        return {
            label: `v${e.version}`,
            description: tags.join('  •  '),
            detail: e.cached ? 'Switches immediately from local toolchain cache' : `Downloads & installs v${e.version} from GitHub Releases`,
            version: e.version,
            active: e.active
        };
    });

    const picked = await vscode.window.showQuickPick(items, {
        title: `Aerix Version Manager (current: ${localData.activeVersion ? 'v' + localData.activeVersion : 'unknown'})`,
        placeHolder: 'Select an Aerix version (>= 1.1.3b) to install or switch to'
    });
    if (!picked) return;
    if (picked.active) {
        vscode.window.showInformationMessage(`Aerix v${picked.version} is already active.`);
        return;
    }

    aerixUpdateInFlight = true;
    try {
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: `Switching Aerix to v${picked.version}...`,
            cancellable: false
        }, async (progress) => {
            output.appendLine(`[Aerix VM] Switching to v${picked.version}...`);
            progress.report({ message: 'Stopping Aerix LSP server...' });
            await client.stop();
            progress.report({ message: `Activating v${picked.version}...` });
            await execAsync(uninst, [`--vm-use=${picked.version}`, '--silent', '--quiet']);
            progress.report({ message: 'Restarting Aerix LSP server...' });
            await client.restart();
            if (statusBar) await refreshAerixStatusBar(statusBar);
        });

        const reloadChoice = await vscode.window.showInformationMessage(
            `Switched active Aerix toolchain to v${picked.version}. Reload window if extension features changed.`,
            'Reload Window',
            'OK'
        );
        if (reloadChoice === 'Reload Window') {
            await vscode.commands.executeCommand('workbench.action.reloadWindow');
        }
    } catch (err) {
        output.appendLine(`[Aerix VM] Switch failed: ${err && err.message ? err.message : err}`);
        vscode.window.showErrorMessage(`Failed to switch Aerix to v${picked.version}: ${err && err.message ? err.message : err}`);
        try { await client.restart(); } catch (_) {}
    } finally {
        aerixUpdateInFlight = false;
    }
}

function deactivate() {}

module.exports = { activate, deactivate };
