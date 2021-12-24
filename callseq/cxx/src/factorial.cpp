
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
