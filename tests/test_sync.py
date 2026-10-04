import pytest
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
    assert sync_vault(store,tmp_path)['written']==1
    untracked=tmp_path/'TechKB/notes/b.md'; untracked.write_text('mine')
    store.data['notes/b.md']=b'other'
    result=sync_vault(store,tmp_path)
    assert result['conflicts']==1 and untracked.read_text()=='mine'


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
