"""Read-only source hygiene and local Markdown link checks."""

import re
import ast
import json
import subprocess
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
import yaml

from lint import load_yaml, unique_json

MARKDOWN = MarkdownIt("commonmark").enable("table")
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".sh",
    ".js",
    ".cjs",
    ".json",
    ".yaml",
    ".yml",
    ".example",
    ".conf",
    ".persist",
    ".influx",
    ".toml",
    ".txt",
    ".items",
}


def hygiene(text):
    failures = []
    if "\r" in text:
        failures.append("use LF line endings")
    if "\0" in text:
        failures.append("unexpected NUL byte")
    if text and not text.endswith("\n"):
        failures.append("missing final newline")
    # Two spaces are meaningful Markdown hard breaks.
    for number, line in enumerate(text.splitlines(), 1):
        trailing = line[len(line.rstrip(" \t")) :]
        if trailing and trailing != "  ":
            failures.append(f"trailing whitespace at line {number}")
    return failures


def anchors(text):
    tokens = MARKDOWN.parse(text)
    result = set()
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        children = tokens[index + 1].children or []
        title = "".join(t.content for t in children if t.type in {"text", "code_inline"})
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        candidate = slug
        counter = 0
        while candidate in result:
            counter += 1
            candidate = f"{slug}-{counter}"
        result.add(candidate)
    # Explicit HTML anchors are also valid GitHub link targets.
    result.update(re.findall(r'(?:id|name)=["\']([^"\']+)["\']', text))
    return result


def markdown_links(path, root):
    failures = []
    for token in MARKDOWN.parse(path.read_text()):
        for child in token.children or []:
            if child.type not in {"link_open", "image"}:
                continue
            href = child.attrGet("href" if child.type == "link_open" else "src")
            parts = urlsplit(href)
            if parts.scheme or parts.netloc:
                continue
            relative = unquote(parts.path)
            target = (
                (
                    root / relative.lstrip("/")
                    if relative.startswith("/")
                    else path.parent / relative
                ).resolve()
                if relative
                else path
            )
            if not target.is_relative_to(root.resolve()):
                failures.append(f"local link escapes repository: {href}")
            elif not target.exists():
                failures.append(f"missing local link target: {href}")
            elif parts.fragment and target.suffix == ".md":
                if unquote(parts.fragment) not in anchors(target.read_text()):
                    failures.append(f"missing Markdown heading: {href}")
    return failures


def is_text(path):
    return path.suffix in TEXT_SUFFIXES or path.name in {"LICENSE", ".gitignore", ".node-version"}


def markdown_examples(text):
    failures = []
    for token in MARKDOWN.parse(text):
        if token.type != "fence":
            continue
        language = token.info.strip().split(" ")[0]
        try:
            if language in {"yaml", "yml"}:
                load_yaml(token.content)
            elif language == "json":
                json.loads(token.content, object_pairs_hook=unique_json)
            elif language == "python":
                ast.parse(token.content)
            elif language in {"bash", "sh", "shell"}:
                result = subprocess.run(
                    ["bash", "-n"], input=token.content, text=True, capture_output=True, check=False
                )
                if result.returncode:
                    raise ValueError("invalid Bash syntax")
        except (ValueError, TypeError, SyntaxError, yaml.YAMLError):
            failures.append(f"invalid {language} example at line {token.map[0] + 1}")
    return failures
