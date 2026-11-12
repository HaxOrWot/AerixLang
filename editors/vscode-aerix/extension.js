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

const SEMANTIC_LEGEND = new vscode.SemanticTokensLegend(TOKEN_TYPES, TOKEN_MODIFIERS);

function resolveAerixBinary() {
    const cfgPath = (vscode.workspace.getConfiguration('aerix').get('executablePath') || '').trim();
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

    stop() {
        const proc = this.proc;
        this.proc = null;
        this.ready = null;
        this.initialized = false;
        this.openedUris.clear();
        for (const [, p] of this.pending) p.resolve(null);
        this.pending.clear();
        if (proc) {
            try { proc.kill(); } catch (_) {}
        }
    }

    restart() {
        this.stop();
        return this.start();
    }

    async _spawnAndInit() {
        const bin = resolveAerixBinary();
        this.output.appendLine(`[Aerix LSP] Starting: ${bin} lsp`);
        this.initialized = false;
        this.openedUris.clear();
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

    async stop() {
        for (const [, pending] of this.dirtyTimers) clearTimeout(pending.timer);
        this.dirtyTimers.clear();
        for (const [, t] of this.diagTimers) clearTimeout(t);
        this.diagTimers.clear();
        if (!this.proc) return;
        try {
            await this._requestRaw('shutdown', null, 2000);
            this._send({ jsonrpc: '2.0', method: 'exit', params: null });
        } catch {
            // ignore
        }
        if (this.proc) this.proc.kill();
        this.proc = null;
        this.initialized = false;
        this.openedUris.clear();
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
        }, '.', '>', ':', '<', '"', '/'),

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
        }, { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] })
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

    context.subscriptions.push(
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
            checkAndApplyUpdates(context, client, output, true);
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
    cands.push('C:\\Aerix\\Uninstall.exe');
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

async function checkAndApplyUpdates(context, client, output, isManual) {
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

function deactivate() {}

module.exports = { activate, deactivate };
