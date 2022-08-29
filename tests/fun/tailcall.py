def loop(x : int, y : int) -> int:
    if x > 0:
        return loop (x - 1, y + 1)
    else:
        return y

print(loop(input_int(), 0))

