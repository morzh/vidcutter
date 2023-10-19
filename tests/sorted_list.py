from sortedcontainers import SortedList


sl = SortedList(['e', 'f', 'c', 'd', 'b'])
print(sl)

index = sl.bisect_right('a')
print(index)

sl.add('a')
print(sl)

