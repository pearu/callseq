# callseq

CallSeq is a tool that allows recording the calling sequence of
function or method calls while running an application.

## Motivation

Imagine joining a project that develops and maintains a C++ based
software with couple of thousands or more files while many of these
can have tens of thousands lines of C++ code. And your task is to
extend the software with a new feature or fix a bug.  Getting
acquinted with such huge code base to resolve your problem can be a
daunting undertaking. Sometimes reading the source code is sufficient
to resolve the problem while othertimes not. As a next step, running
the code and following actual execution paths is helpful for learning
the internals of the software. In fact, this may also give hints what
parts of the code one should pay attention the most to complete the
given programming task.

The CallSeq project provides a tool that allows recording a calling
sequence of functions (including class methods) while running an
application. CallSeq implements the following workflow for debugging
the application:

1. Apply CallSeq hooks to the application sources.
2. Compile and build the application as usual.
3. Run the application. The CallSeq hooks will record the function and
   method calls to a CallSeq output file.
4. Analyze the CallSeq output file.
5. Develop the application and go back to step 2.
6. Remove CallSeq hooks from the application sources and push your
   changes to the application repository as usual.

Currently, CallSeq can be applied to C++ based software using C++-17
or newer standard.

CallSeq should be considered as a complimentary tool to the existing
set of debugging and program analysis tools.

## Example

Consider a test file [test.cpp](callseq/cxx/src/test.cpp) that
illustrates calling various C++ functions, including free functions,
class methods and its static methods.

To apply CallSeq to C++ sources, a command line tool `callseq++` is
provided. Execute

```bash
$ callseq++ callseq/cxx/src --apply --show-diff
```

that will insert CallSeq hooks into all C++ files under
`callseq/cxx/src` (in the given example there is just one C++ source
file). With the option `--show-diff`, the changes to source files will
be shown as follows:

```
Found 1 C++ header/source files in callseq/cxx/src
============================================================

ndiff:
--- callseq/cxx/src/test.cpp (original)
+++ callseq/cxx/src/test.cpp (new)
------------------------------------------------------------
--- #8:
-   A(int a) : m(a), n((a > 0 ? -1 : 1)) {}
+++ #8:
+   A(int a) : m(a), n((a > 0 ? -1 : 1)) {CALLSEQ_SIGNAL(1,this);}
?                                         +++++++++++++++++++++++
--- #10:
-   int bar(int b) const {
+++ #10:
+   int bar(int b) const {CALLSEQ_SIGNAL(2,this);
--- #18:
-   static int car(int b) { return b - 321; }
+++ #18:
+   static int car(int b) {CALLSEQ_SIGNAL(3,CALLSEQ_DUMMY_THIS); return b - 321; }
--- #26:
- int A::car2(int b) { return 2 * b; }
+++ #26:
+ int A::car2(int b) {CALLSEQ_SIGNAL(4,this); return 2 * b; }
?                     +++++++++++++++++++++++
--- #28:
- int foo(int a) {
+++ #28:
+ int foo(int a) {CALLSEQ_SIGNAL(5,CALLSEQ_DUMMY_THIS);
--- #34:
- int foo(int a) {
+++ #34:
+ int foo(int a) {CALLSEQ_SIGNAL(6,CALLSEQ_DUMMY_THIS);
--- #40:
- int main() {
+++ #40:
+ int main() {CALLSEQ_SIGNAL(7,CALLSEQ_DUMMY_THIS);
============================================================
```

Next, let's build the test application (assuming GNU compilers):

```bash
$ g++ -std=c++17 callseq/cxx/src/test.cpp -o ./app -include callseq/cxx/include/callseq.hpp
```

where using the `-include callseq/cxx/include/callseq.hpp` is required
for compiling C++ sources that contain CallSeq hooks. Another way to
achieve the inclusion of `callseq.hpp` header file is to execute:

```bash
export CXXFLAGS="$CXXFLAGS -include callseq/cxx/include/callseq.hpp"
```
prior configuring the build of the application.

The standard output from running the given test application is:

```
$ ./app
callseq logs to callseq.output
foo(12) + foo(23) -> 1392
```

Notice that a file `callseq.output` is created to current working
directory that contains:

```
{7|0x0|0.134384|0xe48eb7|int main()|callseq/cxx/src/test.cpp#40
{5|0x0|0.225147|0xe48eb7|int foo(int)|callseq/cxx/src/test.cpp#28
{1|0x7ffc28fd9498|0.239341|0xe48eb7|A::A(int)|callseq/cxx/src/test.cpp#8
}1|0x7ffc28fd9498|0.251033|0xe48eb7
{2|0x7ffc28fd9498|0.260988|0xe48eb7|int A::bar(int) const|callseq/cxx/src/test.cpp#10
}2|0x7ffc28fd9498|0.271384|0xe48eb7
}5|0x0|0.280532|0xe48eb7
{6|0x0|0.290149|0xe48eb7|int ns::foo(int)|callseq/cxx/src/test.cpp#34
{1|0x7ffc28fd9498|0.299851|0xe48eb7|A::A(int)|callseq/cxx/src/test.cpp#8
}1|0x7ffc28fd9498|0.309408|0xe48eb7
{2|0x7ffc28fd9498|0.318286|0xe48eb7|int A::bar(int) const|callseq/cxx/src/test.cpp#10
}2|0x7ffc28fd9498|0.332838|0xe48eb7
}6|0x0|0.341568|0xe48eb7
}7|0x0|0.359593|0xe48eb7
```

Each line in the CallSeq output file represents an event of either
entering a function/method (lines starting with `{`) or leaving the
function/method (lines starting with `}`). The other fields in a
single line have the following meanings:

1. An event id that corresponds to the code location of entering the
   function/method. The event id is the value specified as the first
   argument to the CPP-macro `CALLSEQ_SIGNAL`.

2. The pointer value of `this` if inside a class method. The value
   `0x0` indicates that the event line corresponds to a free function
   or a static method call.

3. Timestamp of the event in seconds given with nano-seconds
   resolution.

4. The hash id of the thread under which the function/method is being
   executed.

5. The signature of the function/method. Specified only for function
   entering events.

6. The file name and line number of the function/method where the
   events is being triggered. Specified only for function entering
   events.

In future, analyzis tools will be provied for interpretting and
visualizing the content of CallSeq output files.

One may change the application source codes according to normal
development workflow as long as the CallSeq hooks (the CPP-macro
`CALLSEQ_SIGNAL` calls) are not altered. Although, one may always
remove some of these manually if wished.

Finally, to remove all the CallSeq hooks from the application source
codes, run:

```bash
callseq++ callseq/cxx/src --unapply
```

that will restore the application source code to the original state
(modulo the possible modifications introduced from software
development steps).
