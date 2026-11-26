"""Structural citation checks; not semantic entailment."""
import re


def validate(answer, sources):
    valid = {source["id"] for source in sources}
    cited = set(re.findall(r"\[([^\]\n]+)\]", answer))
    if not answer.strip() or len(answer) > 8000 or not cited or not cited <= valid:
        raise ValueError("Unsupported citations")
    for paragraph in answer.split("\n\n"):
        if paragraph.strip() and not re.search(r"\[[^\]\n]+\]", paragraph):
            raise ValueError("Uncited paragraph")
    return True


def validate_extractive(answer, sources):
    """Accept complete verbatim evidence sentences only, with their own citations.

    This establishes text provenance, not source truth or a semantic guarantee for
    arbitrary paraphrases. Quote selection can still omit relevant context.
    """
    validate(answer, sources)
    collection = {source["id"]: source["text"] for source in sources}
    for paragraph in answer.split("\n\n"):
        cited = re.findall(r"\[([^\]\n]+)\]", paragraph)
        quotation = re.sub(r"\[[^\]\n]+\]", "", paragraph).strip().strip('"“”')
        quotation = " ".join(quotation.split())
        if len(quotation) < 20 or quotation[-1:] not in ".!?":
            raise ValueError("Complete evidence sentences required")
        supported = False
        for source_id in cited:
            evidence = " ".join(collection[source_id].split())
            offset = evidence.find(quotation)
            if offset >= 0 and (offset == 0 or evidence[:offset].rstrip()[-1:] in ".!?"):
                supported = True
                break
        if not supported:
            raise ValueError("Generated passage is not a verbatim supporting source quotation")
    return True


def attribute_quotations(answer, sources):
    """Attribute uncited local-model quotations only by exact verified provenance.

    Explicit forged citations, paraphrases and new claims are never repaired.
    """
    paragraphs = []
    for paragraph in answer.strip().split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if re.search(r"\[[^\]\n]+\]", paragraph):
            validate_extractive(paragraph, sources)
            paragraphs.append(paragraph)
            continue
        for source in sources:
            candidate = paragraph + f" [{source['id']}]"
            try:
                validate_extractive(candidate, [source])
            except ValueError:
                continue
            paragraphs.append(candidate)
            break
        else:
            raise ValueError("Local model passage has no exact supporting quotation")
    attributed = "\n\n".join(paragraphs)
    validate_extractive(attributed, sources)
    return attributed
