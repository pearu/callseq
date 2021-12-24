
import os
import re
import shutil
import subprocess
import warnings
import difflib
import callseq.cxx
import callseq.cxx.clang_ast_dump


def _flatten(args):
    for a in args:
        if isinstance(a, str):
            yield a
        else:
            yield from _flatten(a)


def run(cmd, *args):
    new_args = [cmd] + list(_flatten(args))
    r = subprocess.run(new_args, capture_output=True)
    return -r.returncode, r.stdout.decode("utf-8"), r.stderr.decode("utf-8")


class Action:
    """
    Base class for actions.
    """


class Compiler(Action):
    """Compiles and builds a C++ application.
    """

    @staticmethod
    def _get_gnu_compilers(_cache=[]):
        if not _cache:
            _cache.append(None)  # mark being here
            cxx_suffices = ['.cpp', '.cxx']
            c_suffices = ['.c']
            f_suffices = ['.f90', '.f']
            cxx_flags = dict(compile=['-c', '-std='],
                             build=['-std='],
                             output=['-o'])
            c_flags = dict(compile=['-c', '-std='],
                           build=['-std='],
                           output=['-o'])
            f_flags = dict(compile=['-c', '-std='],
                           build=['-std='],
                           output=['-o'])

            def apply_std_to_flags(std, flags):
                new_flags = {}
                for k, lst in flags.items():
                    new_lst = []
                    for a in lst:
                        if a.startswith('-std='):
                            a = '-std=' + std
                        new_lst.append(a)
                    new_flags[k] = new_lst
                return new_flags

            for xmode, cmd, suffices, flags in [
                    ('c++', 'g++', cxx_suffices, cxx_flags),
                    ('c', 'gcc', c_suffices, c_flags),
                    ('fortran', 'gfortran', f_suffices, f_flags)]:
                exe = shutil.which(cmd)
                s, out, err = run(exe, '--version')
                m = re.search(r'(\d+[.]\d+[.]\d+)([^\s]*)', out)
                if m is None:
                    warnings.warn(f'Failed to find version from output {out}')
                    continue
                version = tuple(map(int, m.group(1).split('.'))) + (m.group(2),)
                s, out, err = run(exe, '-v', '--help')
                standards = []
                for line in out.splitlines():
                    line = line.strip()
                    if line.startswith('-std='):
                        line = line[5:]
                        if (
                                (xmode == 'fortran' and line[0] == 'f')
                                or (xmode == 'c++' and line[:3] == 'c++')
                                or (xmode == 'c' and line[0] == 'c' and line[:3] != 'c++')):
                            standards.append(line.split(None, 1)[0])
                _cache.append((exe, version, standards, flags, suffices, apply_std_to_flags))
        for c in _cache:
            if c is not None:
                yield c

    @staticmethod
    def _get_clang_compilers(_cache=[]):
        if not _cache:
            _cache.append(None)  # mark being here
        for c in _cache:
            if c is not None:
                yield c

    @classmethod
    def get(cls, std='C++', extra_flags=[], vendor='gnu'):
        """Construct a compiler instance using the desired language standard.

        Returns None when no compiler is found in the
        environment. Otherwise, return Compiler instance with flags
        supporting the desired language standard.
        """
        assert vendor in ['gnu', 'clang']
        std = std.lower()
        std = {'c': 'c11', 'c++': 'c++11', 'cxx': 'c++11'}.get(std, std)

        all_standards = set()
        for (exe, version, standards, flags,
             suffices, apply_std_to_flags) in getattr(cls, f'_get_{vendor}_compilers')():
            if std in standards:
                return cls(exe, version, apply_std_to_flags(std, flags), suffices)
            all_standards.update(standards)
        if all_standards:
            raise ValueError(f'Language standard {std} not supported in {vendor} compilers.'
                             f' Supported standards: {", ".join(sorted(all_standards))}')
        return None

    def __init__(self, compiler_exe, version, flags, suffices):
        self.compiler_exe = compiler_exe
        self.flags = flags
        self.suffices = suffices
        self.version = version

    def __repr__(self):
        return (f'{type(self).__name__}({self.compiler_exe!r},'
                f' {self.flags}, {self.suffices}, {self.version!r})')

    def __call__(self, source, output, flags=[], task='build'):
        assert task in ['build', 'compile']
        args = [self.flags[task] + flags, source, self.flags['output'], output]
        s, out, err = run(self.compiler_exe, args)
        if s == 0:
            return s, out, err
        raise RuntimeError(f'compilation failed:\n{out}\n{err}')


