import os
import sys


class Location:

    def __init__(self, path, line, col):
        assert isinstance(path, str)
        assert isinstance(line, int)
        assert isinstance(col, int)
        self.path = path
        self.line = line
        self.col = col

    def __repr__(self):
        return f'{type(self).__name__}({self.path!r}, {self.line}, {self.col})'

    def copy(self):
        return type(self)(self.path, self.line, self.col)

    def update(self, **d):
        self.__dict__.update(d)


class Node:
    """Node represents a pair of key and value.

    Node may have children nodes.
    All non-root nodes have parents.
    """

    def __init__(self, parent, prefix, key, value, span, location, prefices, suffices):
        assert isinstance(parent, (Node, type(None)))
        assert isinstance(key, str), key
        assert isinstance(value, str), value
        assert isinstance(location, (type(None), Location))
        self.parent = parent
        self.prefix = prefix  # used only when parsing clang dump output
        self.key = key
        self._value = value   # original value, unused
        self.span = span
        self.location = location
        self.prefices = prefices
        self.suffices = suffices
        self.value = value
        self.nodes = []

    @property
    def loc(self):
        if self.location is None:
            return None
        return self.location.path

    @property
    def lineno(self):
        return self.location.line

    @property
    def colno(self):
        return self.location.col

    def __repr__(self):
        return f'{self.key}({self.value!r})'

    def tostring(self, tab='', filter=None):
        lines = []
        if self.loc is not None:
            lines.append(f'{tab}{self.key}:{self.value}'
                         f'  loc={self.loc}#{self.lineno}:{self.colno}')
        else:
            lines.append(f'{tab}{self.key}:{self.value}')
        for node in self.nodes:
            if filter is None or filter(node):
                lines.append(node.tostring(tab=tab + '  ',
                                           filter=filter))
        return '\n'.join(lines)

    def __str__(self):
        return self.tostring(filter=lambda node: node.key.endswith('Decl'))

    def traverse(self, predicate, reversed=False):
        if predicate(self):
            yield self

        if reversed:
            if self.parent is not None:
                yield from self.parent.traverse(predicate, reversed=reversed)
        else:
            for node in self.nodes:
                yield from node.traverse(predicate, reversed=reversed)

    def iter(self, key, reversed=False):
        return self.traverse(lambda node: node.key == key, reversed=reversed)

    def filter(self, predicate):
        if not predicate(self):
            return None
        nodes = []
        for node in self.nodes:
            node = node.filter(predicate)
            if node is None:
                continue
            nodes.append(node)
        obj = self.shallow_copy()
        obj.nodes = nodes
        return obj

    def cleanup(self):
        if self.key == 'NamespaceDecl':
            if self.value == 'std' or self.value.startswith('_'):
                return
        if self.key in ['FunctionDecl', 'TypedefDecl']:
            if (
                    self.value.startswith('_')
                    or self.value.split(None, 1)[0] in ['new', 'delete', 'new[]', 'delete[]']):
                return
        nodes = []
        public = True
        for node in self.nodes:
            if node.key == 'AccessSpecDecl':
                public = dict(private=False, public=True, protected=False)[node.value]
            if not public:
                continue
            node = node.cleanup()
            if node is None:
                continue
            nodes.append(node)

        if self.key in ['LinkageSpecDecl'] and not nodes:
            return
        if self.loc is not None:
            if self.loc.startswith(sys.prefix):
                return

        if self.key in ['EnumDecl', 'TypedefDecl']:
            return

        if (
                self.key == 'CXXRecordDecl'
                and (self.value == '...' or self.value.split(None, 1)[-1].startswith('_'))
        ):
            return

        obj = self.shallow_copy()
        obj.nodes = nodes
        return obj

    def shallow_copy(self):
        obj = object.__new__(Node)
        obj.parent = self.parent
        obj.key = self.key
        obj.value = self.value
        obj._value = self._value
        obj.nodes = self.nodes
        obj.span = self.span
        obj.location = self.location
        obj.prefices = self.prefices
        obj.suffices = self.suffices
        return obj


def try_parse_ast_location(word, last_location):
    if word == '<invalid sloc>':
        return None
    elif word.startswith('col:'):
        _, col = word.split(':')
        last_location.update(col=int(col))
    elif word.startswith('line:'):
        _, line, col = word.split(':')
        last_location.update(line=int(line), col=int(col))
    elif not word.startswith("'") and ':' in word:
        loc, line, col = word.split(':')
        if not (word.startswith('<built-in>') or word.startswith('<scratch space>')):
            assert os.path.isfile(loc), (loc, word)
        last_location.update(path=loc, line=int(line), col=int(col))
    else:
        return
    return last_location.copy()


