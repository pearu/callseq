#include "Fraction.hpp"

template <typename T> Fraction<T> Fraction<T>::operator+(T other) {
  return Fraction<T>(numel() + other * denom(), denom());
}

template Fraction<int> Fraction<int>::operator+(int other);
