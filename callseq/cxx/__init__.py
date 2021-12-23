import re

"""
CallSeq C++ support.
"""


class Counter:
    def __init__(self):
        self._count = 0

    def next(self):
        self._count += 1
        return self._count


NEXT_COUNTER = Counter().next


def insert_signal_code(ast, source):
    """Insert callseq signal points to a C++ source.

    Signal point is a RAII object that emits a signal when entering a
    C++ function/method and when leaving the function/method.

    A signal consist of static and dynamic data. The static data consists of
      - the name of source file
      - the line number of the function/method name
      - the function/method name

    The dynamic data consists of
      - thread id
      - timestamp
      - the value of (void*)this in case of a method
      - calling tree depth
    """

    def select(node):
        if node.key not in ['CXXConstructorDecl', 'CXXMethodDecl', 'FunctionDecl']:
            return False
        for n in node.nodes:
            if n.key == 'CompoundStmt':  # function/method has body
                return True
        return False

    lines = list(source.splitlines(keepends=True))
    for node in ast.traverse(select):
        has_this = ((node.key == 'CXXConstructorDecl')
                    or (node.key == 'CXXMethodDecl'
                        and 'static' not in node.value.rsplit("'", 1)[-1]))
        lineno, colno = node.lineno-1, node.colno-1
        name = node.value.split(None, 1)[0]
        # sanity check: ast reference must be exact:
        assert lines[lineno][colno:].startswith(name), (lines[lineno], name)
        bracket_lineno = lineno
        while '{' not in lines[bracket_lineno]:
            bracket_lineno += 1
        bracket_colno = lines[bracket_lineno].index('{')
        line = lines[bracket_lineno]
        if not line.startswith('CALLSEQ_SIGNAL(', bracket_colno+1):
            if has_this:
                new_line = (line[:bracket_colno + 1]
                            + f'CALLSEQ_SIGNAL({NEXT_COUNTER()},this);'
                            + line[bracket_colno+1:])
            else:
                new_line = (line[:bracket_colno + 1]
                            + f'CALLSEQ_SIGNAL({NEXT_COUNTER()},CALLSEQ_DUMMY_THIS);'
                            + line[bracket_colno+1:])
            lines[bracket_lineno] = new_line
    output = ''.join(lines)
    return output


def remove_signal_code(source):
    """Remove all callseq signal points from a C++ source file.
    """
    return re.sub(r'CALLSEQ_SIGNAL[(]\d+[,](this|CALLSEQ_DUMMY_THIS)[)];', '', source)
