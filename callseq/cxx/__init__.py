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


def rstrip_template_specialization(line):
    m = re.match(r'\A(.*)[<][^<]*[>]\Z', line)
    return m.group(1).rstrip() if m else line


def insert_signal_code(ast, source, source_string):
    """Insert callseq signal points to a C++ source.

    Signal point is a RAII object that emits a signal when entering a
    C++ function/method and when leaving the function/method.
    """

    def select(node):
        if node.key not in ['CXXConstructorDecl', 'CXXMethodDecl', 'FunctionDecl']:
            return False
        if 'implicit' in node.prefices:
            return False
        for n in node.nodes:
            if n.key == 'CompoundStmt':  # function/method has body
                return node.loc == source
        return False

    lines = list(source_string.splitlines(keepends=True))
    for node in ast.traverse(select):
        has_this = ((node.key == 'CXXConstructorDecl')
                    or (node.key == 'CXXMethodDecl'
                        and 'static' not in node.suffices))
        lineno, colno = node.lineno - 1, node.colno - 1
        name = node.value.split(None, 1)[0]
        m = re.match(r'\A(.*)[<][^<]*[>]\Z', name)
        name = m.group(1) if m else name
        name = rstrip_template_specialization(name)
        line_name = lines[lineno]
        if '(' in line_name:
            line_name = line_name[:line_name.index('(')]
        line_name = rstrip_template_specialization(line_name.strip())
        if not line_name.rstrip().endswith(name):
            print(f'Warning: ast node does not match with line:\n'
                  f'  {lines[lineno][colno:]}name={name!r}\nnode:\n{node.tostring()}\nSKIPPING')
            continue
        stmt = ([node_ for node_ in node.nodes if node_.key == 'CompoundStmt'] or None)[0]
        assert stmt is not None
        bracket_lineno = stmt.lineno - 1
        bracket_colno = stmt.colno - 1
        line = lines[bracket_lineno]
        assert line[bracket_colno] == '{', (bracket_lineno, bracket_colno, line)
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
