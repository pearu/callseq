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

0. Check out the source of the application repository as usual.
1. Apply CallSeq hooks to the application sources using the provided
   CLI tool `callseq++`.
2. Compile and build the application as usual.
3. Run the application. The CallSeq hooks will record the function and
   method calls to a CallSeq output file.
4. Analyze the CallSeq output file.
5. Develop the application and go back to step 2.
6. Remove CallSeq hooks from the application sources using the CLI
   tool `callseq++`.
7. Push your changes to the application repository as usual.

Currently, CallSeq can be applied to C++ based software using C++-17
or newer standard.

CallSeq should be considered as a complimentary tool to the existing
set of debugging and program analysis tools.

## Example

Consider a test file [factorial.cpp](callseq/cxx/src/factorial.cpp):
```c++
// File: factorial.cpp
#include <iostream>

long factorial(long n) {
  if (n <= 1)
    return 1;
  return n * factorial(n - 1);
}

int main() {
  for (int n = 1; n < 5; n++) {
    std::cout << n << "! is " << factorial(n) << std::endl;
  }
}
```

To apply CallSeq to C++ sources, a command line tool `callseq++` is
provided. Execute

```bash
$ callseq++ callseq/cxx/src/factorial.cpp --apply --show-diff
```

that will insert CallSeq hooks into the C++ file `factorial.cpp`.
With the option `--show-diff`, the changes to source files will be
shown as follows:

```
Found 1 C++ header/source files in callseq/cxx/src/factorial.cpp
============================================================

ndiff:
--- callseq/cxx/src/factorial.cpp (original)
+++ callseq/cxx/src/factorial.cpp (new)
------------------------------------------------------------
--- #4:
- long factorial(long n) {
+++ #4:
+ long factorial(long n) {CALLSEQ_SIGNAL(1,CALLSEQ_DUMMY_THIS);
--- #10:
- int main() {
+++ #10:
+ int main() {CALLSEQ_SIGNAL(2,CALLSEQ_DUMMY_THIS);
============================================================
```

Next, let's build the test application (assuming GNU compilers):

```bash
$ g++ -std=c++17 callseq/cxx/src/factorial.cpp -o ./app-factorial -include callseq/cxx/include/callseq.hpp
```

where using the `-include callseq/cxx/include/callseq.hpp` is required
for compiling C++ sources that contain CallSeq hooks. Another way to
achieve the inclusion of
[callseq.hpp](callseq/cxx/include/callseq.hpp) header file is to
execute:

```bash
export CXXFLAGS="$CXXFLAGS -include callseq/cxx/include/callseq.hpp"
```
prior configuring the build of the application (of course, this
assumes the build system uses the `CXXFLAGS` environment variable as
input).

The standard output from running the given test application is:

```
$ ./app-factorial
callseq logs to callseq.output
1! is 1
2! is 2
3! is 6
4! is 24
```

Notice that a file `callseq.output` is created to the current working
directory. Use the `callseq++` to view its content:

```
$ callseq++ callseq.output
{2|0x0|0.10092680|0xe48eb7|int main()|callseq/cxx/src/factorial.cpp#10
  {1|0x0|0.10178666|0xe48eb7|long int factorial(long int)|callseq/cxx/src/factorial.cpp#4
  }1|0x0|0.10191840|0xe48eb7
  {1|0x0|0.10219697|0xe48eb7|long int factorial(long int)|callseq/cxx/src/factorial.cpp#4
    {1|0x0|0.10229763|0xe48eb7|long int factorial(long int)|callseq/cxx/src/factorial.cpp#4
    }1|0x0|0.10238600|0xe48eb7
  }1|0x0|0.10247423|0xe48eb7
  {1|0x0|0.10259247|0xe48eb7|long int factorial(long int)|callseq/cxx/src/factorial.cpp#4
    {1|0x0|0.10268127|0xe48eb7|long int factorial(long int)|callseq/cxx/src/factorial.cpp#4
      {1|0x0|0.10276817|0xe48eb7|long int factorial(long int)|callseq/cxx/src/factorial.cpp#4
      }1|0x0|0.10285352|0xe48eb7
    }1|0x0|0.10293455|0xe48eb7
  }1|0x0|0.10301461|0xe48eb7
  {1|0x0|0.10315599|0xe48eb7|long int factorial(long int)|callseq/cxx/src/factorial.cpp#4
    {1|0x0|0.10324602|0xe48eb7|long int factorial(long int)|callseq/cxx/src/factorial.cpp#4
      {1|0x0|0.10333172|0xe48eb7|long int factorial(long int)|callseq/cxx/src/factorial.cpp#4
        {1|0x0|0.10341658|0xe48eb7|long int factorial(long int)|callseq/cxx/src/factorial.cpp#4
        }1|0x0|0.10350256|0xe48eb7
      }1|0x0|0.10358307|0xe48eb7
    }1|0x0|0.10366290|0xe48eb7
  }1|0x0|0.10374168|0xe48eb7
}2|0x0|0.10388553|0xe48eb7
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
