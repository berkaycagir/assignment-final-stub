#in=5
#in=10
#golden=2
i = input_int()
j = input_int()
k = 0
while i < j:
    i = i + 1
    if i % 2 == 0:
        continue
    k = k + 1
print(k)

