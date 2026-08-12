#!/usr/bin/env python3
import sys


def digital_root(n: int) -> int:
    if n == 0:
        return 0
    return 1 + (n - 1) % 9


def main() -> None:
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    total = 0
    for ch in text:
        if ch.isalpha():
            total += ord(ch.lower()) - ord("a") + 1
        elif ch.isdigit():
            total += int(ch)
    print(f"{total} {digital_root(total)}")


if __name__ == "__main__":
    main()