def parse_ast_line(line, last_location):
    d = {}
    if line.startswith('original'):
        k, line = line.split(None, 1)
        d[k] = True
    words = line.split(None, 2)
    if len(words) == 3 and words[1].startswith('0x'):
        key, addr, line = words
        assert addr.startswith('0x'), (addr, line)
        d.update(key=key, addr=int(addr, 16))
    elif len(words) == 1:
        line = ''
        d.update(key=words[0])
    else:
        key, line = line.split(None, 1)
        d.update(key=key)
    if line.startswith('parent'):
        k, a, line = line.split(None, 2)
        assert a.startswith('0x'), (a, line)
        d.update(parent=int(a, 16))
    if line.startswith('prev'):
        k, a, line = line.split(None, 2)
        assert a.startswith('0x'), (a, line)
        d.update(prev=int(a, 16))
    if line.startswith('<'):
        i = line.index('>')
        while line[:i+1].count('<') != line[:i+1].count('>'):
            i = line.index('>', i + 1)
        span = line[1:i].split(', ')
        line = line[i+1:].lstrip()
        if len(span) == 1:
            d.update(span_start=try_parse_ast_location(span[0], last_location))
        elif len(span) == 2:
            d.update(span_start=try_parse_ast_location(span[0], last_location),
                     span_end=try_parse_ast_location(span[1], last_location))
        else:
            assert 0, (span, line)
    if line.startswith('<invalid sloc>'):
        d.update(location=None)
        line = line[line.index('>')+1:].lstrip()
    if line.startswith('<scratch space>') or line.startswith('<built-in>'):
        word1, word2, line = line.split(None, 2)
        word = word1 + ' ' + word2
        location = try_parse_ast_location(word, last_location)
        d.update(location=location)
    if line and line[0] != '"' and not line.startswith('Text='):
        words = line.split(None, 1)
        if len(words) == 2:
            word, rest = words
            location = try_parse_ast_location(word, last_location)
            if location is not None:
                line = rest
                d.update(location=location)
        elif len(words) == 1:
            location = try_parse_ast_location(words[0], last_location)
            if location is not None:
                line = ''
                d.update(location=location)
    prefices, suffices = [], []
    known_prefices = ['implicit', 'used', 'referenced', 'constexpr', 'struct', 'class', 'invalid']
    known_suffices = ['inline', 'default', 'static', 'trivial', 'definition']
    while True:
        for a in known_prefices:
            if line.startswith(a + ' '):
                prefices.append(a)
                line = line[len(a):].lstrip()
                break
        else:
            break
    d.update(prefices=prefices)

    while True:
        for a in known_suffices:
            if line.endswith(' ' + a):
                suffices.append(a)
                line = line[:-len(a)-1].rstrip()
                break
        else:
            break
    d.update(suffices=suffices)

    d.update(rest=line)
    return d


def parse_ast_dump(ast_dump_output, loc=None):
    """Parse clang ast dump output into a Node tree.
    """
    if loc is not None:
        # ast_dump_output must have been obtained by using absolute
        # path of the input to clang++ command. Otherwise, parse_line
        # is not able to extract file paths correctly. Here we check
        # that loc is absolute path that may indicate if the
        # ast_dump_output constraint has been satisfied.
        assert os.path.isabs(loc), loc  # must use absolute paths
    lines = ast_dump_output.splitlines()
    last_location = Location('', 0, 0)
    for line in lines:
        prefix, rest = line.split('-', 1) if '-' in line else ('', line)
        d = parse_ast_line(rest, last_location)
        key = d['key']
        value = d['rest']
        if not prefix:
            span = Location(loc, 1, 1), Location(loc, len(lines), len(lines[-1]))
            root = current = Node(None, prefix, key, value, span, span[0].copy(),
                                  d['prefices'], d['suffices'])
        else:
            if len(current.prefix) >= len(prefix):
                while len(current.prefix) > len(prefix):
                    current = current.parent
                assert current.prefix[:-1] == prefix[:-1], (current.prefix, prefix)
                current = current.parent
            span_start = d.get('span_start')
            span_end = d.get('span_end', span_start)
            span = (span_start, span_end)
            location = d.get('location', span_start)
            node = Node(current, prefix, key, value, span, location, d['prefices'], d['suffices'])
            current.nodes.append(node)
            current = node
    return root.cleanup()
