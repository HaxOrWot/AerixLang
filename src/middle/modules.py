"""
Aerix Compiler (arxc) — Phase 25: Multi-File Module System & Package Integration
Handles:
1. Inbuilt Language Modules (e.g. 'import Math'):
   - Case-sensitive folder bundling under 'modules/<ModuleName>/'
   - Pure .arx format
   - Dynamic file discovery (automatically detects all .arx files and subfolders)
   - Compilation verification & registration lockfile (.module_verified)
   - Qualified (Math.abs) and direct (abs) access
2. User Source Files (e.g. 'import "./test.arx"'):
   - User-created multi-file compilation
   - Relative and absolute file paths
3. Selective Symbol Imports (e.g. 'import { a, b } from "..."'):
   - Selective filtering of exported symbols
4. Dependency Graph & Cycle Detection:
   - Topological dependency resolution and circular import rejection
5. Package Manifest Integration (aerix.toml):
   - Project dependencies and package resolution
"""

import os
import sys
import json
import hashlib
from typing import List, Set, Dict, Optional, Tuple, Any
from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.frontend.ast_nodes import (
    ProgramNode, ImportNode, ASTNode, MemberAccessNode, IdentifierNode, CallNode,
    FunctionDefNode, VarDeclNode, ClassDefNode, EnumDefNode, TraitDefNode, ExtendDefNode
)
from src.frontend.diagnostics import AerixDiagnostic, format_source_snippet


class ModuleError(AerixDiagnostic):
    """Base exception for module and multi-file resolution errors."""
    def __init__(self, message: str, target: str = "", filename: str = "<stdin>", line: int = 1, col: int = 1, hint: Optional[str] = None):
        self.message = message
        self.target = target
        self.filename = filename
        self.line = line
        self.col = col
        self.hint = hint
        source_line = f"import {target};" if target else ""
        formatted = format_source_snippet(
            file=filename,
            line=line,
            col=col,
            source_line=source_line,
            message=message,
            error_type="MODULE ERROR",
            hint=hint
        )
        super().__init__(formatted)


class ModuleNotFoundError(ModuleError):
    pass


class ModuleCaseError(ModuleError):
    pass


class ModuleCircularError(ModuleError):
    pass


class ModuleSymbolNotFoundError(ModuleError):
    pass


class ModuleVerificationError(ModuleError):
    """Raised when a module fails compilation or semantic verification and cannot be registered."""
    pass


def tag_ast_filename(node: Any, filename: str) -> None:
    """Recursively tags AST nodes with their originating source filename for accurate diagnostics."""
    if node is None or isinstance(node, (int, float, str, bool, bytes)):
        return
    if isinstance(node, ASTNode) and getattr(node, "filename", None) is None:
        try:
            node.filename = filename
        except Exception:
            pass
    if hasattr(node, "__dict__"):
        for val in node.__dict__.values():
            if isinstance(val, list):
                for item in val:
                    tag_ast_filename(item, filename)
            elif isinstance(val, ASTNode):
                tag_ast_filename(val, filename)


