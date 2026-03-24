#temp
import re

f = open('AGAP2\\ressources\\lang.txt', encoding="utf-8")

all = []

try :
    lines = f.readlines()
except Exception as e :
    print(e)
for line in lines :
    if re.findall("\d+\.", line) :
        if len(line) != 0 :
            all.append(line[line.find(".")+2:])
print(all)        

