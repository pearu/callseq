
import os
import callseq
import argparse


def main_cxx():
    std = 'C++'
    parser = argparse.ArgumentParser(
        description='Runtime calling tree generation tool for C++ software')
    parser.add_argument(
        'path', type=str, nargs='+', help='Path to C++ file (header or source) or directory')
    parser.add_argument(
        '-r', '--recursive', default=False, action='store_true',
        help='Recursively collect C++ files from specified paths (default: %(default)s)')
    parser.add_argument('--apply', default=False, action='store_true',
                        help='Insert callseq hooks to C++ files (default: %(default)s)')
    parser.add_argument('--unapply', default=False, action='store_true',
                        help='Remove callseq hooks from C++ files (default: %(default)s)')
    parser.add_argument('--source-root', type=str, default='',
                        help='Root path of C++ sources (default: %(default)s)')
    parser.add_argument('--try-run', default=False, action='store_true',
                        help='Apply actions but don\'t write files (default: %(default)s)')
    parser.add_argument('--show-diff', default=False, action='store_true',
                        help='Output  modifications as ndiff (default: %(default)s)')
    parser.add_argument('--verbose', default=False, action='store_true',
                        help='Be verbose (default: %(default)s)')

    args = parser.parse_args()

    if args.apply or args.unapply:
        sources = callseq.actions.Collector(recursive=args.recursive, std=std)(args.path)

        source_root = args.source_root if args.source_root else os.path.commonprefix(sources)
        if os.path.isfile(source_root):
            source_root = os.path.dirname(source_root)
        print(f'{source_root=}')

        print(f'Found {len(sources)} C++ header/source files in {":".join(args.path)}')

        if args.apply:
            sources = callseq.actions.MultiCallSeq(
                std=std, task='apply', try_run=args.try_run, show_diff=args.show_diff)(sources)

        if args.unapply:
            sources = callseq.actions.MultiCallSeq(
                std=std, task='unapply', try_run=args.try_run, show_diff=args.show_diff)(sources)
    else:
        for path in args.path:
            if os.path.basename(path) == 'callseq.output':
                f = open(path)
                callseq.actions.ShowCallSeqOutput()(f.read())
                f.close()
