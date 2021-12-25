add_executable(test_Fraction test_Fraction.cpp)
target_link_libraries(test_Fraction PUBLIC Symbolic)
target_include_directories(test_Fraction PUBLIC
                          "${PROJECT_BINARY_DIR}"
                          "${PROJECT_SOURCE_DIR}")
