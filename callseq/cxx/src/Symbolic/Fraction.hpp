#pragma once
#include <iostream>

template <typename T> class Fraction {

public:
  Fraction(T numel, T denom) : numel_(numel), denom_(denom) {}
  T numel() const { return numel_; }
  T denom() const { return denom_; }

  Fraction<T> operator+(T other);

private:
  T numel_;
  T denom_;
};

template <typename T>
std::ostream &operator<<(std::ostream &out, const Fraction<T> &fraction) {
  out << fraction.numel() << "/" << fraction.denom();
  return out;
}
