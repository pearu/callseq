#pragma once
/*


Basic usage:

$ callseq++ -r /path/to/application/sources --apply
$ export CXXFLAGS="$CXXFLAGS -include /path/to/callseq.hpp
-DCALLSEQ_OUTPUT=/path/to/callseq.output" # Build and run application, analyze
the output of callseq.output, develop $ callseq++ -r
/path/to/application/sources --unapply

Author: Pearu Peterson
Created: December 2021
*/

#ifdef __CUDACC__

#define CALLSEQ_SIGNAL(CALLING_SITE_ID, THIS)
#define CALLSEQ_DUMMY_THIS nullptr

#else

#include <chrono>
#include <fstream>
#include <iostream>
#include <memory>
#include <mutex>
#include <sstream>
#include <thread>

#ifndef CALLSEQ_OUTPUT
#define CALLSEQ_OUTPUT "callseq.output"
#endif

#define CALLSEQ_SIGNAL(CALLING_SITE_ID, THIS)                                  \
  auto callseq_site_point = callseq::SitePoint(                                \
      CALLING_SITE_ID, THIS, __PRETTY_FUNCTION__, __FILE__, __LINE__);

#define CALLSEQ_DUMMY_THIS (callseq::ThisPlaceholder *)nullptr

namespace callseq {

struct ThisPlaceholder {};

// nanos() returns now in nanoseconds
inline uint64_t nanos() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
             std::chrono::high_resolution_clock::now().time_since_epoch())
      .count();
}

inline uint64_t thread_id() {
  return std::hash<std::thread::id>()(std::this_thread::get_id()) & 0xffffff;
}

class Logger {
public:
  static Logger &getInstance() {
    static Logger instance;
    return instance;
  }
  static void write(const std::string message) {
    getInstance().write_worker(message);
  }
  static uint64_t nanos() { return getInstance().nanos_worker(); }

private:
  Logger() : start_(callseq::nanos()) {
    std::cout << "callseq logs to " << CALLSEQ_OUTPUT << std::endl;
    log_.open(CALLSEQ_OUTPUT);
  }
  ~Logger() { log_.close(); }
  Logger(Logger const &) = delete;
  void operator=(Logger const &) = delete;

  std::mutex write_mutex_;
  void write_worker(const std::string message) {
    std::lock_guard<std::mutex> write_lock(write_mutex_);
    log_ << message << std::endl;
  }
  uint64_t nanos_worker() { return callseq::nanos() - start_; }
  std::ofstream log_;
  uint64_t start_;
};

template <typename T> class SitePoint {

public:
  SitePoint(const size_t calling_site_id, const T *caller_this,
            const char *caller_signature, const char *caller_file,
            const int lineno)
      : calling_site_id_(calling_site_id),
        this_(reinterpret_cast<std::uintptr_t>((void *)caller_this)) {
    auto start = Logger::nanos();
    // <>|<site id>|<object this value or 0x0>|<timestamp in seconds with ns
    // resolution>|<thread id hash>|<caller signature>|<caller file
    // location#lineno>
    std::stringstream stream;
    stream << "{" << calling_site_id_;
    stream << "|0x" << std::hex << this_;
    stream << "|" << std::dec << start / 1000000000 << "."
           << start % 1000000000;
    stream << "|0x" << std::hex << thread_id();
    stream << "|" << caller_signature;
    stream << "|" << caller_file << "#" << std::dec << lineno;
    Logger::write(stream.str());
  }

  ~SitePoint() {
    auto end = Logger::nanos();
    // <site id>|<instance address>|<timestamp in seconds with ns resolution>
    std::stringstream stream;
    stream << "}" << calling_site_id_;
    stream << "|0x" << std::hex << this_;
    stream << "|" << std::dec << end / 1000000000 << "." << end % 1000000000;
    stream << "|0x" << std::hex << thread_id();
    Logger::write(stream.str());
  }

private:
  size_t calling_site_id_;
  uintptr_t this_;
};

#endif

} // namespace callseq
