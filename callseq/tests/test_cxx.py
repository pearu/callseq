import os
import shutil
import tempfile
import difflib
import filecmp
import callseq

def get_root_path():
    return os.path.dirname(os.path.dirname(__file__))


def test_cxx_build():
    test_src = os.path.join(get_root_path(), 'cxx', 'src', 'test.cpp')

    with tempfile.TemporaryDirectory() as working_dir:
        src = os.path.join(working_dir, os.path.basename(test_src))
        shutil.copy(test_src, src)

        compiler = callseq.actions.Compiler.get('c++17')
        app_exe = os.path.join(working_dir, 'app')
        s, out, err = compiler(src, app_exe, task='build')
        assert s == 0

        app = callseq.actions.Application(app_exe)

        s, out, err = app()
        assert s == 0
        assert out.strip() == f'foo(12) + foo(23) -> {12 + 123 + 23 + 1234}'


def test_cxx_callseq_apply_unapply():
    std = 'C++'
    test_src = os.path.join(get_root_path(), 'cxx', 'src', 'test.cpp')

    with tempfile.TemporaryDirectory() as working_dir:
        src = os.path.join(working_dir, os.path.basename(test_src))
        modified_src = os.path.join(working_dir, '_' + os.path.basename(test_src))
        restored_src = os.path.join(working_dir, '__' + os.path.basename(test_src))
        shutil.copy(test_src, src)

        callseq.actions.CallSeq(std=std, task='apply')(src, modified_src)
        callseq.actions.CallSeq(std=std, task='unapply')(modified_src, restored_src)

        result = open(restored_src).read()
        expected = open(src).read()

        #print(''.join(difflib.ndiff(expected.splitlines(keepends=True), result.splitlines(keepends=True))))
        assert len(expected) == len(result)
        assert expected == result


def test_cxx_callseq_apply_apply():
    std = 'C++'
    test_src = os.path.join(get_root_path(), 'cxx', 'src', 'test.cpp')

    with tempfile.TemporaryDirectory() as working_dir:
        src = os.path.join(working_dir, os.path.basename(test_src))
        modified_src = os.path.join(working_dir, '_' + os.path.basename(test_src))
        modified2_src = os.path.join(working_dir, '__' + os.path.basename(test_src))
        shutil.copy(test_src, src)

        ct = callseq.actions.CallSeq(std=std, task='apply')
        ct(src, modified_src)
        ct(modified_src, modified2_src)

        result = open(modified2_src).read()
        expected = open(modified_src).read()

        assert len(expected) == len(result)
        assert expected == result


def test_cxx_callseq_apply_build():
    std = 'C++'
    test_src = os.path.join(get_root_path(), 'cxx', 'src', 'test.cpp')
    callseq_hpp = os.path.join(get_root_path(), 'cxx', 'include', 'callseq.hpp')

    with tempfile.TemporaryDirectory() as working_dir:
        src = os.path.join(working_dir, os.path.basename(test_src))
        modified_src = os.path.join(working_dir, '_' + os.path.basename(test_src))

        shutil.copy(test_src, src)

        callseq.actions.CallSeq(std=std, task='apply')(src, modified_src)

        compiler = callseq.actions.Compiler.get('c++17')
        app_exe = os.path.join(working_dir, 'app')
        callseq_output = os.path.join(working_dir, "callseq.output")
        s, out, err = compiler(modified_src, app_exe,
                               flags = ['-include', callseq_hpp, f'-DCALLSEQ_OUTPUT="{callseq_output}"'],
                               task='build')
        assert s == 0
        app = callseq.actions.Application(app_exe)
        s, out, err = app()
        assert s == 0
        assert out.strip().rsplit('\n', 1)[-1] == f'foo(12) + foo(23) -> {12 + 123 + 23 + 1234}'

        f = open(callseq_output)
        print(f.read())
        f.close()

def test_cxx_ast_dump():
    test_src = os.path.join(get_root_path(), 'cxx', 'src', 'test.cpp')

    with tempfile.TemporaryDirectory() as working_dir:
        src = os.path.join(working_dir, os.path.basename(test_src))
        shutil.copy(test_src, src)

        ast_reader = callseq.actions.ClangAstReader()
        ast = ast_reader(src)
        print(ast)


def test_cxx_multi_callseq_apply_unapply():
    std = 'C++'
    test_src_root = os.path.join(get_root_path(), 'cxx', 'src')
    with tempfile.TemporaryDirectory() as working_dir:
        shutil.copytree(test_src_root, working_dir, dirs_exist_ok=True)
        sources = callseq.actions.Collector(std=std, recursive=True)(working_dir)
        with tempfile.TemporaryDirectory() as copy_working_dir:
            shutil.copytree(working_dir, copy_working_dir, dirs_exist_ok=True)
            copy_sources = callseq.actions.Collector(std=std, recursive=True)(copy_working_dir)
            assert len(copy_sources) == len(sources)
            for f1, f2 in zip(copy_sources, sources):
                assert filecmp.cmp(f1, f2)
            modified_sources = callseq.actions.MultiCallSeq(std=std, task='apply')(sources)
            assert len(modified_sources) == len(sources)
            equal = True
            for f1, f2 in zip(modified_sources, copy_sources):
                equal = equal and filecmp.cmp(f1, f2)
            assert not equal
            restored_sources = callseq.actions.MultiCallSeq(std=std, task='unapply')(modified_sources)
            assert len(restored_sources) == len(copy_sources)
            for f1, f2 in zip(restored_sources, copy_sources):
                assert filecmp.cmp(f1, f2)
