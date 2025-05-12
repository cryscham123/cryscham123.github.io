msg= """q48a01	q48a02	q48a03	q48a04	q48a05	q48a06	q48a07	q48a08	q48a09	q48a10	q48a11	q48a12	q48b1	q48b2	q48b3	q48c1	q48c2	q48c3	q48c4	q48c5	q48c6	q48c7	q48c8	q48c9	q48d1	q48d2	q48d3	q48d4	q48d5	q48d6	q48d7	q49a01	q49a02	q49a03	q49a04	q49a05	q49a06	q49a07	q49a08	q49a09	q49a10	q49a11	q49a12	q49a13	q49a14	q49a15	q49a16	q49a17	q50"""

msg = msg.split('	')
for c in msg:
    print(f"'{c}'", end=',')
