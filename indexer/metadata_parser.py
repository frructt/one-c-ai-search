from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree


ATTRIBUTE_TAGS = {"attribute", "dimension", "resource", "requisite"}
TABULAR_SECTION_TAGS = {"tabularsection", "tablesection", "tablepart"}
FORM_TAGS = {"form"}
COMMAND_TAGS = {"command"}
NAME_TAGS = {"name", "имя"}
SYNONYM_TAGS = {"synonym", "синоним"}
COMMENT_TAGS = {"comment", "комментарий", "description", "описание"}


@dataclass
class ParsedMetadataFile:
    synonym: str = ""
    comment: str = ""
    attributes: list[str] = field(default_factory=list)
    tabular_sections: list[str] = field(default_factory=list)
    forms: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)


class MetadataParseError(RuntimeError):
    pass


def parse_metadata_xml(path: Path) -> ParsedMetadataFile:
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        raise MetadataParseError(str(exc)) from exc

    return ParsedMetadataFile(
        synonym=first_descendant_text(root, SYNONYM_TAGS),
        comment=first_descendant_text(root, COMMENT_TAGS),
        attributes=extract_named_items(root, ATTRIBUTE_TAGS),
        tabular_sections=extract_named_items(root, TABULAR_SECTION_TAGS),
        forms=extract_named_items(root, FORM_TAGS),
        commands=extract_named_items(root, COMMAND_TAGS),
    )


def extract_named_items(root: ElementTree.Element, tag_names: set[str]) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for element in root.iter():
        if local_name(element.tag).lower() not in tag_names:
            continue
        label = element_label(element)
        if not label:
            continue
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(label)
    return items


def element_label(element: ElementTree.Element) -> str:
    name = first_child_text(element, NAME_TAGS) or _attribute_text(element, NAME_TAGS)
    synonym = first_child_text(element, SYNONYM_TAGS)
    comment = first_child_text(element, COMMENT_TAGS)
    values = unique_non_empty([name, synonym, comment])
    if values:
        return " / ".join(values)
    if len(list(element)) == 0:
        return normalize_text(element.text or "")
    return ""


def first_descendant_text(root: ElementTree.Element, tag_names: set[str]) -> str:
    for element in root.iter():
        if local_name(element.tag).lower() in tag_names:
            text = normalize_text(" ".join(element.itertext()))
            if text:
                return text
    return ""


def first_child_text(element: ElementTree.Element, tag_names: set[str]) -> str:
    for child in list(element):
        if local_name(child.tag).lower() in tag_names:
            text = normalize_text(" ".join(child.itertext()))
            if text:
                return text
    return ""


def local_name(tag: str) -> str:
    if "}" in tag:
        tag = tag.rsplit("}", 1)[1]
    if ":" in tag:
        tag = tag.rsplit(":", 1)[1]
    return tag


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def unique_non_empty(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = normalize_text(value)
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _attribute_text(element: ElementTree.Element, names: set[str]) -> str:
    for key, value in element.attrib.items():
        if local_name(key).lower() in names:
            return normalize_text(value)
    return ""
