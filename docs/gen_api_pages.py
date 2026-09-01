"""Gera paginas de referencia de API automaticamente a partir do codigo Python.

Executado pelo plugin `mkdocs-gen-files` em cada build do site. Para cada
modulo em `src/semtree/`, cria uma pagina em `reference/<modulo>.md`
contendo `:::semtree.<modulo>` que o mkdocstrings expande para
documentacao gerada das docstrings.

Sem este script, cada modulo precisaria de pagina escrita a mao. Com ele,
basta escrever boas docstrings nos `.py` e a doc fica em sincronia automatica.
"""

from __future__ import annotations

from pathlib import Path

import mkdocs_gen_files

SRC = Path("src/semtree")
REFERENCE_ROOT = Path("reference")

# Módulos a documentar (caminhos relativos a src/semtree/)
MODULES_TO_DOCUMENT = [
    "config",
    "log",
    "cli",
    "mcp",
    "indexer",
    "retrieval",
    "context",
    "memory",
    "db",
    "scripts",
]


def _module_title(name: str) -> str:
    titles = {
        "cli": "CLI",
        "mcp": "Servidor MCP",
        "indexer": "Indexer (tree-sitter)",
        "retrieval": "Recuperação (exata, FTS5 e prefixo)",
        "context": "Geração de contexto",
        "memory": "Memória de prompts",
        "db": "Persistência (SQLite)",
        "config": "Configuração",
        "log": "Logging",
        "scripts": "Scripts auxiliares",
    }
    return titles.get(name, f"`{name}`")


nav = mkdocs_gen_files.Nav()


for module in MODULES_TO_DOCUMENT:
    module_path = SRC / module
    if module_path.is_dir():
        doc_path = REFERENCE_ROOT / module / "index.md"
        identifier = f"semtree.{module}"
    elif (SRC / f"{module}.py").is_file():
        doc_path = REFERENCE_ROOT / f"{module}.md"
        identifier = f"semtree.{module}"
    else:
        continue

    with mkdocs_gen_files.open(doc_path, "w") as fd:
        fd.write(f"# {_module_title(module)}\n\n")
        fd.write(f"::: {identifier}\n")
        fd.write("    options:\n")
        fd.write("      show_source: false\n")
        fd.write("      show_root_heading: false\n")
        fd.write("      show_submodules: true\n")
        fd.write("      members_order: source\n")
        fd.write("      docstring_style: google\n")
        fd.write("      separate_signature: true\n")
        fd.write("      filters:\n")
        fd.write("        - '!^_'\n")  # esconde _privates
        fd.write("      heading_level: 2\n")

    nav[(module,)] = f"{module}/index.md" if module_path.is_dir() else f"{module}.md"


with mkdocs_gen_files.open(REFERENCE_ROOT / "SUMMARY.md", "w") as fd:
    fd.writelines(nav.build_literate_nav())
