from run_validations import run

def test_dq_framework():
    assert run("config/table_config.json") == 0
