from techkb.cli import main


def test_llm_override_cannot_increase_configured_limit():
    assert main(['run','--max-calls','31'])==1
    assert main(['validate-config','--llm-mode','batch'])==1
    assert main(['sync','--max-calls','0'])==1


def test_readonly_operational_cli_without_credentials(tmp_path,capsys):
    snapshot=tmp_path/'state'; snapshot.mkdir()
    for command in ['cost-report','notify','batch-status']:
        assert main([command,'--state-dir',str(snapshot)])==0
    assert '"jobs": []' in capsys.readouterr().out
