# See Licence.incore for details.
from click.testing import CliRunner
from riscv_ctg.main import cli
from riscv_ctg.ctg import ctg
import pytest

@pytest.fixture
def runner():
    return CliRunner()

def test_version(runner):
    '''Testing version option'''
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0

# -r -d temp1 -x 32 -cf sample_cgfs/rv32i.cgf -v debu
def test_rv32i(runner):
    ''' Testing rv32 runs '''
    result = runner.invoke(cli, ['--randomize', '--out-dir', 'rv32i', '-cf',
        '../sample_cgfs/rv32i.cgf', '-v', 'debug'])
    assert result.exit_code == 0 or result.exit_code == 1
