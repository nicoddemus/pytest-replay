import pytest


@pytest.fixture
def suite(testdir):
    testdir.makepyfile(
        test_1="""
            def test_foo():
                pass
            def test_bar():
                pass
        """,
        test_2="""
            def test_zz():
                pass
        """,
    )


@pytest.mark.parametrize('ext', ['bat', 'sh'])
def test_normal_execution(suite, testdir, ext):
    """Ensure scripts for each shell are created and are in the correct format."""
    dir = testdir.tmpdir / 'replay-scripts'
    result = testdir.runpytest('--replay-script-dir={}'.format(dir),
                               '--replay-script-ext={}'.format(ext))

    result.stdout.fnmatch_lines('*replay dir: {} ({})'.format(dir, ext))

    contents = (dir / '.pytest-replay.{}'.format(ext)).readlines(True)
    if ext == 'bat':
        expected = [
            'REM generated by pytest-replay\n',
            'pytest %* ^\n',
            '  "test_1.py::test_foo" ^\n',
            '  "test_1.py::test_bar" ^\n',
            '  "test_2.py::test_zz"',
        ]
    elif ext == 'sh':
        expected = [
            "# generated by pytest-replay\n",
            "pytest $* \\\n",
            "  'test_1.py::test_foo' \\\n",
            "  'test_1.py::test_bar' \\\n",
            "  'test_2.py::test_zz'",
        ]
    else:
        assert 0

    assert contents == expected
    assert result.ret == 0


@pytest.mark.parametrize('ext', ['bat', 'sh'])
@pytest.mark.parametrize('do_crash', [True, False])
def test_crash(testdir, ext, do_crash):
    testdir.makepyfile(test_crash="""
        import os
        def test_crash():
            if {do_crash}:
                os._exit(1)
        def test_normal():
            pass
    """.format(do_crash=do_crash))
    dir = testdir.tmpdir / 'replay-scripts'
    result = testdir.runpytest_subprocess('--replay-script-dir={}'.format(dir),
                                          '--replay-script-ext={}'.format(ext))

    result.stdout.fnmatch_lines('*replay dir: {} ({})'.format(dir, ext))

    contents = (dir / '.pytest-replay.{}'.format(ext)).read()
    test_id = 'test_crash.py::test_normal'
    if do_crash:
        assert test_id not in contents
        assert result.ret != 0
    else:
        assert test_id in contents
        assert result.ret == 0


def test_xdist(testdir):
    testdir.makepyfile("""
        import pytest
        @pytest.mark.parametrize('i', range(10))
        def test(i):
            pass
    """)
    dir = testdir.tmpdir / 'replay-scripts'
    procs = 2
    testdir.runpytest_subprocess('-n', procs,
                                 '--replay-script-dir={}'.format(dir))

    files = dir.listdir()
    assert len(files) == procs
    test_ids = []
    for f in files:
        for line in f.readlines():
            fields = line.split()
            first = fields[0].strip()
            # skip first quote
            if first[1:].startswith('test_xdist.py::'):
                # strip quotes
                test_ids.append(first[1:-1])
    expected_ids = ['test_xdist.py::test[{}]'.format(x) for x in range(10)]
    assert sorted(test_ids) == sorted(expected_ids)
