

#include <iostream>

class A {

public:
  A(int a) : m(a), n((a > 0 ? -1 : 1)) {}

  int bar(int b) const {
    int r = m;
    for (int i = 0; i < b; i++) {
      r++;
    }
    return r;
  }

  static int car(int b) { return b - 321; }

  int car2(int b);

private:
  int m, n;
};

int A::car2(int b) { return 2 * b; }

int foo(int a) {
  A a_(a);
  return a_.bar(123);
}

namespace ns {
int foo(int a) {
  A a_(a);
  return a_.bar(1234);
}
} // namespace ns

int main() {
  std::cout << "foo(12) + foo(23) -> " << foo(12) + ns::foo(23) << std::endl;
}
