# callseq
CallSeq is a function/method calling sequence recording tool

CallSeq is a tool that allows recording the calling sequence of
functions or method calls during an application runtime. The basic
workflow of using CallSeq is as follows:

1. Apply CallSeq hooks to the application sources.
2. Compile and build the application.
3. Running the application will record the function and method calls
   to CallSeq output file.
4. Analyze CallSeq output file and develop the application. Go to step
   2.
5. Unapply CallSeq hooks to the application sources.

Currently, CallSeq can be applied to C++ based software that uses
C++-17 or newer standard.

## Example

Consider a test file [test.cpp](callseq/cxx/src/test.cpp) than
illustrates various C++ functions, including free functions and class
methods and its static methods.

To apply CallSeq to C++ sources, a command line tool `callseq++` is
provided. Execute

```bash
callseq++ callseq/cxx/src --apply --show-diff
```

that will insert CallSeq hooks into C++ files under
`callseq/cxx/src`. With the option `--show-diff`, the changes to
source files will be shown:

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

Next, let's build the test application:

```bash
g++ -std=c++17 callseq/cxx/src/test.cpp -o ./app -include callseq/cxx/include/callseq.hpp
```

where using the `-include callseq/cxx/include/callseq.hpp` is required for
compiling C++ with CallSeq applied. Another way to specify this globally is to execute:

```bash
export CXXFLAGS="$CXXFLAGS -include callseq/cxx/include/callseq.hpp"
```
prior configuring the application build.

The console output from running the application is:

```
$ ./app
callseq logs to callseq.output
foo(12) + foo(23) -> 1392
```

In addition, running the application produces the CallSeq output
stored in file `callseq.output` that has the following content:

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

where each line represents an event of either entering a
function/method (lines starting with `{`) or leaving the
function/method (lines starting with `}`). The other fields in a
single line have the following meanings:

1. An event id that corresponds to the code location of entering the
   function/method

2. The pointer value of `this` if inside a method, otherwise, `0x0`
   value corresponds to free functions of static methods

3. Timestamp of the event in seconds given in nano-seconds resolution.

4. The (shortened) hash id of the thread where the function/method is being executed.

5. The signature of the function/method

6. The file name and line number of the function/method entering
   point.

In future, analyzis tools will be provied for interpretting and
visualizing the content of CallSeq output files.

One may change the application source codes for development as long as
the CallSeq hooks (the CPP macro `CALLSEQ_SIGNAL` calls) are not
altered, although, one may always remove some these manually if
wished.

Finally, to remove all the CallSeq hooks from the application source
codes, run:

```bash
callseq++ callseq/cxx/src --unapply
```
