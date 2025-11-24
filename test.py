log = [['right', 2], ['forward', 5], ['left', 3], ['forward', 4]]
new_log = []
temp = []
for e in log:
    if e[0] == 'left':
        temp.append(['right', e[1]])
    elif e[0] == 'right':
        temp.append(['left', e[1]])
    else:
        temp.append(e)
for i in range(len(temp), 0, -1):
    new_log.append(temp[i-1])

print(log)
print(new_log)