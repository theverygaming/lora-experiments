#pragma once
#include <stddef.h>

template<class T, size_t len> class Queue {
public:
    bool full() {
        return ((head + 1) % len) == tail;
    }

    bool empty() {
        return head == tail;
    }

    T* writeNext() {
        if (full()) {
            return nullptr;
        }
        T *p = &data[head];
        head = (head + 1) % len;
        return p;
    }

    T* readNext() {
        if (empty()) {
            return nullptr;
        }
        return &data[tail];
    }

    void readNextDone() {
        tail = (tail + 1) % len;
    }

private:
    size_t head = 0; // next write
    size_t tail = 0; // next read
    T data[len];
};
