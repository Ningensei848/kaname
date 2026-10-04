import json
import os
from pathlib import Path

import pytest
import techkb.sync as sync_module
from techkb.sync import sync_vault
from techkb.cli import main


def test_sync_and_local_edit_conflict_without_deletion(harness,tmp_path):
    store=harness.store
    name='notes/2026/10/article.md'; store.data[name]=b'original'
    assert sync_vault(store,tmp_path)['written']==1
    assert sync_vault(store,tmp_path)['unchanged']==1
    path=tmp_path/'TechKB'/name; path.write_text('my annotation')
    store.data[name]=b'new remote'
    assert sync_vault(store,tmp_path)['conflicts']==1
    assert path.read_text()=='my annotation'
    del store.data[name]
    sync_vault(store,tmp_path)
    assert path.read_text()=='my annotation'
    assert not store.writes


def test_sync_remote_update_and_untracked_file(harness,tmp_path):
    store=harness.store; name='notes/a.md'; store.data[name]=b'first'
    sync_vault(store,tmp_path); store.data[name]=b'second'
    result=sync_vault(store,tmp_path)
    assert result['written']==0 and result['conflicts']==1 and result['incoming_written']==1
    path=tmp_path/'TechKB'/name
    assert path.read_bytes()==b'first'
    candidate=tmp_path/'TechKB'/result['updates'][0]['incoming']
    assert candidate.read_bytes()==b'second'
    manifest=json.loads((tmp_path/'TechKB/.techkb-sync.json').read_bytes())
    assert manifest[name]==sync_module.digest(b'first')
    repeated=sync_vault(store,tmp_path)
    assert repeated['incoming_written']==0 and repeated['updates'][0]['status']=='unchanged'
    untracked=tmp_path/'TechKB/notes/b.md'; untracked.write_text('mine')
    store.data['notes/b.md']=b'other'
    result=sync_vault(store,tmp_path)
    assert result['conflicts']==2 and untracked.read_text()=='mine'


@pytest.mark.parametrize('invalid',['notes/../../evil.md','notes/2026/../evil.md','notes/A.md'])
def test_validate_all_before_writes(harness,tmp_path,invalid):
    harness.store.data={'notes/a.md':b'good',invalid:b'bad'}
    with pytest.raises(ValueError):
        sync_vault(harness.store,tmp_path)
    assert not (tmp_path/'TechKB/notes/a.md').exists()


def test_symlink_cannot_escape_vault(harness,tmp_path):
    root=tmp_path/'TechKB'; root.mkdir(); (root/'notes').symlink_to(tmp_path/'elsewhere')
    harness.store.data['notes/a.md']=b'bad'
    with pytest.raises(ValueError):
        sync_vault(harness.store,tmp_path)


def test_cli_sync_preview_is_offline(harness,tmp_path,capsys):
    snapshot=tmp_path/'snapshot'; (snapshot/'notes').mkdir(parents=True)
    (snapshot/'notes/a.md').write_text('note')
    vault=tmp_path/'vault'
    assert main(['sync','--state-dir',str(snapshot),'--vault',str(vault),'--dry-run'])==0
    assert not (vault/'TechKB/notes/a.md').exists()
    assert '"planned": 1' in capsys.readouterr().out


def test_edit_between_planning_and_write_is_preserved(harness,tmp_path):
    h=harness; h.store.data={'notes/a.md':b'first','notes/b.md':b'other'}
    sync_vault(h.store,tmp_path)
    path=tmp_path/'TechKB/notes/a.md'; h.store.data['notes/a.md']=b'remote update'
    read=h.store.read
    def concurrent_read(name):
        if name=='notes/b.md': path.write_text('new local edit')
        return read(name)
    h.store.read=concurrent_read
    result=sync_vault(h.store,tmp_path)
    assert result['conflicts']==1 and path.read_text()=='new local edit'
    assert result['written']==0


@pytest.mark.parametrize('rename', [False, True])
def test_edit_during_candidate_publication_is_preserved(harness,tmp_path,monkeypatch,rename):
    store=harness.store; name='notes/a.md'; store.data[name]=b'first'
    sync_vault(store,tmp_path)
    path=tmp_path/'TechKB'/name; store.data[name]=b'remote update'
    original=sync_module.publish_new
    def concurrently_edited(destination,content):
        if rename:
            replacement=path.with_suffix('.editing')
            replacement.write_bytes(b'last moment edit')
            os.replace(replacement,path)
        else:
            path.write_bytes(b'last moment edit')
        return original(destination,content)
    monkeypatch.setattr(sync_module,'publish_new',concurrently_edited)
    result=sync_vault(store,tmp_path)
    assert result['conflicts']==1 and result['written']==0
    assert path.read_bytes()==b'last moment edit'
    assert (tmp_path/'TechKB'/result['updates'][0]['incoming']).read_bytes()==b'remote update'
    manifest=json.loads((tmp_path/'TechKB/.techkb-sync.json').read_bytes())
    assert manifest[name]==sync_module.digest(b'first')


def test_editor_after_unchanged_check_is_preserved(harness,tmp_path,monkeypatch):
    store=harness.store; store.data['notes/a.md']=b'first'
    sync_vault(store,tmp_path)
    path=tmp_path/'TechKB/notes/a.md'; original=sync_module.atomic
    def concurrently_edited(destination,content):
        if destination.name=='.techkb-sync.json':
            path.write_bytes(b'edit after final hash')
        original(destination,content)
    monkeypatch.setattr(sync_module,'atomic',concurrently_edited)
    sync_vault(store,tmp_path)
    assert path.read_bytes()==b'edit after final hash'
    monkeypatch.setattr(sync_module,'atomic',original)
    result=sync_vault(store,tmp_path)
    assert result['conflicts']==1 and path.read_bytes()==b'edit after final hash'


