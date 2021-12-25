
#include "Symbolic/Fraction.hpp"
#include <iostream>

int main() {
  Fraction<int> x(1, 2);
  std::cout << "x=" << x << std::endl;
  std::cout << "x+1=" << x + 1 << std::endl;
}
