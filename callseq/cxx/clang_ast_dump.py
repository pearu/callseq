
import re
import os
import sys


def parse_line(line):
    lst = []
    if line.startswith('0x'):
        id_, line = line.split(None, 1)  # strip hex value
        lst.append(dict(id=id_))
    while line:
        if line.startswith('<'):
            i1 = line.index('>', 0)
            while line.count('<', 0, i1) > line.count('>', 0, i1+1):
                i1 = line.index('>', i1 + 1)
            lst.append(parse_line(line[1:i1]))
            line = line[i1+1:].strip()
        elif line.startswith('/'):
            path, line = line.split(None, 1) if ' ' in line else (line, '')
            if path.endswith(','):
                path = path[:-1]
            if ':' in path:
                path, lineno, colno = path.split(':')
                path = dict(path=path, lineno=int(lineno), colno=int(colno))
            else:
                path = dict(path=path)
            lst.append(path)
        elif line.startswith('line:') or line.startswith('col:'):
            loc, line = line.split(None, 1) if ' ' in line else (line, '')
            if loc.endswith(','):
                loc = loc[:-1]
            items = loc.split(':')
            kind, nums = items[0], tuple(map(int, items[1:]))
            if kind == 'line':
                assert len(nums) == 2, nums
                lst.append(dict(lineno=nums[0], colno=nums[1]))
            elif kind == 'col':
                assert len(nums) == 1, nums
                lst.append(dict(colno=nums[0]))
            else:
                assert 0
        else:
            if line.split(None, 1)[0] in ['parent', 'prev'] and ' ' in line:
                kind, hnum, line = line.split(None, 2)
                lst.append({kind: hnum})
                continue
            lst.append(line)
            line = ''
    return lst


def get_location(items):
    path, line, col = None, None, None
    for item in reversed(items):
        if isinstance(item, dict):
            path_ = item.get('path')
            line_ = item.get('lineno')
            col_ = item.get('colno')
        elif isinstance(item, list):
            path_, line_, col_ = get_location(item)
        else:
            continue
        if path is None:
            path = path_
        if line is None:
            line = line_
        if col is None:
            col = col_
    return path, line, col


class Node:
    """Node represents a pair of key and value.

    Node may have children nodes.
    All non-root nodes have parents.
    """

    def __init__(self, parent, prefix, key, value):
        assert isinstance(parent, (Node, type(None)))
        assert isinstance(key, str), key
        assert isinstance(value, str), value
        self.parent = parent
        self.prefix = prefix  # used only when parsing clang dump output
        self.key = key
        self._value = value   # original value, unused
        items = parse_line(value)
        loc, lineno, colno = get_location(items)
        if loc is None:
            if self.parent is not None:
                if self.parent.nodes:
                    loc = self.parent.nodes[-1].loc
                else:
                    loc = self.parent.loc
                if lineno is None:
                    if self.parent.nodes:
                        lineno = self.parent.nodes[-1].lineno
                    else:
                        lineno = self.parent.lineno

        self.loc = loc
        self.lineno = lineno
        self.colno = colno

        if key == 'TranslationUnitDecl':
            value = ''
        elif key in ['NamespaceDecl', 'AccessSpecDecl', 'LinkageSpecDecl']:
            # take last word
            value = value.rsplit(None, 1)[-1]
        elif key in ['TypedefDecl', 'CXXMethodDecl', 'CXXConstructorDecl', 'CXXDestructorDecl',
                     'ParmVarDecl', 'TypeAliasDecl', 'EnumConstantDecl', 'FunctionDecl',
                     'VarDecl', 'FieldDecl', 'IndirectFieldDecl', 'UnresolvedUsingValueDecl',
                     ]:
            # name 'signature' rest
            # warning: pre-name part may be relevant as well
            i = value.find("'")
            j = value.rfind("'")
            assert -1 not in {i, j}, (key, value)
            name = value[:i].rstrip().rsplit(None, 1)[-1]
            if key == 'ParmVarDecl' and ':' in name:
                name = ''
            sig = value[i:j+1]
            rest = value[j+1:].lstrip()
            value = f'{name} {sig} {rest}'
        elif key == 'CXXRecordDecl':
            m = re.match(r'.*\b(struct|class)\b\s+(.*)\s+definition', value)
            if m is not None:
                value = '%s %s' % m.groups()
            else:
                value = '...'
        elif key in [
                'UsingShadowDecl', 'CXXConversionDecl', 'NonTypeTemplateParmDecl',
                'UsingDirectiveDecl', 'FriendDecl', 'EnumDecl', 'ClassTemplateDecl',
                'TemplateTypeParmDecl', 'ClassTemplateSpecializationDecl', 'TypeAliasTemplateDecl',
                'FunctionTemplateDecl', 'UsingDecl', 'ClassTemplatePartialSpecializationDecl',
                'TemplateTemplateParmDecl', 'StaticAssertDecl', 'VarTemplateDecl', ''
        ]:
            # TODO: process only if needed
            value = '...'
        elif key.endswith('Decl'):
            # reporting just for awareness
            print(f'TODO1[{key}]: {value}')
            assert "'" not in value
        else:
            pass
            # print(f'TODO2[{key}]: {value}')
        self.value = value
        self.nodes = []

    def __repr__(self):
        return f'{self.key}({self.value!r})'

    def tostring(self, tab='', filter=None):
        lines = []
        lines.append(f'{tab}{self.key}:{self.value}  loc={self.loc}#{self.lineno}:{self.colno}')
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
        obj.loc = self.loc
        obj.lineno = self.lineno
        obj.colno = self.colno
        return obj


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
    for line in ast_dump_output.splitlines():
        prefix, rest = line.split('-', 1) if '-' in line else ('', line)
        lst = rest.split(None, 1)
        key, value = lst if len(lst) == 2 else (lst[0], '')
        if not prefix:
            root = current = Node(None, prefix, key, value)
            root.loc = loc
        else:
            if len(current.prefix) < len(prefix):
                node = Node(current, prefix, key, value)
                current.nodes.append(node)
            else:
                while len(current.prefix) > len(prefix):
                    current = current.parent
                assert current.prefix[:-1] == prefix[:-1], (current.prefix, prefix)
                node = Node(current.parent, prefix, key, value)
                current.parent.nodes.append(node)
            current = node
    return root.cleanup()
