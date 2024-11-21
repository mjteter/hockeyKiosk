

x = {
     'SEA': {'wins': 9, 'losses': 9, 'points': 18, 'pointPctg': 0.48},
     'EDM': {'wins': 10, 'losses': 8, 'points': 22, 'pointPctg': 0.55},
     'COL': {'wins': 10, 'losses': 9, 'points': 20, 'pointPctg': 0.526},
     'VAN': {'wins': 9, 'losses': 6, 'points': 21, 'pointPctg': 0.5833},
     'ANA': {'wins': 8, 'losses': 8, 'points': 18, 'pointPctg': 0.5}
     }
# x = {1: 2, 3: 4, 4: 3, 2: 1, 0: 0}
# dict(sorted(x.items(), key=lambda item: item[1]))

y = dict(sorted(x.items(), key=lambda item: (-item[1]['points'], -item[1]['pointPctg'])))

for tm in y.keys():
    print(tm, y[tm])