def extract_referenced_symbols(node: Any) -> Set[str]:
    """
    Recursively extracts all identifier and type symbols referenced by an AST node.
    Used to compute transitive dependency closures when importing selective symbols.
    """
    symbols: Set[str] = set()
    if node is None or isinstance(node, (int, float, str, bool, bytes)):
        return symbols

    def clean_type_name(tname: Optional[str]) -> Optional[str]:
        if not tname:
            return None
        clean = tname.strip().lstrip("&").strip()
        if clean.startswith("mut "):
            clean = clean[4:].strip()
        if "[" in clean:
            inner = clean.strip("[]")
            clean = inner.split(";")[0].strip()
        clean = clean.split("<")[0].strip()
        return clean if clean and clean.isidentifier() else None

    node_type = type(node).__name__

    if hasattr(node, "name") and isinstance(node.name, str) and node_type == "IdentifierNode":
        symbols.add(node.name)

    if hasattr(node, "class_name") and isinstance(node.class_name, str):
        c = clean_type_name(node.class_name)
        if c:
            symbols.add(c)

    if hasattr(node, "base_class") and isinstance(node.base_class, str):
        c = clean_type_name(node.base_class)
        if c:
            symbols.add(c)

    if hasattr(node, "traits") and isinstance(node.traits, list):
        for tr in node.traits:
            if isinstance(tr, str) and tr.isidentifier():
                symbols.add(tr)

    if hasattr(node, "return_type") and isinstance(node.return_type, str):
        c = clean_type_name(node.return_type)
        if c:
            symbols.add(c)

    if hasattr(node, "type_name") and isinstance(node.type_name, str):
        c = clean_type_name(node.type_name)
        if c:
            symbols.add(c)

    if hasattr(node, "target_type") and isinstance(node.target_type, str):
        c = clean_type_name(node.target_type)
        if c:
            symbols.add(c)

    if hasattr(node, "__dict__"):
        for k, v in node.__dict__.items():
            if k in ("name", "line", "col", "filename", "source_lines", "resolved_mangled_name", "resolved_type"):
                continue
            if isinstance(v, list):
                for item in v:
                    symbols.update(extract_referenced_symbols(item))
            elif isinstance(v, dict):
                for item in v.values():
                    symbols.update(extract_referenced_symbols(item))
            elif isinstance(v, ASTNode):
                symbols.update(extract_referenced_symbols(v))

    return symbols


def filter_declarations_with_dependencies(
    declarations: List[ASTNode],
    requested_symbols: Optional[List[str]] = None
) -> List[ASTNode]:
    """
    Filters declarations for module/file imports:
    1. Always strips 'fn main()' since main is only the entrypoint for the root file.
    2. If requested_symbols is provided, computes transitive dependency closure so that
       any helper functions, types, and constants required by the requested symbols
       are automatically preserved.
    3. If requested_symbols is None/empty, includes all declarations except 'main'.
    """
    # 1. Exclude 'fn main()' from any imported unit
    non_main = [
        d for d in declarations
        if not (isinstance(d, FunctionDefNode) and d.name == "main")
    ]

    if not requested_symbols:
        return non_main

    # 2. Build index of available named declarations
    decls_by_name: Dict[str, ASTNode] = {}
    for d in non_main:
        name = getattr(d, "name", None)
        if name:
            decls_by_name[name] = d

    # 3. Compute transitive closure
    needed_names: Set[str] = set(requested_symbols)
    queue = list(requested_symbols)

    while queue:
        curr_name = queue.pop(0)
        decl = decls_by_name.get(curr_name)
        if decl:
            refs = extract_referenced_symbols(decl)
            for ref in refs:
                if ref in decls_by_name and ref not in needed_names:
                    needed_names.add(ref)
                    queue.append(ref)

    # 4. Filter declarations matching closure or unnamed extensions of needed types
    result = []
    for d in non_main:
        name = getattr(d, "name", None)
        if name is not None:
            if name in needed_names:
                result.append(d)
        else:
            if isinstance(d, ExtendDefNode):
                if d.class_name in needed_names:
                    result.append(d)
            else:
                result.append(d)

    return result