def test_new_file_created_during_atomic_publication_is_never_replaced(harness,tmp_path,monkeypatch):
    store=harness.store; store.data['notes/a.md']=b'remote'
    path=tmp_path/'TechKB/notes/a.md'; original=os.link
    def concurrently_created(source,destination):
        if Path(destination)==path:
            path.write_bytes(b'new local file')
        return original(source,destination)
    monkeypatch.setattr(sync_module.os,'link',concurrently_created)
    result=sync_vault(store,tmp_path)
    assert result['conflicts']==1 and result['written']==0 and result['incoming_written']==1
    assert path.read_bytes()==b'new local file'
    assert json.loads((tmp_path/'TechKB/.techkb-sync.json').read_bytes())=={}
    assert list((tmp_path/'TechKB').rglob('.techkb-*'))==[tmp_path/'TechKB/.techkb-sync.json']


def test_publish_exposes_completed_bytes_and_refuses_overwrite(tmp_path,monkeypatch):
    path=tmp_path/'note.md'; original=os.link; seen=[]
    def observe(source,destination):
        assert Path(source).read_bytes()==b'completed remote'
        assert not Path(destination).exists()
        seen.append(True)
        return original(source,destination)
    monkeypatch.setattr(sync_module.os,'link',observe)
    assert sync_module.publish_new(path,b'completed remote')
    assert seen and path.read_bytes()==b'completed remote'
    monkeypatch.setattr(sync_module.os,'link',original)
    path.write_bytes(b'edited')
    assert not sync_module.publish_new(path,b'other')
    assert path.read_bytes()==b'edited' and not list(tmp_path.glob('.techkb-*'))


def test_edited_candidate_is_preserved_and_not_accepted_as_remote(harness,tmp_path):
    store=harness.store; store.data['notes/a.md']=b'first'
    sync_vault(store,tmp_path); store.data['notes/a.md']=b'remote update'
    result=sync_vault(store,tmp_path)
    incoming=tmp_path/'TechKB'/result['updates'][0]['incoming']
    incoming.write_bytes(b'annotated candidate')
    again=sync_vault(store,tmp_path)
    assert again['updates'][0]['status']=='conflict' and again['incoming_written']==0
    assert incoming.read_bytes()==b'annotated candidate'
    assert (tmp_path/'TechKB/notes/a.md').read_bytes()==b'first'


def test_preview_does_not_write_candidates_or_manifest(harness,tmp_path):
    harness.store.data['notes/a.md']=b'first'
    sync_vault(harness.store,tmp_path)
    before=(tmp_path/'TechKB/.techkb-sync.json').read_bytes()
    harness.store.data['notes/a.md']=b'update'
    result=sync_vault(harness.store,tmp_path,dry_run=True)
    assert result['incoming_planned']==1 and result['incoming_written']==0
    assert result['updates'][0]['status']=='planned'
    assert not (tmp_path/'TechKB/incoming').exists()
    assert (tmp_path/'TechKB/.techkb-sync.json').read_bytes()==before


def test_manual_merge_is_acknowledged_without_replacing_existing_note(harness,tmp_path):
    store=harness.store; store.data['notes/a.md']=b'first'
    sync_vault(store,tmp_path); store.data['notes/a.md']=b'update'
    result=sync_vault(store,tmp_path)
    root=tmp_path/'TechKB'; incoming=root/result['updates'][0]['incoming']
    (root/'notes/a.md').write_bytes(incoming.read_bytes())
    accepted=sync_vault(store,tmp_path)
    assert accepted['status']=='success' and accepted['unchanged']==1
    assert accepted['written']==accepted['incoming_written']==0
    assert json.loads((root/'.techkb-sync.json').read_bytes())['notes/a.md']==sync_module.digest(b'update')
    assert incoming.exists()


def test_unsupported_hard_links_fail_without_partial_note(harness,tmp_path,monkeypatch):
    harness.store.data['notes/a.md']=b'remote'
    def unsupported(*args,**kwargs):
        raise OSError('hard links unsupported')
    monkeypatch.setattr(sync_module.os,'link',unsupported)
    with pytest.raises(OSError):
        sync_vault(harness.store,tmp_path)
    assert not (tmp_path/'TechKB/notes/a.md').exists()
    assert not list((tmp_path/'TechKB/notes').glob('.techkb-*'))
    assert not (tmp_path/'TechKB/.techkb-sync.lock').exists()


def test_candidate_symlink_is_rejected_before_any_notes_are_written(harness,tmp_path):
    store=harness.store; store.data['notes/a.md']=b'first'
    sync_vault(store,tmp_path)
    (tmp_path/'TechKB/incoming').symlink_to(tmp_path/'outside',target_is_directory=True)
    store.data['notes/a.md']=b'updated'; store.data['notes/b.md']=b'new'
    with pytest.raises(ValueError):
        sync_vault(store,tmp_path)
    assert not (tmp_path/'TechKB/notes/b.md').exists()
    assert (tmp_path/'TechKB/notes/a.md').read_bytes()==b'first'
