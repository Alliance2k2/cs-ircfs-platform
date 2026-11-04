"""Export missing Kinyarwanda strings for native review, or check a reviewed pack."""
import argparse
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PATTERN=re.compile(r'^\s*"([^"\n]+)"\s*:\s*("(?:[^"\\]|\\.)*")',re.M)


def messages(path):
    return {key:json.loads(value) for key,value in PATTERN.findall(path.read_text(encoding="utf-8-sig"))}


def package():
    english={**messages(ROOT/'frontend/src/i18n/en.ts'),**messages(ROOT/'frontend/src/i18n/en.workspaces.ts'),**messages(ROOT/'frontend/src/i18n/en.operations.ts')}
    rw=messages(ROOT/'frontend/src/i18n/rw.ts')
    return {"language":"rw","review_status":"pending_native_review","reviewer":"","evidence_reference":"",
        "note":"Review terminology and placeholders with field staff. This export does not claim translation or field acceptance.",
        "entries":[{"key":key,"english":value,"kinyarwanda":rw.get(key,""),"approved":False} for key,value in sorted(english.items())]}


def check(pack):
    expected={r['key']:r['english'] for r in package()['entries']}
    rows={r['key']:r for r in pack.get('entries',[])}
    errors=[]
    if pack.get("review_status")!="approved_native_review":errors.append("Native review status must be approved_native_review")
    if len(rows)!=len(pack.get("entries",[])):errors.append("Duplicate translation keys")
    if set(rows)-set(expected):errors.append("Unknown translation keys")
    if not str(pack.get('reviewer','')).strip() or not str(pack.get('evidence_reference','')).strip():errors.append('Native reviewer and evidence reference are required')
    for key,english in expected.items():
        row=rows.get(key,{})
        target=str(row.get('kinyarwanda','')).strip()
        if row.get('english')!=english or not target or row.get('approved') is not True:errors.append(key)
        elif sorted(re.findall(r'\{[^{}]+\}',english))!=sorted(re.findall(r'\{[^{}]+\}',target)):errors.append(key+': placeholder mismatch')
    return errors


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--check-reviewed',type=Path)
    parser.add_argument('--apply-reviewed',action='store_true',help='Apply only a fully reviewed valid pack to rw.ts')
    args=parser.parse_args()
    if args.check_reviewed:
        errors=check(json.loads(args.check_reviewed.read_text(encoding='utf-8-sig')))
        print(json.dumps({'accepted':not errors,'missing_or_invalid':errors},ensure_ascii=False,indent=2))
        if args.apply_reviewed and not errors:
            pack=json.loads(args.check_reviewed.read_text(encoding='utf-8-sig'))
            translated={row['key']:row['kinyarwanda'] for row in pack['entries']}
            content='import type { MessageKey } from "./en";\nexport const rw: Partial<Record<MessageKey, string>> = '+json.dumps(translated,ensure_ascii=False,indent=2)+';\n'
            (ROOT/'frontend/src/i18n/rw.ts').write_text(content,encoding='utf-8')
        raise SystemExit(bool(errors))
    if args.apply_reviewed:parser.error("--apply-reviewed requires --check-reviewed")
    pack=package()
    output=json.dumps(pack,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(output,encoding='utf-8')
    else:print(output)

if __name__=='__main__':main()
