from scripts.translation_review import package,check


def test_translation_review_requires_native_approval_and_preserves_placeholders():
    pack=package()
    assert len(pack['entries'])>400
    assert check(pack)
    pack['review_status']='approved_native_review'
    pack['reviewer']='Native test reviewer'
    pack['evidence_reference']='Review test fixture'
    for row in pack['entries']:
        row['kinyarwanda']=row['english']
        row['approved']=True
    assert check(pack)==[]
    row=next(row for row in pack['entries'] if '{' in row['english'])
    row['kinyarwanda']='Missing required placeholders'
    assert any('placeholder mismatch' in item for item in check(pack))


def test_assistant_review_preserves_english_and_draft_kinyarwanda_separately():
    entries={row['key']:row for row in package()['entries']}
    assert entries['assistant.question']['english']=='Your question'
    assert entries['assistant.question']['kinyarwanda']=='Ikibazo cyawe'
    assert entries['assistant.question']['approved'] is False
