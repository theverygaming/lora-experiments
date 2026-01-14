#pragma once

void logging_log(int level, const char *fmt, ...);

#define LOG_DEBUG(fmt, ...) logging_log(4, fmt, ##__VA_ARGS__)
#define LOG_INFO(fmt, ...) logging_log(3, fmt, ##__VA_ARGS__)
#define LOG_WARNING(fmt, ...) logging_log(2, fmt, ##__VA_ARGS__)
#define LOG_ERROR(fmt, ...) logging_log(1, fmt, ##__VA_ARGS__)