class Application(Action):
    """Application runner
    """

    def __init__(self, application_exe):
        self.application_exe = application_exe

    def __call__(self, *args):
        s, out, err = run(self.application_exe, list(args))
        if s == 0:
            return s, out, err
        raise RuntimeError(f'application failed:\n{out}\n{err}')


class CallSeq(Action):

    def __init__(self, std='C++', task='apply', try_run=False, show_diff=False):
        self.std = std.lower()

        if self.std == 'c++':
            self.ast_reader = ClangAstReader()
            self.apply_method = callseq.cxx.insert_signal_code
            self.unapply_method = callseq.cxx.remove_signal_code
        else:
            raise NotImplementedError(repr(self.std))

        self.task = task
        self.try_run = try_run
        self.show_diff = show_diff

    def __call__(self, source, output=None):
        f = open(source)
        source_string = f.read()
        f.close()
        if self.task == 'apply':
            ast = self.ast_reader(source)
            output_string = self.apply_method(ast, source_string)
        elif self.task == 'unapply':
            output_string = self.unapply_method(source_string)
        else:
            assert 0

        if output is None:
            output = source
        if self.show_diff:
            show_ndiff(source, source_string, output, output_string)
        if not (source == output and source_string == output_string):
            if not self.try_run:
                f = open(output, 'w')
                f.write(output_string)
                f.close()
        return output


def show_ndiff(file1, content1, file2, content2):
    lineno1 = lineno2 = 0
    line1_head = True
    line2_head = True
    lines1 = content1.splitlines(keepends=True)
    lines2 = content2.splitlines(keepends=True)
    print('='*60)
    print(f'\nndiff:\n--- {file1} (original)\n+++ {file2} (new)')
    print('-'*60)
    for line in difflib.ndiff(lines1, lines2):
        if line[:2] == '- ':
            lineno1 += 1
            line2_head = True
            if line1_head:
                print(f'--- #{lineno1}:')
                line1_head = False
            print(line, end='')
        elif line[:2] == '+ ':
            lineno2 += 1
            line1_head = True
            if line2_head:
                print(f'+++ #{lineno2}:')
                line2_head = False
            print(line, end='')
        elif line[:2] == '? ':
            line1_head = True
            line2_head = True
            print(line, end='')
        else:
            line1_head = True
            line2_head = True
            lineno1 += 1
            lineno2 += 1
    print('='*60)


class MultiCallSeq(Action):

    def __init__(self, std='C++', task='apply', try_run=False, show_diff=False):
        self.callseq = CallSeq(std=std, task=task, try_run=try_run, show_diff=show_diff)

    def __call__(self, sources):
        return list(map(self.callseq, sources))


class ClangAstReader(Action):
    """AST reader of C++ files.
    """

    def __init__(self):
        self.clang_exe = shutil.which('clang++')
        assert self.clang_exe  # make sure that clang++ is installed (e.g. conda install clangxx)
        self.ast_dump_flags = ['-Xclang', '-ast-dump', '-fsyntax-only', '-fno-diagnostics-color']

    def __call__(self, source, flags=[]):
        source = os.path.abspath(source)
        s, out, err = run(self.clang_exe, self.ast_dump_flags, flags, source)
        return callseq.cxx.clang_ast_dump.parse_ast_dump(out, source)


class Collector(Action):
    """Collects files with the given file standard
    """

    std_extensions = {'c++': ['.h', '.hpp', '.hxx', '.c', '.cpp', '.cxx'],
                      'c': ['.h', '.c']}

    def __init__(self, recursive=False, std='C++'):
        self.recursive = recursive
        std = std.lower()
        std = dict(cxx='c++').get(std, std)
        self.extensions = self.std_extensions[std]

    def collect(self, path, recursive=None):
        if isinstance(path, str):
            if os.path.isdir(path) and (recursive is None or recursive):
                for name in os.listdir(path):
                    yield from self.collect(os.path.join(path, name), recursive=self.recursive)
            else:
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in self.extensions:
                        yield path
        elif isinstance(path, (list, tuple, set)):
            for path_ in path:
                yield from self.collect(path_, recursive=recursive)
        else:
            raise TypeError(f'expected str or list as a path argument, got {type(path)}')

    def __call__(self, *paths):
        return list(sorted(set(self.collect(paths))))


class ShowCallSeqOutput(Action):

    def __call__(self, callseq_output):

        tabs = 0
        for line in callseq_output.splitlines():
            if line[0] == '{':
                print('  ' * tabs + line)
                tabs += 1
            elif line[0] == '}':
                tabs -= 1
                print('  ' * tabs + line)
            else:
                assert 0
