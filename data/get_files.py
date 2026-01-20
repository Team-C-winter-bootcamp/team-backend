import os
import json

for root, dirs, files in os.walk("1.데이터"):
    for file in files:
        if file.endswith(".json"):
            print(os.path.join(root, file))
