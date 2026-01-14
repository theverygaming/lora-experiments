#include <logging.h>
#include <serialcon.h>
#include <stdarg.h>
#include <stdio.h>

static const char *level_lookup[4] = {
    "ERROR",
    "WARNING",
    "INFO",
    "DEBUG"
};

void logging_log(int level, const char *fmt, ...) {
    char buf[256];

    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    serialcon_print("(");
    serialcon_print(level_lookup[level-1]);
    serialcon_print("): ");
    serialcon_println(buf);
}