class ModuleResolver:
    """
    Orchestrates Phase 25 multi-file compilation and module resolution.
    Differentiates between:
      - Inbuilt language modules (e.g. `import Math`) living in `modules/<ModuleName>/`
      - User-created source files (e.g. `import "./test.arx"`) resolved relative to source
    """

    def __init__(self, base_filename: str = "<stdin>", search_paths: Optional[List[str]] = None):
        self.base_filename = os.path.abspath(base_filename) if base_filename != "<stdin>" else "<stdin>"
        self.search_paths = self._compute_search_paths(search_paths)
        self.loaded_modules: Set[str] = set()
        self.loaded_files: Set[str] = set()
        self.resolving_stack: List[str] = []
        self.module_symbols: Dict[str, Set[str]] = {}

    def _compute_search_paths(self, custom_paths: Optional[List[str]] = None) -> List[str]:
        paths = []
        if custom_paths:
            paths.extend(custom_paths)

        # 1. Environment variable AERIX_MODULE_PATH
        env_paths = os.environ.get("AERIX_MODULE_PATH", "")
        if env_paths:
            for p in env_paths.split(os.pathsep):
                if p.strip():
                    paths.append(os.path.abspath(p.strip()))

        # 2. aerix.toml project manifest search
        project_root = self._find_project_root()
        if project_root:
            manifest_modules = os.path.join(project_root, "modules")
            paths.append(manifest_modules)

        # 3. modules/ directory in compiler repository root
        here = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(here, "..", ".."))
        root_modules = os.path.join(repo_root, "modules")
        paths.append(root_modules)

        # 4. modules/ directory next to input file
        if self.base_filename and self.base_filename != "<stdin>":
            file_dir = os.path.dirname(self.base_filename)
            paths.append(os.path.join(file_dir, "modules"))

        # 5. modules/ directory in current working directory
        paths.append(os.path.join(os.getcwd(), "modules"))

        # Deduplicate while preserving order
        unique_paths: List[str] = []
        for p in paths:
            norm = os.path.normcase(os.path.abspath(p))
            if norm not in [os.path.normcase(x) for x in unique_paths]:
                unique_paths.append(os.path.abspath(p))

        return unique_paths

    def _find_project_root(self) -> Optional[str]:
        """Finds closest parent directory containing aerix.toml."""
        start_dir = os.path.dirname(self.base_filename) if self.base_filename != "<stdin>" else os.getcwd()
        cur = os.path.abspath(start_dir)
        while True:
            if os.path.isfile(os.path.join(cur, "aerix.toml")):
                return cur
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
        return None

    def find_inbuilt_module_dir(self, module_name: str, node: ImportNode) -> str:
        """
        Locates the directory for inbuilt module `module_name`.
        Enforces strict case sensitivity even on Windows NTFS.
        """
        case_mismatches = []
        for parent_dir in self.search_paths:
            if not os.path.isdir(parent_dir):
                continue
            try:
                entries = os.listdir(parent_dir)
            except OSError:
                continue

            for entry in entries:
                full_path = os.path.join(parent_dir, entry)
                if os.path.isdir(full_path):
                    if entry == module_name:
                        return full_path
                    elif entry.lower() == module_name.lower():
                        case_mismatches.append((entry, parent_dir))

        if case_mismatches:
            actual_name, pdir = case_mismatches[0]
            raise ModuleCaseError(
                f"Inbuilt module '{module_name}' cannot be imported due to a case mismatch.\n"
                f"The directory on disk is named '{actual_name}', but was imported as '{module_name}'.\n"
                f"In Aerix, module imports are strictly case-sensitive.",
                target=module_name,
                filename=self.base_filename,
                line=node.line,
                col=node.col,
                hint=f"Rename the import to 'import {actual_name}' or rename directory '{pdir}\\{actual_name}'."
            )

        searched = "\n".join(f"  - {sp}" for sp in self.search_paths)
        raise ModuleNotFoundError(
            f"Inbuilt module '{module_name}' could not be found.\nSearched directories:\n{searched}",
            target=module_name,
            filename=self.base_filename,
            line=node.line,
            col=node.col,
            hint=f"Ensure a folder named '{module_name}' containing pure .arx files exists in the modules directory."
        )

    def resolve_user_file_path(self, file_path: str, node: ImportNode) -> str:
        """
        Resolves a user-created source file path relative to the importing file.
        """
        if os.path.isabs(file_path):
            candidate = os.path.normpath(file_path)
        else:
            base_dir = os.path.dirname(self.base_filename) if self.base_filename != "<stdin>" else os.getcwd()
            candidate = os.path.normpath(os.path.join(base_dir, file_path))

        if not os.path.isfile(candidate):
            # Also try appending .arx if omitted
            if not candidate.endswith(".arx") and os.path.isfile(candidate + ".arx"):
                candidate = candidate + ".arx"
            else:
                raise ModuleNotFoundError(
                    f"User source file '{file_path}' does not exist (resolved to '{candidate}').",
                    target=file_path,
                    filename=self.base_filename,
                    line=node.line,
                    col=node.col,
                    hint="Verify the relative file path and ensure the user source file exists."
                )

        return candidate

    def _compute_files_hash(self, files: List[str]) -> str:
        hasher = hashlib.sha256()
        for fpath in sorted(files):
            hasher.update(os.path.basename(fpath).encode("utf-8"))
            try:
                with open(fpath, "rb") as f:
                    hasher.update(f.read())
            except OSError:
                pass
        return hasher.hexdigest()

    def verify_and_register_module(
        self,
        module_dir: str,
        module_name: str,
        arx_files: List[str],
        node: Optional[ImportNode] = None
    ) -> Dict[str, Any]:
        """
        Compiles and verifies all .arx files in a module.
        Only registers the module if all files compile cleanly with zero errors.
        Writes .module_verified lockfile upon successful verification.
        """
        manifest_path = os.path.join(module_dir, ".module_verified")
        current_hash = self._compute_files_hash(arx_files)

        # Check if already verified with matching content hash
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("hash") == current_hash and meta.get("verified") is True:
                    return meta
            except Exception:
                pass

        # Module requires compilation & verification
        collected_symbols: Set[str] = set()
        from src.middle.semantic import SemanticAnalyzer
        module_decls: List[ASTNode] = []

        for fpath in arx_files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    source = f.read()
                lines = source.splitlines()
                lexer = Lexer(source, filename=fpath)
                tokens = lexer.tokenize()
                parser = Parser(tokens, lines, filename=fpath)
                ast = parser.parse()

                for d in ast.declarations:
                    name = getattr(d, "name", None)
                    if name:
                        collected_symbols.add(name)
                    module_decls.append(d)
            except Exception as e:
                line = getattr(node, "line", 1) if node else 1
                col = getattr(node, "col", 1) if node else 1
                raise ModuleVerificationError(
                    f"Module '{module_name}' failed compilation check on '{os.path.basename(fpath)}':\n{str(e)}",
                    target=module_name,
                    filename=self.base_filename,
                    line=line,
                    col=col,
                    hint="Fix syntax and grammar errors before registering the module."
                )

        # Semantic Type Verification
        try:
            combined_ast = ProgramNode(1, 1, declarations=module_decls)
            analyzer = SemanticAnalyzer(module_name, ["// module verification check"])
            analyzer.analyze(combined_ast)
        except Exception as e:
            line = getattr(node, "line", 1) if node else 1
            col = getattr(node, "col", 1) if node else 1
            raise ModuleVerificationError(
                f"Module '{module_name}' failed semantic type verification:\n{str(e)}",
                target=module_name,
                filename=self.base_filename,
                line=line,
                col=col,
                hint="Ensure all variable types, function calls, and expressions in the module are valid."
            )

        # Verification succeeded! Register the module
        meta = {
            "module": module_name,
            "verified": True,
            "hash": current_hash,
            "files": [os.path.relpath(f, module_dir) for f in arx_files],
            "symbols": sorted(list(collected_symbols)),
            "registered_at": os.path.getmtime(arx_files[0]) if arx_files else 0
        }

        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except OSError:
            pass

        return meta

    def resolve(self, program: ProgramNode) -> ProgramNode:
        """
        Scans ProgramNode for ImportNodes, resolves each user file or inbuilt module,
        bundles declarations in topological dependency order, checks for cycles,
        applies selective symbol filtering if requested, and rewrites qualified module access.
        """
        new_declarations: List[ASTNode] = []
        for decl in program.declarations:
            if isinstance(decl, ImportNode):
                mod_decls = self.resolve_import_node(decl)
                new_declarations.extend(mod_decls)
            else:
                new_declarations.append(decl)

        program.declarations = new_declarations

        # Rewrite qualified access: Module.symbol -> symbol
        self._rewrite_qualified_access(program)
        return program

    def resolve_import_node(self, node: ImportNode) -> List[ASTNode]:
        if node.is_user_file or node.file_path:
            return self._resolve_user_file_import(node)
        else:
            return self._resolve_inbuilt_module_import(node)

    def _resolve_user_file_import(self, node: ImportNode) -> List[ASTNode]:
        file_path_str = node.file_path or ""
        resolved_path = self.resolve_user_file_path(file_path_str, node)
        norm_key = os.path.normcase(os.path.abspath(resolved_path))

        if norm_key in self.resolving_stack:
            chain = " -> ".join(self.resolving_stack + [norm_key])
            raise ModuleCircularError(
                f"Circular file dependency detected: {chain}",
                target=file_path_str,
                filename=self.base_filename,
                line=node.line,
                col=node.col,
                hint="Refactor file dependencies into a Directed Acyclic Graph (DAG) to avoid cyclic imports."
            )

        if norm_key in self.loaded_files:
            return []

        self.resolving_stack.append(norm_key)
        declarations: List[ASTNode] = []

        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                source = f.read()

            lines = source.splitlines()
            lexer = Lexer(source, filename=resolved_path)
            tokens = lexer.tokenize()
            parser = Parser(tokens, lines, filename=resolved_path)
            file_ast = parser.parse()

            # Recursively resolve any imports in the child user file
            nested_resolver = ModuleResolver(base_filename=resolved_path, search_paths=self.search_paths)
            nested_resolver.loaded_modules = self.loaded_modules
            nested_resolver.loaded_files = self.loaded_files
            nested_resolver.resolving_stack = self.resolving_stack
            nested_resolver.module_symbols = self.module_symbols
            file_ast = nested_resolver.resolve(file_ast)

            tag_ast_filename(file_ast, resolved_path)

            exported_symbols = set()
            for d in file_ast.declarations:
                name = getattr(d, "name", None)
                if name and not (isinstance(d, FunctionDefNode) and name == "main"):
                    exported_symbols.add(name)

            # Filter selective imports if requested: import { a, b } from "./file.arx"
            if node.symbols:
                for req in node.symbols:
                    if req not in exported_symbols:
                        raise ModuleSymbolNotFoundError(
                            f"Symbol '{req}' was requested in selective import, but was not found in user file '{file_path_str}'.",
                            target=file_path_str,
                            filename=self.base_filename,
                            line=node.line,
                            col=node.col,
                            hint=f"Available symbols in '{os.path.basename(resolved_path)}': {', '.join(sorted(exported_symbols))}"
                        )
                declarations.extend(filter_declarations_with_dependencies(file_ast.declarations, node.symbols))
            else:
                declarations.extend(filter_declarations_with_dependencies(file_ast.declarations, None))

            self.loaded_files.add(norm_key)
        finally:
            self.resolving_stack.pop()

        return declarations

    def _resolve_inbuilt_module_import(self, node: ImportNode) -> List[ASTNode]:
        module_name = node.module_name or ""
        if module_name in self.resolving_stack:
            chain = " -> ".join(self.resolving_stack + [module_name])
            raise ModuleCircularError(
                f"Circular module dependency detected: {chain}",
                target=module_name,
                filename=self.base_filename,
                line=node.line,
                col=node.col,
                hint="Refactor module dependencies to avoid cyclic imports."
            )

        if module_name in self.loaded_modules:
            return []

        module_dir = self.find_inbuilt_module_dir(module_name, node)

        # Dynamically discover all .arx files in the module folder (including subdirectories)
        arx_files: List[str] = []
        for root_dir, _, files in os.walk(module_dir):
            for f in sorted(files):
                if f.endswith(".arx"):
                    arx_files.append(os.path.normpath(os.path.join(root_dir, f)))
        arx_files.sort()

        if not arx_files:
            raise ModuleError(
                f"Inbuilt module '{module_name}' at '{module_dir}' contains no .arx source files.",
                target=module_name,
                filename=self.base_filename,
                line=node.line,
                col=node.col,
                hint="Add at least one pure Aerix (.arx) source file to this module directory."
            )

        # Verify and Register Module before allowing import
        self.verify_and_register_module(module_dir, module_name, arx_files, node)

        self.resolving_stack.append(module_name)
        symbols_exported: Set[str] = set()
        module_declarations: List[ASTNode] = []

        try:
            for file_path in arx_files:
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()

                lines = source.splitlines()
                lexer = Lexer(source, filename=file_path)
                tokens = lexer.tokenize()
                parser = Parser(tokens, lines, filename=file_path)
                mod_ast = parser.parse()

                # Recursively resolve any imports within this module file
                nested_resolver = ModuleResolver(base_filename=file_path, search_paths=self.search_paths)
                nested_resolver.loaded_modules = self.loaded_modules
                nested_resolver.loaded_files = self.loaded_files
                nested_resolver.resolving_stack = self.resolving_stack
                nested_resolver.module_symbols = self.module_symbols
                mod_ast = nested_resolver.resolve(mod_ast)

                for d in mod_ast.declarations:
                    name = getattr(d, "name", None)
                    if name and not (isinstance(d, FunctionDefNode) and name == "main"):
                        symbols_exported.add(name)
                    module_declarations.append(d)

            self.loaded_modules.add(module_name)
            self.module_symbols[module_name] = symbols_exported

            # Selective import filtering: import { a, b } from Math
            if node.symbols:
                for req in node.symbols:
                    if req not in symbols_exported:
                        raise ModuleSymbolNotFoundError(
                            f"Symbol '{req}' was requested in selective import, but was not found in module '{module_name}'.",
                            target=module_name,
                            filename=self.base_filename,
                            line=node.line,
                            col=node.col,
                            hint=f"Available symbols in '{module_name}': {', '.join(sorted(symbols_exported))}"
                        )
                return filter_declarations_with_dependencies(module_declarations, node.symbols)
            else:
                return filter_declarations_with_dependencies(module_declarations, None)

        finally:
            self.resolving_stack.pop()

        return module_declarations

    def _rewrite_qualified_access(self, root: ASTNode) -> None:
        """
        Traverses the AST and rewrites MemberAccessNode(IdentifierNode(ModuleName), 'symbol')
        into IdentifierNode('symbol') for symbols exported by ModuleName.
        If accessed as a field/constant (e.g. Math.PI), rewrites to CallNode(IdentifierNode('PI'), [])
        if 'PI' is a zero-argument function.
        """
        def rewrite_node(node: Any) -> Any:
            if node is None or not isinstance(node, ASTNode):
                return node

            # Check if this node is CallNode with callee = MemberAccessNode(IdentifierNode(mod), member)
            if isinstance(node, CallNode) and isinstance(node.callee, MemberAccessNode):
                if isinstance(node.callee.object_expr, IdentifierNode):
                    mod_name = node.callee.object_expr.name
                    if mod_name in self.module_symbols:
                        if node.callee.member in self.module_symbols[mod_name]:
                            node.callee = IdentifierNode(
                                line=node.callee.line,
                                col=node.callee.col,
                                name=node.callee.member
                            )

            # Check if this node is standalone MemberAccessNode(IdentifierNode(mod), member)
            elif isinstance(node, MemberAccessNode):
                if isinstance(node.object_expr, IdentifierNode):
                    mod_name = node.object_expr.name
                    if mod_name in self.module_symbols:
                        member = node.member
                        if member in self.module_symbols[mod_name]:
                            # If nullary constant function, rewrite to call
                            if member in ("PI", "E", "TAU", "SQRT2", "LN2", "LN10", "INF", "pi", "e", "tau"):
                                return CallNode(
                                    line=node.line,
                                    col=node.col,
                                    callee=IdentifierNode(line=node.line, col=node.col, name=member),
                                    args=[]
                                )
                            return IdentifierNode(line=node.line, col=node.col, name=member)

            # Traverse child fields
            for field_name, value in list(getattr(node, "__dict__", {}).items()):
                if isinstance(value, list):
                    setattr(node, field_name, [rewrite_node(item) for item in value])
                elif isinstance(value, ASTNode):
                    setattr(node, field_name, rewrite_node(value))

            return node

        rewrite_node(root)
